//! ONNX Runtime bindings and tensor operations.
//!
//! Provides SIMD-accelerated tensor operations (`matrix_multiply_f32`,
//! `relu_f32`, `softmax_f32`, `argmax_f32`) and an [`OnnxModel`]
//! struct for model inference lifecycle.
//!
//! ## Architecture
//!
//! - When `no_zig` is **not** set (default), tensor operations delegate to
//!   Zig FFI ([`sensei_tensor_*`](super::main.zig) exports).
//! - When `no_zig` **is** set, pure-Rust fallback implementations are used.
//! - ONNX Runtime model loading is not yet implemented end-to-end; the
//!   software fallback model returns a static output based on predefined
//!   matrix operations.

use sensei_core::SenseiError;

// ──────────────────────────────────────────────
// FFI declarations — linked from `zig/libsensei_zig.a`
// ──────────────────────────────────────────────

#[cfg(not(no_zig))]
extern "C" {
    /// Compute C = A × B where A is m×k, B is k×n.
    /// Returns a pointer to the flat f32 result, or null on allocation failure.
    /// Caller must free with `std::heap.page_allocator.free()`.
    fn sensei_tensor_matrix_multiply_f32(
        a: *const f32,
        b: *const f32,
        m: usize,
        n: usize,
        k: usize,
    ) -> *mut f32;

    /// Free a buffer previously allocated by Zig's page_allocator.
    fn sensei_free(ptr: *mut u8, size: usize);

    /// In-place ReLU activation on an f32 tensor.
    fn sensei_tensor_relu_f32(tensor: *mut f32, len: usize);

    /// Stable softmax along the specified dimension.
    fn sensei_tensor_softmax_f32(tensor: *mut f32, len: usize, dim: usize);

    /// Argmax — returns the index of the maximum value.
    fn sensei_tensor_argmax_f32(tensor: *const f32, len: usize, dim: usize) -> usize;

    /// Argmax per-slice — returns a pointer to `len/dim` indices.
    fn sensei_tensor_argmax_f32_dim(tensor: *const f32, len: usize, dim: usize) -> *mut usize;

    /// Load an ONNX model from a file path.
    /// Returns an opaque pointer to a Zig-allocated Model, or null.
    fn sensei_onnx_model_load(path: *const std::os::raw::c_char) -> *mut std::ffi::c_void;

    /// Query whether a model is actually backed by ONNX Runtime.
    fn sensei_onnx_model_is_onnx(model: *const std::ffi::c_void) -> bool;

    /// Run inference — takes flat f32 input, fills flat f32 output.
    /// Returns 0 on success, -1 on error.
    fn sensei_onnx_model_run(
        model: *mut std::ffi::c_void,
        input_data: *const f32,
        input_len: usize,
        output_data: *mut f32,
        output_len: usize,
    ) -> i32;

    /// Release an ONNX model previously loaded via `sensei_onnx_model_load`.
    fn sensei_onnx_model_deinit(model: *mut std::ffi::c_void);
}

// ══════════════════════════════════════════════
// Pure-Rust fallback implementations
// ══════════════════════════════════════════════

/// Pure-Rust fallback for `matrix_multiply_f32`.
///
/// Uses a simple triple-loop. No SIMD acceleration.
pub fn matrix_multiply_f32_fallback(
    a: &[f32],
    b: &[f32],
    m: usize,
    n: usize,
    k: usize,
) -> Vec<f32> {
    assert_eq!(a.len(), m * k, "A dimensions don't match m×k");
    assert_eq!(b.len(), k * n, "B dimensions don't match k×n");

    let mut result = vec![0.0f32; m * n];

    for i in 0..m {
        for j in 0..n {
            let mut sum = 0.0f32;
            for t in 0..k {
                sum += a[i * k + t] * b[t * n + j];
            }
            result[i * n + j] = sum;
        }
    }

    result
}

/// Pure-Rust fallback for `relu_f32`.
pub fn relu_f32_fallback(tensor: &mut [f32]) {
    for x in tensor.iter_mut() {
        if *x < 0.0 {
            *x = 0.0;
        }
    }
}

/// Pure-Rust fallback for `softmax_f32` (stable softmax).
pub fn softmax_f32_fallback(tensor: &mut [f32], dim: usize) {
    assert!(tensor.len() % dim == 0, "tensor length not divisible by dim");
    let batch_count = tensor.len() / dim;

    for batch in 0..batch_count {
        let start = batch * dim;
        let slice = &mut tensor[start..start + dim];

        // Find max for numerical stability
        let max_val = slice.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

        // Exponentiate and sum
        let mut sum = 0.0f32;
        for x in slice.iter_mut() {
            *x = (*x - max_val).exp();
            sum += *x;
        }

        // Normalize
        let inv_sum = 1.0 / sum;
        for x in slice.iter_mut() {
            *x *= inv_sum;
        }
    }
}

/// Pure-Rust fallback for `argmax_f32`.
pub fn argmax_f32_fallback(tensor: &[f32], _dim: usize) -> usize {
    tensor
        .iter()
        .enumerate()
        .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(idx, _)| idx)
        .unwrap_or(0)
}

/// Pure-Rust fallback for per-slice argmax.
pub fn argmax_f32_dim_fallback(tensor: &[f32], dim: usize) -> Vec<usize> {
    assert!(tensor.len() % dim == 0, "tensor length not divisible by dim");
    let batch_count = tensor.len() / dim;

    (0..batch_count)
        .map(|batch| {
            let start = batch * dim;
            let slice = &tensor[start..start + dim];
            slice
                .iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
                .map(|(idx, _)| idx)
                .unwrap_or(0)
        })
        .collect()
}

// ══════════════════════════════════════════════
// Safe Rust public API
// ══════════════════════════════════════════════

/// Compute C = A × B where A is m×k and B is k×n.
///
/// Uses Zig SIMD when available; falls back to a scalar loop.
///
/// # Errors
///
/// Returns [`SenseiError::Internal`] if the Zig FFI returns null
/// (allocation failure).
pub fn matrix_multiply_f32(
    a: &[f32],
    b: &[f32],
    m: usize,
    n: usize,
    k: usize,
) -> Result<Vec<f32>, SenseiError> {
    #[cfg(not(no_zig))]
    {
        let ptr = unsafe {
            sensei_tensor_matrix_multiply_f32(a.as_ptr(), b.as_ptr(), m, n, k)
        };
        if ptr.is_null() {
            return Err(SenseiError::Internal(
                "matrix_multiply_f32: Zig allocation failed".into(),
            ));
        }
        // Copy into a Vec so the Zig allocation can be freed via sensei_free.
        // Must NOT use Vec::from_raw_parts because Zig's page_allocator uses
        // mmap directly, which is incompatible with Rust's Global allocator (free).
        let len = m * n;
        let result = std::ptr::slice_from_raw_parts(ptr, len);
        let vec = unsafe { (*result).to_vec() };
        unsafe { sensei_free(ptr as *mut u8, len * std::mem::size_of::<f32>()) };
        Ok(vec)
    }

    #[cfg(no_zig)]
    {
        Ok(matrix_multiply_f32_fallback(a, b, m, n, k))
    }
}

/// In-place ReLU activation on an f32 tensor.
///
/// Uses Zig SIMD when available; falls back to scalar loop.
pub fn relu_f32(tensor: &mut [f32]) -> Result<(), SenseiError> {
    #[cfg(not(no_zig))]
    {
        unsafe {
            sensei_tensor_relu_f32(tensor.as_mut_ptr(), tensor.len());
        }
        Ok(())
    }

    #[cfg(no_zig)]
    {
        relu_f32_fallback(tensor);
        Ok(())
    }
}

/// Stable softmax along the specified dimension.
///
/// Uses Zig SIMD when available; falls back to scalar loop.
///
/// # Panics
///
/// Panics if `tensor.len()` is not divisible by `dim`.
pub fn softmax_f32(tensor: &mut [f32], dim: usize) -> Result<(), SenseiError> {
    #[cfg(not(no_zig))]
    {
        unsafe {
            sensei_tensor_softmax_f32(tensor.as_mut_ptr(), tensor.len(), dim);
        }
        Ok(())
    }

    #[cfg(no_zig)]
    {
        softmax_f32_fallback(tensor, dim);
        Ok(())
    }
}

/// Argmax (global) — returns the index of the maximum value.
///
/// Uses Zig SIMD when available; falls back to scalar loop.
pub fn argmax_f32(tensor: &[f32], dim: usize) -> Result<usize, SenseiError> {
    #[cfg(not(no_zig))]
    {
        let idx = unsafe { sensei_tensor_argmax_f32(tensor.as_ptr(), tensor.len(), dim) };
        Ok(idx)
    }

    #[cfg(no_zig)]
    {
        Ok(argmax_f32_fallback(tensor, dim))
    }
}

/// Argmax per-slice — returns indices, one per slice of size `dim`.
///
/// Uses the Zig export when available; falls back to a scalar loop.
///
/// Returns an error when `tensor.len()` is not divisible by `dim`.
pub fn argmax_f32_dim(tensor: &[f32], dim: usize) -> Result<Vec<usize>, SenseiError> {
    if dim == 0 || tensor.len() % dim != 0 {
        return Err(SenseiError::Validation(format!(
            "tensor length {} must be divisible by dim {}",
            tensor.len(),
            dim
        )));
    }

    #[cfg(not(no_zig))]
    {
        let batch_count = tensor.len() / dim;
        let ptr = unsafe { sensei_tensor_argmax_f32_dim(tensor.as_ptr(), tensor.len(), dim) };
        if ptr.is_null() {
            return Err(SenseiError::Internal("Zig argmax_f32_dim failed".to_string()));
        }
        let result = unsafe { std::slice::from_raw_parts(ptr, batch_count) }.to_vec();
        unsafe { sensei_free(ptr as *mut u8, batch_count * std::mem::size_of::<usize>()) };
        Ok(result)
    }

    #[cfg(no_zig)]
    {
        Ok(argmax_f32_dim_fallback(tensor, dim))
    }
}

// ══════════════════════════════════════════════
// OnnxModel — model lifecycle
// ══════════════════════════════════════════════

/// Input tensor for [`OnnxModel::run()`].
#[derive(Debug, Clone)]
pub struct TensorInput {
    /// Flat f32 data.
    pub data: Vec<f32>,
    /// Shape dimensions (e.g. `vec![1, 3, 224, 224]`).
    pub shape: Vec<i64>,
}

/// Output tensor from [`OnnxModel::run()`].
#[derive(Debug, Clone)]
pub struct TensorOutput {
    /// Flat f32 data.
    pub data: Vec<f32>,
    /// Shape dimensions.
    pub shape: Vec<i64>,
}

/// An ONNX model loaded into memory.
///
/// When Zig/ONNX Runtime is linked, this wraps a Zig-allocated
/// [`onnx::Model`](../zig/src/onnx_runtime.zig) via FFI.
/// Otherwise, it uses a software fallback that returns a static
/// 4-element softmax output (no actual .onnx loading).
pub struct OnnxModel {
    /// Opaque handle to the Zig-allocated Model (null when using fallback).
    handle: *mut std::ffi::c_void,
    /// Whether this model is backed by ONNX Runtime or fallback.
    is_onnx: bool,
}

/// Number of output classes for the fallback model.
const FALLBACK_OUTPUT_DIM: usize = 4;

impl OnnxModel {
    /// Load an ONNX model from a file path.
    ///
    /// When the Zig library is linked, this delegates to
    /// [`sensei_onnx_model_load`]. When not, or when loading fails,
    /// returns a software fallback model.
    #[allow(unused_variables)]
    pub fn load(path: &str) -> Result<Self, SenseiError> {
        #[cfg(not(no_zig))]
        {
            let c_path = std::ffi::CString::new(path)
                .map_err(|e| SenseiError::Internal(format!("invalid model path: {e}")))?;
            let handle = unsafe { sensei_onnx_model_load(c_path.as_ptr()) };
            if !handle.is_null() {
                return Ok(OnnxModel {
                    handle,
                    is_onnx: unsafe { sensei_onnx_model_is_onnx(handle) },
                });
            }
        }

        // Fallback: return a no-op model with softmax output
        Ok(OnnxModel {
            handle: std::ptr::null_mut(),
            is_onnx: false,
        })
    }

    /// Run inference with the provided input tensors.
    ///
    /// When backed by ONNX Runtime, delegates to
    /// [`sensei_onnx_model_run`]. Otherwise applies the software
    /// fallback (2-layer MLP returning a 4-element softmax).
    pub fn run(&self, inputs: &[TensorInput]) -> Result<Vec<TensorOutput>, SenseiError> {
        #[cfg(not(no_zig))]
        if self.is_onnx {
            return self.run_onnx(inputs);
        }
        self.run_fallback(inputs)
    }

    /// ONNX Runtime inference path.
    /// Only compiled when Zig FFI is available.
    #[cfg(not(no_zig))]
    fn run_onnx(&self, inputs: &[TensorInput]) -> Result<Vec<TensorOutput>, SenseiError> {
        let input = inputs.first().ok_or_else(|| {
            SenseiError::Validation("at least one input tensor required".into())
        })?;

        let input_len = input.data.len();
        let mut output = vec![0.0f32; FALLBACK_OUTPUT_DIM];

        let ret = unsafe {
            sensei_onnx_model_run(
                self.handle,
                input.data.as_ptr(),
                input_len,
                output.as_mut_ptr(),
                output.len(),
            )
        };

        if ret != 0 {
            return Err(SenseiError::Internal("ONNX model run failed".into()));
        }

        Ok(vec![TensorOutput {
            data: output,
            shape: vec![FALLBACK_OUTPUT_DIM as i64],
        }])
    }

    /// Software fallback inference: 2-layer MLP.
    fn run_fallback(&self, inputs: &[TensorInput]) -> Result<Vec<TensorOutput>, SenseiError> {
        let input = inputs.first().ok_or_else(|| {
            SenseiError::Validation("at least one input tensor required".into())
        })?;

        let x = &input.data;
        let input_dim = x.len();

        // Layer 1: input_dim → 8, ReLU
        let w1: Vec<f32> = (0..input_dim * 8)
            .map(|i| (i as f32 % input_dim as f32) * 0.1 + 0.01)
            .collect();
        let b1: Vec<f32> = (0..8).map(|i| i as f32 * 0.01).collect();

        let mut hidden = matrix_multiply_f32_fallback(x, &w1, 1, 8, input_dim);
        for (h, b) in hidden.iter_mut().zip(b1.iter()) {
            *h += b;
        }
        relu_f32_fallback(&mut hidden);

        // Layer 2: 8 → 4, Softmax
        let w2: Vec<f32> = (0..8 * FALLBACK_OUTPUT_DIM)
            .map(|i| (i as f32 % 8.0) * 0.05 + 0.01)
            .collect();
        let b2: Vec<f32> = vec![0.01f32; FALLBACK_OUTPUT_DIM];

        let mut output =
            matrix_multiply_f32_fallback(&hidden, &w2, 1, FALLBACK_OUTPUT_DIM, 8);
        for (o, b) in output.iter_mut().zip(b2.iter()) {
            *o += b;
        }
        softmax_f32_fallback(&mut output, FALLBACK_OUTPUT_DIM);

        Ok(vec![TensorOutput {
            data: output,
            shape: vec![FALLBACK_OUTPUT_DIM as i64],
        }])
    }

    /// Release model resources.
    ///
    /// If backed by ONNX Runtime, frees the Zig-allocated model.
    pub fn deinit(&mut self) {
        #[cfg(not(no_zig))]
        {
            if self.is_onnx && !self.handle.is_null() {
                unsafe {
                    sensei_onnx_model_deinit(self.handle);
                }
            }
        }
        self.handle = std::ptr::null_mut();
        self.is_onnx = false;
    }
}

impl Drop for OnnxModel {
    fn drop(&mut self) {
        self.deinit();
    }
}

// ══════════════════════════════════════════════
// Tests
// ══════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_matrix_multiply_f32_fallback() {
        // A = [[1, 2], [3, 4]]  (2×2)
        // B = [[5, 6], [7, 8]]  (2×2)
        // C = [[19, 22], [43, 50]]
        let a = vec![1.0, 2.0, 3.0, 4.0];
        let b = vec![5.0, 6.0, 7.0, 8.0];
        let c = matrix_multiply_f32_fallback(&a, &b, 2, 2, 2);
        assert!((c[0] - 19.0).abs() < 1e-5);
        assert!((c[1] - 22.0).abs() < 1e-5);
        assert!((c[2] - 43.0).abs() < 1e-5);
        assert!((c[3] - 50.0).abs() < 1e-5);
    }

    #[test]
    fn test_relu_f32_fallback() {
        let mut v = vec![-2.0, -1.0, 0.0, 1.0, 2.0];
        relu_f32_fallback(&mut v);
        assert_eq!(v, vec![0.0, 0.0, 0.0, 1.0, 2.0]);
    }

    #[test]
    fn test_softmax_f32_fallback() {
        let mut v = vec![1.0, 2.0, 3.0, 4.0];
        softmax_f32_fallback(&mut v, 4);
        let sum: f32 = v.iter().sum();
        assert!((sum - 1.0).abs() < 1e-5);
        // Values should increase with input (exponential preserves order)
        assert!(v[0] < v[1]);
        assert!(v[1] < v[2]);
        assert!(v[2] < v[3]);
    }

    #[test]
    fn test_softmax_multi_batch() {
        let mut v = vec![0.0, 0.0, 0.0, 1.0, 2.0, 3.0];
        softmax_f32_fallback(&mut v, 3);
        let sum0: f32 = v[0..3].iter().sum();
        let sum1: f32 = v[3..6].iter().sum();
        assert!((sum0 - 1.0).abs() < 1e-5);
        assert!((sum1 - 1.0).abs() < 1e-5);
        // Uniform batch
        assert!((v[0] - 1.0 / 3.0).abs() < 1e-5);
    }

    #[test]
    fn test_argmax_f32_fallback() {
        let v = vec![0.1, 0.5, 0.3, 0.7, 0.2];
        let idx = argmax_f32_fallback(&v, 5);
        assert_eq!(idx, 3); // 0.7 at index 3
    }

    #[test]
    fn test_argmax_dim_fallback() {
        let v = vec![0.1, 0.9, 0.3, 0.5, 0.2, 0.8];
        let result = argmax_f32_dim_fallback(&v, 3);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0], 1); // 0.9 at index 1 in first batch
        assert_eq!(result[1], 2); // 0.8 at index 2 in second batch
    }

    #[test]
    fn test_fallback_model_run() {
        let model = OnnxModel::load("dummy.onnx").expect("should create fallback model");
        assert!(!model.is_onnx);

        let inputs = vec![TensorInput {
            data: vec![1.0, 2.0, 3.0, 4.0],
            shape: vec![4],
        }];

        let outputs = model.run(&inputs).expect("fallback run should succeed");
        assert_eq!(outputs.len(), 1);
        assert_eq!(outputs[0].data.len(), FALLBACK_OUTPUT_DIM);

        // Output should be a valid probability distribution (softmax)
        let sum: f32 = outputs[0].data.iter().sum();
        assert!((sum - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_safe_api_matrix_multiply() {
        let a = vec![1.0, 2.0, 3.0, 4.0];
        let b = vec![5.0, 6.0, 7.0, 8.0];
        let result = crate::onnx::matrix_multiply_f32(&a, &b, 2, 2, 2);
        assert!(result.is_ok());
        let c = result.unwrap();
        assert!((c[0] - 19.0).abs() < 1e-5);
    }
}
