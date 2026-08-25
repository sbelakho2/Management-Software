//! Hook for responsive breakpoint detection.
//!
//! Listens to `window.resize` events and exposes reactive signals
//! for mobile, tablet, desktop, and current breakpoint.
//!
//! # Usage
//! ```ignore
//! let resp = use_responsive();
//! let is_mobile = move || resp.is_mobile.get();
//! ```

use leptos::ev::resize;
use leptos::prelude::*;
use leptos::web_sys;

/// Reactive information about the current viewport size.
#[derive(Clone)]
pub struct ResponsiveInfo {
    /// Whether the viewport width is less than 768px.
    pub is_mobile: Memo<bool>,
    /// Whether the viewport width is between 768px and 1024px.
    pub is_tablet: Memo<bool>,
    /// Whether the viewport width is greater than 1024px.
    pub is_desktop: Memo<bool>,
    /// The current viewport width in pixels.
    pub width: RwSignal<f64>,
    /// The current breakpoint name (`"sm"`, `"md"`, `"lg"`, `"xl"`).
    pub breakpoint: Memo<String>,
}

/// Create and provide a [`ResponsiveInfo`] that reacts to window resize events.
///
/// Call once at the app root. Access from anywhere using the returned value
/// or via a provided context.
pub fn provide_responsive() -> ResponsiveInfo {
    let width = RwSignal::new(get_window_width());

    let is_mobile = Memo::new(move |_| width.get() < 768.0);

    let is_tablet = Memo::new(move |_| {
        let w = width.get();
        (768.0..1024.0).contains(&w)
    });

    let is_desktop = Memo::new(move |_| width.get() >= 1024.0);

    let breakpoint = Memo::new(move |_| {
        let w = width.get();
        if w < 768.0 {
            "sm".to_string()
        } else if w < 1024.0 {
            "md".to_string()
        } else if w < 1440.0 {
            "lg".to_string()
        } else {
            "xl".to_string()
        }
    });

    let info = ResponsiveInfo {
        is_mobile,
        is_tablet,
        is_desktop,
        width,
        breakpoint,
    };

    // Attach resize listener using leptos's window_event_listener which
    // handles lifecycle (cleanup on component destroy) automatically.
    // The resize event type is web_sys::UiEvent in leptos.
    let info_clone = info.clone();
    window_event_listener(resize, move |_: web_sys::UiEvent| {
        info_clone.width.set(get_window_width());
    });

    provide_context(info.clone());
    info
}

/// Access the [`ResponsiveInfo`] from anywhere in the component tree.
///
/// # Panics
/// Panics if no `ResponsiveInfo` has been provided via [`provide_responsive`].
pub fn use_responsive() -> ResponsiveInfo {
    expect_context::<ResponsiveInfo>()
}

fn get_window_width() -> f64 {
    web_sys::window()
        .map(|w| {
            w.inner_width()
                .ok()
                .and_then(|v| v.as_f64())
                .unwrap_or(1024.0)
        })
        .unwrap_or(1024.0)
}
