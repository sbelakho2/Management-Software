//! LLaMA/GGML Inference bridge.
//!
//! Provides Rust-safe wrappers around the Zig LLM inference engine
//! ([`llm.zig`](../../zig/src/llm.zig)), with a pure-Rust fallback
//! that implements a hardcoded pattern-matching chatbot.
//!
//! ## Architecture
//!
//! - When `no_zig` is **not** set (default), delegates to Zig FFI
//!   ([`sensei_llm_*`](../../zig/src/main.zig) exports).
//! - When `no_zig` **is** set, pure-Rust fallback implementations are used.

use sensei_core::error::SenseiError;

// ──────────────────────────────────────────────
// Safe pointer wrapper for Send/Sync
// ──────────────────────────────────────────────

/// Wrapper around a raw `*mut c_void` handle that explicitly implements
/// [`Send`] and [`Sync`].
///
/// The underlying Zig inference engine is designed to be called from a
/// single thread at a time, with external synchronisation (e.g. via
/// [`Mutex`]). This wrapper documents and enforces that contract.
#[repr(transparent)]
pub(crate) struct LlamaHandle(pub *mut std::ffi::c_void);

// SAFETY: The handle is only accessed under a Mutex in LlamaRunner,
// ensuring single-threaded access. The Zig engine itself is stateless
// regarding thread-local storage.
unsafe impl Send for LlamaHandle {}
unsafe impl Sync for LlamaHandle {}

// ──────────────────────────────────────────────
// Zig FFI declarations
// ──────────────────────────────────────────────

#[cfg(not(no_zig))]
extern "C" {
    /// Initialise the LLaMA runner.
    /// Returns an opaque handle, or null on failure.
    fn sensei_llm_init(
        config: *const std::ffi::c_void,
        weights: *const f32,
        weights_len: usize,
        tokenizer: *mut std::ffi::c_void,
    ) -> *mut std::ffi::c_void;

    /// Generate a response.
    /// Returns a pointer to a null-terminated string, or null on error.
    fn sensei_llm_generate(
        runner: *mut std::ffi::c_void,
        prompt: *const u8,
        prompt_len: usize,
        max_tokens: usize,
        temperature: f32,
        top_k: u32,
        top_p: f32,
    ) -> *mut u8;

    /// Free a string returned by `sensei_llm_generate`.
    fn sensei_llm_free_string(ptr: *mut u8);

    /// Destroy a LLaMA runner.
    fn sensei_llm_deinit(runner: *mut std::ffi::c_void);

    /// Whether the runner holds real (non-randomly-initialised) model weights.
    fn sensei_llm_has_weights(runner: *mut std::ffi::c_void) -> bool;
}

// ══════════════════════════════════════════════
// Configuration
// ══════════════════════════════════════════════

/// Configuration parameters for a LLaMA model.
#[repr(C)]
#[derive(Debug, Clone)]
pub struct LlamaConfig {
    /// Embedding dimension (e.g., 4096).
    pub dim: usize,
    /// Number of transformer layers.
    pub n_layers: usize,
    /// Number of attention heads.
    pub n_heads: usize,
    /// Number of key/value heads (for GQA).
    pub n_kv_heads: usize,
    /// Vocabulary size.
    pub vocab_size: usize,
    /// Maximum sequence length.
    pub max_seq_len: usize,
}

impl Default for LlamaConfig {
    fn default() -> Self {
        Self {
            dim: 4096,
            n_layers: 32,
            n_heads: 32,
            n_kv_heads: 8,
            vocab_size: 32000,
            max_seq_len: 2048,
        }
    }
}

// ══════════════════════════════════════════════
// LLaMA Runner
// ══════════════════════════════════════════════

/// A LLaMA model runner, backed by Zig FFI or pure-Rust fallback.
pub struct LlamaRunner {
    /// Opaque handle to the Zig-allocated LlamaRunner (null when using fallback).
    handle: LlamaHandle,
    /// Whether this runner is backed by Zig.
    has_zig: bool,
}

impl LlamaRunner {
    /// Create a new [`LlamaRunner`] with the given configuration and weights.
    ///
    /// When the Zig library is linked, delegates to
    /// [`sensei_llm_init`]. When not, or when initialisation fails,
    /// returns a software fallback runner.
    pub fn new(config: LlamaConfig, weights: &[f32]) -> Result<Self, SenseiError> {
        #[cfg(not(no_zig))]
        {
            // Build a minimal tokenizer on the Zig side
            // For simplicity, we pass a null tokenizer and let the fallback handle it
            let handle = unsafe {
                sensei_llm_init(
                    &config as *const LlamaConfig as *const std::ffi::c_void,
                    weights.as_ptr(),
                    weights.len(),
                    std::ptr::null_mut(),
                )
            };

            if !handle.is_null() {
                return Ok(LlamaRunner {
                    handle: LlamaHandle(handle),
                    has_zig: true,
                });
            }
        }

        // Fallback: create a pure-Rust runner with minimal vocab
        Ok(LlamaRunner {
            handle: LlamaHandle(std::ptr::null_mut()),
            has_zig: false,
        })
    }

    /// Generate a response to the given prompt.
    ///
    /// Backed by Zig: delegates to [`sensei_llm_generate`] once real model
    /// weights are loaded. Without weights (or in a `SENSEI_NO_ZIG` build)
    /// generation fails with a clear error — fabricated pattern-matched
    /// answers are never presented as AI output.
    pub fn generate(
        &mut self,
        prompt: &str,
        max_tokens: usize,
        temperature: f32,
        top_k: u32,
        top_p: f32,
    ) -> Result<String, SenseiError> {
        #[cfg(not(no_zig))]
        if self.has_zig {
            if !self.has_weights() {
                return Err(SenseiError::Internal(
                    "The AI model is not loaded — load model weights to enable AI generation."
                        .to_string(),
                ));
            }
            return self.generate_zig(prompt, max_tokens, temperature, top_k, top_p);
        }

        Err(SenseiError::Internal(
            "This build does not include the Zig AI runtime (SENSEI_NO_ZIG); AI generation is unavailable."
                .to_string(),
        ))
    }

    /// Whether the Zig runner holds real (non-random) model weights.
    #[cfg(not(no_zig))]
    fn has_weights(&self) -> bool {
        if self.handle.0.is_null() {
            return false;
        }
        unsafe { sensei_llm_has_weights(self.handle.0) }
    }

    /// Zig-backed generation.
    #[cfg(not(no_zig))]
    fn generate_zig(
        &self,
        prompt: &str,
        max_tokens: usize,
        temperature: f32,
        top_k: u32,
        top_p: f32,
    ) -> Result<String, SenseiError> {
        let prompt_bytes = prompt.as_bytes();
        let ptr = unsafe {
            sensei_llm_generate(
                self.handle.0,
                prompt_bytes.as_ptr(),
                prompt_bytes.len(),
                max_tokens,
                temperature,
                top_k,
                top_p,
            )
        };

        if ptr.is_null() {
            return Err(SenseiError::Internal(
                "AI generation failed — the model weights may be missing or corrupted.".to_string(),
            ));
        }

        let result = unsafe { std::ffi::CStr::from_ptr(ptr as *const i8) }
            .to_str()
            .map_err(|e| SenseiError::Internal(format!("LLM output not valid UTF-8: {e}")))?
            .to_string();

        unsafe { sensei_llm_free_string(ptr) };

        Ok(result)
    }
}

impl Drop for LlamaRunner {
    fn drop(&mut self) {
        #[cfg(not(no_zig))]
        {
            if self.has_zig && !self.handle.0.is_null() {
                unsafe {
                    sensei_llm_deinit(self.handle.0);
                }
            }
        }
        self.handle = LlamaHandle(std::ptr::null_mut());
        self.has_zig = false;
    }
}

// ══════════════════════════════════════════════
// Tests
// ══════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_llama_config_default() {
        let config = LlamaConfig::default();
        assert_eq!(config.dim, 4096);
        assert_eq!(config.n_layers, 32);
        assert_eq!(config.n_heads, 32);
        assert_eq!(config.n_kv_heads, 8);
        assert_eq!(config.vocab_size, 32000);
        assert_eq!(config.max_seq_len, 2048);
    }
}
