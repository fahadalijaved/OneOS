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
pub struct r#SensorProps {
  pub r#commonProps: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_11_CommonProps,
  pub r#sensorType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_FaceSensorType,
  pub r#halControlsPreview: bool,
  pub r#previewDisplayId: i32,
  pub r#enrollPreviewWidth: i32,
  pub r#enrollPreviewHeight: i32,
  pub r#enrollTranslationX: f32,
  pub r#enrollTranslationY: f32,
  pub r#enrollPreviewScale: f32,
  pub r#supportsDetectInteraction: bool,
}
impl Default for r#SensorProps {
  fn default() -> Self {
    Self {
      r#commonProps: Default::default(),
      r#sensorType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_FaceSensorType::UNKNOWN,
      r#halControlsPreview: false,
      r#previewDisplayId: 0,
      r#enrollPreviewWidth: 0,
      r#enrollPreviewHeight: 0,
      r#enrollTranslationX: 0.000000f32,
      r#enrollTranslationY: 0.000000f32,
      r#enrollPreviewScale: 0.000000f32,
      r#supportsDetectInteraction: false,
    }
  }
}
impl binder::Parcelable for r#SensorProps {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#commonProps)?;
      subparcel.write(&self.r#sensorType)?;
      subparcel.write(&self.r#halControlsPreview)?;
      subparcel.write(&self.r#previewDisplayId)?;
      subparcel.write(&self.r#enrollPreviewWidth)?;
      subparcel.write(&self.r#enrollPreviewHeight)?;
      subparcel.write(&self.r#enrollTranslationX)?;
      subparcel.write(&self.r#enrollTranslationY)?;
      subparcel.write(&self.r#enrollPreviewScale)?;
      subparcel.write(&self.r#supportsDetectInteraction)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#commonProps = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#sensorType = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#halControlsPreview = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#previewDisplayId = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollPreviewWidth = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollPreviewHeight = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollTranslationX = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollTranslationY = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#enrollPreviewScale = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#supportsDetectInteraction = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#SensorProps);
binder::impl_deserialize_for_parcelable!(r#SensorProps);
impl binder::binder_impl::ParcelableMetadata for r#SensorProps {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.face.SensorProps" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#SensorProps as _7_android_8_hardware_10_biometrics_4_face_11_SensorProps;
}
