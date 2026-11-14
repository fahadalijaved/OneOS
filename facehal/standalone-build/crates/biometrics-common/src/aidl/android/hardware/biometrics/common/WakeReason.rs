/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=4 --hash=8a6cd86630181a4df6f20056259ec200ffe39209 -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/biometrics-common /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/AuthenticateReason.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/CommonProps.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/ComponentInfo.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/DisplayState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/FoldState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/ICancellationSignal.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationContext.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationReason.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/SensorStrength.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/WakeReason.aidl
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
  r#WakeReason : [i32; 10] {
    r#UNKNOWN = 0,
    r#POWER_BUTTON = 1,
    r#GESTURE = 2,
    r#WAKE_KEY = 3,
    r#WAKE_MOTION = 4,
    r#LID = 5,
    r#DISPLAY_GROUP_ADDED = 6,
    r#TAP = 7,
    r#LIFT = 8,
    r#BIOMETRIC = 9,
  }
}
pub(crate) mod mangled {
 pub use super::r#WakeReason as _7_android_8_hardware_10_biometrics_6_common_10_WakeReason;
}
