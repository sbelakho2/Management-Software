//! # Sensei Frontend — WASM Entry Point
//!
//! Bootstraps the Leptos application in the browser.

#[cfg(target_arch = "wasm32")]
use leptos::mount::mount_to_body;
#[cfg(target_arch = "wasm32")]
use sensei_frontend::app::App;

#[cfg(target_arch = "wasm32")]
fn main() {
    console_error_panic_hook::set_once();
    console_log::init_with_level(log::Level::Debug).expect("Failed to init console logger");

    mount_to_body(|| {
        leptos::view! { <App /> }
    });
}

#[cfg(not(target_arch = "wasm32"))]
fn main() {
    // SSR mode would go here
    println!("sensei-frontend requires WASM target to run in browser");
}
