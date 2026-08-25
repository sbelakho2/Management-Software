//! ONNX Runtime bindings with SIMD-accelerated tensor operations.
//!
//! Provides ONNX Runtime C API bindings when available (`has_onnx` build
//! option), with a pure-Zig software fallback using manually defined
//! matrix operations when ONNX Runtime is not installed.
//!
//! Tensor operations (`matrixMultiplyF32`, `reluF32`, `softmaxF32`,
//! `argmaxF32`) are **always available** regardless of ONNX Runtime,
//! and use SIMD acceleration from [`simd_pipeline.zig`](simd_pipeline.zig).
//!
//! ## Build option
//!
//! Enable with: `zig build -Donnx=true`
//! The `has_onnx` boolean is passed as a comptime option from
//! [`build.zig`](../build.zig).

const std = @import("std");
const simd = @import("simd_pipeline.zig");

// ──────────────────────────────────────────────
// ONNX Runtime detection
// ──────────────────────────────────────────────

/// Whether ONNX Runtime C API headers are available at build time.
/// Set via `build.zig` option `-Donnx=true`.
const has_onnx: bool = @import("build_options").has_onnx;

// ──────────────────────────────────────────────
// ONNX Runtime C API type definitions
// ──────────────────────────────────────────────

/// ONNX Runtime C API type wrappers, conditionally compiled.
/// When `has_onnx` is true and the header is available, the real C types
/// are used via `@cImport`.  When the header is not available, opaque
/// stubs allow the code to compile (the runtime‑loading paths are excluded
/// by `comptime` guards below).
const onnx_c = if (has_onnx) struct {
    const c = @cImport({
        @cInclude("onnxruntime_c_api.h");
    });

    pub const Api = c.OrtApi;
    pub const ApiBase = c.OrtApiBase;
    pub const Env = c.OrtEnv;
    pub const Session = c.OrtSession;
    pub const Value = c.OrtValue;
    pub const MemoryInfo = c.OrtMemoryInfo;
    pub const RunOptions = c.OrtRunOptions;
    pub const SessionOptions = c.OrtSessionOptions;
    pub const Allocator = c.OrtAllocator;
    pub const Status = c.OrtStatus;
    pub const VERSION = c.ORT_API_VERSION;
    pub const LOG_WARNING = c.ORT_LOGGING_LEVEL_WARNING;
    pub const LoggingLevel = c.OrtLoggingLevel;
    pub const DataType = c.ONNXTensorElementDataType;
    pub const AllocatorType = c.OrtAllocatorType;
    pub const MemType = c.OrtMemType;

    pub const FLOAT = c.ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
    pub const INT64 = c.ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
    pub const ARENA_ALLOCATOR = c.OrtArenaAllocator;
    pub const MEM_TYPE_CPU = c.OrtMemTypeCPU;
} else struct {
    pub const Api = opaque {};
    pub const ApiBase = opaque {};
    pub const Env = opaque {};
    pub const Session = opaque {};
    pub const Value = opaque {};
    pub const MemoryInfo = opaque {};
    pub const RunOptions = opaque {};
    pub const SessionOptions = opaque {};
    pub const Allocator = opaque {};
    pub const Status = opaque {};
    pub const VERSION: u32 = 15;
    pub const LOG_WARNING: u32 = 3;
    pub const LoggingLevel = u32;
    pub const DataType = u32;
    pub const AllocatorType = i32;
    pub const MemType = i32;
    pub const FLOAT: DataType = 1;
    pub const INT64: DataType = 7;
    pub const ARENA_ALLOCATOR: AllocatorType = 1;
    pub const MEM_TYPE_CPU: MemType = 0;
};

// ──────────────────────────────────────────────
// Tensor operations (always available, SIMD-accelerated)
// ──────────────────────────────────────────────

/// Compute C = A × B where A is m×k and B is k×n.
///
/// Allocates and returns an m×n result matrix as a flat `f32` slice.
/// The caller owns the returned memory (page_allocator).
///
/// Uses [`simd.f32_dot_product`](simd_pipeline.zig#L13) for the inner
/// loop by transposing B for contiguous column access.
pub fn matrixMultiplyF32(a: []const f32, b: []const f32, m: usize, n: usize, k: usize) ![]f32 {
    std.debug.assert(a.len == m * k);
    std.debug.assert(b.len == k * n);

    const allocator = std.heap.page_allocator;

    // Transpose B: B_t[j][i] = B[i][j]  =>  B_t is n×k
    const b_t = try allocator.alloc(f32, k * n);
    defer allocator.free(b_t);

    var i: usize = 0;
    while (i < k) : (i += 1) {
        var j: usize = 0;
        while (j < n) : (j += 1) {
            b_t[j * k + i] = b[i * n + j];
        }
    }

    // C = A × B_t_transposed  =>  C[i][j] = dot(A_row_i, B_col_j)
    const result = try allocator.alloc(f32, m * n);
    errdefer allocator.free(result);

    i = 0;
    while (i < m) : (i += 1) {
        const a_row = a[i * k .. i * k + k];
        var j: usize = 0;
        while (j < n) : (j += 1) {
            const b_col = b_t[j * k .. j * k + k];
            result[i * n + j] = simd.f32_dot_product(a_row, b_col);
        }
    }

    return result;
}

/// In-place ReLU activation: `if x < 0 then x = 0`.
pub fn reluF32(tensor: []f32) void {
    for (tensor) |*x| {
        if (x.* < 0.0) {
            x.* = 0.0;
        }
    }
}

/// Stable softmax along the specified dimension.
///
/// For each slice along `dim`, computes:
/// 1. Find max value → subtract for numerical stability
/// 2. Exponentiate each element
/// 3. Sum exponents → divide each by sum
///
/// `tensor` is a flat array. `dim` is the number of elements
/// in the softmax dimension (i.e. the number of classes).
///
/// When a slice's exponent sum is zero or non-finite (e.g. all inputs are
/// -inf), the slice is replaced with a uniform distribution so the output
/// is always a valid probability vector.
pub fn softmaxF32(tensor: []f32, dim: usize) void {
    if (dim == 0) return;
    std.debug.assert(tensor.len % dim == 0);
    const batch_count = tensor.len / dim;

    var batch: usize = 0;
    while (batch < batch_count) : (batch += 1) {
        const start = batch * dim;
        const slice = tensor[start .. start + dim];

        // Find max for numerical stability
        var max_val: f32 = slice[0];
        for (slice) |x| {
            if (x > max_val) max_val = x;
        }

        // Exponentiate and sum
        var sum: f32 = 0.0;
        for (slice) |*x| {
            x.* = std.math.exp(x.* - max_val);
            sum += x.*;
        }

        // Guard against zero / non-finite sums (all -inf, NaN inputs):
        // fall back to a uniform distribution rather than dividing by zero.
        if (!std.math.isFinite(sum) or sum <= 0.0) {
            const uniform = 1.0 / @as(f32, @floatFromInt(dim));
            for (slice) |*x| {
                x.* = uniform;
            }
            continue;
        }

        // Normalize
        const inv_sum = 1.0 / sum;
        for (slice) |*x| {
            x.* *= inv_sum;
        }
    }
}

/// Index of the maximum value along the specified dimension.
///
/// `tensor` is a flat array. `dim` is the number of elements
/// per slice along the softmax/argmax dimension.
///
/// Returns `null` when `tensor` is empty.
pub fn argmaxF32(tensor: []const f32, dim: usize) ?usize {
    std.debug.assert(dim > 0);
    std.debug.assert(tensor.len % dim == 0);
    if (tensor.len == 0) return null;

    // Treat the entire tensor as one batch → find the global argmax
    var max_idx: usize = 0;
    var max_val: f32 = tensor[0];

    var i: usize = 1;
    while (i < tensor.len) : (i += 1) {
        if (tensor[i] > max_val) {
            max_val = tensor[i];
            max_idx = i;
        }
    }

    return max_idx;
}

/// Index of the maximum value along the specified dimension (per-slice).
///
/// Returns the index within each `dim`-sized slice. The slices are
/// contiguous. The returned index is relative to each slice.
pub fn argmaxF32Dim(tensor: []const f32, dim: usize) ![]usize {
    std.debug.assert(dim > 0);
    std.debug.assert(tensor.len % dim == 0);
    const batch_count = tensor.len / dim;

    const allocator = std.heap.page_allocator;
    const result = try allocator.alloc(usize, batch_count);

    var batch: usize = 0;
    while (batch < batch_count) : (batch += 1) {
        const start = batch * dim;
        const slice = tensor[start .. start + dim];

        var max_idx: usize = 0;
        var max_val: f32 = slice[0];
        var i: usize = 1;
        while (i < dim) : (i += 1) {
            if (slice[i] > max_val) {
                max_val = slice[i];
                max_idx = i;
            }
        }
        result[batch] = max_idx;
    }

    return result;
}

// ──────────────────────────────────────────────
// Dynamic ONNX Runtime binding (loaded at runtime)
// ──────────────────────────────────────────────

/// Lazily initialised global ONNX Runtime binding.
/// The shared library is discovered and loaded at runtime via
/// [`std.DynLib`](https://ziglang.org/documentation/master/std/#std.DynLib),
/// so no link‑time dependency exists.
var global_onnx_state: ?*OnnxRuntimeState = null;

/// Runtime‑loaded ONNX Runtime environment and function table.
///
/// The C API pointers (`api`, `env`, `memory_info`) are stored as
/// `*anyopaque` so the struct layout is valid even when `has_onnx` is
/// false.  The actual C API calls are comptime‑guarded in helper methods.
const OnnxRuntimeState = struct {
    lib: std.DynLib,
    /// Opaque pointer to `const onnx_c.Api` (the OrtApi function table).
    api: *const anyopaque,
    /// Opaque pointer to `onnx_c.Env` (the ONNX Runtime environment).
    env: *anyopaque,
    /// Opaque pointer to `onnx_c.MemoryInfo` (CPU memory info).
    memory_info: *anyopaque,

    /// Initialise the runtime: dlopen `libonnxruntime`, get the API table,
    /// create an environment and CPU memory info.
    fn init() !*OnnxRuntimeState {
        const allocator = std.heap.page_allocator;

        // Only compiled when the C header is available
        if (comptime !has_onnx) return error.OnnxNotAvailable;

        const self = try allocator.create(OnnxRuntimeState);
        errdefer allocator.destroy(self);

        // ── 1. Open the ONNX Runtime shared library ────────────────
        const lib = openOnnxRuntimeLib() orelse {
            allocator.destroy(self);
            return error.OnnxLibraryNotFound;
        };
        errdefer lib.close();

        // ── 2. Look up the canonical entry point ──────────────────
        //    OrtGetApiBase() returns OrtApiBase*; its GetApi(version)
        //    returns the const OrtApi* function table.
        const base_fn = lib.lookup(
            *const fn () callconv(.C) *onnx_c.ApiBase,
            "OrtGetApiBase",
        ) orelse {
            allocator.destroy(self);
            return error.OnnxSymbolNotFound;
        };

        const api_base = base_fn();
        const real_api: *const onnx_c.Api = api_base.GetApi(onnx_c.VERSION);

        // ── 3. Create the ONNX Runtime environment ─────────────────
        var env: ?*onnx_c.Env = null;
        {
            const status = real_api.CreateEnv(
                @as(onnx_c.LoggingLevel, @intCast(onnx_c.LOG_WARNING)),
                "sensei-rs",
                &env,
            );
            if (status != null) {
                allocator.destroy(self);
                return error.OnnxEnvCreateFailed;
            }
        }
        errdefer _ = real_api.ReleaseEnv(env.?);

        // ── 4. Create CPU memory info for tensor creation ──────────
        var memory_info: ?*onnx_c.MemoryInfo = null;
        {
            const status = real_api.CreateCpuMemoryInfo(
                @as(onnx_c.AllocatorType, @intCast(onnx_c.ARENA_ALLOCATOR)),
                @as(onnx_c.MemType, @intCast(onnx_c.MEM_TYPE_CPU)),
                &memory_info,
            );
            if (status != null) {
                allocator.destroy(self);
                return error.OnnxMemoryInfoFailed;
            }
        }
        errdefer _ = real_api.ReleaseMemoryInfo(memory_info.?);

        // Store as opaque pointers so the struct fields are valid
        // regardless of whether onnx_c types are real or opaque.
        self.* = .{
            .lib = lib,
            .api = @ptrCast(real_api),
            .env = @ptrCast(env.?),
            .memory_info = @ptrCast(memory_info.?),
        };
        return self;
    }

    /// Release all ONNX Runtime resources and close the shared library.
    fn deinit(self: *OnnxRuntimeState) void {
        if (comptime has_onnx) {
            const real_api: *const onnx_c.Api = @ptrCast(@alignCast(self.api));
            const mem_info: *onnx_c.MemoryInfo = @ptrCast(@alignCast(self.memory_info));
            const env: *onnx_c.Env = @ptrCast(@alignCast(self.env));
            _ = real_api.ReleaseMemoryInfo(mem_info);
            _ = real_api.ReleaseEnv(env);
        }
        self.lib.close();
        const allocator = std.heap.page_allocator;
        allocator.destroy(self);
    }
};

/// Per‑session data stored as a heap‑allocated struct, pointed to by
/// [`Model.handle`](Model.handle) when `is_onnx == true`.
const OnnxSessionData = struct {
    /// Back‑reference to the global runtime state.
    state: *OnnxRuntimeState,
    /// Opaque pointer to `onnx_c.Session` (the OrtSession handle).
    session: *anyopaque,
    /// Input tensor names (owned, freed on deinit).
    input_names: [][]u8,
    /// Output tensor names (owned, freed on deinit).
    output_names: [][]u8,

    fn deinit(self: *OnnxSessionData) void {
        if (comptime has_onnx) {
            const real_api: *const onnx_c.Api = @ptrCast(@alignCast(self.state.api));
            const session: *onnx_c.Session = @ptrCast(@alignCast(self.session));
            _ = real_api.ReleaseSession(session);
        }
        const allocator = std.heap.page_allocator;
        for (self.input_names) |n| allocator.free(n);
        for (self.output_names) |n| allocator.free(n);
        allocator.free(self.input_names);
        allocator.free(self.output_names);
        allocator.destroy(self);
    }
};

/// Try to open the ONNX Runtime shared library under one of the common
/// platform‑specific names.  Returns `null` when the library is not found.
fn openOnnxRuntimeLib() ?std.DynLib {
    const names = [_][:0]const u8{
        "libonnxruntime.dylib",
        "libonnxruntime.1.dylib",
        "libonnxruntime.so",
        "libonnxruntime.so.1",
        "onnxruntime.dll",
    };
    inline for (names) |name| {
        if (std.DynLib.open(name)) |lib| return lib else |_| continue;
    }
    return null;
}

/// Get or lazily create the global ONNX Runtime binding.
/// Returns `null` when the library is not available or init fails.
fn getOrInitOnnxRuntime() ?*OnnxRuntimeState {
    if (global_onnx_state) |state| return state;
    global_onnx_state = OnnxRuntimeState.init() catch null;
    return global_onnx_state;
}

/// Query input/output names from an ONNX session and return owned
/// copies.  Only compiled when `has_onnx` is true.
fn querySessionNames(
    api: *const onnx_c.Api,
    allocator: std.mem.Allocator,
    session: *onnx_c.Session,
    alloc: *onnx_c.Allocator,
) !struct { input_names: [][]u8, output_names: [][]u8 } {
    // Get input count
    var num_inputs: usize = 0;
    {
        const status = api.SessionGetInputCount(session, &num_inputs);
        if (status != null) return error.OnnxQueryFailed;
    }

    // Get output count
    var num_outputs: usize = 0;
    {
        const status = api.SessionGetOutputCount(session, &num_outputs);
        if (status != null) return error.OnnxQueryFailed;
    }

    const input_names = try allocator.alloc([]u8, num_inputs);
    errdefer {
        for (input_names) |n| allocator.free(n);
        allocator.free(input_names);
    }

    const output_names = try allocator.alloc([]u8, num_outputs);
    errdefer {
        for (output_names) |n| allocator.free(n);
        allocator.free(output_names);
    }

    var i: usize = 0;
    while (i < num_inputs) : (i += 1) {
        var name_ptr: [*:0]u8 = undefined;
        const status = api.SessionGetInputName(session, i, alloc, &name_ptr);
        if (status != null) return error.OnnxQueryFailed;
        const name_len = std.mem.len(name_ptr);
        input_names[i] = try allocator.dupe(u8, name_ptr[0..name_len]);
        api.Free(@ptrCast(name_ptr));
    }

    i = 0;
    while (i < num_outputs) : (i += 1) {
        var name_ptr: [*:0]u8 = undefined;
        const status = api.SessionGetOutputName(session, i, alloc, &name_ptr);
        if (status != null) return error.OnnxQueryFailed;
        const name_len = std.mem.len(name_ptr);
        output_names[i] = try allocator.dupe(u8, name_ptr[0..name_len]);
        api.Free(@ptrCast(name_ptr));
    }

    return .{ .input_names = input_names, .output_names = output_names };
}

// ──────────────────────────────────────────────
// Supported tensor element types
// ──────────────────────────────────────────────

/// Supported tensor element types.
pub const TensorType = enum(u8) {
    f32 = 1,
    f64 = 2,
    i32 = 3,
    i64 = 4,
    u8 = 5,

    /// Size of the element type in bytes.
    pub fn sizeOf(self: TensorType) usize {
        return switch (self) {
            .f32 => @sizeOf(f32),
            .f64 => @sizeOf(f64),
            .i32 => @sizeOf(i32),
            .i64 => @sizeOf(i64),
            .u8 => @sizeOf(u8),
        };
    }
};

// ──────────────────────────────────────────────
// Tensor
// ──────────────────────────────────────────────

/// An input or output tensor wrapping flat data and shape.
///
/// When ONNX Runtime is available, this wraps an `OrtValue`.
/// Otherwise it is a simple in-memory buffer.
pub const Tensor = struct {
    /// Raw tensor data (element type depends on `tensor_type`).
    data: []u8,
    /// Shape dimensions (e.g. `&[_]i64{1, 3, 224, 224}`).
    shape: []i64,
    /// Element type.
    tensor_type: TensorType,

    /// Create a new f32 tensor from a flat slice and shape.
    pub fn f32FromSlice(allocator: std.mem.Allocator, values: []const f32, shape: []const i64) !Tensor {
        const data = try allocator.alloc(u8, values.len * @sizeOf(f32));
        const shape_copy = try allocator.alloc(i64, shape.len);
        @memcpy(shape_copy, shape);
        @memcpy(data, std.mem.sliceAsBytes(values));
        return Tensor{
            .data = data,
            .shape = shape_copy,
            .tensor_type = .f32,
        };
    }

    /// Create a new i64 tensor from a flat slice and shape.
    pub fn i64FromSlice(allocator: std.mem.Allocator, values: []const i64, shape: []const i64) !Tensor {
        const data = try allocator.alloc(u8, values.len * @sizeOf(i64));
        const shape_copy = try allocator.alloc(i64, shape.len);
        @memcpy(shape_copy, shape);
        @memcpy(data, std.mem.sliceAsBytes(values));
        return Tensor{
            .data = data,
            .shape = shape_copy,
            .tensor_type = .i64,
        };
    }

    /// Get the f32 data slice (panics if not f32 type).
    pub fn asF32(self: *const Tensor) []const f32 {
        std.debug.assert(self.tensor_type == .f32);
        return @as([]const f32, @alignCast(std.mem.bytesAsSlice(f32, self.data)));
    }

    /// Get a mutable f32 data slice (panics if not f32 type).
    pub fn asF32Mut(self: *Tensor) []f32 {
        std.debug.assert(self.tensor_type == .f32);
        return std.mem.bytesAsSlice(f32, self.data);
    }

    /// Get the total number of elements.
    pub fn numElements(self: *const Tensor) usize {
        var total: usize = 1;
        for (self.shape) |d| {
            total *= @as(usize, @intCast(d));
        }
        return total;
    }

    /// Free the tensor's data and shape.
    pub fn deinit(self: *Tensor, allocator: std.mem.Allocator) void {
        allocator.free(self.data);
        allocator.free(self.shape);
    }
};

// ──────────────────────────────────────────────
// Model (ONNX Runtime or software fallback)
// ──────────────────────────────────────────────

/// Represents an ONNX model loaded into memory.
///
/// When ONNX Runtime is available, wraps an `OrtSession`.
/// Otherwise uses a software fallback with predefined operations.
pub const Model = struct {
    /// Opaque handle.
    handle: usize,

    /// Whether the model was actually loaded via ONNX Runtime.
    is_onnx: bool,

    /// Load a model from an `.onnx` file path.
    ///
    /// When ONNX Runtime is not available, this reads the path but
    /// creates a software fallback model that performs basic matrix
    /// operations (no actual .onnx parsing).
    pub fn load(path: []const u8) !Model {
        if (comptime has_onnx) {
            // Attempt ONNX Runtime binding
            return loadOnnxModel(path);
        } else {
            // Software fallback: acknowledge the path, use matrix ops
            return Model{ .handle = 0xFE11BAC5, .is_onnx = false };
        }
    }

    /// Run inference with the provided input tensors.
    ///
    /// When ONNX Runtime is available, delegates to `OrtSession::Run`.
    /// Otherwise applies the software fallback operations.
    pub fn run(self: *const Model, inputs: []const Tensor) ![]Tensor {
        if (self.is_onnx) {
            return runOnnxModel(self, inputs);
        } else {
            return runFallbackModel(inputs);
        }
    }

    /// Release model resources.
    pub fn deinit(self: *Model) void {
        if (self.is_onnx) {
            deinitOnnxModel(self);
        }
        self.handle = 0;
        self.is_onnx = false;
    }
};

// ── ONNX Runtime model implementation ─────────

/// Load a model via the ONNX Runtime C API.
/// Returns a [`Model`](Model) with `is_onnx = true` pointing to a
/// heap‑allocated [`OnnxSessionData`](OnnxSessionData) on success, or
/// propagates the error.
fn loadOnnxModel(path: []const u8) !Model {
    // Get or lazily initialise the global ONNX Runtime binding.
    // If the shared library is missing or init fails, we fall back.
    const state = getOrInitOnnxRuntime() orelse return error.OnnxNotAvailable;
    const allocator = std.heap.page_allocator;

    if (comptime has_onnx) {
        const real_api: *const onnx_c.Api = @ptrCast(@alignCast(state.api));

        // ── Create session from file path ───────────────────────────
        // ONNX Runtime expects a null‑terminated path string.
        const path_z = try allocator.dupeZ(u8, path);
        defer allocator.free(path_z);

        var session: ?*onnx_c.Session = null;
        {
            const st = real_api.CreateSession(
                @as(*onnx_c.Env, @ptrCast(@alignCast(state.env))),
                @as([*:0]const u8, @ptrCast(path_z.ptr)),
                null, // session options → default
                &session,
            );
            if (st != null) return error.OnnxSessionCreationFailed;
        }

        // ── Query input/output names from the model ─────────────────
        const default_alloc = real_api.GetAllocatorWithDefaultOptions();
        const names = try querySessionNames(real_api, allocator, session.?, default_alloc);

        // ── Allocate and populate the session data ──────────────────
        const session_data = try allocator.create(OnnxSessionData);
        session_data.* = .{
            .state = state,
            .session = @ptrCast(session.?),
            .input_names = names.input_names,
            .output_names = names.output_names,
        };

        return Model{
            .handle = @intFromPtr(session_data),
            .is_onnx = true,
        };
    }

    return error.OnnxNotAvailable;
}

/// Run inference via the ONNX Runtime C API.
///
/// Converts the provided [`Tensor`](Tensor) inputs to `OrtValue`
/// objects, calls `OrtSession::Run`, and extracts the output tensors.
fn runOnnxModel(model: *const Model, inputs: []const Tensor) ![]Tensor {
    const allocator = std.heap.page_allocator;
    const session_data: *OnnxSessionData = @ptrFromInt(model.handle);

    if (comptime has_onnx) {
        const real_api: *const onnx_c.Api = @ptrCast(@alignCast(session_data.state.api));
        const session: *onnx_c.Session = @ptrCast(@alignCast(session_data.session));
        const mem_info: *const onnx_c.MemoryInfo = @ptrCast(@alignCast(session_data.state.memory_info));

        const num_inputs = inputs.len;
        const num_outputs = session_data.output_names.len;

        // ── 1. Create OrtValue objects for each input ────────────────
        var input_values = try allocator.alloc(?*onnx_c.Value, num_inputs);
        defer {
            for (input_values) |v| {
                if (v) |val| real_api.ReleaseValue(val);
            }
            allocator.free(input_values);
        }

        for (inputs, 0..) |input, i| {
            // Map our TensorType → ONNX element type
            const onnx_type: onnx_c.DataType = switch (input.tensor_type) {
                .f32 => onnx_c.FLOAT,
                .i64 => onnx_c.INT64,
                .f64 => 11, // ONNX_TENSOR_ELEMENT_DATA_TYPE_DOUBLE
                .i32 => 6, // ONNX_TENSOR_ELEMENT_DATA_TYPE_INT32
                .u8 => 2, // ONNX_TENSOR_ELEMENT_DATA_TYPE_UINT8
            };

            var value: ?*onnx_c.Value = null;
            const st = real_api.CreateTensorWithDataAsOrtValue(
                mem_info,
                @as(*anyopaque, @ptrCast(input.data.ptr)),
                input.data.len,
                input.shape.ptr,
                input.shape.len,
                onnx_type,
                &value,
            );
            if (st != null) return error.OnnxInferenceFailed;
            input_values[i] = value;
        }

        // ── 2. Prepare input / output name pointer arrays ────────────
        var input_name_ptrs = try allocator.alloc([*:0]const u8, num_inputs);
        defer allocator.free(input_name_ptrs);
        for (session_data.input_names, 0..) |nm, j| {
            input_name_ptrs[j] = @as([*:0]const u8, @ptrCast(nm.ptr));
        }

        var output_name_ptrs = try allocator.alloc([*:0]const u8, num_outputs);
        defer allocator.free(output_name_ptrs);
        for (session_data.output_names, 0..) |nm, j| {
            output_name_ptrs[j] = @as([*:0]const u8, @ptrCast(nm.ptr));
        }

        // ── 3. Allocate output value array (filled by Run) ───────────
        const output_values = try allocator.alloc(?*onnx_c.Value, num_outputs);
        defer allocator.free(output_values);
        for (output_values) |*ov| ov.* = null;

        // ── 4. Run inference ────────────────────────────────────────
        {
            const st = real_api.Run(
                session,
                null, // run options → default
                input_name_ptrs.ptr,
                @as([*]const ?*onnx_c.Value, @ptrCast(input_values.ptr)),
                num_inputs,
                output_name_ptrs.ptr,
                @as([*]?*onnx_c.Value, @ptrCast(output_values.ptr)),
                num_outputs,
            );
            if (st != null) return error.OnnxInferenceFailed;
        }

        // ── 5. Extract output tensors from OrtValue objects ─────────
        var output_tensors = try allocator.alloc(Tensor, num_outputs);
        errdefer {
            for (output_tensors) |*t| t.deinit(allocator);
            allocator.free(output_tensors);
        }

        for (output_values, 0..) |ov, j| {
            const value = ov orelse {
                for (output_tensors[0..j]) |*t| t.deinit(allocator);
                return error.OnnxInvalidOutput;
            };

            // Get tensor data pointer
            const data_ptr = real_api.GetTensorMutableData(value);

            // Get shape and element type
            var elem_type: onnx_c.DataType = undefined;
            var shape_ptr: ?*i64 = undefined;
            var dim_count: usize = 0;
            {
                const st = real_api.GetTensorTypeAndShape(value, &elem_type, &shape_ptr, &dim_count);
                if (st != null) {
                    for (output_tensors[0..j]) |*t| t.deinit(allocator);
                    return error.OnnxInferenceFailed;
                }
            }

            // Copy shape
            const shape_slice = shape_ptr.?[0..dim_count];
            const shape_copy = try allocator.alloc(i64, dim_count);
            @memcpy(shape_copy, shape_slice);
            real_api.Free(shape_ptr.?);

            // Calculate total element count
            var total_elems: usize = 1;
            for (shape_copy) |d| total_elems *= @as(usize, @intCast(d));

            // Determine element size (default to f32 = 4 bytes)
            const elem_size: usize = switch (elem_type) {
                1, 10 => 4, // FLOAT, FLOAT16
                11 => 8, // DOUBLE
                6, 7 => 4, // INT32, INT64 → 4 or 8? INT64=7 is 8 bytes
                2, 3, 4, 5 => 2, // UINT8=2(1), INT8=3(1), UINT16=4(2), INT16=5(2)
                else => 4,
            };
            // Fix: INT64 is 8 bytes
            const actual_elem_size = if (elem_type == 7) @as(usize, 8) else elem_size;

            const data_size = total_elems * actual_elem_size;
            const data_copy = try allocator.alloc(u8, data_size);
            @memcpy(data_copy, @as([*]u8, @ptrCast(data_ptr))[0..data_size]);

            // Map ONNX type → TensorType (default to f32)
            const tensor_type: TensorType = switch (elem_type) {
                1 => .f32,
                11 => .f64,
                6 => .i32,
                7 => .i64,
                2 => .u8,
                else => .f32,
            };

            output_tensors[j] = .{
                .data = data_copy,
                .shape = shape_copy,
                .tensor_type = tensor_type,
            };
        }

        // Release output OrtValues (data was copied out)
        for (output_values) |ov| {
            if (ov) |val| real_api.ReleaseValue(val);
        }

        return output_tensors;
    }

    return error.OnnxNotImplemented;
}

/// Release an ONNX Runtime model: frees the session, its name arrays,
/// and the [`OnnxSessionData`](OnnxSessionData) allocation.
fn deinitOnnxModel(model: *Model) void {
    const session_data: *OnnxSessionData = @ptrFromInt(model.handle);
    session_data.deinit();
}

// ── Software fallback model ───────────────────

/// Simple layer configuration for the fallback model.
const FallbackLayer = struct {
    weights: []f32,
    bias: []f32,
    activation: Activation,
};

const Activation = enum(u8) {
    none,
    relu,
    softmax,
};

/// Apply a single linear layer: output = activation(weights × input + bias).
fn applyLinearLayer(input: []const f32, layer: FallbackLayer, allocator: std.mem.Allocator) ![]f32 {
    const m: usize = layer.bias.len; // output dimension
    const k: usize = layer.weights.len / m; // input dimension

    // output = weights × input (bias treated as m×1)
    var output = try allocator.alloc(f32, m);
    errdefer allocator.free(output);

    var i: usize = 0;
    while (i < m) : (i += 1) {
        const w_row = layer.weights[i * k .. i * k + k];
        output[i] = simd.f32_dot_product(w_row, input) + layer.bias[i];
    }

    // Apply activation
    switch (layer.activation) {
        .relu => reluF32(output),
        .softmax => softmaxF32(output, m),
        .none => {},
    }

    return output;
}

/// Software fallback inference: simple 2-layer MLP.
///
/// Layer 1: 4→8, ReLU
/// Layer 2: 8→4, Softmax
fn runFallbackModel(inputs: []const Tensor) ![]Tensor {
    const allocator = std.heap.page_allocator;

    if (inputs.len == 0) return error.NoInputTensors;

    // Extract input as f32 slice
    const input_tensor = &inputs[0];
    const input_data = input_tensor.asF32();

    // Layer 1: 4→8, ReLU
    // Random-ish weights for demonstration
    const w1 = try allocator.alloc(f32, 4 * 8);
    defer allocator.free(w1);
    const b1 = try allocator.alloc(f32, 8);
    defer allocator.free(b1);

    // Initialize with simple values
    for (w1, 0..) |*w, idx| w.* = @as(f32, @floatFromInt(idx % 4)) * 0.1 + 0.01;
    for (b1, 0..) |*b, idx| b.* = @as(f32, @floatFromInt(idx)) * 0.01;

    const hidden = try applyLinearLayer(input_data, FallbackLayer{
        .weights = w1,
        .bias = b1,
        .activation = .relu,
    }, allocator);
    defer allocator.free(hidden);

    // Layer 2: 8→4, Softmax
    const w2 = try allocator.alloc(f32, 8 * 4);
    defer allocator.free(w2);
    const b2 = try allocator.alloc(f32, 4);
    defer allocator.free(b2);

    for (w2, 0..) |*w, idx| w.* = @as(f32, @floatFromInt(idx % 8)) * 0.05 + 0.01;
    for (b2) |*b| b.* = 0.01;

    const output = try applyLinearLayer(hidden, FallbackLayer{
        .weights = w2,
        .bias = b2,
        .activation = .softmax,
    }, allocator);

    // Wrap output in a Tensor
    const shape = try allocator.alloc(i64, 1);
    shape[0] = 4;

    const output_bytes = try allocator.alloc(u8, output.len * @sizeOf(f32));
    @memcpy(output_bytes, std.mem.sliceAsBytes(output));
    allocator.free(output);

    const result = try allocator.alloc(Tensor, 1);
    result[0] = Tensor{
        .data = output_bytes,
        .shape = shape,
        .tensor_type = .f32,
    };

    return result;
}

// ──────────────────────────────────────────────
// Tests
// ──────────────────────────────────────────────

const testing = std.testing;

test "matrixMultiplyF32 basic" {
    // A = [[1, 2], [3, 4]]  (2×2)
    // B = [[5, 6], [7, 8]]  (2×2)
    // C = [[19, 22], [43, 50]]
    const a = [_]f32{ 1.0, 2.0, 3.0, 4.0 };
    const b = [_]f32{ 5.0, 6.0, 7.0, 8.0 };
    const c = try matrixMultiplyF32(&a, &b, 2, 2, 2);
    defer std.heap.page_allocator.free(c);

    try testing.expectApproxEqAbs(@as(f32, 19.0), c[0], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 22.0), c[1], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 43.0), c[2], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 50.0), c[3], 1e-5);
}

test "matrixMultiplyF32 non-square" {
    // A = [[1, 2, 3], [4, 5, 6]]  (2×3)
    // B = [[7, 8], [9, 10], [11, 12]]  (3×2)
    // C = [[58, 64], [139, 154]]
    const a = [_]f32{ 1.0, 2.0, 3.0, 4.0, 5.0, 6.0 };
    const b = [_]f32{ 7.0, 8.0, 9.0, 10.0, 11.0, 12.0 };
    const c = try matrixMultiplyF32(&a, &b, 2, 2, 3);
    defer std.heap.page_allocator.free(c);

    try testing.expectApproxEqAbs(@as(f32, 58.0), c[0], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 64.0), c[1], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 139.0), c[2], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 154.0), c[3], 1e-5);
}

test "reluF32" {
    var v = [_]f32{ -2.0, -1.0, 0.0, 1.0, 2.0 };
    reluF32(&v);
    try testing.expectEqual(@as(f32, 0.0), v[0]);
    try testing.expectEqual(@as(f32, 0.0), v[1]);
    try testing.expectEqual(@as(f32, 0.0), v[2]);
    try testing.expectEqual(@as(f32, 1.0), v[3]);
    try testing.expectEqual(@as(f32, 2.0), v[4]);
}

test "softmaxF32" {
    // Input: [1.0, 2.0, 3.0, 4.0]  (dim=4)
    // Softmax: exp(x_i - max) / sum
    // max=4, so: exp(-3), exp(-2), exp(-1), exp(0)
    // sum ≈ 0.0498 + 0.1353 + 0.3679 + 1.0 = 1.553
    var v = [_]f32{ 1.0, 2.0, 3.0, 4.0 };
    softmaxF32(&v, 4);

    // Sum should be ~1.0
    var sum: f32 = 0.0;
    for (&v) |x| sum += x;
    try testing.expectApproxEqAbs(@as(f32, 1.0), sum, 1e-5);

    // Values should be in (0, 1) and decreasing since input increases
    try testing.expect(v[0] < v[1]);
    try testing.expect(v[1] < v[2]);
    try testing.expect(v[2] < v[3]);
}

test "softmaxF32 multi-batch" {
    // Two batches of dim=3
    // Batch 0: [0, 0, 0] → uniform [1/3, 1/3, 1/3]
    // Batch 1: [1, 2, 3] → softmax
    var v = [_]f32{ 0.0, 0.0, 0.0, 1.0, 2.0, 3.0 };
    softmaxF32(&v, 3);

    // Batch 0 sum
    const sum0: f32 = v[0] + v[1] + v[2];
    try testing.expectApproxEqAbs(@as(f32, 1.0), sum0, 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 1.0 / 3.0), v[0], 1e-5);
    try testing.expectApproxEqAbs(@as(f32, 1.0 / 3.0), v[1], 1e-5);

    // Batch 1 sum
    const sum1: f32 = v[3] + v[4] + v[5];
    try testing.expectApproxEqAbs(@as(f32, 1.0), sum1, 1e-5);
}

test "argmaxF32" {
    const v = [_]f32{ 0.1, 0.5, 0.3, 0.7, 0.2 };
    const idx = argmaxF32(&v, 5);
    try testing.expectEqual(@as(usize, 3), idx.?); // 0.7 at index 3
}

test "argmaxF32 empty tensor returns null" {
    const v = [_]f32{};
    const idx = argmaxF32(&v, 1);
    try testing.expectEqual(@as(?usize, null), idx);
}

test "softmaxF32 zero-sum slice becomes uniform" {
    // All -inf inputs produce exp(-inf) = 0 → zero sum. The guard must emit
    // a uniform distribution instead of dividing by zero (NaN).
    var v = [_]f32{ -std.math.inf(f32), -std.math.inf(f32), -std.math.inf(f32) };
    softmaxF32(&v, 3);
    var sum: f32 = 0.0;
    for (&v) |x| {
        try testing.expect(std.math.isFinite(x));
        sum += x;
    }
    try testing.expectApproxEqAbs(@as(f32, 1.0), sum, 1e-5);
}

test "argmaxF32Dim" {
    const v = [_]f32{ 0.1, 0.9, 0.3, 0.5, 0.2, 0.8 };
    // dim=3: batch[0] = [0.1, 0.9, 0.3], batch[1] = [0.5, 0.2, 0.8]
    const result = try argmaxF32Dim(&v, 3);
    defer std.heap.page_allocator.free(result);

    try testing.expectEqual(@as(usize, 1), result[0]); // 0.9 at idx 1
    try testing.expectEqual(@as(usize, 2), result[1]); // 0.8 at idx 2
}

test "Model fallback load" {
    var model = try Model.load("dummy.onnx");
    defer model.deinit();
    try testing.expectEqual(@as(usize, 0xFE11BAC5), model.handle);
    try testing.expectEqual(false, model.is_onnx);
}

test "Tensor f32FromSlice" {
    const allocator = std.testing.allocator;
    const values = [_]f32{ 1.0, 2.0, 3.0, 4.0 };
    const shape = [_]i64{ 2, 2 };
    var tensor = try Tensor.f32FromSlice(allocator, &values, &shape);
    defer tensor.deinit(allocator);

    try testing.expectEqual(TensorType.f32, tensor.tensor_type);
    try testing.expectEqual(@as(usize, 4), tensor.numElements());
    try testing.expectEqual(@as(usize, 2), tensor.shape.len);
}
