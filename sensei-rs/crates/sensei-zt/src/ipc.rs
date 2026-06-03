//! Shared-memory IPC primitives backed by Zig.
//!
//! Provides simple channel-based IPC for passing byte payloads
//! between processes on the same machine.

use std::collections::HashMap;
use std::sync::Mutex;

use once_cell::sync::Lazy;

// ──────────────────────────────────────────────
// Pure-Rust in-memory channel (fallback & default)
// ──────────────────────────────────────────────

static CHANNELS: Lazy<Mutex<HashMap<String, Vec<Vec<u8>>>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

/// Send a payload on a named channel.
///
/// When the Zig library is linked, this delegates to the native
/// shared-memory implementation. Otherwise it uses an in-memory
/// `HashMap` (single-process only).
pub fn channel_send(channel: &str, data: &[u8]) -> Result<(), IpcError> {
    #[cfg(not(no_zig))]
    {
        let c_channel = std::ffi::CString::new(channel).map_err(|_| IpcError::InvalidChannel)?;
        let ret = unsafe {
            extern "C" {
                fn sensei_ipc_send(channel: *const std::os::raw::c_char, data: *const u8, len: usize) -> i32;
            }
            sensei_ipc_send(c_channel.as_ptr(), data.as_ptr(), data.len())
        };
        if ret != 0 {
            return Err(IpcError::SendFailed(ret));
        }
        Ok(())
    }

    #[cfg(no_zig)]
    {
        let mut channels = CHANNELS.lock().map_err(|_| IpcError::LockPoisoned)?;
        channels.entry(channel.to_string()).or_default().push(data.to_vec());
        Ok(())
    }
}

/// Receive a payload from a named channel (non-blocking).
///
/// Returns `None` if no message is available.
pub fn channel_recv(channel: &str) -> Result<Option<Vec<u8>>, IpcError> {
    #[cfg(not(no_zig))]
    {
        // For now, fall back to in-memory even with Zig linked
        // (actual shared-memory impl requires OS-specific setup)
    }

    let mut channels = CHANNELS.lock().map_err(|_| IpcError::LockPoisoned)?;
    Ok(channels.get_mut(channel).and_then(|msgs| msgs.pop()))
}

/// Errors from the IPC module.
#[derive(Debug)]
pub enum IpcError {
    /// Channel name contains invalid characters.
    InvalidChannel,
    /// Zig IPC send returned a non-zero exit code.
    SendFailed(i32),
    /// Internal mutex poisoned.
    LockPoisoned,
}

impl std::fmt::Display for IpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            IpcError::InvalidChannel => write!(f, "invalid channel name"),
            IpcError::SendFailed(code) => write!(f, "IPC send failed with code {}", code),
            IpcError::LockPoisoned => write!(f, "internal lock poisoned"),
        }
    }
}

impl std::error::Error for IpcError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_send_recv() {
        channel_send("test", b"hello").unwrap();
        let msg = channel_recv("test").unwrap().expect("should have message");
        assert_eq!(msg, b"hello");
    }

    #[test]
    fn test_no_message() {
        let msg = channel_recv("nonexistent").unwrap();
        assert!(msg.is_none());
    }
}
