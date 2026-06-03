//! API-level service abstractions and managers.
//!
//! Provides real-time communication infrastructure including WebSocket
//! connection management and Server-Sent Events (SSE) broadcasting.

pub mod sse;
pub mod ws;

pub use sse::SseManager;
pub use ws::WebSocketManager;
