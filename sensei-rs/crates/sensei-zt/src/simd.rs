//! SIMD-accelerated numerical routines.
//!
//! Delegates to Zig when the native library is available; otherwise
//! provides pure-Rust fallbacks using portable SIMD or scalar loops.

// ──────────────────────────────────────────────
// Zig-backed implementations
// ──────────────────────────────────────────────

#[cfg(not(no_zig))]
extern "C" {
    fn sensei_simd_f32_dot_product(a: *const f32, b: *const f32, len: usize) -> f32;
    fn sensei_simd_f32_normalize(v: *mut f32, len: usize);
    fn sensei_simd_i16_scale(v: *mut i16, len: usize, factor: f32);
}

/// Compute the dot product of two `f32` slices.
///
/// Uses Zig SIMD when available; falls back to a scalar loop.
///
/// Returns an error when the slice lengths differ (no panics).
pub fn f32_dot_product(a: &[f32], b: &[f32]) -> Result<f32, &'static str> {
    if a.len() != b.len() {
        return Err("slice lengths must match for dot product");
    }

    #[cfg(not(no_zig))]
    {
        Ok(unsafe { sensei_simd_f32_dot_product(a.as_ptr(), b.as_ptr(), a.len()) })
    }

    #[cfg(no_zig)]
    {
        Ok(a.iter().zip(b.iter()).map(|(x, y)| x * y).sum())
    }
}

/// Normalise an `f32` slice in place (L2 norm).
pub fn f32_normalize(v: &mut [f32]) {
    #[cfg(not(no_zig))]
    {
        unsafe { sensei_simd_f32_normalize(v.as_mut_ptr(), v.len()) }
    }

    #[cfg(no_zig)]
    {
        let norm: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > f32::EPSILON {
            for x in v.iter_mut() {
                *x /= norm;
            }
        }
    }
}

/// Scale an `i16` slice by a floating-point factor, rounding to nearest.
pub fn i16_scale(v: &mut [i16], factor: f32) {
    #[cfg(not(no_zig))]
    {
        unsafe { sensei_simd_i16_scale(v.as_mut_ptr(), v.len(), factor) }
    }

    #[cfg(no_zig)]
    {
        for x in v.iter_mut() {
            *x = (*x as f32 * factor).round() as i16;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dot_product() {
        let a = vec![1.0, 2.0, 3.0];
        let b = vec![4.0, 5.0, 6.0];
        let result = f32_dot_product(&a, &b).unwrap();
        assert!((result - 32.0).abs() < 1e-5);
    }

    #[test]
    fn test_dot_product_mismatched_lengths_returns_error() {
        let a = vec![1.0, 2.0, 3.0];
        let b = vec![4.0, 5.0];
        assert!(f32_dot_product(&a, &b).is_err());
    }

    #[test]
    fn test_normalize() {
        let mut v = vec![3.0, 4.0];
        f32_normalize(&mut v);
        assert!((v[0] - 0.6).abs() < 1e-5);
        assert!((v[1] - 0.8).abs() < 1e-5);
    }

    #[test]
    fn test_i16_scale() {
        let mut v = vec![10, 20, 30];
        i16_scale(&mut v, 0.5);
        assert_eq!(v, vec![5, 10, 15]);
    }
}
