use std::env;
use std::path::PathBuf;

fn main() {
    let root = PathBuf::from(env::var("FACEHAL_ROOT").expect("FACEHAL_ROOT is required"));
    let native = root.join("standalone-build/native");
    let system_lib64 = env::var("ANDROID_SYSTEM_LIB64")
        .expect("ANDROID_SYSTEM_LIB64 is required (path to system lib64 for camera/media NDK libs)");
    let vendor_lib64 = env::var("ANDROID_VENDOR_LIB64")
        .expect("ANDROID_VENDOR_LIB64 is required (path to vendor lib64)");

    println!("cargo::rerun-if-changed={}", native.join("libfacehal_bridge.a").display());
    println!("cargo::rustc-link-search=native={}", native.display());
    println!("cargo::rustc-link-search=native={system_lib64}");
    println!("cargo::rustc-link-search=native={vendor_lib64}");
    println!("cargo::rustc-link-lib=static=facehal_bridge");
    println!("cargo::rustc-link-lib=dylib=camera2ndk_vendor");
    println!("cargo::rustc-link-lib=dylib=mediandk");
    println!("cargo::rustc-link-lib=dylib=nativewindow");
    println!("cargo::rustc-link-lib=dylib=log");
    println!("cargo::rustc-link-lib=dylib=dl");
    println!("cargo::rustc-link-lib=dylib=c++_shared");
}
