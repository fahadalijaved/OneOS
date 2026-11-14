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
#[derive(Debug)]
pub struct r#FaceEnrollOptions {
  pub r#hardwareAuthToken: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken,
  pub r#enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType,
  pub r#features: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature>,
  #[deprecated = "use {@link surfacePreview} instead {@link NativeHandle} a handle used to render content from the face HAL. Note that only one of [{@link surfacePreview}, {@link nativeHandlePreview}] should be set at one time."]
  pub r#nativeHandlePreview: Option<crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>,
  pub r#surfacePreview: Option<nativewindow::Surface>,
  pub r#context: Option<crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext>,
}
impl Default for r#FaceEnrollOptions {
  fn default() -> Self {
    Self {
      r#hardwareAuthToken: Default::default(),
      r#enrollmentType: Default::default(),
      r#features: Default::default(),
      r#nativeHandlePreview: Default::default(),
      r#surfacePreview: Default::default(),
      r#context: Default::default(),
    }
  }
}
impl binder::Parcelable for r#FaceEnrollOptions {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#hardwareAuthToken)?;
      subparcel.write(&self.r#enrollmentType)?;
      subparcel.write(&self.r#features)?;
      subparcel.write(&self.r#nativeHandlePreview)?;
      subparcel.write(&self.r#surfacePreview)?;
      subparcel.write(&self.r#context)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#hardwareAuthToken = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollmentType = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#features = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#nativeHandlePreview = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#surfacePreview = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#context = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#FaceEnrollOptions);
binder::impl_deserialize_for_parcelable!(r#FaceEnrollOptions);
impl binder::binder_impl::ParcelableMetadata for r#FaceEnrollOptions {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.face.FaceEnrollOptions" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#FaceEnrollOptions as _7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions;
}
