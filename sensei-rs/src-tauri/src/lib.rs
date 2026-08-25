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
#[tauri::command]
async fn get_battery_level() -> BatteryInfo {
    BatteryInfo {
        level: 1.0,
        charging: true,
    }
}

/// Checks network connectivity by performing a lightweight DNS / TCP check.
#[tauri::command]
async fn check_connectivity() -> bool {
    tokio::net::TcpStream::connect("8.8.8.8:53").await.is_ok()
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
async fn get_push_token() -> String {
    #[cfg(mobile)]
    {
        // TODO: Integrate with native push notification SDK.
        // The `tauri-plugin-notification` handles local notifications;
        // for remote push, a dedicated plugin (e.g., tauri-plugin-push)
        // is needed to obtain the APNs/FCM token.
        String::new()
    }

    #[cfg(not(mobile))]
    {
        // Push notifications are not available on desktop.
        String::new()
    }
}

/// Opens the native share sheet with the provided content string.
/// On desktop we write the content to the clipboard as a fallback.
#[tauri::command]
async fn share_via_native(content: String) -> Result<(), String> {
    // Use the `clipboard` crate to copy text to the system clipboard.
    // We avoid the `arboard` crate (which Tauri's internal clipboard uses)
    // to keep dependencies minimal.
    let content_clone = content.clone();
    #[cfg(any(target_os = "macos", target_os = "linux", target_os = "windows"))]
    {
        // On desktop, copy to clipboard via a simple shell command.
        let result = std::process::Command::new("sh")
            .arg("-c")
            .arg(format!("echo {} | pbcopy", shell_escape(&content_clone)))
            .output();
        match result {
            Ok(_) => Ok(()),
            Err(e) => Err(format!("Failed to copy to clipboard: {e}")),
        }
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    {
        let _ = content;
        Ok(())
    }
}

/// Escapes a string for safe use in a shell command.
fn shell_escape(s: &str) -> String {
    // Simple backslash-escape for common shell metacharacters
    let mut escaped = String::with_capacity(s.len() + 4);
    for ch in s.chars() {
        match ch {
            '\\' | '\'' | '"' | '`' | '$' | '!' | '&' | '|' | ';' | '<' | '>' | '(' | ')' | '{'
            | '}' | '[' | ']' | '*' | '?' | '~' | ' ' | '\t' | '\n' => {
                escaped.push('\\');
                escaped.push(ch);
            }
            _ => escaped.push(ch),
        }
    }
    escaped
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
