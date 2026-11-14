/*
 * Copyright (C) 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

use std::env;
use std::path::PathBuf;
use std::process::Command;

fn android_api_level() -> u32 {
    let value = env::var("FACEHAL_ANDROID_API").unwrap_or_else(|_| "29".into());
    let api = value
        .parse::<u32>()
        .unwrap_or_else(|_| panic!("FACEHAL_ANDROID_API must be a number, got {value:?}"));
    assert!(api >= 29, "Face HAL Binder requires Android API 29 or newer");
    api
}

fn main() {
    println!("cargo::rerun-if-env-changed=FACEHAL_ANDROID_API");
    println!("cargo::rerun-if-env-changed=BINDER_NDK_LIB_DIR");
    println!("cargo::rerun-if-env-changed=BINDER_PLATFORM_HEADERS");

    let ndk_home = PathBuf::from(env::var("ANDROID_NDK_HOME").unwrap());
    let toolchain = ndk_home.join("toolchains/llvm/prebuilt/linux-x86_64/");
    let sysroot = toolchain.join("sysroot");
    let platform_headers = env::var("BINDER_PLATFORM_HEADERS").unwrap();
    let target = env::var("TARGET").expect("TARGET is not set");
    let api = android_api_level();
    let clang_target = match target.as_str() {
        "aarch64-linux-android" => "aarch64-linux-android",
        "x86_64-linux-android" => "x86_64-linux-android",
        _ if target.ends_with("-android") => panic!("unsupported Android target for Binder: {target}"),
        _ => "",
    };
    let mut bindings = bindgen::Builder::default()
        .clang_arg(format!("--sysroot={}", sysroot.display()))
        .clang_arg("-D__ANDROID_VENDOR__")
        .clang_arg(format!("-I{platform_headers}"))
        // TODO figure out what the "standard" #define is and use that instead
        .header("BinderBindings.hpp")
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
        // Keep in sync with libbinder_ndk_bindgen_flags.txt
        .default_enum_style(bindgen::EnumVariation::Rust { non_exhaustive: true })
        .constified_enum("android::c_interface::consts::.*")
        .allowlist_type("android::c_interface::.*")
        .allowlist_type("AStatus")
        .allowlist_type("AIBinder_Class")
        .allowlist_type("AIBinder")
        .allowlist_type("AIBinder_Weak")
        .allowlist_type("AIBinder_DeathRecipient")
        .allowlist_type("AParcel")
        .allowlist_type("binder_status_t")
        .blocklist_function("vprintf")
        .blocklist_function("strtold")
        .blocklist_function("_vtlog")
        .blocklist_function("vscanf")
        .blocklist_function("vfprintf_worker")
        .blocklist_function("vsprintf")
        .blocklist_function("vsnprintf")
        .blocklist_function("vsnprintf_filtered")
        .blocklist_function("vfscanf")
        .blocklist_function("vsscanf")
        .blocklist_function("vdprintf")
        .blocklist_function("vasprintf")
        .blocklist_function("strtold_l")
        .allowlist_function(".*");
    if target.ends_with("-android") {
        bindings = bindings
            .clang_arg(format!("--target={clang_target}{api}"))
            .clang_arg(format!("-D__ANDROID_MIN_SDK_VERSION__={api}"));
    }
    let bindings = bindings
        .generate()
        .expect("Couldn't generate bindings");
    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings.write_to_file(out_path.join("bindings.rs")).expect("Couldn't write bindings.");

    if target.ends_with("-android") {
        // The standalone NDK linker stubs intentionally omit Android
        // platform-only Binder entry points.  The Rust Binder crate uses four
        // of those symbols for the vendor service manager and thread pool.
        // Build a tiny C trampoline which resolves them from the target's
        // already-loaded libbinder_ndk.so at runtime; this keeps the final ELF
        // free of unresolved symbols without linking unstable C++ libbinder.
        let clang = toolchain.join("bin").join(format!("{clang_target}{api}-clang"));
        let source = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap())
            .join("binder_ndk_compat.c");
        let object = out_path.join("binder_ndk_compat.o");
        let archive = out_path.join("libbinder_ndk_compat.a");
        let compile = Command::new(&clang)
            .arg("-fPIC")
            .arg("-fno-stack-protector")
            .arg(format!("-D__ANDROID_MIN_SDK_VERSION__={api}"))
            .arg("-c")
            .arg(&source)
            .arg("-o")
            .arg(&object)
            .status()
            .expect("failed to invoke Android clang for Binder trampoline");
        assert!(compile.success(), "Android clang failed to build Binder trampoline");
        let ar = toolchain.join("bin/llvm-ar");
        let archive_status = Command::new(ar)
            .args(["rcs"])
            .arg(&archive)
            .arg(&object)
            .status()
            .expect("failed to invoke llvm-ar for Binder trampoline");
        assert!(archive_status.success(), "llvm-ar failed to build Binder trampoline");
        println!("cargo::rustc-link-search=native={}", out_path.display());
        println!("cargo::rustc-link-lib=static=binder_ndk_compat");
        if let Ok(lib_dir) = env::var("BINDER_NDK_LIB_DIR") {
            println!("cargo::rustc-link-search=native={lib_dir}");
        }
    } else {
        // Host checks exercise Rust parsing/type contracts only.  They must not
        // attempt to link Android Binder libraries.
        println!("cargo:warning=host check: skipping Android Binder link objects");
    }
    if target.ends_with("-android") {
        println!("cargo::rustc-link-lib=binder_ndk");
    }
}
