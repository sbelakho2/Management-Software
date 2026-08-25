//! WebSocket and Server-Sent Events (SSE) route handlers.
//!
//! Provides real-time communication endpoints:
//! - `GET /api/v1/ws` — WebSocket upgrade with JWT auth via `?token=` query param
//! - `GET /api/v1/sse` — SSE stream with JWT auth via `?token=` query param

use std::convert::Infallible;
use std::time::Duration;

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    response::{
        sse::{Event, Sse},
        IntoResponse,
    },
};
use futures::stream::{select, StreamExt};
use futures::SinkExt;
use serde::Deserialize;
use tokio_stream::wrappers::{errors::BroadcastStreamRecvError, BroadcastStream, IntervalStream};
use tracing::{info, warn};
use uuid::Uuid;

use crate::state::AppState;

/// Query-string parameters for WebSocket and SSE endpoints.
#[derive(Debug, Deserialize)]
pub struct TokenQuery {
    /// JWT access token for authentication.
    pub token: String,
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

/// Handle WebSocket upgrade requests.
///
/// Authentication is performed by extracting the JWT from the `?token=` query
/// parameter (since the WebSocket API does not support custom headers in
/// browsers). On successful validation, the connection is upgraded and a
/// dedicated handler manages the lifecycle.
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Query(params): Query<TokenQuery>,
) -> impl IntoResponse {
    // Validate JWT token from query param
    let claims = match state.jwt_service.validate_access_token(&params.token) {
        Ok(c) => c,
        Err(e) => {
            warn!(error = %e, "WebSocket authentication failed");
            return (
                axum::http::StatusCode::UNAUTHORIZED,
                "Unauthorized: invalid token",
            )
                .into_response();
        }
    };

    let user_id = claims.sub;
    let tenant_id = claims.tenant_id;

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
/// 1. Registers the user connection for direct messaging.
/// 2. Joins the tenant-wide room automatically and KEEPS the receiver so
///    tenant broadcasts actually reach the client.
/// 3. Loops reading incoming messages; handles `{"type":"join","room":"..."}`
///    to dynamically join additional rooms (validated).
/// 4. Forwards user-directed and tenant messages from the broadcast channels
///    to the client, plus periodic heartbeat pings.
/// 5. On disconnect or error, cleans up all state.
async fn handle_socket(socket: WebSocket, state: AppState, user_id: Uuid, tenant_id: Uuid) {
    let ws_manager = &state.ws_manager;
    let tenant_room = format!("tenant:{tenant_id}");

    // Register the user connection for direct messages.
    let mut user_rx = ws_manager.register_connection(user_id).await;

    // Join the tenant room and KEEP the receiver — dropping it would
    // silently unsubscribe this client from tenant broadcasts.
    let mut tenant_rx = ws_manager.join_room(&tenant_room).await;

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        "WebSocket client connected"
    );

    // Split the socket into sender and receiver halves.
    let (mut ws_sender, mut ws_receiver) = socket.split();

    // Create an mpsc channel so the main loop can send messages (e.g. pongs
    // and join errors) through the ws_sender without directly owning it
    // (it's owned by the spawned task below).
    let (outgoing_tx, mut outgoing_rx) = tokio::sync::mpsc::channel::<Message>(256);

    // Spawn a task that drains the outgoing queue, the user-directed
    // broadcast channel, and the tenant broadcast channel, sending
    // everything through the WebSocket sender.
    let send_task = tokio::spawn(async move {
        loop {
            tokio::select! {
                // Outgoing messages from the main loop (e.g. pong responses).
                Some(msg) = outgoing_rx.recv() => {
                    if ws_sender.send(msg).await.is_err() {
                        break;
                    }
                }
                // User-directed messages from the broadcast channel.
                result = user_rx.recv() => {
                    match result {
                        Ok(text) => {
                            if ws_sender.send(Message::Text(text.into())).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
                // Tenant-wide messages from the broadcast channel.
                result = tenant_rx.recv() => {
                    match result {
                        Ok(text) => {
                            if ws_sender.send(Message::Text(text.into())).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
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
    ///   tenant when it exists in an entity store (unknown entities are
    ///   allowed through — they may live in a service-owned store).
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
                    Some(true) | None => Ok(()),
                    Some(false) => Err(format!("Cannot join a foreign entity's room '{room}'")),
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
                let map = $store.read().await;
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
                                    ws_manager.join_room(&room).await;
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

    // Unregister the user connection.
    ws_manager.unregister_connection(user_id).await;

    info!(
        user_id = %user_id,
        "WebSocket client fully disconnected, resources cleaned up"
    );
}

/// Handle Server-Sent Events (SSE) connections.
///
/// Authentication is performed via JWT in the `?token=` query parameter.
/// On success, the client receives an infinite SSE stream that merges:
/// - Events from the user-specific channel (`user:{user_id}`)
/// - Events from the tenant-wide channel (`tenant:{tenant_id}`)
/// - Heartbeat pings every 30 seconds to keep the connection alive
pub async fn sse_handler(
    State(state): State<AppState>,
    Query(params): Query<TokenQuery>,
) -> impl IntoResponse {
    // Validate JWT token from query param.
    let claims = match state.jwt_service.validate_access_token(&params.token) {
        Ok(c) => c,
        Err(e) => {
            warn!(error = %e, "SSE authentication failed");
            return (
                axum::http::StatusCode::UNAUTHORIZED,
                "Unauthorized: invalid token",
            )
                .into_response();
        }
    };

    let user_id = claims.sub;
    let tenant_id = claims.tenant_id;

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
