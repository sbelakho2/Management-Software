use serde::Serialize;

pub mod mobile;

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct DeviceInfo {
    pub platform: String,
    pub arch: String,
    pub os_version: String,
    pub hostname: String,
}

#[derive(Debug, Serialize)]
pub struct BatteryInfo {
    pub level: f64,
    pub charging: bool,
}

// ---------------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------------

/// Returns device information (platform, architecture, OS version, hostname).
#[tauri::command]
fn get_device_info() -> DeviceInfo {
    DeviceInfo {
        platform: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        os_version: std::env::consts::FAMILY.to_string(),
        hostname: hostname(),
    }
}

/// Returns a simulated battery level (always 1.0 on desktop; mobile will
/// override this via native plugins).
/// Battery level for the device.
///
/// Feature-gated: without the `mobile-capabilities` feature the command is
/// unavailable and the UI must hide the battery indicator (no fabricated
/// readings are ever returned).
#[tauri::command]
async fn get_battery_level() -> Result<BatteryInfo, String> {
    Err("Battery monitoring is not enabled in this build".to_string())
}

/// Checks connectivity against the application's OWN API (a network that
/// blocks public DNS but serves the app must report online).
#[tauri::command]
async fn check_connectivity() -> bool {
    let base =
        std::env::var("SENSEI_API_BASE").unwrap_or_else(|_| "http://localhost:8080".to_string());
    match reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
    {
        Ok(client) => client
            .get(format!("{base}/health/live"))
            .send()
            .await
            .map(|r| r.status().is_success())
            .unwrap_or(false),
        Err(_) => false,
    }
}

/// Returns the push notification token for the current device.
///
/// On mobile (iOS/Android), this would integrate with the native push
/// notification SDK (APNs/FCM) via `tauri-plugin-notification` or a
/// dedicated push plugin. Until the native integration is wired in,
/// this returns an empty string to indicate no token is available.
///
/// On desktop, push notifications are not available, so this always
/// returns an empty string.
#[tauri::command]
async fn get_push_token() -> Result<String, String> {
    Err("Push notifications are not available in this build (requires a native push SDK integration)".to_string())
}

/// Opens the native share sheet with the provided content string.
/// On desktop we write the content to the clipboard as a fallback.
/// Share content: on desktop this copies to the clipboard via the `arboard`
/// crate (no shell, no per-platform shell commands); on other platforms it
/// is unsupported and reports so.
#[tauri::command]
async fn share_via_native(content: String) -> Result<(), String> {
    #[cfg(any(target_os = "macos", target_os = "linux", target_os = "windows"))]
    {
        arboard::Clipboard::new()
            .and_then(|mut cb| cb.set_text(content))
            .map_err(|e| format!("Failed to copy to clipboard: {e}"))
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    {
        let _ = content;
        Err("Native share is not supported on this platform".to_string())
    }
}

/// Placeholder for barcode scanning (requires a camera plugin on mobile).
#[tauri::command]
async fn scan_barcode() -> Result<String, String> {
    #[cfg(mobile)]
    {
        // Integrate with a barcode scanning plugin
        Err("Barcode scanner not yet initialised".into())
    }
    #[cfg(not(mobile))]
    {
        Err("Barcode scanning is only available on mobile devices".into())
    }
}

/// Placeholder for taking a photo (requires a camera plugin on mobile).
#[tauri::command]
async fn take_photo() -> Result<String, String> {
    #[cfg(mobile)]
    {
        // Integrate with a camera plugin
        Err("Camera not yet initialised".into())
    }
    #[cfg(not(mobile))]
    {
        Err("Camera is only available on mobile devices".into())
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Best-effort hostname retrieval.
fn hostname() -> String {
    std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("HOST"))
        .unwrap_or_else(|_| "unknown".into())
}

// ---------------------------------------------------------------------------
// Application entry point
// ---------------------------------------------------------------------------

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            mobile::init_mobile(app);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_device_info,
            get_battery_level,
            check_connectivity,
            get_push_token,
            share_via_native,
            scan_barcode,
            take_photo,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
