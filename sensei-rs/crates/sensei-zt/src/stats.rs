//! SIMD-accelerated SPC statistics.
//!
//! Delegates to Zig when the native library is available; otherwise
//! provides pure-Rust fallback implementations.

// ──────────────────────────────────────────────
// Foreign types shared with Zig
// ──────────────────────────────────────────────

/// Process capability analysis result (mirrors Zig's `CapabilityResult`).
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct CapabilityResult {
    pub cp: f64,
    pub cpk: f64,
    pub pp: f64,
    pub ppk: f64,
    pub mean: f64,
    pub std_dev: f64,
    pub within_std_dev: f64,
    pub below_lsl: f64,
    pub above_usl: f64,
    pub total_defect_pct: f64,
}

/// Histogram result.
#[derive(Debug, Clone)]
pub struct HistogramResult {
    pub bins: Vec<f64>,
    pub counts: Vec<usize>,
    pub bin_width: f64,
    pub min_val: f64,
    pub max_val: f64,
}

// ──────────────────────────────────────────────
// Zig-backed implementations
// ──────────────────────────────────────────────

#[cfg(not(no_zig))]
extern "C" {
    fn sensei_stats_mean(data: *const f64, len: usize) -> f64;
    fn sensei_stats_std_dev(data: *const f64, len: usize, mean_val: f64) -> f64;
    fn sensei_stats_capability(
        data: *const f64,
        len: usize,
        lsl: f64,
        usl: f64,
        subgroup_size: usize,
        result: *mut CapabilityResult,
    );
    fn sensei_stats_histogram(
        data: *const f64,
        len: usize,
        bin_count: usize,
        out_bins: *mut f64,
        out_counts: *mut usize,
    ) -> i32;
}

// ──────────────────────────────────────────────
// Public API
// ──────────────────────────────────────────────

/// Compute the arithmetic mean of `data`.
pub fn mean(data: &[f64]) -> f64 {
    if data.is_empty() {
        return 0.0;
    }

    #[cfg(not(no_zig))]
    {
        unsafe { sensei_stats_mean(data.as_ptr(), data.len()) }
    }

    #[cfg(no_zig)]
    {
        data.iter().sum::<f64>() / data.len() as f64
    }
}

/// Compute the population standard deviation of `data`.
pub fn std_dev(data: &[f64]) -> f64 {
    if data.is_empty() {
        return 0.0;
    }
    let mu = mean(data);

    #[cfg(not(no_zig))]
    {
        unsafe { sensei_stats_std_dev(data.as_ptr(), data.len(), mu) }
    }

    #[cfg(no_zig)]
    {
        let variance = data.iter().map(|x| (x - mu).powi(2)).sum::<f64>() / data.len() as f64;
        variance.sqrt()
    }
}

/// Calculate process capability indices from raw data.
pub fn calculate_capability(
    data: &[f64],
    lsl: f64,
    usl: f64,
    subgroup_size: usize,
) -> CapabilityResult {
    if data.len() < 2 {
        return CapabilityResult {
            cp: 0.0,
            cpk: 0.0,
            pp: 0.0,
            ppk: 0.0,
            mean: mean(data),
            std_dev: 0.0,
            within_std_dev: 0.0,
            below_lsl: 0.0,
            above_usl: 0.0,
            total_defect_pct: 0.0,
        };
    }

    #[cfg(not(no_zig))]
    {
        let mut result = CapabilityResult {
            cp: 0.0,
            cpk: 0.0,
            pp: 0.0,
            ppk: 0.0,
            mean: 0.0,
            std_dev: 0.0,
            within_std_dev: 0.0,
            below_lsl: 0.0,
            above_usl: 0.0,
            total_defect_pct: 0.0,
        };
        unsafe {
            sensei_stats_capability(
                data.as_ptr(),
                data.len(),
                lsl,
                usl,
                subgroup_size,
                &mut result,
            );
        }
        result
    }

    #[cfg(no_zig)]
    {
        let mu = mean(data);
        let sigma_overall = std_dev(data);
        let within_std_dev = estimate_within_std_dev(data, subgroup_size);
        calculate_capability_from_stats(mu, sigma_overall, within_std_dev, lsl, usl)
    }
}

/// Calculate process capability indices from pre-computed statistics.
pub fn calculate_capability_from_stats(
    mean_val: f64,
    std_dev: f64,
    within_std_dev: f64,
    lsl: f64,
    usl: f64,
) -> CapabilityResult {
    let tolerance = usl - lsl;

    let cp = if within_std_dev > 0.0 {
        tolerance / (6.0 * within_std_dev)
    } else {
        0.0
    };

    let cpu = if within_std_dev > 0.0 {
        (usl - mean_val) / (3.0 * within_std_dev)
    } else {
        0.0
    };
    let cpl = if within_std_dev > 0.0 {
        (mean_val - lsl) / (3.0 * within_std_dev)
    } else {
        0.0
    };
    let cpk = cpu.min(cpl);

    let pp = if std_dev > 0.0 {
        tolerance / (6.0 * std_dev)
    } else {
        0.0
    };

    let ppu = if std_dev > 0.0 {
        (usl - mean_val) / (3.0 * std_dev)
    } else {
        0.0
    };
    let ppl = if std_dev > 0.0 {
        (mean_val - lsl) / (3.0 * std_dev)
    } else {
        0.0
    };
    let ppk = ppu.min(ppl);

    let below_lsl = if std_dev > 0.0 {
        normal_cdf((lsl - mean_val) / std_dev) * 100.0
    } else {
        0.0
    };
    let above_usl = if std_dev > 0.0 {
        (1.0 - normal_cdf((usl - mean_val) / std_dev)) * 100.0
    } else {
        0.0
    };

    CapabilityResult {
        cp,
        cpk,
        pp,
        ppk,
        mean: mean_val,
        std_dev,
        within_std_dev,
        below_lsl,
        above_usl,
        total_defect_pct: below_lsl + above_usl,
    }
}

/// Calculate a histogram with the specified number of bins.
pub fn calculate_histogram(data: &[f64], bin_count: usize) -> HistogramResult {
    if data.is_empty() || bin_count == 0 {
        return HistogramResult {
            bins: Vec::new(),
            counts: Vec::new(),
            bin_width: 0.0,
            min_val: 0.0,
            max_val: 0.0,
        };
    }

    #[cfg(not(no_zig))]
    {
        let mut bins = vec![0.0f64; bin_count];
        let mut counts = vec![0usize; bin_count];

        let ret = unsafe {
            sensei_stats_histogram(
                data.as_ptr(),
                data.len(),
                bin_count,
                bins.as_mut_ptr(),
                counts.as_mut_ptr(),
            )
        };

        if ret != 0 {
            return HistogramResult {
                bins: Vec::new(),
                counts: Vec::new(),
                bin_width: 0.0,
                min_val: 0.0,
                max_val: 0.0,
            };
        }

        let min_val = data.iter().cloned().fold(f64::INFINITY, f64::min);
        let max_val = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let bin_width = if bin_count > 0 {
            (max_val - min_val) / bin_count as f64
        } else {
            0.0
        };

        HistogramResult {
            bins,
            counts,
            bin_width,
            min_val,
            max_val,
        }
    }

    #[cfg(no_zig)]
    {
        let min_val = data.iter().cloned().fold(f64::INFINITY, f64::min);
        let max_val = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        let adj_min = min_val;
        let adj_max = if max_val <= min_val {
            min_val + 1.0
        } else {
            max_val
        };

        let bin_width = (adj_max - adj_min) / bin_count as f64;

        let mut bins = Vec::with_capacity(bin_count);
        let mut counts = vec![0usize; bin_count];

        for b in 0..bin_count {
            bins.push(adj_min + b as f64 * bin_width);
        }

        for &x in data {
            let mut idx = ((x - adj_min) / bin_width).floor() as usize;
            if idx >= bin_count {
                idx = bin_count - 1;
            }
            counts[idx] += 1;
        }

        HistogramResult {
            bins,
            counts,
            bin_width,
            min_val,
            max_val,
        }
    }
}

/// Standard normal CDF (Abramowitz & Stegun approximation).
///
/// Φ(z) = (1/√(2π)) ∫₋∞ᶻ exp(-t²/2) dt
///      = 0.5 * (1 + erf(z / √2))
pub fn normal_cdf(x: f64) -> f64 {
    if x < -8.0 {
        return 0.0;
    }
    if x > 8.0 {
        return 1.0;
    }

    // Scale: erf(z) = erf(x / √2), where Φ(x) = 0.5 * (1 + erf(x/√2))
    const INV_SQRT2: f64 = 0.7071067811865475;
    let z = x * INV_SQRT2;

    let a1 = 0.254829592;
    let a2 = -0.284496736;
    let a3 = 1.421413741;
    let a4 = -1.453152027;
    let a5 = 1.061405429;
    let p = 0.3275911;

    let abs_z = z.abs();
    let t = 1.0 / (1.0 + p * abs_z);
    let erf_approx =
        1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * (-abs_z * abs_z).exp();

    if z >= 0.0 {
        0.5 * (1.0 + erf_approx)
    } else {
        0.5 * (1.0 - erf_approx)
    }
}

/// Standard normal quantile (inverse CDF) — Acklam's rational approximation.
pub fn normal_quantile(p: f64) -> f64 {
    if p <= 0.0 {
        return -8.0;
    }
    if p >= 1.0 {
        return 8.0;
    }
    if p == 0.5 {
        return 0.0;
    }

    let a = [
        -3.969683028665376e+01,
        2.209460984245205e+02,
        -2.759285104469687e+02,
        138.357751867269,
        -3.066479806614716e+01,
        2.506628277459239e+00,
    ];
    let b = [
        -5.447609879822406e+01,
        1.615858368580409e+02,
        -1.556989798598866e+02,
        6.680131188771972e+01,
        -1.328068155288572e+01,
    ];
    let c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e+00,
        -2.549732539343734e+00,
        4.374664141464968e+00,
        2.938163982698783e+00,
    ];
    let d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e+00,
        3.754408661907416e+00,
    ];

    let p_low = 0.02425;
    let p_high = 1.0 - p_low;

    if p < p_low {
        let q = (-2.0 * p.ln()).sqrt();
        (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    } else if p <= p_high {
        let q = p - 0.5;
        let r = q * q;
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    } else {
        let q = (-2.0 * (1.0 - p).ln()).sqrt();
        -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    }
}

// ──────────────────────────────────────────────
// Internal helpers (pure-Rust fallback)
// ──────────────────────────────────────────────

/// Estimate within-group standard deviation using moving range.
///
/// Only used by the pure-Rust capability path (`SENSEI_NO_ZIG` builds); the
/// Zig-linked build computes this natively.
#[cfg(no_zig)]
fn estimate_within_std_dev(data: &[f64], subgroup_size: usize) -> f64 {
    if data.len() < 2 {
        return 0.0;
    }

    let sg = if subgroup_size < 2 { 2 } else { subgroup_size };

    let mut sum_r = 0.0;
    let mut count = 0usize;

    let mut i = 0;
    while i + sg <= data.len() {
        let mut min_val = data[i];
        let mut max_val = data[i];
        for j in 1..sg {
            if data[i + j] < min_val {
                min_val = data[i + j];
            }
            if data[i + j] > max_val {
                max_val = data[i + j];
            }
        }
        sum_r += max_val - min_val;
        count += 1;
        i += sg;
    }

    if count == 0 {
        return 0.0;
    }
    let rbar = sum_r / count as f64;
    let d2_val = d2(sg);
    if d2_val <= 0.0 {
        return 0.0;
    }
    rbar / d2_val
}

/// d2 constant for estimating σ from Rbar.
pub fn d2(subgroup_size: usize) -> f64 {
    const TABLE: [f64; 24] = [
        1.128, // n=2
        1.693, // n=3
        2.059, // n=4
        2.326, // n=5
        2.534, // n=6
        2.704, // n=7
        2.847, // n=8
        2.970, // n=9
        3.078, // n=10
        3.173, // n=11
        3.258, // n=12
        3.336, // n=13
        3.407, // n=14
        3.472, // n=15
        3.532, // n=16
        3.588, // n=17
        3.640, // n=18
        3.689, // n=19
        3.735, // n=20
        3.778, // n=21
        3.819, // n=22
        3.858, // n=23
        3.895, // n=24
        3.931, // n=25
    ];
    if (2..=25).contains(&subgroup_size) {
        TABLE[subgroup_size - 2]
    } else if subgroup_size > 25 {
        let n = subgroup_size as f64;
        std::f64::consts::SQRT_2 * (1.0 - 3.0 / (4.0 * n - 1.0))
    } else {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mean_basic() {
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        assert!((mean(&data) - 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_mean_empty() {
        assert_eq!(mean(&[]), 0.0);
    }

    #[test]
    fn test_std_dev() {
        let data = vec![2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0];
        let sd = std_dev(&data);
        assert!((sd - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_calculate_capability_centered() {
        let data = vec![10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1];
        let result = calculate_capability(&data, 9.5, 10.5, 3);

        assert!(result.cp > 1.0);
        assert!((result.mean - 10.0).abs() < 0.1);
        assert!(result.cpk > 0.5);
        assert!(result.pp > 0.0);
        assert!(result.total_defect_pct < 50.0);
    }

    #[test]
    fn test_calculate_capability_from_stats() {
        let result = calculate_capability_from_stats(10.0, 0.5, 0.4, 8.0, 12.0);

        // Cp = (12-8) / (6*0.4) = 4/2.4 ≈ 1.667
        assert!((result.cp - 1.6667).abs() < 0.01);
        // Cpk = min((12-10)/(3*0.4), (10-8)/(3*0.4)) = 1.667
        assert!((result.cpk - 1.6667).abs() < 0.01);
        // Pp = 4/(6*0.5) = 1.333
        assert!((result.pp - 1.3333).abs() < 0.01);
        assert!((result.mean - 10.0).abs() < 0.001);
    }

    #[test]
    fn test_calculate_histogram() {
        let data = vec![1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0];
        let hist = calculate_histogram(&data, 5);

        assert_eq!(hist.bins.len(), 5);
        assert!(hist.bin_width > 0.0);
        let total: usize = hist.counts.iter().sum();
        assert_eq!(total, data.len());
    }

    #[test]
    fn test_normal_cdf() {
        assert!((normal_cdf(0.0) - 0.5).abs() < 1e-6);
        assert!((normal_cdf(1.0) - 0.8413).abs() < 0.001);
        assert!((normal_cdf(-1.0) - 0.1587).abs() < 0.001);
        assert!((normal_cdf(2.0) - 0.9772).abs() < 0.001);
    }

    #[test]
    fn test_normal_quantile() {
        assert!((normal_quantile(0.5)).abs() < 1e-6);
        assert!((normal_quantile(0.8413) - 1.0).abs() < 0.01);
        assert!((normal_quantile(0.1587) + 1.0).abs() < 0.01);
    }

    #[test]
    fn test_d2_constant() {
        assert!((d2(2) - 1.128).abs() < 0.001);
        assert!((d2(5) - 2.326).abs() < 0.001);
    }

    #[test]
    fn test_calculate_capability_defect_pcts() {
        // Process with mean=10, sd=1, LSL=8, USL=12
        // Z_lower = -2 → ~2.275%, Z_upper = 2 → ~2.275%, total ≈ 4.55%
        let result = calculate_capability_from_stats(10.0, 1.0, 1.0, 8.0, 12.0);
        assert!((result.below_lsl - 2.275).abs() < 0.1);
        assert!((result.above_usl - 2.275).abs() < 0.1);
        assert!((result.total_defect_pct - 4.55).abs() < 0.2);
    }
}
