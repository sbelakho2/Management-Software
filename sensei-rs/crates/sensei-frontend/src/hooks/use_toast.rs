//! Hook for showing toast notifications via the UI store.
//!
//! # Usage
//! ```ignore
//! let toast = use_toast();
//! toast("Record saved successfully", "success", 3000);
//! ```

use crate::stores::ui::use_ui_store;

/// Returns a closure that shows a toast notification via the global [`UiStore`].
///
/// The returned closure accepts three arguments:
/// - `message` — The toast text.
/// - `level` — Severity (`"info"`, `"success"`, `"warning"`, `"error"`).
/// - `duration_ms` — Auto-dismiss time in milliseconds.
///
/// # Panics
/// Panics if no `UiStore` has been provided via [`provide_ui_store`].
pub fn use_toast() -> impl Fn(&str, &str, u64) {
    let ui = use_ui_store();
    move |message: &str, level: &str, duration_ms: u64| {
        ui.show_toast(message, level, duration_ms);
    }
}
