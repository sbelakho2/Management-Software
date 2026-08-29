//! Realtime store (item 63): a WebSocket subscription that pushes
//! operational events (Andon, production, quality) into reactive signals —
//! nobody must refresh the Andon page to learn that the process stopped.
//!
//! Protocol (backend `/api/v1/ws`): the client joins the tenant room with
//! `{"type":"join","room":"tenant:{id}"}` and receives `RealtimeEnvelope`
//! JSON (event_type + payload). The envelope's `event_type` selects the
//! reactive channel.

use leptos::prelude::*;
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

/// The latest Andon event pushed over the socket.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct AndonPush {
    pub andon_id: Option<String>,
    pub severity: Option<String>,
    pub issue_type: Option<String>,
    pub status: Option<String>,
}

/// Reactive realtime state shared through the component tree.
#[derive(Debug, Clone)]
pub struct RealtimeStore {
    /// Connection state (visible in the chrome: CONNECTED / RECONNECTING).
    pub connected: RwSignal<bool>,
    /// The most recent Andon event pushed by the server.
    pub last_andon: RwSignal<Option<AndonPush>>,
    /// Total Andon pushes received this session.
    pub andon_push_count: RwSignal<u32>,
    /// Last error text (for an explicit status line, never silent).
    pub error: RwSignal<Option<String>>,
}

impl Default for RealtimeStore {
    fn default() -> Self {
        Self::new()
    }
}

impl RealtimeStore {
    pub fn new() -> Self {
        Self {
            connected: RwSignal::new(false),
            last_andon: RwSignal::new(None),
            andon_push_count: RwSignal::new(0),
            error: RwSignal::new(None),
        }
    }

    /// Connect to `/api/v1/ws` and join the tenant room. The bearer token
    /// travels in the query string (the browser WebSocket API cannot set
    /// headers); the backend validates it on connect.
    pub fn connect(&self, api_base: &str, tenant_id: &str, token: &str) {
        let ws_url = format!(
            "{}?token={}",
            api_base
                .replace("http://", "ws://")
                .replace("https://", "wss://")
                .trim_end_matches('/'),
            token
        );
        let store = self.clone();
        let tenant_id = tenant_id.to_string();
        leptos::task::spawn_local(async move {
            let Ok(ws) = web_sys::WebSocket::new(&ws_url) else {
                store
                    .error
                    .set(Some("WebSocket unsupported in this browser".to_string()));
                return;
            };
            ws.set_binary_type(web_sys::BinaryType::Arraybuffer);

            // onopen: mark connected and join the tenant room.
            {
                let store = store.clone();
                let tenant_id = tenant_id.clone();
                let ws_join = ws.clone();
                let onopen = Closure::<dyn FnMut()>::new(move || {
                    store.connected.set(true);
                    store.error.set(None);
                    let join = serde_json::json!({
                        "type": "join",
                        "room": format!("tenant:{tenant_id}"),
                    });
                    let _ = ws_join.send_with_str(&join.to_string());
                });
                ws.set_onopen(Some(onopen.as_ref().unchecked_ref()));
                onopen.forget();
            }

            // onmessage: parse the RealtimeEnvelope; route Andon events.
            {
                let store = store.clone();
                let onmessage = Closure::<dyn FnMut(web_sys::MessageEvent)>::new(
                    move |ev: web_sys::MessageEvent| {
                        let data = ev.data();
                        let text = match data.dyn_into::<js_sys::JsString>() {
                            Ok(s) => s.as_string().unwrap_or_default(),
                            Err(data) => {
                                if let Ok(bytes) = data.dyn_into::<js_sys::ArrayBuffer>() {
                                    let u8s = js_sys::Uint8Array::new(&bytes);
                                    String::from_utf8_lossy(&u8s.to_vec()).to_string()
                                } else {
                                    String::new()
                                }
                            }
                        };
                        let Ok(envelope) = serde_json::from_str::<serde_json::Value>(&text) else {
                            return;
                        };
                        let event_type = envelope
                            .get("event_type")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        if event_type.contains("andon") {
                            let payload = envelope.get("payload").cloned().unwrap_or_default();
                            if let Ok(push) = serde_json::from_value::<AndonPush>(payload) {
                                store.last_andon.set(Some(push));
                                store.andon_push_count.update(|c| *c += 1);
                            }
                        }
                    },
                );
                ws.set_onmessage(Some(onmessage.as_ref().unchecked_ref()));
                onmessage.forget();
            }

            // onclose: mark disconnected with an explicit state (item 63:
            // a dead socket must never look like a quiet healthy system).
            {
                let store = store.clone();
                let onclose = Closure::<dyn FnMut()>::new(move || {
                    store.connected.set(false);
                    store.error.set(Some(
                        "Realtime disconnected — events may be stale".to_string(),
                    ));
                });
                ws.set_onclose(Some(onclose.as_ref().unchecked_ref()));
                onclose.forget();
            }
        });
    }
}
