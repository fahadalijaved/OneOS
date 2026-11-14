/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=4 --hash=c43fbb9be4a662cc9ace640dba21cccdb84c6c21 -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/face /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/AcquiredInfo.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/AuthenticationFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/BaseFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Cell.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentStage.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentStageConfig.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentType.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Error.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/FaceEnrollOptions.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/FaceSensorType.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Feature.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/IFace.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/ISession.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/ISessionCallback.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/SensorProps.aidl
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
  #[repr(C, align(1))]
  r#EnrollmentType : [i8; 2] {
    r#DEFAULT = 0,
    r#ACCESSIBILITY = 1,
  }
}
pub(crate) mod mangled {
 pub use super::r#EnrollmentType as _7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType;
}
