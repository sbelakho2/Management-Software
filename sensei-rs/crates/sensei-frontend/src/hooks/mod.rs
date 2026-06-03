//! Reactive hooks for common application patterns.
//!
//! Provides Leptos hooks for keyboard shortcuts, toast notifications,
//! responsive breakpoints, and i18n access.

pub mod use_keyboard_shortcuts;
pub mod use_responsive;
pub mod use_toast;

pub use use_keyboard_shortcuts::*;
pub use use_responsive::*;
pub use use_toast::*;
