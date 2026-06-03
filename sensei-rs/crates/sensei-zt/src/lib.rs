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

#[cfg(not(no_zig))]
#[allow(dead_code)]
extern "C" {
    fn sensei_zig_version() -> *const std::os::raw::c_char;
    fn sensei_simd_f32_dot_product(a: *const f32, b: *const f32, len: usize) -> f32;
    fn sensei_simd_f32_normalize(v: *mut f32, len: usize);
    fn sensei_simd_i16_scale(v: *mut i16, len: usize, factor: f32);
    fn sensei_arena_init(capacity: usize);
    fn sensei_arena_alloc(size: usize) -> *mut u8;
    fn sensei_arena_reset();
    fn sensei_ipc_send(channel: *const std::os::raw::c_char, data: *const u8, len: usize) -> i32;
    fn sensei_ipc_recv(channel: *const std::os::raw::c_char, out: *mut u8, cap: usize) -> i32;
    fn sensei_tensor_matrix_multiply_f32(
        a: *const f32,
        b: *const f32,
        m: usize,
        n: usize,
        k: usize,
    ) -> *mut f32;
    fn sensei_tensor_relu_f32(tensor: *mut f32, len: usize);
    fn sensei_tensor_softmax_f32(tensor: *mut f32, len: usize, dim: usize);
    fn sensei_tensor_argmax_f32(tensor: *const f32, len: usize, dim: usize) -> usize;
    fn sensei_tensor_argmax_f32_dim(tensor: *const f32, len: usize, dim: usize) -> *mut usize;
    fn sensei_onnx_model_load(path: *const std::os::raw::c_char) -> *mut std::ffi::c_void;
    fn sensei_onnx_model_run(
        model: *mut std::ffi::c_void,
        input_data: *const f32,
        input_len: usize,
        output_data: *mut f32,
        output_len: usize,
    ) -> i32;
    fn sensei_onnx_model_deinit(model: *mut std::ffi::c_void);
    fn sensei_llm_init(
        config: *const std::ffi::c_void,
        weights: *const f32,
        weights_len: usize,
        tokenizer: *mut std::ffi::c_void,
    ) -> *mut std::ffi::c_void;
    fn sensei_llm_generate(
        runner: *mut std::ffi::c_void,
        prompt: *const u8,
        prompt_len: usize,
        max_tokens: usize,
        temperature: f32,
        top_k: u32,
        top_p: f32,
    ) -> *mut u8;
    fn sensei_llm_free_string(ptr: *mut u8);
    fn sensei_llm_deinit(runner: *mut std::ffi::c_void);
    fn sensei_llm_fallback_chat(prompt: *const u8, prompt_len: usize) -> *mut u8;
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
