//! Mobile-specific initialisation for iOS and Android.
//!
//! This module registers platform-specific hooks that are called during
//! Tauri's `setup` phase.  On desktop builds the code is compiled as a
//! no-op so that it does not introduce any unused-dependency warnings.

// ---------------------------------------------------------------------------
// iOS / Android initialisation
// ---------------------------------------------------------------------------

#[cfg(mobile)]
pub fn init_mobile(app: &tauri::App) {
    use tauri::Manager;

    // ── Push notification registration ──────────────────────────────
    // The `tauri-plugin-notification` handles the JavaScript-side; here
    // we can hook into the native registration lifecycle if needed.
    let _ = app.handle();

    // ── Background processing ───────────────────────────────────────
    // On iOS, short-lived background tasks can be registered with
    // `BGTaskScheduler`.  On Android, `WorkManager` is the canonical
    // approach.  Both are out of scope for this initial setup but the
    // extension point is documented here.

    // ── Deep linking ────────────────────────────────────────────────
    // Deep-link handlers are registered via `tauri-plugin-deep-link`
    // when that plugin is added to the dependency list.
}

// ---------------------------------------------------------------------------
// Desktop no-op
// ---------------------------------------------------------------------------

#[cfg(not(mobile))]
pub fn init_mobile(_app: &tauri::App) {
    // No platform-specific initialisation is needed on desktop targets.
}
