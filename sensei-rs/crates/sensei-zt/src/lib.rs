//! # sensei-zt — Zig FFI Bridge
//!
//! Provides high-performance primitives backed by Zig when available,
//! with pure-Rust fallbacks otherwise.
//!
//! ## Modules
//!
//! * [`simd`] — SIMD-accelerated numerical routines.
//! * [`allocator`] — Custom memory allocators (arena, pool).
//! * [`ipc`] — Shared-memory IPC channels.
//! * [`onnx`] — ONNX Runtime bindings and tensor operations.
//! * [`llm`] — LLaMA/GGML inference engine.
//! * [`image`] — SIMD-accelerated image processing.
//! * [`stats`] — SPC statistics with SIMD accumulation.

pub mod allocator;
pub mod image;
pub mod ipc;
pub mod llm;
pub mod onnx;
pub mod simd;
pub mod stats;

// ──────────────────────────────────────────────
// FFI declarations — linked from `zig/libsensei_zig.a`
// ──────────────────────────────────────────────
//
// Each submodule declares and uses only the exports it needs
// (simd.rs, onnx.rs, llm.rs). This crate root only declares the
// version export it actually calls.

#[cfg(not(no_zig))]
extern "C" {
    fn sensei_zig_version() -> *const std::os::raw::c_char;
}

/// Return the version string from the Zig library, or a fallback.
pub fn zig_version() -> &'static str {
    #[cfg(not(no_zig))]
    {
        unsafe {
            let ptr = sensei_zig_version();
            if ptr.is_null() {
                return "unknown (null)";
            }
            match std::ffi::CStr::from_ptr(ptr).to_str() {
                Ok(s) => s,
                Err(_) => "unknown (invalid utf8)",
            }
        }
    }
    #[cfg(no_zig)]
    {
        "pure-rust (zig not available)"
    }
}
