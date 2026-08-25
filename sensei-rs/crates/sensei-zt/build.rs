//! Build script for sensei-zt.
//!
//! Compiles the Zig static library (from `zig/`) and links it against the
//! Rust crate. Zig is a REQUIRED build component: the high-performance
//! paths (SIMD, ONNX, LLM, image, stats) live in Zig, so silently skipping
//! it would ship a different (slower, non-accelerated) binary without any
//! signal. The only way to build without Zig is the explicit opt-out
//! environment variable `SENSEI_NO_ZIG=1`, which is a deliberate developer
//! choice (e.g. cross-compilation CI) — never an automatic fallback.

fn main() {
    // Allow the custom `no_zig` cfg key used for fallback detection
    println!("cargo::rustc-check-cfg=cfg(no_zig)");

    if std::env::var("SENSEI_NO_ZIG").is_ok() {
        println!("cargo:warning=SENSEI_NO_ZIG is set — building sensei-zt without the Zig library (pure Rust implementations)");
        println!("cargo:rustc-cfg=no_zig");
        return;
    }

    // Locate the `zig` binary — its absence is a build error, not a fallback.
    let zig = match which::which("zig") {
        Ok(path) => path,
        Err(_) => {
            panic!(
                "sensei-zt requires the Zig toolchain (>= 0.15.0). Install Zig \
                 (https://ziglang.org/download/) and ensure `zig` is on PATH, or \
                 explicitly opt out with SENSEI_NO_ZIG=1 if you intend to build \
                 the pure-Rust variant."
            );
        }
    };

    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let workspace_root = std::path::Path::new(&manifest_dir)
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();

    let zig_src = workspace_root.join("zig");

    // Determine the build mode
    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());
    let build_mode = match profile.as_str() {
        "release" => "-Doptimize=ReleaseFast",
        _ => "-Doptimize=Debug",
    };

    // Run `zig build`
    let prefix = workspace_root.join("target").join("zig");
    let status = std::process::Command::new(&zig)
        .args(["build", build_mode, "--prefix"])
        .arg(&prefix)
        .current_dir(&zig_src)
        .status()
        .expect("failed to spawn zig build");

    if !status.success() {
        panic!(
            "`zig build` failed (exit status {status}). The Zig library is a required \
             component of sensei-zt — fix the build failure rather than bypassing it, \
             or explicitly opt out with SENSEI_NO_ZIG=1."
        );
    }

    // Link the Zig static library
    let lib_dir = workspace_root.join("target").join("zig").join("lib");

    println!("cargo:rustc-link-search={}", lib_dir.display());
    println!("cargo:rustc-link-lib=static=sensei_zig");
    println!("cargo:rerun-if-changed={}", zig_src.display());
}
