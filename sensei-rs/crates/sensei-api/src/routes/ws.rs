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
    response::{sse::{Event, Sse}, IntoResponse},
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
/// 2. Joins the tenant-wide room automatically.
/// 3. Loops reading incoming messages; handles `{"type":"join","room":"..."}`
///    to dynamically join additional rooms.
/// 4. Forwards user-directed messages from the broadcast channel to the client.
/// 5. On disconnect or error, cleans up all state.
async fn handle_socket(
    socket: WebSocket,
    state: AppState,
    user_id: Uuid,
    tenant_id: Uuid,
) {
    let ws_manager = &state.ws_manager;
    let tenant_room = format!("tenant:{tenant_id}");

    // Register the user connection for direct messages.
    let mut user_rx = ws_manager.register_connection(user_id).await;

    // Automatically join the tenant room.
    let _tenant_rx = ws_manager.join_room(&tenant_room).await;

    info!(
        user_id = %user_id,
        tenant_id = %tenant_id,
        "WebSocket client connected"
    );

    // Split the socket into sender and receiver halves.
    let (mut ws_sender, mut ws_receiver) = socket.split();

    // Create an mpsc channel so the main loop can send messages (e.g. pongs)
    // through the ws_sender without directly owning it (it's owned by the
    // spawned task below).
    let (outgoing_tx, mut outgoing_rx) = tokio::sync::mpsc::channel::<Message>(256);

    // Spawn a task that drains the outgoing queue and the user-directed
    // broadcast channel, sending everything through the WebSocket sender.
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
            }
        }
    });

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
                            ws_manager.join_room(&room).await;
                            joined_rooms.push(room.clone());
                            info!(
                                user_id = %user_id,
                                room = %room,
                                "Client joined room"
                            );
                        }
                    }
                }
                // All other text messages are silently ignored by the server.
                // They can be extended to support custom message types later.
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

    // Cleanup: abort the send task.
    send_task.abort();

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
