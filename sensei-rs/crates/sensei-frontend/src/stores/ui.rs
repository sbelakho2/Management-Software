//! Reactive UI store for global application UI state.
//!
//! Manages sidebar, theme, density, breadcrumbs, toasts, modals,
//! and global search — all through reactive signals.
//!
//! # Usage
//! ```ignore
//! let ui = provide_ui_store();
//! ui.toggle_sidebar();
//! ui.show_toast("Record saved", "success", 3000);
//! ```

use leptos::prelude::*;
use uuid::Uuid;

/// A breadcrumb trail segment.
#[derive(Debug, Clone)]
pub struct Breadcrumb {
    pub label: String,
    pub path: String,
}

/// A toast notification message.
#[derive(Debug, Clone)]
pub struct ToastMessage {
    pub id: String,
    pub message: String,
    pub level: String,
    pub duration_ms: u64,
}

/// Global reactive UI state.
///
/// Provide once at the app root via [`provide_ui_store`] and access
/// anywhere via [`use_ui_store`].
#[derive(Debug, Clone)]
pub struct UiStore {
    /// Whether the sidebar is currently open.
    pub sidebar_open: RwSignal<bool>,
    /// Active theme name (`"light"` | `"dark"`).
    pub theme: RwSignal<String>,
    /// UI density (`"normal"` | `"compact"`).
    pub density: RwSignal<String>,
    /// Current active route path.
    pub active_route: RwSignal<String>,
    /// Breadcrumb trail for navigation context.
    pub breadcrumbs: RwSignal<Vec<Breadcrumb>>,
    /// Global search query string.
    pub global_search_query: RwSignal<String>,
    /// Active toast notifications (newest last).
    pub toasts: RwSignal<Vec<ToastMessage>>,
    /// Whether a modal dialog is open.
    pub modal_open: RwSignal<bool>,
    /// Optional modal content identifier.
    pub modal_content: RwSignal<Option<String>>,
    /// Display mode (item 70): "desk" | "gemba" | "station".
    /// Station mode hides navigation and enlarges targets; gemba mode
    /// prioritizes one-handed tablet use.
    pub display_mode: RwSignal<String>,
}

impl UiStore {
    /// Create a new `UiStore` with defaults (sidebar open, light theme, normal density).
    pub fn new() -> Self {
        Self {
            sidebar_open: RwSignal::new(true),
            theme: RwSignal::new("light".to_string()),
            density: RwSignal::new("normal".to_string()),
            active_route: RwSignal::new(String::new()),
            breadcrumbs: RwSignal::new(Vec::new()),
            global_search_query: RwSignal::new(String::new()),
            toasts: RwSignal::new(Vec::new()),
            modal_open: RwSignal::new(false),
            modal_content: RwSignal::new(None),
            display_mode: RwSignal::new("desk".to_string()),
        }
    }

    /// Toggle the sidebar between open and closed.
    pub fn toggle_sidebar(&self) {
        self.sidebar_open.update(|v| *v = !*v);
    }

    /// Set the active theme.
    pub fn set_theme(&self, theme: &str) {
        self.theme.set(theme.to_string());
    }

    /// Toggle between `"normal"` and `"compact"` density.
    pub fn toggle_density(&self) {
        self.density.update(|d| {
            *d = if d.as_str() == "compact" {
                "normal".to_string()
            } else {
                "compact".to_string()
            };
        });
    }

    /// Push a breadcrumb onto the navigation trail.
    pub fn push_breadcrumb(&self, label: &str, path: &str) {
        self.breadcrumbs.update(|b| {
            b.push(Breadcrumb {
                label: label.to_string(),
                path: path.to_string(),
            });
        });
    }

    /// Pop the last breadcrumb from the navigation trail.
    pub fn pop_breadcrumb(&self) {
        self.breadcrumbs.update(|b| {
            b.pop();
        });
    }

    /// Show a toast notification.
    ///
    /// * `message` — The text to display.
    /// * `level` — Severity level (`"info"`, `"success"`, `"warning"`, `"error"`).
    /// * `duration_ms` — Auto-dismiss duration in milliseconds.
    pub fn show_toast(&self, message: &str, level: &str, duration_ms: u64) {
        let id = Uuid::new_v4().to_string();
        self.toasts.update(|t| {
            t.push(ToastMessage {
                id,
                message: message.to_string(),
                level: level.to_string(),
                duration_ms,
            });
        });
    }

    /// Dismiss a toast by its unique id.
    pub fn dismiss_toast(&self, id: &str) {
        self.toasts.update(|t| t.retain(|toast| toast.id != id));
    }

    /// Open a modal with the given content identifier.
    pub fn open_modal(&self, content: &str) {
        self.modal_content.set(Some(content.to_string()));
        self.modal_open.set(true);
    }

    /// Close the currently open modal.
    pub fn close_modal(&self) {
        self.modal_open.set(false);
        self.modal_content.set(None);
    }
}

impl Default for UiStore {
    fn default() -> Self {
        Self::new()
    }
}

/// Provide the [`UiStore`] as a reactive context (call once at app root).
pub fn provide_ui_store() -> UiStore {
    let store = UiStore::new();
    provide_context(store.clone());
    store
}

/// Access the [`UiStore`] from anywhere in the component tree.
///
/// # Panics
/// Panics if no `UiStore` has been provided via [`provide_ui_store`].
pub fn use_ui_store() -> UiStore {
    expect_context::<UiStore>()
}
