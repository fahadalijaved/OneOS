fn main() {
    // Cargo builds use the Binder NDK surface.  The AOSP Android.bp build
    // supplies this cfg as well; without it the crate compiles platform-only
    // helpers and adds versioned symbols that are not part of the minimum
    // vendor NDK contract.
    println!("cargo::rustc-check-cfg=cfg(android_vendor)");
    println!("cargo::rustc-cfg=android_vendor");
}
