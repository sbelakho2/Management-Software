//! Zig native library entry point for sensei-zt.
//!
//! Exposes C-compatible functions for SIMD, memory allocation,
//! IPC primitives, ONNX Runtime bindings, tensor operations,
//! LLM inference, image processing, and SPC statistics
//! consumed by the Rust FFI bridge.

const std = @import("std");
const simd = @import("simd_pipeline.zig");
const allocator_module = @import("allocator.zig");
const ipc = @import("ipc.zig");
const benchmarking = @import("benchmarking.zig");
const onnx = @import("onnx_runtime.zig");
const llm = @import("llm.zig");
const image = @import("image.zig");
const stats = @import("stats.zig");

const VERSION: [*:0]const u8 = "0.1.0";

// ──────────────────────────────────────────────
// Version
// ──────────────────────────────────────────────

export fn sensei_zig_version() [*:0]const u8 {
    return VERSION;
}

// ──────────────────────────────────────────────
// SIMD routines
// ──────────────────────────────────────────────

export fn sensei_simd_f32_dot_product(a: [*]const f32, b: [*]const f32, len: usize) f32 {
    return simd.f32_dot_product(a[0..len], b[0..len]);
}

export fn sensei_simd_f32_normalize(v: [*]f32, len: usize) void {
    simd.f32_normalize(v[0..len]);
}

export fn sensei_simd_i16_scale(v: [*]i16, len: usize, factor: f32) void {
    simd.i16_scale(v[0..len], factor);
}

// ──────────────────────────────────────────────
// Arena allocator
// ──────────────────────────────────────────────

var global_arena: allocator_module.ArenaAllocator = undefined;
var global_arena_initialized: bool = false;

export fn sensei_arena_init(capacity: usize) void {
    global_arena = allocator_module.ArenaAllocator.init(capacity);
    global_arena_initialized = true;
}

export fn sensei_arena_alloc(size: usize) ?*anyopaque {
    if (!global_arena_initialized) return null;
    const block = global_arena.alloc(size) orelse return null;
    return @ptrCast(block.ptr);
}

export fn sensei_arena_reset() void {
    if (global_arena_initialized) {
        global_arena.reset();
    }
}

// ──────────────────────────────────────────────
// IPC — named channel send/recv
// ──────────────────────────────────────────────

var global_ipc = ipc.ChannelMap.init(std.heap.page_allocator);

export fn sensei_ipc_send(channel: [*:0]const u8, data: [*]const u8, len: usize) i32 {
    const slice = data[0..len];
    const chan = channel[0..std.mem.len(channel)];
    global_ipc.send(chan, slice) catch return -1;
    return 0;
}

export fn sensei_ipc_recv(channel: [*:0]const u8, out: [*]u8, cap: usize) i32 {
    const chan = channel[0..std.mem.len(channel)];
    const msg = global_ipc.recv(chan) orelse return -1;
    const copy_len = @min(msg.len, cap);
    @memcpy(out[0..copy_len], msg[0..copy_len]);
    return @intCast(copy_len);
}

// ──────────────────────────────────────────────
// Benchmarking helper (called from Rust benchmarks)
// ──────────────────────────────────────────────

export fn sensei_bench_f32_dot_product(a: [*]const f32, b: [*]const f32, len: usize, iterations: usize) f64 {
    return benchmarking.bench_dot_product(a[0..len], b[0..len], iterations);
}

// ══════════════════════════════════════════════
// Tensor operations (SIMD-accelerated)
// ══════════════════════════════════════════════

/// Compute C = A × B where A is m×k, B is k×n.
/// Returns a pointer to the flat f32 result array, caller must free via
/// `std.heap.page_allocator.free()`.
/// On error, returns null.
export fn sensei_tensor_matrix_multiply_f32(
    a: [*]const f32,
    b: [*]const f32,
    m: usize,
    n: usize,
    k: usize,
) ?[*]f32 {
    const result = onnx.matrixMultiplyF32(a[0 .. m * k], b[0 .. k * n], m, n, k) catch return null;
    return result.ptr;
}

/// In-place ReLU activation on an f32 tensor.
export fn sensei_tensor_relu_f32(tensor: [*]f32, len: usize) void {
    onnx.reluF32(tensor[0..len]);
}

/// Stable softmax along the specified dimension.
/// `tensor` must have length divisible by `dim`.
export fn sensei_tensor_softmax_f32(tensor: [*]f32, len: usize, dim: usize) void {
    onnx.softmaxF32(tensor[0..len], dim);
}

/// Argmax (global) — returns the index of the maximum value in the tensor.
export fn sensei_tensor_argmax_f32(tensor: [*]const f32, len: usize, dim: usize) usize {
    return onnx.argmaxF32(tensor[0..len], dim);
}

/// Argmax per-slice — returns a pointer to an array of indices,
/// one per slice of size `dim`. Caller must free via
/// `std.heap.page_allocator.free()`.
/// On error, returns null.
export fn sensei_tensor_argmax_f32_dim(
    tensor: [*]const f32,
    len: usize,
    dim: usize,
) ?[*]usize {
    const result = onnx.argmaxF32Dim(tensor[0..len], dim) catch return null;
    return result.ptr;
}

// ══════════════════════════════════════════════
// ONNX Runtime model lifecycle
// ══════════════════════════════════════════════

/// Load an ONNX model from a file path.
/// Returns an opaque handle (pointer to Model), or null on failure.
export fn sensei_onnx_model_load(path: [*:0]const u8) ?*onnx.Model {
    const path_slice = std.mem.sliceTo(path, 0);
    const model = onnx.Model.load(path_slice) catch return null;

    // Allocate a Model on the heap so Rust can hold the pointer
    const allocator = std.heap.page_allocator;
    const ptr = allocator.create(onnx.Model) catch return null;
    ptr.* = model;
    return ptr;
}

/// Run inference with input tensors and return output tensors.
/// For now, returns a simple status code (0 = success, -1 = error).
export fn sensei_onnx_model_run(
    model: *onnx.Model,
    input_data: [*]const f32,
    input_len: usize,
    output_data: [*]f32,
    output_len: usize,
) i32 {
    // Build a single input tensor from the flat data
    const allocator = std.heap.page_allocator;
    const shape = allocator.alloc(i64, 1) catch return -1;
    defer allocator.free(shape);
    shape[0] = @intCast(input_len);

    var tensor = onnx.Tensor.f32FromSlice(allocator, input_data[0..input_len], shape) catch return -1;
    defer tensor.deinit(allocator);

    const inputs = allocator.alloc(onnx.Tensor, 1) catch return -1;
    defer allocator.free(inputs);
    inputs[0] = tensor;

    const outputs = model.run(inputs) catch return -1;
    defer {
        for (outputs) |*t| t.deinit(allocator);
        allocator.free(outputs);
    }

    if (outputs.len > 0) {
        const out_data = outputs[0].asF32();
        const copy_len = @min(out_data.len, output_len);
        @memcpy(output_data[0..copy_len], out_data[0..copy_len]);
    }

    return 0;
}

/// Release an ONNX model previously loaded via `sensei_onnx_model_load`.
export fn sensei_onnx_model_deinit(model: *onnx.Model) void {
    model.deinit();
    const allocator = std.heap.page_allocator;
    allocator.destroy(model);
}

/// Query whether a model loaded via `sensei_onnx_model_load` is actually
/// backed by ONNX Runtime (`true`) or a software fallback (`false`).
export fn sensei_onnx_model_is_onnx(model: *const onnx.Model) bool {
    return model.is_onnx;
}

// ══════════════════════════════════════════════
// LLM / Chatbot routines
// ══════════════════════════════════════════════

/// Global LlamaRunner instance (owned by the library).
var global_llm_runner: ?*llm.LlamaRunner = null;

/// Initialise the LLaMA runner with a config and flattened weights.
///
/// `config_ptr` points to a `TransformerConfig` struct with dim, n_layers,
/// n_heads, n_kv_heads, vocab_size, max_seq_len.
/// `weights_ptr` points to an array of `weights_len` f32 weight values.
/// `tokenizer` is a pre-initialised Tokenizer (the library takes ownership).
///
/// Returns an opaque handle (pointer to LlamaRunner), or null on failure.
export fn sensei_llm_init(
    config_ptr: *const llm.TransformerConfig,
    weights_ptr: [*]const f32,
    weights_len: usize,
    tokenizer_ptr: ?*llm.Tokenizer,
) ?*anyopaque {
    const allocator = std.heap.page_allocator;
    const weights = weights_ptr[0..weights_len];
    const config = config_ptr.*;

    // Take ownership of the tokenizer (move it), or create a default one
    const tokenizer = if (tokenizer_ptr) |t| t.* else llm.Tokenizer.init(allocator);

    const runner = allocator.create(llm.LlamaRunner) catch return null;
    runner.* = llm.LlamaRunner.init(config, weights, tokenizer, allocator);
    global_llm_runner = runner;
    return @ptrCast(runner);
}

/// Generate a response to the given prompt.
///
/// `runner_ptr` is the opaque handle returned by `sensei_llm_init`.
/// `prompt_ptr` / `prompt_len` specify the input text.
/// `max_tokens` is the maximum number of tokens to generate.
/// `temperature`, `top_k`, `top_p` are sampling parameters.
///
/// Returns a pointer to a null-terminated UTF-8 string allocated with
/// `std.heap.page_allocator`. The caller must free it with
/// `sensei_llm_free_string`.
/// Returns null on error.
export fn sensei_llm_generate(
    runner_ptr: *anyopaque,
    prompt_ptr: [*]const u8,
    prompt_len: usize,
    max_tokens: usize,
    temperature: f32,
    top_k: u32,
    top_p: f32,
) ?[*]u8 {
    const runner: *llm.LlamaRunner = @ptrCast(@alignCast(runner_ptr));
    const prompt = prompt_ptr[0..prompt_len];

    const result = runner.generate(prompt, max_tokens, temperature, top_k, top_p, std.heap.page_allocator) catch return null;
    // Ensure null-terminated
    const null_term = std.heap.page_allocator.alloc(u8, result.len + 1) catch return null;
    @memcpy(null_term[0..result.len], result);
    null_term[result.len] = 0;
    std.heap.page_allocator.free(result);
    return null_term.ptr;
}

/// Free a string previously returned by `sensei_llm_generate`.
export fn sensei_llm_free_string(ptr: [*]u8) void {
    var len: usize = 0;
    while (ptr[len] != 0) : (len += 1) {}
    std.heap.page_allocator.free(ptr[0 .. len + 1]);
}

/// Destroy a LLaMA runner previously created by `sensei_llm_init`.
export fn sensei_llm_deinit(runner_ptr: *anyopaque) void {
    const runner: *llm.LlamaRunner = @ptrCast(@alignCast(runner_ptr));
    runner.deinit();
    const allocator = std.heap.page_allocator;
    allocator.destroy(runner);
    if (global_llm_runner == runner) {
        global_llm_runner = null;
    }
}

/// Software fallback chatbot: takes a prompt string and returns a response.
/// Returns a pointer to a null-terminated UTF-8 string, or null on error.
/// Caller must free with `sensei_llm_free_string`.
export fn sensei_llm_fallback_chat(prompt_ptr: [*]const u8, prompt_len: usize) ?[*]u8 {
    const prompt = prompt_ptr[0..prompt_len];
    const response = llm.fallbackChat(prompt);
    const null_term = std.heap.page_allocator.dupe(u8, response) catch return null;
    return null_term.ptr;
}

// ══════════════════════════════════════════════
// Image processing routines
// ══════════════════════════════════════════════

/// Convert RGBA pixels to grayscale in place.
/// Overwrites the first `width * height` bytes with grayscale values.
export fn sensei_image_rgb_to_grayscale(pixels: [*]u8, width: usize, height: usize) void {
    image.rgbToGrayscale(pixels[0 .. width * height * 4], width, height);
}

/// Resize an image using bilinear interpolation.
/// Returns a pointer to the allocated result buffer, or null on failure.
/// Caller must free with `sensei_image_free`.
export fn sensei_image_resize_bilinear(
    src: [*]const u8,
    src_w: usize,
    src_h: usize,
    dst_w: usize,
    dst_h: usize,
    channels: usize,
) ?[*]u8 {
    const result = image.resizeBilinear(src[0 .. src_w * src_h * channels], src_w, src_h, dst_w, dst_h, channels) catch return null;
    return result.ptr;
}

/// Apply Sobel edge detection to a grayscale image.
/// `output` must be pre-allocated with `width * height` bytes.
export fn sensei_image_sobel_edge_detect(gray: [*]const u8, width: usize, height: usize, output: [*]u8) void {
    image.sobelEdgeDetect(gray[0 .. width * height], width, height, output[0 .. width * height]);
}

/// Free a buffer previously returned by `sensei_image_resize_bilinear`.
export fn sensei_image_free(ptr: [*]u8, size: usize) void {
    const allocator = std.heap.page_allocator;
    const slice = ptr[0..size];
    allocator.free(slice);
}

/// Free a buffer previously allocated by Zig's page_allocator.
/// Must pass the exact pointer and byte count returned by the Zig function.
export fn sensei_free(ptr: [*]u8, size: usize) void {
    const allocator = std.heap.page_allocator;
    const slice = ptr[0..size];
    allocator.free(slice);
}

// ══════════════════════════════════════════════
// SPC Statistics routines
// ══════════════════════════════════════════════

/// Compute the mean of an f64 array.
export fn sensei_stats_mean(data: [*]const f64, len: usize) f64 {
    return stats.mean(data[0..len]);
}

/// Compute the standard deviation of an f64 array.
export fn sensei_stats_std_dev(data: [*]const f64, len: usize, mean_val: f64) f64 {
    return stats.stdDev(data[0..len], mean_val);
}

/// Compute process capability indices from raw data.
/// The result is written to the `result` pointer provided by the caller.
export fn sensei_stats_capability(
    data: [*]const f64,
    len: usize,
    lsl: f64,
    usl: f64,
    subgroup_size: usize,
    result_ptr: *stats.CapabilityResult,
) void {
    const cap = stats.calculateCapability(data[0..len], lsl, usl, subgroup_size);
    result_ptr.* = cap;
}

/// Compute a histogram from raw data.
/// Fills pre-allocated `out_bins` and `out_counts` arrays (each of length `bin_count`).
/// Returns 0 on success, -1 on error.
export fn sensei_stats_histogram(
    data: [*]const f64,
    len: usize,
    bin_count: usize,
    out_bins: [*]f64,
    out_counts: [*]usize,
) i32 {
    const hist = stats.calculateHistogram(data[0..len], bin_count);
    if (hist.bin_count == 0) return -1;

    // Copy results to pre-allocated arrays
    const bins_slice = out_bins[0..@min(hist.bin_count, bin_count)];
    const counts_slice = out_counts[0..@min(hist.bin_count, bin_count)];
    @memcpy(bins_slice, hist.bins[0..bins_slice.len]);
    @memcpy(counts_slice, hist.counts[0..counts_slice.len]);

    // Free the Zig-allocated buffers
    std.heap.page_allocator.free(hist.bins);
    std.heap.page_allocator.free(hist.counts);

    return 0;
}

test {
    @import("std").testing.refAllDecls(@This());
}
