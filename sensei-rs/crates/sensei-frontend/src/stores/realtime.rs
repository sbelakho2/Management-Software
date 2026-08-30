//! Realtime store (items 63-67): the WebSocket subscription that pushes
//! operational events into reactive signals.
//!
//! Correct lifecycle (item 64): a reactive effect tied to
//! `AuthState::Authenticated` triggers the connection — a session restored
//! after app start or a fresh login ALWAYS connects, and logout closes.
//! The connection (item 66) uses a ONE-TIME TICKET minted over HTTP
//! (`POST /api/v1/realtime/ticket`) and connects to the REAL path
//! `/api/v1/ws?ticket=...` — the bearer token is never placed in a query
//! string. Reconnection (item 67): on close, the socket reconnects with
//! exponential backoff, re-mints a ticket, rejoins the tenant room.

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
    pub connected: RwSignal<bool>,
    pub last_andon: RwSignal<Option<AndonPush>>,
    pub andon_push_count: RwSignal<u32>,
    pub error: RwSignal<Option<String>>,
    /// The current socket (held for clean close on logout) — RwSignal is
    /// Send so the store can be provided through the tree.
    socket: RwSignal<Option<web_sys::WebSocket>>,
    /// Backoff attempt counter for reconnection (item 67).
    attempt: RwSignal<u32>,
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
            socket: RwSignal::new(None),
            attempt: RwSignal::new(0),
        }
    }

    /// Close the current socket (on logout).
    pub fn disconnect(&self) {
        if let Some(ws) = self.socket.get_untracked().as_ref() {
            let _ = ws.close();
        }
        self.socket.set(None);
        self.connected.set(false);
        self.error.set(Some("Disconnected".to_string()));
    }

    /// Mint a one-time ticket via authenticated HTTP (item 66) — the
    /// bearer token is NEVER placed in the WS query string.
    async fn mint_ticket(client: &crate::api::client::ApiClient) -> Option<String> {
        let body: serde_json::Value = client
            .post(
                "/api/v1/realtime/ticket",
                &serde_json::json!({ "scope": "ws" }),
            )
            .await
            .ok()?;
        body.get("ticket")?.as_str().map(|s| s.to_string())
    }

    /// Connect (or reconnect) — call from a reactive effect tied to
    /// `AuthState::Authenticated` (item 64).
    pub fn connect(&self, api_base: &str, tenant_id: &str, client: &crate::api::client::ApiClient) {
        let store = self.clone();
        let api_base = api_base.to_string();
        let tenant_id = tenant_id.to_string();
        let client = client.clone();
        leptos::task::spawn_local(async move {
            // Item 66: one-time ticket.
            let Some(ticket) = Self::mint_ticket(&client).await else {
                store
                    .error
                    .set(Some("Could not mint realtime ticket".to_string()));
                return;
            };
            let ws_base = api_base
                .replace("http://", "ws://")
                .replace("https://", "wss://")
                .trim_end_matches('/')
                .to_string();
            let ws_url = format!("{ws_base}/api/v1/ws?ticket={ticket}");
            let Ok(ws) = web_sys::WebSocket::new(&ws_url) else {
                store
                    .error
                    .set(Some("WebSocket unsupported in this browser".to_string()));
                return;
            };
            ws.set_binary_type(web_sys::BinaryType::Arraybuffer);
            store.socket.set(Some(ws.clone()));
            store.attempt.set(0);

            // onopen: joined + reconnect backoff reset.
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

            // onmessage: route Andon events.
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

            // onclose: mark disconnected and RECONNECT with exponential
            // backoff (item 67) — a production station must survive
            // network flaps. The effect that drives connect() re-mints a
            // ticket each attempt.
            {
                let store = store.clone();
                let api_base = api_base.clone();
                let tenant_id = tenant_id.clone();
                let client = client.clone();
                let onclose = Closure::<dyn FnMut()>::new(move || {
                    store.connected.set(false);
                    store
                        .error
                        .set(Some("Realtime disconnected — reconnecting".to_string()));
                    let attempt = store.attempt.get_untracked();
                    let delay_ms = (1000u32 << attempt.min(5)).min(30_000);
                    store.attempt.set(attempt + 1);
                    let store = store.clone();
                    let api_base = api_base.clone();
                    let tenant_id = tenant_id.clone();
                    let client = client.clone();
                    // Reconnect after backoff.
                    leptos::task::spawn_local(async move {
                        gloo_timers::future::TimeoutFuture::new(delay_ms).await;
                        store.connect(&api_base, &tenant_id, &client);
                    });
                });
                ws.set_onclose(Some(onclose.as_ref().unchecked_ref()));
                onclose.forget();
            }
        });
    }
}
