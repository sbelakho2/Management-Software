//! Benchmarking helpers for Zig and Rust interop.
//!
//! Provides micro-benchmark routines that are called from Rust
//! via FFI to measure SIMD throughput.

const std = @import("std");
const simd = @import("simd_pipeline.zig");

/// Benchmark the f32 dot product over `iterations` runs.
/// Returns the total time in nanoseconds.
pub fn bench_dot_product(a: []const f32, b: []const f32, iterations: usize) f64 {
    var total_ns: f64 = 0.0;

    for (0..iterations) |_| {
        const start = std.time.nanoTimestamp();
        _ = simd.f32_dot_product(a, b);
        const end = std.time.nanoTimestamp();
        total_ns += @as(f64, @floatFromInt(end - start));
    }

    return total_ns / @as(f64, @floatFromInt(iterations));
}

/// Benchmark the f32 normalize function over `iterations` runs.
pub fn bench_normalize(v: []f32, iterations: usize) f64 {
    var total_ns: f64 = 0.0;

    for (0..iterations) |_| {
        const start = std.time.nanoTimestamp();
        simd.f32_normalize(v);
        const end = std.time.nanoTimestamp();
        total_ns += @as(f64, @floatFromInt(end - start));
    }

    return total_ns / @as(f64, @floatFromInt(iterations));
}

test "bench_dot_product runs without error" {
    const a = [_]f32{ 1.0, 2.0, 3.0, 4.0 };
    const b = [_]f32{ 5.0, 6.0, 7.0, 8.0 };
    const avg_ns = bench_dot_product(&a, &b, 10);
    // Just ensure it runs and returns a reasonable value
    try std.testing.expect(avg_ns >= 0.0);
}
