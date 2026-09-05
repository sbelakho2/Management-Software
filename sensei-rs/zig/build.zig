//! Build script for the Zig native library used by sensei-zt.
//!
//! Produces a static library (`libsensei_zig.a`) containing
//! SIMD, arena allocator, IPC primitives, and ONNX Runtime bindings.

const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // ── ONNX Runtime support ──────────────────────────────────────────
    // Enable with: zig build -Donnx=true
    const has_onnx = b.option(bool, "onnx", "Enable ONNX Runtime C API bindings") orelse false;

    // Create a build options module so source files can @import("build_options")
    const options = b.addOptions();
    options.addOption(bool, "has_onnx", has_onnx);

    const lib_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    // The archive is linked into Rust executables, which are PIE on Linux:
    // emit position-independent code so static linking never trips
    // R_X86_64_32 relocations against non-PIC data.
    lib_module.pic = true;

    // Pass `has_onnx` as a build option module
    lib_module.addOptions("build_options", options);

    // Enable SIMD for x86_64 and aarch64
    if (target.result.cpu.arch == .x86_64) {
        lib_module.addCMacro("SENSEI_USE_AVX2", "1");
    } else if (target.result.cpu.arch == .aarch64) {
        lib_module.addCMacro("SENSEI_USE_NEON", "1");
    }

    const lib = b.addLibrary(.{
        .name = "sensei_zig",
        .root_module = lib_module,
    });

    // Strip debug info in release builds
    if (optimize != .Debug) {
        lib_module.strip = true;
    }

    b.installArtifact(lib);

    // Unit tests
    const test_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    test_module.addOptions("build_options", options);

    const lib_unit_tests = b.addTest(.{
        .root_module = test_module,
    });

    const run_lib_unit_tests = b.addRunArtifact(lib_unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_lib_unit_tests.step);
}
