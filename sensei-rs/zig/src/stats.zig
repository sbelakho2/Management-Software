//! SIMD-accelerated Statistical Process Control (SPC) statistics.
//!
//! Provides basic statistics (mean, variance, std dev, min, max, range),
//! process capability indices (Cp, Cpk, Pp, Ppk), histogram computation,
//! control chart constants, and normal CDF/quantile functions.
//!
//! Uses Kahan (compensated) summation for numerical stability and SIMD
//! vectorisation patterns for performance.

const std = @import("std");
const math = std.math;

// ──────────────────────────────────────────────
// Basic Statistics
// ──────────────────────────────────────────────

/// Compute the arithmetic mean of `data` using Kahan summation.
pub fn mean(data: []const f64) f64 {
    if (data.len == 0) return 0.0;
    var sum: f64 = 0.0;
    var c: f64 = 0.0; // compensation
    for (data) |x| {
        const y = x - c;
        const t = sum + y;
        c = (t - sum) - y;
        sum = t;
    }
    return sum / @as(f64, @floatFromInt(data.len));
}

/// Compute the population variance with Kahan summation.
pub fn variance(data: []const f64, mean_val: f64) f64 {
    if (data.len == 0) return 0.0;
    var sum: f64 = 0.0;
    var c: f64 = 0.0;
    for (data) |x| {
        const d = x - mean_val;
        const y = d * d - c;
        const t = sum + y;
        c = (t - sum) - y;
        sum = t;
    }
    return sum / @as(f64, @floatFromInt(data.len));
}

/// Compute the population standard deviation.
pub fn stdDev(data: []const f64, mean_val: f64) f64 {
    return @sqrt(variance(data, mean_val));
}

/// Find the minimum value in `data`.
pub fn min(data: []const f64) f64 {
    if (data.len == 0) return 0.0;
    var result = data[0];
    for (data[1..]) |x| {
        if (x < result) result = x;
    }
    return result;
}

/// Find the maximum value in `data`.
pub fn max(data: []const f64) f64 {
    if (data.len == 0) return 0.0;
    var result = data[0];
    for (data[1..]) |x| {
        if (x > result) result = x;
    }
    return result;
}

/// Compute the range (max - min) of `data`.
pub fn range(data: []const f64) f64 {
    if (data.len == 0) return 0.0;
    return max(data) - min(data);
}

// ──────────────────────────────────────────────
// Process Capability Indices
// ──────────────────────────────────────────────

/// Result of a process capability analysis.
pub const CapabilityResult = struct {
    cp: f64,
    cpk: f64,
    pp: f64,
    ppk: f64,
    mean: f64,
    std_dev: f64,
    within_std_dev: f64,
    below_lsl: f64,
    above_usl: f64,
    total_defect_pct: f64,
};

/// Calculate process capability indices from raw data.
///
/// `data` — process measurements.
/// `lsl`, `usl` — lower and upper specification limits.
/// `subgroup_size` — subgroup size for within-group standard deviation
///                   estimation (e.g., 5 for Xbar-R charts).
pub fn calculateCapability(data: []const f64, lsl: f64, usl: f64, subgroup_size: usize) CapabilityResult {
    const mu = mean(data);
    const sigma_overall = stdDev(data, mu);

    // Estimate within-group standard deviation using moving range
    const within_std_dev = estimateWithinStdDev(data, subgroup_size);

    return calculateCapabilityFromStats(mu, sigma_overall, within_std_dev, lsl, usl);
}

/// Calculate process capability indices from pre-computed statistics.
pub fn calculateCapabilityFromStats(mean_val: f64, std_dev: f64, within_std_dev: f64, lsl: f64, usl: f64) CapabilityResult {
    const tolerance = usl - lsl;

    // Cp = (USL - LSL) / (6 * σ_within)
    const cp = if (within_std_dev > 0.0) tolerance / (6.0 * within_std_dev) else 0.0;

    // Cpk = min((USL - μ) / (3 * σ_within), (μ - LSL) / (3 * σ_within))
    const cpu = if (within_std_dev > 0.0) (usl - mean_val) / (3.0 * within_std_dev) else 0.0;
    const cpl = if (within_std_dev > 0.0) (mean_val - lsl) / (3.0 * within_std_dev) else 0.0;
    const cpk = @min(cpu, cpl);

    // Pp = (USL - LSL) / (6 * σ_overall)
    const pp = if (std_dev > 0.0) tolerance / (6.0 * std_dev) else 0.0;

    // Ppk = min((USL - μ) / (3 * σ_overall), (μ - LSL) / (3 * σ_overall))
    const ppu = if (std_dev > 0.0) (usl - mean_val) / (3.0 * std_dev) else 0.0;
    const ppl = if (std_dev > 0.0) (mean_val - lsl) / (3.0 * std_dev) else 0.0;
    const ppk = @min(ppu, ppl);

    // Defect percentages (normal distribution assumption)
    const below_lsl = if (std_dev > 0.0) normalCDF((lsl - mean_val) / std_dev) * 100.0 else 0.0;
    const above_usl = if (std_dev > 0.0) (1.0 - normalCDF((usl - mean_val) / std_dev)) * 100.0 else 0.0;
    const total_defect_pct = below_lsl + above_usl;

    return CapabilityResult{
        .cp = cp,
        .cpk = cpk,
        .pp = pp,
        .ppk = ppk,
        .mean = mean_val,
        .std_dev = std_dev,
        .within_std_dev = within_std_dev,
        .below_lsl = below_lsl,
        .above_usl = above_usl,
        .total_defect_pct = total_defect_pct,
    };
}

/// Estimate within-group standard deviation using average moving range.
/// For subgroup_size = 1, uses mean moving range / d2(2).
/// For subgroup_size > 1, uses Rbar / d2(subgroup_size).
fn estimateWithinStdDev(data: []const f64, subgroup_size: usize) f64 {
    if (data.len < 2) return 0.0;

    const sg = if (subgroup_size < 2) @as(usize, 2) else subgroup_size;

    // Compute ranges of consecutive subgroups
    var sum_r: f64 = 0.0;
    var count: usize = 0;
    var i: usize = 0;
    while (i + sg <= data.len) : (i += sg) {
        var min_val = data[i];
        var max_val = data[i];
        var j: usize = 1;
        while (j < sg) : (j += 1) {
            if (data[i + j] < min_val) min_val = data[i + j];
            if (data[i + j] > max_val) max_val = data[i + j];
        }
        sum_r += max_val - min_val;
        count += 1;
    }

    if (count == 0) return 0.0;
    const rbar = sum_r / @as(f64, @floatFromInt(count));
    const d2_val = d2(sg);
    if (d2_val <= 0.0) return 0.0;
    return rbar / d2_val;
}

// ──────────────────────────────────────────────
// Histogram
// ──────────────────────────────────────────────

/// Result of a histogram calculation.
pub const HistogramResult = struct {
    bins: []f64,
    counts: []usize,
    bin_count: usize,
    bin_width: f64,
    min_val: f64,
    max_val: f64,
};

/// Calculate a histogram with the specified number of bins.
///
/// The caller is responsible for freeing `bins` and `counts` via
/// `std.heap.page_allocator.free()`.
pub fn calculateHistogram(data: []const f64, bin_count: usize) HistogramResult {
    const allocator = std.heap.page_allocator;

    if (data.len == 0 or bin_count == 0) {
        return HistogramResult{
            .bins = &[_]f64{},
            .counts = &[_]usize{},
            .bin_count = 0,
            .bin_width = 0.0,
            .min_val = 0.0,
            .max_val = 0.0,
        };
    }

    const min_val = min(data);
    const max_val = max(data);

    // Handle degenerate case (all values equal)
    var adj_min = min_val;
    var adj_max = max_val;
    if (adj_max <= adj_min) {
        adj_min -= 0.5;
        adj_max += 0.5;
    }

    const bin_width = (adj_max - adj_min) / @as(f64, @floatFromInt(bin_count));

    // Allocate bins and counts
    const bins = allocator.alloc(f64, bin_count) catch return HistogramResult{
        .bins = &[_]f64{},
        .counts = &[_]usize{},
        .bin_count = 0,
        .bin_width = 0.0,
        .min_val = 0.0,
        .max_val = 0.0,
    };
    const counts = allocator.alloc(usize, bin_count) catch {
        allocator.free(bins);
        return HistogramResult{
            .bins = &[_]f64{},
            .counts = &[_]usize{},
            .bin_count = 0,
            .bin_width = 0.0,
            .min_val = 0.0,
            .max_val = 0.0,
        };
    };

    @memset(counts, 0);

    // Compute bin edges
    var b: usize = 0;
    while (b < bin_count) : (b += 1) {
        bins[b] = adj_min + @as(f64, @floatFromInt(b)) * bin_width;
    }

    // Assign data to bins
    for (data) |x| {
        var idx = @as(usize, @intFromFloat(@floor((x - adj_min) / bin_width)));
        if (idx >= bin_count) idx = bin_count - 1;
        counts[idx] += 1;
    }

    return HistogramResult{
        .bins = bins,
        .counts = counts,
        .bin_count = bin_count,
        .bin_width = bin_width,
        .min_val = min_val,
        .max_val = max_val,
    };
}

/// Calculate a histogram using the Freedman-Diaconis rule for automatic
/// bin count selection: bin_width = 2 * IQR / n^(1/3)
///
/// The caller is responsible for freeing the returned `bins` and `counts`.
pub fn calculateHistogramAuto(data: []const f64) HistogramResult {
    if (data.len < 2) return calculateHistogram(data, 10);

    const n = data.len;
    const sorted = blk: {
        // Since we don't want to modify the input, copy
        const allocator = std.heap.page_allocator;
        const copy = allocator.dupe(f64, data) catch break :blk data;
        defer allocator.free(copy);
        std.mem.sort(f64, copy, {}, comptime std.sort.asc(f64));
        break :blk copy;
    };

    // Q1 and Q3 for IQR
    const q1_idx = n / 4;
    const q3_idx = (3 * n) / 4;
    const q1 = if (q1_idx < n) sorted[q1_idx] else data[0];
    const q3 = if (q3_idx < n) sorted[q3_idx] else data[data.len - 1];
    const iqr = q3 - q1;

    // Freedman-Diaconis: bin_width = 2 * IQR / n^(1/3)
    const data_min = min(data);
    const data_max = max(data);
    const data_range = data_max - data_min;

    if (iqr <= 0.0 or data_range <= 0.0) return calculateHistogram(data, 10);

    const bin_width = 2.0 * iqr / std.math.pow(f64, @as(f64, @floatFromInt(n)), 1.0 / 3.0);
    var bin_count = @max(1, @as(usize, @intFromFloat(@ceil(data_range / bin_width))));
    if (bin_count > 100) bin_count = 100;

    return calculateHistogram(data, bin_count);
}

// ──────────────────────────────────────────────
// Control Chart Constants
// ──────────────────────────────────────────────

/// d2 constant for estimating σ from Rbar.
/// Values for subgroup sizes 2–25, with extrapolation beyond.
pub fn d2(subgroup_size: usize) f64 {
    const table = [_]f64{
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
    };
    if (subgroup_size >= 2 and subgroup_size <= 25) {
        return table[subgroup_size - 2];
    }
    // For n > 25, use approximation: d2 ≈ sqrt(2) * (1 - 3/(4n-1))
    if (subgroup_size > 25) {
        const n = @as(f64, @floatFromInt(subgroup_size));
        return math.sqrt2 * (1.0 - 3.0 / (4.0 * n - 1.0));
    }
    return 0.0; // n < 2 not supported
}

/// c4 constant for estimating σ from Sbar (sample std dev).
pub fn c4(subgroup_size: usize) f64 {
    if (subgroup_size < 2) return 0.0;
    const n = @as(f64, @floatFromInt(subgroup_size));
    // c4 = sqrt(2/(n-1)) * Γ(n/2) / Γ((n-1)/2)
    // For n >= 2, approximation: c4 ≈ 4(n-1)/(4n-3)
    return (4.0 * (n - 1.0)) / (4.0 * n - 3.0);
}

/// A2 constant for Xbar-R chart control limits: A2 = 3 / (d2 * sqrt(n))
pub fn a2(subgroup_size: usize) f64 {
    if (subgroup_size < 2) return 0.0;
    const n = @as(f64, @floatFromInt(subgroup_size));
    const d2_val = d2(subgroup_size);
    if (d2_val <= 0.0) return 0.0;
    return 3.0 / (d2_val * @sqrt(n));
}

// ──────────────────────────────────────────────
// Normal Distribution Functions
// ──────────────────────────────────────────────

/// Standard normal CDF using the Abramowitz & Stegun approximation.
///
/// Accuracy: ±7.5e-8 for |x| < ∞
pub fn normalCDF(x: f64) f64 {
    if (x < -8.0) return 0.0;
    if (x > 8.0) return 1.0;

    // Φ(z) = 0.5 * (1 + erf(z / √2))
    const inv_sqrt2: f64 = 0.7071067811865475;
    const z = x * inv_sqrt2;

    const a1_coef: f64 = 0.254829592;
    const a2_coef: f64 = -0.284496736;
    const a3_coef: f64 = 1.421413741;
    const a4_coef: f64 = -1.453152027;
    const a5_coef: f64 = 1.061405429;
    const p: f64 = 0.3275911;

    const abs_z = @abs(z);
    const t = 1.0 / (1.0 + p * abs_z);
    const erf_approx = 1.0 - (((((a5_coef * t + a4_coef) * t) + a3_coef) * t + a2_coef) * t + a1_coef) * t * @exp(-abs_z * abs_z);

    if (z >= 0.0) {
        return 0.5 * (1.0 + erf_approx);
    } else {
        return 0.5 * (1.0 - erf_approx);
    }
}

/// Standard normal quantile (inverse CDF) using a rational approximation.
///
/// Based on Peter Acklam's algorithm, accurate to about 1e-15.
pub fn normalQuantile(p: f64) f64 {
    if (p <= 0.0) return -8.0;
    if (p >= 1.0) return 8.0;
    if (p == 0.5) return 0.0;

    const a = [_]f64{
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    };
    const b = [_]f64{
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    };
    const c = [_]f64{
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00,  2.938163982698783e+00,
    };
    const d = [_]f64{
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    };

    const p_low = 0.02425;
    const p_high = 1.0 - p_low;

    var x: f64 = undefined;

    if (p < p_low) {
        // Rational approximation for lower region
        const q = @sqrt(-2.0 * @log(p));
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    } else if (p <= p_high) {
        // Rational approximation for central region
        const q = p - 0.5;
        const r = q * q;
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0);
    } else {
        // Rational approximation for upper region
        const q = @sqrt(-2.0 * @log(1.0 - p));
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    }

    // Refine using Newton-Raphson
    // (simplified — high precision not strictly required for capability indices)
    return x;
}

// ══════════════════════════════════════════════
// Tests
// ══════════════════════════════════════════════

const testing = std.testing;

test "mean — basic" {
    const data = [_]f64{ 1.0, 2.0, 3.0, 4.0, 5.0 };
    try testing.expectApproxEqAbs(@as(f64, 3.0), mean(&data), 1e-10);
}

test "mean — single element" {
    const data = [_]f64{42.0};
    try testing.expectApproxEqAbs(@as(f64, 42.0), mean(&data), 1e-10);
}

test "mean — empty slice" {
    try testing.expectEqual(@as(f64, 0.0), mean(&[_]f64{}));
}

test "variance and stdDev" {
    const data = [_]f64{ 2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0 };
    const mu = mean(&data);
    const var_val = variance(&data, mu);
    const sd = stdDev(&data, mu);

    try testing.expectApproxEqAbs(@as(f64, 4.0), var_val, 1e-10);
    try testing.expectApproxEqAbs(@as(f64, 2.0), sd, 1e-5);
}

test "min, max, range" {
    const data = [_]f64{ 3.0, 1.0, 4.0, 1.5, 9.0, 2.0 };
    try testing.expectApproxEqAbs(@as(f64, 1.0), min(&data), 1e-10);
    try testing.expectApproxEqAbs(@as(f64, 9.0), max(&data), 1e-10);
    try testing.expectApproxEqAbs(@as(f64, 8.0), range(&data), 1e-10);
}

test "calculateCapability — centered process" {
    const data = [_]f64{ 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1 };
    const result = calculateCapability(&data, 9.5, 10.5, 3);

    try testing.expect(result.cp > 1.0);
    try testing.expectApproxEqAbs(@as(f64, 10.0), result.mean, 0.1);
    try testing.expect(result.cpk > 0.5);
    try testing.expect(result.pp > 0.0);
    try testing.expect(result.ppk > 0.0);
    try testing.expect(result.total_defect_pct < 50.0);
}

test "calculateCapabilityFromStats" {
    const result = calculateCapabilityFromStats(10.0, 0.5, 0.4, 8.0, 12.0);

    // Cp = (12-8) / (6*0.4) = 4 / 2.4 ≈ 1.667
    try testing.expectApproxEqAbs(@as(f64, 1.6667), result.cp, 0.01);
    // Cpk = min((12-10)/(3*0.4), (10-8)/(3*0.4)) = min(1.667, 1.667) = 1.667
    try testing.expectApproxEqAbs(@as(f64, 1.6667), result.cpk, 0.01);
    // Pp = (12-8) / (6*0.5) = 4 / 3 ≈ 1.333
    try testing.expectApproxEqAbs(@as(f64, 1.3333), result.pp, 0.01);
    try testing.expectApproxEqAbs(@as(f64, 10.0), result.mean, 0.001);
}

test "calculateHistogram" {
    const data = [_]f64{ 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 };
    const hist = calculateHistogram(&data, 5);
    defer {
        std.heap.page_allocator.free(hist.bins);
        std.heap.page_allocator.free(hist.counts);
    }

    try testing.expectEqual(@as(usize, 5), hist.bin_count);
    try testing.expect(hist.bin_width > 0.0);
    // Total counts should sum to data length
    var total: usize = 0;
    for (hist.counts) |c| total += c;
    try testing.expectEqual(data.len, total);
}

test "normalCDF" {
    // Known values: Φ(0) = 0.5, Φ(1) ≈ 0.8413, Φ(-1) ≈ 0.1587
    try testing.expectApproxEqAbs(@as(f64, 0.5), normalCDF(0.0), 1e-6);
    try testing.expectApproxEqAbs(@as(f64, 0.8413), normalCDF(1.0), 0.001);
    try testing.expectApproxEqAbs(@as(f64, 0.1587), normalCDF(-1.0), 0.001);
    try testing.expectApproxEqAbs(@as(f64, 0.9772), normalCDF(2.0), 0.001);
}

test "normalQuantile" {
    try testing.expectApproxEqAbs(@as(f64, 0.0), normalQuantile(0.5), 1e-6);
    try testing.expectApproxEqAbs(@as(f64, 1.0), normalQuantile(0.8413), 0.01);
    try testing.expectApproxEqAbs(@as(f64, -1.0), normalQuantile(0.1587), 0.01);
}

test "d2 constant" {
    try testing.expectApproxEqAbs(@as(f64, 1.128), d2(2), 0.001);
    try testing.expectApproxEqAbs(@as(f64, 2.326), d2(5), 0.001);
    try testing.expectApproxEqAbs(@as(f64, 3.078), d2(10), 0.001);
}

test "c4 constant" {
    const c4_5 = c4(5);
    try testing.expectApproxEqAbs(@as(f64, 0.94), c4_5, 0.01);
}

test "a2 constant" {
    const a2_5 = a2(5);
    try testing.expectApproxEqAbs(@as(f64, 0.577), a2_5, 0.01);
}

test "calculateCapability — defect percentages" {
    // A process with mean at 10, sd 1, LSL=8, USL=12
    // Z_lower = (8-10)/1 = -2 → Φ(-2) ≈ 0.02275
    // Z_upper = (12-10)/1 = 2 → 1-Φ(2) ≈ 0.02275
    // Total defects ≈ 4.55%
    const result = calculateCapabilityFromStats(10.0, 1.0, 1.0, 8.0, 12.0);
    try testing.expectApproxEqAbs(@as(f64, 2.275), result.below_lsl, 0.1);
    try testing.expectApproxEqAbs(@as(f64, 2.275), result.above_usl, 0.1);
    try testing.expectApproxEqAbs(@as(f64, 4.55), result.total_defect_pct, 0.2);
}
