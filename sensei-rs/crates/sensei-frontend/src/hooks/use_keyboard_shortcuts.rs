//! Hook for registering global keyboard shortcuts.
//!
//! # Usage
//! ```ignore
//! use_keyboard_shortcuts(vec![
//!     Shortcut {
//!         key: "k".into(),
//!         ctrl: true, alt: false, shift: false,
//!         description: "Open search".into(),
//!         action: Arc::new(|| { /* open search */ }),
//!     },
//! ]);
//! ```

use leptos::ev::keydown;
use leptos::prelude::*;
use leptos::web_sys::KeyboardEvent;
use std::sync::Arc;

/// A keyboard shortcut definition.
pub struct Shortcut {
    /// The key identifier (e.g. `"k"`, `"Escape"`, `"Enter"`).
    pub key: String,
    /// Whether the Ctrl (or Cmd on macOS) modifier is required.
    pub ctrl: bool,
    /// Whether the Alt modifier is required.
    pub alt: bool,
    /// Whether the Shift modifier is required.
    pub shift: bool,
    /// Human-readable description of the shortcut.
    pub description: String,
    /// The action to perform when the shortcut is triggered.
    pub action: Arc<dyn Fn() + Send + Sync>,
}

/// Register global keyboard shortcuts by attaching a `keydown` event listener
/// to the `window` object. The shortcuts are active for the lifetime of the
/// component (the listener is removed on cleanup).
pub fn use_keyboard_shortcuts(shortcuts: Vec<Shortcut>) {
    let shortcuts = shortcuts
        .into_iter()
        .map(|s| {
            let key = s.key.to_lowercase();
            ShortcutData {
                key,
                ctrl: s.ctrl,
                alt: s.alt,
                shift: s.shift,
                description: s.description,
                action: s.action,
            }
        })
        .collect::<Vec<_>>();

    // Use leptos's window_event_listener which handles cleanup automatically
    // and doesn't require the handler to be Send + Sync.
    window_event_listener(keydown, move |event: KeyboardEvent| {
        let ctrl = event.ctrl_key() || event.meta_key(); // Ctrl or Cmd
        let alt = event.alt_key();
        let shift = event.shift_key();
        let key = event.key().to_lowercase();

        for shortcut in &shortcuts {
            if shortcut.key == key
                && shortcut.ctrl == ctrl
                && shortcut.alt == alt
                && shortcut.shift == shift
            {
                event.prevent_default();
                (shortcut.action)();
                return;
            }
        }
    });
}

struct ShortcutData {
    key: String,
    ctrl: bool,
    alt: bool,
    shift: bool,
    #[allow(dead_code)]
    description: String,
    action: Arc<dyn Fn() + Send + Sync>,
}
