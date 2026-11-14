#[cfg(target_os = "android")]
unsafe extern "C" {
    fn facehal_binder_ndk_has_api31() -> bool;
}

pub(crate) fn has_api31() -> bool {
    #[cfg(target_os = "android")]
    unsafe {
        return facehal_binder_ndk_has_api31();
    }

    #[cfg(not(target_os = "android"))]
    false
}
