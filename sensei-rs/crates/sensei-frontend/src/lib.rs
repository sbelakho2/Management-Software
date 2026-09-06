//! # Sensei Frontend Library
//!
//! Leptos-based frontend for the Sensei ERP system.
//! Can be compiled to WASM for browser use or used for server-side rendering.

pub mod api;
pub mod app;
pub mod components;
pub mod error_boundary;
pub mod generated;
pub mod hooks;
pub mod i18n;
pub mod pages;
pub mod pwa;
pub mod router;
pub mod state;
pub mod stores;

/// WASM entry point (Trunk builds the `cdylib` target, so the app boots
/// from a `#[wasm_bindgen(start)]` export here — a `main` in the binary
/// target is never compiled into the served bundle).
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn run() {
    console_error_panic_hook::set_once();
    let _ = console_log::init_with_level(log::Level::Debug);
    leptos::mount::mount_to_body(|| leptos::view! { <app::App /> });
}
