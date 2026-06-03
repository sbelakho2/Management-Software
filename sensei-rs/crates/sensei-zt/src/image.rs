//! SIMD-accelerated image processing routines.
//!
//! Delegates to Zig when the native library is available; otherwise
//! provides pure-Rust fallback implementations that produce identical results.

use sensei_core::error::SenseiError;

// ──────────────────────────────────────────────
// Zig-backed implementations
// ──────────────────────────────────────────────

#[cfg(not(no_zig))]
extern "C" {
    fn sensei_image_rgb_to_grayscale(pixels: *mut u8, width: usize, height: usize);
    fn sensei_image_resize_bilinear(
        src: *const u8,
        src_w: usize,
        src_h: usize,
        dst_w: usize,
        dst_h: usize,
        channels: usize,
    ) -> *mut u8;
    fn sensei_image_sobel_edge_detect(gray: *const u8, width: usize, height: usize, output: *mut u8);
    fn sensei_image_free(ptr: *mut u8, size: usize);
}

/// Convert RGBA pixels to grayscale in place.
///
/// `pixels` must be `width * height * 4` bytes long.
/// The first `width * height` bytes are overwritten with grayscale values.
pub fn rgb_to_grayscale(pixels: &mut [u8], width: usize, height: usize) -> Result<(), SenseiError> {
    let expected_len = width * height * 4;
    if pixels.len() < expected_len {
        return Err(SenseiError::Validation(format!(
            "pixels buffer too short: {} < {}",
            pixels.len(),
            expected_len
        )));
    }

    #[cfg(not(no_zig))]
    {
        unsafe {
            sensei_image_rgb_to_grayscale(pixels.as_mut_ptr(), width, height);
        }
    }

    #[cfg(no_zig)]
    {
        let coeff_r: f32 = 0.299;
        let coeff_g: f32 = 0.587;
        let coeff_b: f32 = 0.114;
        let total = width * height;

        let mut src_idx = 0usize;
        let mut dst_idx = 0usize;

        // Process 4 pixels at a time
        while src_idx + 4 <= total {
            for k in 0..4 {
                let base = (src_idx + k) * 4;
                let r = pixels[base] as f32;
                let g = pixels[base + 1] as f32;
                let b = pixels[base + 2] as f32;
                let y = (r * coeff_r + g * coeff_g + b * coeff_b).min(255.0) as u8;
                pixels[dst_idx + k] = y;
            }
            src_idx += 4;
            dst_idx += 4;
        }

        // Remainder
        while src_idx < total {
            let base = src_idx * 4;
            let r = pixels[base] as f32;
            let g = pixels[base + 1] as f32;
            let b = pixels[base + 2] as f32;
            let y = (r * coeff_r + g * coeff_g + b * coeff_b).min(255.0) as u8;
            pixels[dst_idx] = y;
            src_idx += 1;
            dst_idx += 1;
        }
    }

    Ok(())
}

/// Resize an image using bilinear interpolation.
///
/// `src` — source pixel data (row-major, `channels` bytes per pixel).
/// `src_w`, `src_h` — source dimensions.
/// `dst_w`, `dst_h` — target dimensions.
/// `channels` — bytes per pixel (1 for grayscale, 3 for RGB).
///
/// Returns a newly allocated `Vec<u8>` with the resized image.
pub fn resize_bilinear(
    src: &[u8],
    src_w: usize,
    src_h: usize,
    dst_w: usize,
    dst_h: usize,
    channels: usize,
) -> Result<Vec<u8>, SenseiError> {
    if src_w == 0 || src_h == 0 || dst_w == 0 || dst_h == 0 || channels == 0 {
        return Err(SenseiError::Validation(
            "dimensions must be positive".into(),
        ));
    }

    let dst_len = dst_w * dst_h * channels;
    if src.len() < src_w * src_h * channels {
        return Err(SenseiError::Validation(
            "source buffer too short for given dimensions".into(),
        ));
    }

    #[cfg(not(no_zig))]
    {
        unsafe {
            let ptr = sensei_image_resize_bilinear(
                src.as_ptr(),
                src_w,
                src_h,
                dst_w,
                dst_h,
                channels,
            );
            if ptr.is_null() {
                return Err(SenseiError::Internal(
                    "Zig resize_bilinear returned null".into(),
                ));
            }
            // Copy into a Vec so the Zig allocation can be freed
            let result = std::ptr::slice_from_raw_parts(ptr, dst_len);
            let vec = (*result).to_vec();
            sensei_image_free(ptr, dst_len);
            Ok(vec)
        }
    }

    #[cfg(no_zig)]
    {
        let mut dst = vec![0u8; dst_len];
        let x_ratio = src_w as f32 / dst_w as f32;
        let y_ratio = src_h as f32 / dst_h as f32;

        for dy in 0..dst_h {
            let src_y_f = dy as f32 * y_ratio;
            let src_y_i = (src_y_f.floor() as usize).min(src_h - 1);
            let src_y_i1 = (src_y_i + 1).min(src_h - 1);
            let y_frac = src_y_f - src_y_f.floor();

            for dx in 0..dst_w {
                let src_x_f = dx as f32 * x_ratio;
                let src_x_i = (src_x_f.floor() as usize).min(src_w - 1);
                let src_x_i1 = (src_x_i + 1).min(src_w - 1);
                let x_frac = src_x_f - src_x_f.floor();

                for c in 0..channels {
                    let p00 = src[(src_y_i * src_w + src_x_i) * channels + c] as f32;
                    let p10 = src[(src_y_i * src_w + src_x_i1) * channels + c] as f32;
                    let p01 = src[(src_y_i1 * src_w + src_x_i) * channels + c] as f32;
                    let p11 = src[(src_y_i1 * src_w + src_x_i1) * channels + c] as f32;

                    let top = p00 * (1.0 - x_frac) + p10 * x_frac;
                    let bottom = p01 * (1.0 - x_frac) + p11 * x_frac;
                    let val = top * (1.0 - y_frac) + bottom * y_frac;

                    dst[(dy * dst_w + dx) * channels + c] = (val.min(255.0)) as u8;
                }
            }
        }

        Ok(dst)
    }
}

/// Apply Sobel edge detection to a grayscale image.
///
/// `gray` — input grayscale pixels (1 byte per pixel).
/// `width`, `height` — image dimensions.
///
/// Returns a new `Vec<u8>` of size `width * height` with edge magnitudes.
pub fn sobel_edge_detect(gray: &[u8], width: usize, height: usize) -> Result<Vec<u8>, SenseiError> {
    let expected_len = width * height;
    if gray.len() < expected_len {
        return Err(SenseiError::Validation(format!(
            "gray buffer too short: {} < {}",
            gray.len(),
            expected_len
        )));
    }

    #[cfg(not(no_zig))]
    {
        let mut output = vec![0u8; expected_len];
        unsafe {
            sensei_image_sobel_edge_detect(gray.as_ptr(), width, height, output.as_mut_ptr());
        }
        Ok(output)
    }

    #[cfg(no_zig)]
    {
        let mut output = vec![0u8; expected_len];
        let gx_kernel: [i8; 9] = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
        let gy_kernel: [i8; 9] = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

        for y in 1..height - 1 {
            for x in 1..width - 1 {
                let mut gx: i32 = 0;
                let mut gy: i32 = 0;

                for ky in 0..3 {
                    for kx in 0..3 {
                        let px = gray[(y + ky - 1) * width + (x + kx - 1)] as i32;
                        let ki = ky * 3 + kx;
                        gx += px * gx_kernel[ki] as i32;
                        gy += px * gy_kernel[ki] as i32;
                    }
                }

                let mag = ((gx * gx + gy * gy) as f32).sqrt();
                output[y * width + x] = (mag.min(255.0)) as u8;
            }
        }

        // Borders are already 0 from vec initialization
        Ok(output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rgb_to_grayscale_known_values() {
        // Red, green, blue, white RGBA pixels
        let mut pixels = vec![
            255u8, 0, 0, 255, // red
            0, 255, 0, 255, // green
            0, 0, 255, 255, // blue
            255, 255, 255, 255, // white
        ];
        rgb_to_grayscale(&mut pixels, 2, 2).unwrap();

        // Red:   Y = 0.299*255 ≈ 76
        // Green: Y = 0.587*255 ≈ 149.685 → truncates to 149
        // Blue:  Y = 0.114*255 ≈ 29
        // White: Y = 255
        assert_eq!(pixels[0], 76);
        assert_eq!(pixels[1], 149);
        assert_eq!(pixels[2], 29);
        assert_eq!(pixels[3], 255);
    }

    #[test]
    fn test_resize_bilinear_2x2_to_4x4() {
        let src: Vec<u8> = vec![0, 255, 255, 0];
        let dst = resize_bilinear(&src, 2, 2, 4, 4, 1).unwrap();

        assert_eq!(dst.len(), 16);
        // Corner values should be preserved
        assert_eq!(dst[0], 0); // top-left
        assert_eq!(dst[3], 255); // top-right
        assert_eq!(dst[12], 255); // bottom-left
        assert_eq!(dst[15], 0); // bottom-right
    }

    #[test]
    fn test_sobel_edge_detect_uniform() {
        let gray: Vec<u8> = vec![128; 16]; // 4x4 uniform
        let output = sobel_edge_detect(&gray, 4, 4).unwrap();

        // All interior pixels should be 0 (uniform image → no edges)
        assert_eq!(output[1 * 4 + 1], 0);
        assert_eq!(output[1 * 4 + 2], 0);
        assert_eq!(output[2 * 4 + 1], 0);
        assert_eq!(output[2 * 4 + 2], 0);
        // Borders should be 0
        assert_eq!(output[0], 0);
    }

    #[test]
    fn test_rgb_to_grayscale_error() {
        let mut pixels = vec![0u8; 3]; // Too small for even 1 RGBA pixel
        let result = rgb_to_grayscale(&mut pixels, 1, 1);
        assert!(result.is_err());
    }
}
