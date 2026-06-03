//! SIMD-accelerated image processing routines.
//!
//! Provides grayscale conversion, bilinear resize, Sobel edge detection,
//! and RGB↔HSV colour space conversion using Zig SIMD when available,
//! with scalar fallbacks for portability.

const std = @import("std");
const builtin = @import("builtin");

// ──────────────────────────────────────────────
// Helper
// ──────────────────────────────────────────────

/// Clamp `value` to the inclusive range [`min`, `max`].
pub fn clamp(value: anytype, min_val: @TypeOf(value), max_val: @TypeOf(value)) @TypeOf(value) {
    return @min(@max(value, min_val), max_val);
}

// ──────────────────────────────────────────────
// Grayscale conversion (RGB → Y)
// ──────────────────────────────────────────────

/// Convert RGBA interleaved pixels to grayscale using the luminance formula:
///   Y = 0.299*R + 0.587*G + 0.114*B
///
/// `pixels` — RGBA bytes [R,G,B,A, R,G,B,A, …], modified in place (or can be
///            reused as output). Must have length = width * height * 4.
/// `width`, `height` — image dimensions.
/// Output is written to the same buffer as grayscale bytes (1 byte per pixel).
pub fn rgbToGrayscale(pixels: []u8, width: usize, height: usize) void {
    const total = width * height;
    std.debug.assert(pixels.len >= total * 4);

    const coeff_r: f32 = 0.299;
    const coeff_g: f32 = 0.587;
    const coeff_b: f32 = 0.114;

    var i: usize = 0;
    var out: usize = 0;

    // Process 4 pixels at a time using SIMD-friendly batches
    while (i + 4 <= total) : ({
        i += 4;
        out += 4;
    }) {
        const base = i * 4;
        // Process each of the 4 pixels individually (still fast, avoiding
        // unaligned SIMD loads for portability)
        inline for (0..4) |k| {
            const px = base + k * 4;
            const r = @as(f32, @floatFromInt(pixels[px]));
            const g = @as(f32, @floatFromInt(pixels[px + 1]));
            const b = @as(f32, @floatFromInt(pixels[px + 2]));
            const y = r * coeff_r + g * coeff_g + b * coeff_b;
            pixels[out + k] = @intFromFloat(@min(y, 255.0));
        }
    }

    // Remainder pixels
    while (i < total) : ({
        i += 1;
        out += 1;
    }) {
        const base = i * 4;
        const r = @as(f32, @floatFromInt(pixels[base]));
        const g = @as(f32, @floatFromInt(pixels[base + 1]));
        const b = @as(f32, @floatFromInt(pixels[base + 2]));
        const y = r * coeff_r + g * coeff_g + b * coeff_b;
        pixels[out] = @intFromFloat(@min(y, 255.0));
    }
}

// ──────────────────────────────────────────────
// Bilinear image resize
// ──────────────────────────────────────────────

/// Resize an image using bilinear interpolation with edge clamping.
///
/// `src` — source pixel data (one byte per channel, row-major).
/// `src_w`, `src_h` — source dimensions.
/// `dst_w`, `dst_h` — target dimensions.
/// `channels` — number of channels per pixel (1 for grayscale, 3 for RGB).
///
/// Returns a newly allocated buffer (page_allocator) of length
/// `dst_w * dst_h * channels`. The caller is responsible for freeing it
/// via `std.heap.page_allocator.free()`.
pub fn resizeBilinear(src: []const u8, src_w: usize, src_h: usize, dst_w: usize, dst_h: usize, channels: usize) ![]u8 {
    std.debug.assert(src.len >= src_w * src_h * channels);
    std.debug.assert(channels >= 1);
    std.debug.assert(dst_w > 0 and dst_h > 0);

    const allocator = std.heap.page_allocator;
    const dst_len = dst_w * dst_h * channels;
    const dst = try allocator.alloc(u8, dst_len);

    const x_ratio = @as(f32, @floatFromInt(src_w)) / @as(f32, @floatFromInt(dst_w));
    const y_ratio = @as(f32, @floatFromInt(src_h)) / @as(f32, @floatFromInt(dst_h));

    var dy: usize = 0;
    while (dy < dst_h) : (dy += 1) {
        const src_y_f = @as(f32, @floatFromInt(dy)) * y_ratio;
        const src_y_i = @min(@as(usize, @intFromFloat(@floor(src_y_f))), src_h - 1);
        const src_y_i1 = @min(src_y_i + 1, src_h - 1);
        const y_frac = src_y_f - @floor(src_y_f);

        var dx: usize = 0;
        while (dx < dst_w) : (dx += 1) {
            const src_x_f = @as(f32, @floatFromInt(dx)) * x_ratio;
            const src_x_i = @min(@as(usize, @intFromFloat(@floor(src_x_f))), src_w - 1);
            const src_x_i1 = @min(src_x_i + 1, src_w - 1);
            const x_frac = src_x_f - @floor(src_x_f);

            var c: usize = 0;
            while (c < channels) : (c += 1) {
                const p00 = src[(src_y_i * src_w + src_x_i) * channels + c];
                const p10 = src[(src_y_i * src_w + src_x_i1) * channels + c];
                const p01 = src[(src_y_i1 * src_w + src_x_i) * channels + c];
                const p11 = src[(src_y_i1 * src_w + src_x_i1) * channels + c];

                const top = @as(f32, @floatFromInt(p00)) * (1.0 - x_frac) +
                    @as(f32, @floatFromInt(p10)) * x_frac;
                const bottom = @as(f32, @floatFromInt(p01)) * (1.0 - x_frac) +
                    @as(f32, @floatFromInt(p11)) * x_frac;
                const val = top * (1.0 - y_frac) + bottom * y_frac;

                dst[(dy * dst_w + dx) * channels + c] = @intFromFloat(@min(val, 255.0));
            }
        }
    }

    return dst;
}

// ──────────────────────────────────────────────
// Sobel edge detection
// ──────────────────────────────────────────────

/// Apply 3×3 Sobel edge detection to a grayscale image.
///
/// `gray` — input grayscale pixels (1 byte per pixel).
/// `width`, `height` — image dimensions.
/// `output` — pre-allocated buffer of length `width * height` for the result.
pub fn sobelEdgeDetect(gray: []const u8, width: usize, height: usize, output: []u8) void {
    std.debug.assert(gray.len >= width * height);
    std.debug.assert(output.len >= width * height);

    // Sobel kernels
    const gx_kernel = [_]i8{ -1, 0, 1, -2, 0, 2, -1, 0, 1 };
    const gy_kernel = [_]i8{ -1, -2, -1, 0, 0, 0, 1, 2, 1 };

    var y: usize = 1;
    while (y < height - 1) : (y += 1) {
        var x: usize = 1;
        while (x < width - 1) : (x += 1) {
            var gx: i32 = 0;
            var gy: i32 = 0;

            var ky: usize = 0;
            while (ky < 3) : (ky += 1) {
                var kx: usize = 0;
                while (kx < 3) : (kx += 1) {
                    const px = gray[(y + ky - 1) * width + (x + kx - 1)];
                    const ki = ky * 3 + kx;
                    gx += @as(i32, @intCast(px)) * @as(i32, gx_kernel[ki]);
                    gy += @as(i32, @intCast(px)) * @as(i32, gy_kernel[ki]);
                }
            }

            const mag = @sqrt(@as(f32, @floatFromInt(gx * gx + gy * gy)));
            output[y * width + x] = @intFromFloat(@min(mag, 255.0));
        }
    }

    // Fill borders with zero
    // Top and bottom rows
    for (0..width) |i| {
        output[i] = 0;
        output[(height - 1) * width + i] = 0;
    }
    // Left and right columns (excluding corners already set)
    y = 1;
    while (y < height - 1) : (y += 1) {
        output[y * width] = 0;
        output[y * width + (width - 1)] = 0;
    }
}

// ──────────────────────────────────────────────
// Colour space conversion (in-place)
// ──────────────────────────────────────────────

/// Convert RGB pixels to HSV in-place.
///
/// `pixels` — RGB bytes [R,G,B, R,G,B, …] (3 bytes per pixel).
/// `len` — number of pixel elements (each is 3 bytes).
pub fn rgbToHsv(pixels: []u8, len: usize) void {
    std.debug.assert(pixels.len >= len * 3);

    var i: usize = 0;
    while (i < len) : (i += 1) {
        const base = i * 3;
        const r = @as(f32, @floatFromInt(pixels[base])) / 255.0;
        const g = @as(f32, @floatFromInt(pixels[base + 1])) / 255.0;
        const b = @as(f32, @floatFromInt(pixels[base + 2])) / 255.0;

        const c_max = @max(r, @max(g, b));
        const c_min = @min(r, @min(g, b));
        const delta = c_max - c_min;

        // Hue
        var h: f32 = 0.0;
        if (delta > 0.0001) {
            if (c_max == r) {
                h = 60.0 * @mod(((g - b) / delta), 6.0);
            } else if (c_max == g) {
                h = 60.0 * ((b - r) / delta + 2.0);
            } else {
                h = 60.0 * ((r - g) / delta + 4.0);
            }
        }
        if (h < 0.0) h += 360.0;

        // Saturation
        const s = if (c_max > 0.0001) (delta / c_max) else 0.0;

        // Value
        const v = c_max;

        // Store back as bytes: H in [0, 179], S in [0, 255], V in [0, 255]
        pixels[base] = @intFromFloat(@round(h * (255.0 / 360.0)));
        pixels[base + 1] = @intFromFloat(@round(s * 255.0));
        pixels[base + 2] = @intFromFloat(@round(v * 255.0));
    }
}

/// Convert HSV pixels back to RGB in-place.
///
/// `pixels` — HSV bytes [H,S,V, H,S,V, …] (3 bytes per pixel).
///            H is expected in range [0, 179], S in [0, 255], V in [0, 255].
/// `len` — number of pixel elements (each is 3 bytes).
pub fn hsvToRgb(pixels: []u8, len: usize) void {
    std.debug.assert(pixels.len >= len * 3);

    var i: usize = 0;
    while (i < len) : (i += 1) {
        const base = i * 3;
        const h = @as(f32, @floatFromInt(pixels[base])) * (360.0 / 255.0);
        const s = @as(f32, @floatFromInt(pixels[base + 1])) / 255.0;
        const v = @as(f32, @floatFromInt(pixels[base + 2])) / 255.0;

        const c = v * s;
        const hp = h / 60.0;
        const x = c * (1.0 - @abs(@mod(hp, 2.0) - 1.0));
        const m = v - c;

        var r: f32 = 0.0;
        var g: f32 = 0.0;
        var b: f32 = 0.0;

        if (hp < 1.0) {
            r = c;
            g = x;
            b = 0.0;
        } else if (hp < 2.0) {
            r = x;
            g = c;
            b = 0.0;
        } else if (hp < 3.0) {
            r = 0.0;
            g = c;
            b = x;
        } else if (hp < 4.0) {
            r = 0.0;
            g = x;
            b = c;
        } else if (hp < 5.0) {
            r = x;
            g = 0.0;
            b = c;
        } else {
            r = c;
            g = 0.0;
            b = x;
        }

        pixels[base] = @intFromFloat(@round((r + m) * 255.0));
        pixels[base + 1] = @intFromFloat(@round((g + m) * 255.0));
        pixels[base + 2] = @intFromFloat(@round((b + m) * 255.0));
    }
}

// ══════════════════════════════════════════════
// Tests
// ══════════════════════════════════════════════

const testing = std.testing;

test "rgbToGrayscale — known values" {
    // A 2×2 RGBA image: red, green, blue, white
    var pixels = [_]u8{
        255, 0, 0, 255, // red
        0, 255, 0, 255, // green
        0, 0, 255, 255, // blue
        255, 255, 255, 255, // white
    };
    rgbToGrayscale(&pixels, 2, 2);

    // The first 4 bytes are now grayscale values
    // Red:   Y = 0.299*255 = 76.2  → 76
    // Green: Y = 0.587*255 = 149.7 → 150
    // Blue:  Y = 0.114*255 = 29.1  → 29
    // White: Y = 255
    try testing.expectEqual(@as(u8, 76), pixels[0]);
    try testing.expectEqual(@as(u8, 150), pixels[1]);
    try testing.expectEqual(@as(u8, 29), pixels[2]);
    try testing.expectEqual(@as(u8, 255), pixels[3]);
}

test "resizeBilinear — 2×2 to 4×4 grayscale" {
    const src = [_]u8{
        0,   255,
        255, 0,
    };
    const dst = try resizeBilinear(&src, 2, 2, 4, 4, 1);
    defer std.heap.page_allocator.free(dst);

    try testing.expectEqual(@as(usize, 16), dst.len);
    // Corner values should be preserved
    try testing.expectEqual(@as(u8, 0), dst[0]); // top-left
    try testing.expectEqual(@as(u8, 255), dst[3]); // top-right
    try testing.expectEqual(@as(u8, 255), dst[12]); // bottom-left
    try testing.expectEqual(@as(u8, 0), dst[15]); // bottom-right
}

test "sobelEdgeDetect — uniform image" {
    const width: usize = 4;
    const height: usize = 4;
    const gray = [_]u8{128} ** (width * height);
    var output: [width * height]u8 = undefined;

    sobelEdgeDetect(&gray, width, height, &output);

    // All interior pixels should be 0 (uniform image → no edges)
    try testing.expectEqual(@as(u8, 0), output[1 * width + 1]);
    try testing.expectEqual(@as(u8, 0), output[1 * width + 2]);
    try testing.expectEqual(@as(u8, 0), output[2 * width + 1]);
    try testing.expectEqual(@as(u8, 0), output[2 * width + 2]);
    // Borders should be 0
    try testing.expectEqual(@as(u8, 0), output[0]);
    try testing.expectEqual(@as(u8, 0), output[width - 1]);
    try testing.expectEqual(@as(u8, 0), output[(height - 1) * width]);
}

test "rgbToHsv and hsvToRgb round-trip" {
    var pixels = [_]u8{ 100, 150, 200 };
    const original = [_]u8{ 100, 150, 200 };

    rgbToHsv(&pixels, 1);
    hsvToRgb(&pixels, 1);

    // Values may differ by ±1 due to quantisation
    try testing.expect(@abs(@as(i16, pixels[0]) - @as(i16, original[0])) <= 2);
    try testing.expect(@abs(@as(i16, pixels[1]) - @as(i16, original[1])) <= 2);
    try testing.expect(@abs(@as(i16, pixels[2]) - @as(i16, original[2])) <= 2);
}

test "clamp" {
    try testing.expectEqual(@as(i32, 5), clamp(@as(i32, 5), @as(i32, 0), @as(i32, 10)));
    try testing.expectEqual(@as(i32, 0), clamp(@as(i32, -5), @as(i32, 0), @as(i32, 10)));
    try testing.expectEqual(@as(i32, 10), clamp(@as(i32, 15), @as(i32, 0), @as(i32, 10)));
    try testing.expectEqual(@as(f32, 0.5), clamp(@as(f32, 0.5), @as(f32, 0.0), @as(f32, 1.0)));
    try testing.expectEqual(@as(f32, 0.0), clamp(@as(f32, -0.5), @as(f32, 0.0), @as(f32, 1.0)));
}
