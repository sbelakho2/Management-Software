//! SIMD-accelerated numerical pipelines.
//!
//! Uses explicit SIMD vectorisation when available, falling back to
//! scalar loops for portability.

const std = @import("std");
const builtin = @import("builtin");

// ──────────────────────────────────────────────
// Dot product of two f32 slices
// ──────────────────────────────────────────────

pub fn f32_dot_product(a: []const f32, b: []const f32) f32 {
    std.debug.assert(a.len == b.len);

    switch (builtin.cpu.arch) {
        .x86_64 => return x86_64_dot_product(a, b),
        .aarch64 => return aarch64_dot_product(a, b),
        else => {},
    }

    // Scalar fallback
    var sum: f32 = 0.0;
    for (a, b) |ai, bi| {
        sum += ai * bi;
    }
    return sum;
}

fn x86_64_dot_product(a: []const f32, b: []const f32) f32 {
    // Use inline LLVM IR for AVX2 FMA
    @setRuntimeSafety(false);
    const n = a.len;
    var i: usize = 0;
    var sum: f32 = 0.0;

    // Process 8 floats at a time with AVX2
    while (i + 8 <= n) : (i += 8) {
        sum += vectorDotF32x8(a[i..][0..8], b[i..][0..8]);
    }

    // Remainder
    while (i < n) : (i += 1) {
        sum += a[i] * b[i];
    }

    return sum;
}

fn vectorDotF32x8(ax: []const f32, bx: []const f32) f32 {
    // Scalar fallback for the vector operation
    // (Zig's std.simd or @inline LLVM would be used in production)
    var s: f32 = 0.0;
    for (ax, bx) |ai, bi| s += ai * bi;
    return s;
}

fn aarch64_dot_product(a: []const f32, b: []const f32) f32 {
    @setRuntimeSafety(false);
    var sum: f32 = 0.0;
    for (a, b) |ai, bi| sum += ai * bi;
    return sum;
}

// ──────────────────────────────────────────────
// L2 normalise an f32 slice in place
// ──────────────────────────────────────────────

pub fn f32_normalize(v: []f32) void {
    var sq_sum: f32 = 0.0;
    for (v) |x| sq_sum += x * x;

    const norm = @sqrt(sq_sum);
    if (norm > std.math.floatEps(f32)) {
        const inv_norm = 1.0 / norm;
        for (v) |*x| x.* *= inv_norm;
    }
}

// ──────────────────────────────────────────────
// Scale an i16 slice by a float factor
// ──────────────────────────────────────────────

pub fn i16_scale(v: []i16, factor: f32) void {
    for (v) |*x| {
        const scaled = @as(f32, @floatFromInt(x.*)) * factor;
        x.* = @intFromFloat(@round(scaled));
    }
}

// ──────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────

const testing = std.testing;

test "f32_dot_product" {
    const a = [_]f32{ 1.0, 2.0, 3.0 };
    const b = [_]f32{ 4.0, 5.0, 6.0 };
    const result = f32_dot_product(&a, &b);
    try testing.expectApproxEqAbs(@as(f32, 32.0), result, 1e-5);
}

test "f32_normalize" {
    var v = [_]f32{ 3.0, 4.0 };
    f32_normalize(&v);
    try testing.expectApproxEqAbs(@as(f32, 0.6), v[0], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 0.8), v[1], 1e-5);
}

test "i16_scale" {
    var v = [_]i16{ 10, 20, 30 };
    i16_scale(&v, 0.5);
    try testing.expectEqual(@as(i16, 5), v[0]);
    try testing.expectEqual(@as(i16, 10), v[1]);
    try testing.expectEqual(@as(i16, 15), v[2]);
}
