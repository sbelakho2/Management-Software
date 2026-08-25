//! WebSocket and Server-Sent Events (SSE) route handlers.
//!
//! Provides real-time communication endpoints:
//! - `POST /api/v1/realtime/ticket` — mint a one-time connection ticket
//!   (authenticated; scope `"ws"` or `"sse"`).
//! - `GET /api/v1/ws?ticket=...` — WebSocket upgrade, authenticated by a
//!   one-time realtime ticket (replaces the legacy `?token=` JWT).
//! - `GET /api/v1/sse?ticket=...` — SSE stream, authenticated the same way.
//!
//! Tickets are short-lived (30s) and consumed atomically on first use, so
//! a stolen ticket cannot be replayed and never authenticates a different
//! transport than the one it was minted for.

use std::convert::Infallible;
use std::time::Duration;

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    http::StatusCode,
    response::{
        sse::{Event, Sse},
        IntoResponse, Json, Response,
    },
};
use futures::stream::{select, StreamExt};
use futures::SinkExt;
use sensei_auth::middleware::AuthenticatedUser;
use serde::{Deserialize, Serialize};
use tokio_stream::wrappers::{errors::BroadcastStreamRecvError, BroadcastStream, IntervalStream};
use tracing::{info, warn};
use uuid::Uuid;

use crate::state::{AppState, REALTIME_TICKET_TTL_SECS};

/// Request body for `POST /api/v1/realtime/ticket`.
#[derive(Debug, Deserialize)]
pub struct TicketRequest {
    /// Transport scope: `"ws"` or `"sse"`.
    pub scope: String,
}

/// Response body for `POST /api/v1/realtime/ticket`.
#[derive(Debug, Serialize)]
pub struct TicketResponse {
    /// The one-time ticket value (pass it as `?ticket=` on the WS/SSE
    /// endpoints).
    pub ticket: String,
    /// Seconds until the ticket expires (see [`REALTIME_TICKET_TTL_SECS`]).
    pub expires_in: u64,
}

/// Query-string parameters for the WebSocket and SSE endpoints.
#[derive(Debug, Deserialize)]
pub struct TicketQuery {
    /// One-time realtime ticket (replaces the legacy `?token=` JWT).
    pub ticket: Uuid,
}

/// Incoming WebSocket message for dynamic room joins.
#[derive(Debug, Deserialize)]
struct RoomJoinMessage {
    /// Message type — must be `"join"`.
    #[serde(rename = "type")]
    msg_type: String,
    /// Room name to join.
    room: String,
}

/// Mint a one-time realtime connection ticket for the authenticated user.
///
/// Contract (consumed by the frontend and other clients):
///
/// ```http
/// POST /api/v1/realtime/ticket
/// Authorization: Bearer <access_token>
/// Content-Type: application/json
///
/// { "scope": "ws" }   // or "sse"
/// ```
///
/// ```http
/// 200 OK
/// { "ticket": "<uuid>", "expires_in": 30 }
/// ```
pub async fn realtime_ticket_handler(
    State(state): State<AppState>,
    user: AuthenticatedUser,
    Json(body): Json<TicketRequest>,
) -> Response {
    if body.scope != "ws" && body.scope != "sse" {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "error": "invalid_scope",
                "message": "scope must be \"ws\" or \"sse\"",
            })),
        )
            .into_response();
    }

    match state
        .realtime_tickets
        .create(user.user_id, user.tenant_id, &body.scope)
        .await
    {
        Ok(ticket) => (
            StatusCode::OK,
            Json(TicketResponse {
                ticket: ticket.ticket.to_string(),
                expires_in: REALTIME_TICKET_TTL_SECS,
            }),
        )
            .into_response(),
        Err(e) => {
            warn!(error = %e, "Failed to create realtime ticket");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({
                    "error": "internal_error",
                    "message": "Failed to create realtime ticket",
                })),
            )
                .into_response()
        }
    }
}

/// Handle WebSocket upgrade requests.
///
/// Authentication is performed by consuming a one-time realtime ticket from
/// the `?ticket=` query parameter (the WebSocket API does not support
/// custom headers in browsers). The ticket identifies the user, is scoped
/// to the `ws` transport, and is revoked on first use.
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Query(params): Query<TicketQuery>,
) -> Response {
    let (user_id, tenant_id) = match state.realtime_tickets.consume(params.ticket, "ws").await {
        Ok(Some(ids)) => ids,
        Ok(None) => {
            warn!(ticket = %params.ticket, "WebSocket ticket invalid, expired, or reused");
            return (
                StatusCode::UNAUTHORIZED,
                Json(serde_json::json!({
                    "error": "realtime_ticket_invalid",
                    "message": "Invalid, expired, or already-used realtime ticket",
                })),
            )
                .into_response();
        }
        Err(e) => {
            warn!(error = %e, "Failed to consume WebSocket ticket");
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({
                    "error": "internal_error",
                    "message": "Failed to validate realtime ticket",
                })),
            )
                .into_response();
        }
    };

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        "WebSocket upgrade initiated"
    );

    ws.on_upgrade(move |socket| handle_socket(socket, state, user_id, tenant_id))
        .into_response()
}

/// Handle an established WebSocket connection.
///
/// 1. Registers the connection (multi-tab aware) and joins the tenant-wide
///    room, KEEPING the receiver so tenant broadcasts actually reach the
///    client.
/// 2. Loops reading incoming messages; handles `{"type":"join","room":"..."}`
///    to dynamically join additional rooms (validated, fail-closed).
/// 3. Forwards user-directed, tenant, and dynamically-joined room messages
///    from the broadcast channels to the client, plus periodic heartbeat
///    pings.
/// 4. On disconnect or error, removes exactly this connection (other tabs
///    of the same user stay alive) and drops the room subscriptions.
async fn handle_socket(socket: WebSocket, state: AppState, user_id: Uuid, tenant_id: Uuid) {
    let ws_manager = &state.ws_manager;
    let tenant_room = format!("tenant:{tenant_id}");

    // Register this connection. The handle carries a connection id so
    // cleanup removes exactly this socket, never a sibling tab's.
    let handle = ws_manager.connect(user_id, tenant_id).await;
    let connection_id = handle.connection_id;
    let user_rx = handle.rx;

    // Join the tenant room and KEEP the receiver — dropping it would
    // silently unsubscribe this client from tenant broadcasts.
    let tenant_rx = ws_manager.join_room(&tenant_room).await;

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        connection_id,
        "WebSocket client connected"
    );

    // Split the socket into sender and receiver halves.
    let (mut ws_sender, mut ws_receiver) = socket.split();

    // Create an mpsc channel so the main loop can send messages (e.g. pongs
    // and join errors) through the ws_sender without directly owning it
    // (it's owned by the spawned task below).
    let (outgoing_tx, mut outgoing_rx) = tokio::sync::mpsc::channel::<Message>(256);

    // Dynamically-joined room streams are handed to the send task over this
    // channel and added to its poll set.
    let (stream_tx, mut stream_rx) = tokio::sync::mpsc::channel::<BroadcastStream<String>>(16);

    // Spawn a task that drains the outgoing queue and every subscribed
    // broadcast channel (user-directed, tenant, and joined rooms), sending
    // everything through the WebSocket sender.
    let send_task = tokio::spawn(async move {
        let mut all_streams = futures::stream::SelectAll::new();
        all_streams.push(BroadcastStream::new(user_rx));
        all_streams.push(BroadcastStream::new(tenant_rx));
        loop {
            tokio::select! {
                // Outgoing messages from the main loop (e.g. pong responses).
                Some(msg) = outgoing_rx.recv() => {
                    if ws_sender.send(msg).await.is_err() {
                        break;
                    }
                }
                // Newly joined room streams to add to the poll set.
                Some(stream) = stream_rx.recv() => {
                    all_streams.push(stream);
                }
                // Messages from any subscribed channel (user, tenant, rooms).
                Some(result) = all_streams.next() => {
                    match result {
                        Ok(text) => {
                            if ws_sender.send(Message::Text(text.into())).await.is_err() {
                                break;
                            }
                        }
                        // Lagged receivers are skipped; the connection stays
                        // alive so a slow burst does not kill the socket.
                        Err(BroadcastStreamRecvError::Lagged(_)) => {}
                    }
                }
                else => break,
            }
        }
    });

    // Heartbeat: ping the client every 30 seconds to keep the connection
    // alive and detect dead peers.
    let heartbeat_tx = outgoing_tx.clone();
    let heartbeat_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(30));
        loop {
            interval.tick().await;
            if heartbeat_tx
                .send(Message::Ping(axum::body::Bytes::new()))
                .await
                .is_err()
            {
                break;
            }
        }
    });

    /// Validate that a client may join the given room.
    ///
    /// Allowed patterns:
    /// - `tenant:{own_tenant_id}` — only your own tenant room;
    /// - `user:{own_user_id}` — only your own direct-message room;
    /// - `entity:{type}:{id}` — the entity must belong to the client's
    ///   tenant. Validation **fails closed**: entities that are unknown to
    ///   every entity store are denied, as are entities of another tenant.
    async fn validate_room(
        state: &AppState,
        room: &str,
        user_id: Uuid,
        tenant_id: Uuid,
    ) -> std::result::Result<(), String> {
        let parts: Vec<&str> = room.splitn(3, ':').collect();
        match parts.as_slice() {
            ["tenant", id] => {
                let id = id
                    .parse::<Uuid>()
                    .map_err(|_| format!("Invalid tenant room '{room}'"))?;
                if id != tenant_id {
                    return Err(format!("Cannot join another tenant's room '{room}'"));
                }
                Ok(())
            }
            ["user", id] => {
                let id = id
                    .parse::<Uuid>()
                    .map_err(|_| format!("Invalid user room '{room}'"))?;
                if id != user_id {
                    return Err(format!("Cannot join another user's room '{room}'"));
                }
                Ok(())
            }
            ["entity", _entity_type, id] => {
                // Room format is `entity:{type}:{id}`; the entity type is a
                // free-form label, so only the id is validated.
                let entity_id = id
                    .parse::<Uuid>()
                    .map_err(|_| format!("Invalid entity room '{room}'"))?;
                match entity_belongs_to_tenant(state, entity_id, tenant_id).await {
                    // Fail closed: only entities positively confirmed to
                    // belong to this tenant are joinable.
                    Some(true) => Ok(()),
                    None | Some(false) => {
                        Err(format!("Cannot join a foreign entity's room '{room}'"))
                    }
                }
            }
            _ => Err(format!("Room '{room}' is not a valid joinable room")),
        }
    }

    /// Look up an entity across the tenant-scoped entity stores and report
    /// whether it belongs to `tenant_id`. Returns `None` when the entity is
    /// not found in any store.
    async fn entity_belongs_to_tenant(
        state: &AppState,
        entity_id: Uuid,
        tenant_id: Uuid,
    ) -> Option<bool> {
        // Each store is checked only for membership + tenant ownership.
        macro_rules! check_store {
            ($store:expr) => {{
                let map = $store.read(tenant_id).await;
                if let Some(entity) = map.get(&entity_id) {
                    return Some(entity.tenant_id == tenant_id);
                }
            }};
        }
        check_store!(state.tasks);
        check_store!(state.work_centers);
        check_store!(state.production_cells);
        check_store!(state.obeya_boards);
        check_store!(state.kanban_boards);
        check_store!(state.standard_work_documents);
        check_store!(state.opportunities);
        check_store!(state.knowledge_packs);
        check_store!(state.training_courses);
        check_store!(state.ctq_characteristics);
        check_store!(state.inventory_items);
        check_store!(state.warehouses);
        check_store!(state.escalation_policies);
        check_store!(state.learning_modules);
        check_store!(state.lsw_standards);
        check_store!(state.kpi_definitions);
        check_store!(state.state_machine_instances);
        check_store!(state.notification_triggers);
        check_store!(state.saved_views);
        check_store!(state.work_packets);
        check_store!(state.cost_builds);
        None
    }

    // Track rooms the client has joined (beyond the automatic tenant room).
    let mut joined_rooms: Vec<String> = vec![tenant_room.clone()];

    // Read incoming messages from the WebSocket receiver half.
    while let Some(msg_result) = ws_receiver.next().await {
        match msg_result {
            Ok(Message::Text(text)) => {
                // Try to parse as a room-join command.
                if let Ok(join_msg) = serde_json::from_str::<RoomJoinMessage>(&text) {
                    if join_msg.msg_type == "join" {
                        let room = join_msg.room;
                        if !joined_rooms.contains(&room) {
                            match validate_room(&state, &room, user_id, tenant_id).await {
                                Ok(()) => {
                                    // Subscribe and keep the receiver in the
                                    // send task's poll set — discarding it
                                    // (as before) silently dropped every
                                    // message for this room.
                                    let rx = ws_manager.join_room(&room).await;
                                    if stream_tx.send(BroadcastStream::new(rx)).await.is_err() {
                                        break;
                                    }
                                    joined_rooms.push(room.clone());
                                    info!(
                                        user_id = %user_id,
                                        room = %room,
                                        "Client joined room"
                                    );
                                }
                                Err(err) => {
                                    warn!(user_id = %user_id, room = %room, error = %err, "Room join rejected");
                                    let _ = outgoing_tx
                                        .send(Message::Text(
                                            format!(
                                                "{{ \"type\": \"error\", \"message\": {err:?} }}"
                                            )
                                            .into(),
                                        ))
                                        .await;
                                }
                            }
                        }
                    }
                }
                // All other text messages are silently ignored by the server.
            }
            Ok(Message::Close(_)) => {
                info!(user_id = %user_id, "WebSocket client disconnected (close frame)");
                break;
            }
            Ok(Message::Ping(data)) => {
                // Forward pong response through the outgoing channel.
                if outgoing_tx.send(Message::Pong(data)).await.is_err() {
                    break;
                }
            }
            Ok(Message::Pong(_)) => {
                // Ignore pong responses.
            }
            Ok(Message::Binary(_)) => {
                // Binary messages are not supported; silently ignore.
            }
            Err(e) => {
                warn!(
                    user_id = %user_id,
                    error = %e,
                    "WebSocket receive error"
                );
                break;
            }
        }
    }

    // Cleanup: abort the send task and the heartbeat.
    send_task.abort();
    heartbeat_task.abort();

    // Unregister exactly this connection; sibling tabs of the same user
    // remain connected.
    ws_manager.disconnect(connection_id).await;

    // Drop our room subscriptions (empty rooms are also swept lazily).
    for room in joined_rooms {
        ws_manager.leave_room(&room).await;
    }

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        connection_id,
        "WebSocket client fully disconnected, resources cleaned up"
    );
}

/// Handle Server-Sent Events (SSE) connections.
///
/// Authentication is performed by consuming a one-time realtime ticket from
/// the `?ticket=` query parameter, scoped to the `sse` transport. On
/// success, the client receives an infinite SSE stream that merges:
/// - Events from the user-specific channel (`user:{user_id}`)
/// - Events from the tenant-wide channel (`tenant:{tenant_id}`)
/// - Heartbeat pings every 30 seconds to keep the connection alive
pub async fn sse_handler(
    State(state): State<AppState>,
    Query(params): Query<TicketQuery>,
) -> Response {
    let (user_id, tenant_id) = match state.realtime_tickets.consume(params.ticket, "sse").await {
        Ok(Some(ids)) => ids,
        Ok(None) => {
            warn!(ticket = %params.ticket, "SSE ticket invalid, expired, or reused");
            return (
                StatusCode::UNAUTHORIZED,
                Json(serde_json::json!({
                    "error": "realtime_ticket_invalid",
                    "message": "Invalid, expired, or already-used realtime ticket",
                })),
            )
                .into_response();
        }
        Err(e) => {
            warn!(error = %e, "Failed to consume SSE ticket");
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({
                    "error": "internal_error",
                    "message": "Failed to validate realtime ticket",
                })),
            )
                .into_response();
        }
    };

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        "SSE client connected"
    );

    let sse_manager = &state.sse_manager;
    let user_channel = format!("user:{user_id}");
    let tenant_channel = format!("tenant:{tenant_id}");

    // Subscribe to user-specific and tenant-wide channels.
    let user_rx = sse_manager.subscribe(&user_channel).await;
    let tenant_rx = sse_manager.subscribe(&tenant_channel).await;

    // Convert broadcast receivers to streams.
    let user_stream = BroadcastStream::new(user_rx).filter_map(|result| async {
        match result {
            Ok(msg) => Some(Ok::<_, Infallible>(Event::default().data(msg))),
            Err(BroadcastStreamRecvError::Lagged(n)) => {
                warn!(skipped = %n, "SSE user channel lagged");
                None
            }
        }
    });

    let tenant_stream = BroadcastStream::new(tenant_rx).filter_map(|result| async {
        match result {
            Ok(msg) => Some(Ok::<_, Infallible>(Event::default().data(msg))),
            Err(BroadcastStreamRecvError::Lagged(n)) => {
                warn!(skipped = %n, "SSE tenant channel lagged");
                None
            }
        }
    });

    // Heartbeat every 30 seconds to keep the connection alive.
    let heartbeat = IntervalStream::new(tokio::time::interval(Duration::from_secs(30)))
        .map(|_| Ok(Event::default().event("heartbeat").data("ping")));

    // Merge all three streams into one.
    let stream = select(select(user_stream, tenant_stream), heartbeat);

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        "SSE stream established"
    );

    Sse::new(stream).into_response()
}
