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
use std::collections::HashMap;

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
#[allow(dead_code)]
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

    /// Software fallback chatbot (always available).
    fn sensei_llm_fallback_chat(prompt: *const u8, prompt_len: usize) -> *mut u8;
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
#[allow(dead_code)]
pub struct LlamaRunner {
    /// Opaque handle to the Zig-allocated LlamaRunner (null when using fallback).
    handle: LlamaHandle,
    /// Configuration.
    config: LlamaConfig,
    /// Whether this runner is backed by Zig.
    has_zig: bool,
    /// Tokenizer vocabulary (for fallback).
    vocab: HashMap<String, u32>,
    /// Id-to-token mapping (for fallback).
    id_to_token: HashMap<u32, String>,
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
                    config,
                    has_zig: true,
                    vocab: HashMap::new(),
                    id_to_token: HashMap::new(),
                });
            }
        }

        // Fallback: create a pure-Rust runner with minimal vocab
        let mut vocab = HashMap::new();
        let mut id_to_token = HashMap::new();

        // Add special tokens
        vocab.insert("<PAD>".to_string(), 0);
        id_to_token.insert(0, "<PAD>".to_string());
        vocab.insert("<BOS>".to_string(), 1);
        id_to_token.insert(1, "<BOS>".to_string());
        vocab.insert("<EOS>".to_string(), 2);
        id_to_token.insert(2, "<EOS>".to_string());

        Ok(LlamaRunner {
            handle: LlamaHandle(std::ptr::null_mut()),
            config,
            has_zig: false,
            vocab,
            id_to_token,
        })
    }

    /// Generate a response to the given prompt.
    ///
    /// When backed by Zig, delegates to [`sensei_llm_generate`].
    /// Otherwise uses the pattern-matching fallback chatbot.
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
            return self.generate_zig(prompt, max_tokens, temperature, top_k, top_p);
        }

        self.generate_fallback(prompt)
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
            return Err(SenseiError::Internal("LLM generation failed".into()));
        }

        let result = unsafe { std::ffi::CStr::from_ptr(ptr as *const i8) }
            .to_str()
            .map_err(|e| SenseiError::Internal(format!("LLM output not valid UTF-8: {e}")))?
            .to_string();

        unsafe { sensei_llm_free_string(ptr) };

        Ok(result)
    }

    /// Pure-Rust fallback generation using pattern matching.
    fn generate_fallback(&self, prompt: &str) -> Result<String, SenseiError> {
        let lower = prompt.to_lowercase();
        let response = FALLBACK_RESPONSES
            .iter()
            .filter_map(|pattern| {
                let match_count = pattern
                    .keywords
                    .iter()
                    .filter(|kw| lower.contains(&kw.to_lowercase()))
                    .count();
                if match_count > 0 {
                    Some((match_count, pattern.response))
                } else {
                    None
                }
            })
            .max_by_key(|(count, _)| *count)
            .map(|(_, resp)| resp)
            .unwrap_or(DEFAULT_FALLBACK_RESPONSE);

        Ok(response.to_string())
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
// Software fallback responses
// ══════════════════════════════════════════════

struct ResponsePattern {
    keywords: &'static [&'static str],
    response: &'static str,
}

const FALLBACK_RESPONSES: &[ResponsePattern] = &[
    ResponsePattern {
        keywords: &["hello", "hi", "hey", "greetings"],
        response: "Hello! I'm Sensei AI, your manufacturing assistant. How can I help you today?",
    },
    ResponsePattern {
        keywords: &["help", "what can you do", "capabilities"],
        response: "I can help you with quality management, maintenance tracking, production monitoring, supply chain management, and continuous improvement initiatives. Try asking me about a specific topic!",
    },
    ResponsePattern {
        keywords: &["quality", "ncr", "non-conformance", "inspection"],
        response: "For quality management, I can help with non-conformance reports (NCRs), corrective actions (CAPAs), inspections, audits, and supplier quality. What specific quality topic interests you?",
    },
    ResponsePattern {
        keywords: &["maintenance", "pm", "preventive", "equipment", "work request"],
        response: "For maintenance, I can assist with work requests, preventive maintenance schedules, equipment tracking, and warranty management. What maintenance task can I help with?",
    },
    ResponsePattern {
        keywords: &["production", "manufacturing", "work order", "schedule"],
        response: "For production, I can help with work orders, production scheduling, bill of materials (BOM), and material requirements planning (MRP). What production topic would you like to explore?",
    },
    ResponsePattern {
        keywords: &["supply chain", "inventory", "purchase order", "rfq", "supplier"],
        response: "For supply chain, I can assist with RFQs, purchase orders, inventory management, sales orders, and supplier evaluation. How can I help with your supply chain needs?",
    },
    ResponsePattern {
        keywords: &["finance", "invoice", "payment", "budget", "accounting"],
        response: "For finance, I can help with invoices, payments, budgets, journal entries, and cost rollups. What financial topic would you like to discuss?",
    },
    ResponsePattern {
        keywords: &["hr", "employee", "training", "leave", "timecard"],
        response: "For HR, I can assist with employee management, training records, leave requests, timecards, and performance reviews. How can I help with HR matters?",
    },
    ResponsePattern {
        keywords: &["continuous improvement", "kaizen", "lean", "six sigma", "andon"],
        response: "For continuous improvement, I can help with Andon systems, A3 problem-solving, risk management, and Kaizen projects. What improvement initiative are you working on?",
    },
    ResponsePattern {
        keywords: &["safety", "lockout", "tagout", "loto", "osha"],
        response: "For safety, I can assist with lockout/tagout (LOTO) procedures, safety audits, and compliance tracking. Safety is our top priority — how can I help?",
    },
    ResponsePattern {
        keywords: &["thanks", "thank you", "appreciate"],
        response: "You're welcome! I'm here to help. Feel free to ask me anything about manufacturing operations.",
    },
    ResponsePattern {
        keywords: &["bye", "goodbye", "see you"],
        response: "Goodbye! Feel free to come back anytime you need assistance with your manufacturing operations.",
    },
];

const DEFAULT_FALLBACK_RESPONSE: &str =
    "I'm Sensei AI, your manufacturing operations assistant. I can help with quality, maintenance, production, supply chain, finance, HR, and continuous improvement topics. What would you like to know more about?";

// ══════════════════════════════════════════════
// Tests
// ══════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_llama_runner_new_fallback() {
        let config = LlamaConfig {
            dim: 4,
            n_layers: 1,
            n_heads: 2,
            n_kv_heads: 1,
            vocab_size: 10,
            max_seq_len: 8,
        };
        let weights = vec![0.0f32; 100];
        let runner = LlamaRunner::new(config, &weights);
        assert!(runner.is_ok());
    }

    #[test]
    fn test_generate_fallback_hello() {
        let config = LlamaConfig::default();
        let weights = vec![0.0f32; 100];
        let mut runner = LlamaRunner::new(config, &weights).unwrap();
        let response = runner.generate("hello", 10, 1.0, 10, 0.9).unwrap();
        assert!(response.contains("Hello!"));
    }

    #[test]
    fn test_generate_fallback_quality() {
        let config = LlamaConfig::default();
        let weights = vec![0.0f32; 100];
        let mut runner = LlamaRunner::new(config, &weights).unwrap();
        let response = runner.generate("need help with quality inspection", 10, 1.0, 10, 0.9).unwrap();
        assert!(response.contains("quality"));
    }

    #[test]
    fn test_generate_fallback_maintenance() {
        let config = LlamaConfig::default();
        let weights = vec![0.0f32; 100];
        let mut runner = LlamaRunner::new(config, &weights).unwrap();
        let response = runner.generate("maintenance work request", 10, 1.0, 10, 0.9).unwrap();
        assert!(response.contains("maintenance"));
    }

    #[test]
    fn test_generate_fallback_unknown() {
        let config = LlamaConfig::default();
        let weights = vec![0.0f32; 100];
        let mut runner = LlamaRunner::new(config, &weights).unwrap();
        let response = runner.generate("asdfghjkl", 10, 1.0, 10, 0.9).unwrap();
        assert!(response.contains("Sensei AI"));
    }

    #[test]
    fn test_generate_fallback_bye() {
        let config = LlamaConfig::default();
        let weights = vec![0.0f32; 100];
        let mut runner = LlamaRunner::new(config, &weights).unwrap();
        let response = runner.generate("goodbye", 10, 1.0, 10, 0.9).unwrap();
        assert!(response.contains("Goodbye"));
    }

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
