/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=4 --hash=d60ca1bb57f94508910cac7b8910c85e2a49a11f -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/keymaster /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4/android/hardware/keymaster/HardwareAuthToken.aidl /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4/android/hardware/keymaster/HardwareAuthenticatorType.aidl /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4/android/hardware/keymaster/SecurityLevel.aidl /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4/android/hardware/keymaster/Timestamp.aidl /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4/android/hardware/keymaster/VerificationToken.aidl
 *
 * DO NOT CHECK THIS FILE INTO A CODE TREE (e.g. git, etc..).
 * ALWAYS GENERATE THIS FILE FROM UPDATED AIDL COMPILER
 * AS A BUILD INTERMEDIATE ONLY. THIS IS NOT SOURCE CODE.
 */
#![forbid(unsafe_code)]
#![cfg_attr(rustfmt, rustfmt_skip)]
#![allow(non_upper_case_globals)]
use binder::declare_binder_enum;
declare_binder_enum! {
  #[repr(C, align(4))]
  r#HardwareAuthenticatorType : [i32; 4] {
    r#NONE = 0,
    r#PASSWORD = 1,
    r#FINGERPRINT = 2,
    r#ANY = -1,
  }
}
pub(crate) mod mangled {
 pub use super::r#HardwareAuthenticatorType as _7_android_8_hardware_9_keymaster_25_HardwareAuthenticatorType;
}
