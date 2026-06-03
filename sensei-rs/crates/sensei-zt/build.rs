//! Build script for sensei-zt.
//!
//! Compiles the Zig static library (from `zig/`) and links it
//! against the Rust crate when the `zig` feature is enabled.
//!
//! When building without Zig installed, this build script gracefully
//! skips compilation and the crate exposes pure-Rust fallbacks.

fn main() {
    // Allow the custom `no_zig` cfg key used for fallback detection
    println!("cargo::rustc-check-cfg=cfg(no_zig)");
    // Attempt to locate the `zig` binary
    let zig = match which::which("zig") {
        Ok(path) => path,
        Err(_) => {
            println!("cargo:warning=zig not found on PATH — skipping Zig compilation");
            println!("cargo:rustc-cfg=no_zig");
            return;
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
        .args(&[
            "build",
            build_mode,
            "--prefix",
            &prefix.display().to_string(),
        ])
        .current_dir(&zig_src)
        .status()
        .expect("failed to run zig build");

    if !status.success() {
        println!("cargo:warning=zig build failed — falling back to pure Rust implementation");
        println!("cargo:rustc-cfg=no_zig");
        return;
    }

    // Link the Zig static library
    let lib_dir = workspace_root
        .join("target")
        .join("zig")
        .join("lib");

    println!("cargo:rustc-link-search={}", lib_dir.display());
    println!("cargo:rustc-link-lib=static=sensei_zig");
    println!("cargo:rerun-if-changed={}", zig_src.display());
}
