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
#[derive(Debug)]
pub struct r#ComponentInfo {
  pub r#componentId: String,
  pub r#hardwareVersion: String,
  pub r#firmwareVersion: String,
  pub r#serialNumber: String,
  pub r#softwareVersion: String,
}
impl Default for r#ComponentInfo {
  fn default() -> Self {
    Self {
      r#componentId: Default::default(),
      r#hardwareVersion: Default::default(),
      r#firmwareVersion: Default::default(),
      r#serialNumber: Default::default(),
      r#softwareVersion: Default::default(),
    }
  }
}
impl binder::Parcelable for r#ComponentInfo {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#componentId)?;
      subparcel.write(&self.r#hardwareVersion)?;
      subparcel.write(&self.r#firmwareVersion)?;
      subparcel.write(&self.r#serialNumber)?;
      subparcel.write(&self.r#softwareVersion)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#componentId = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#hardwareVersion = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#firmwareVersion = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#serialNumber = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#softwareVersion = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#ComponentInfo);
binder::impl_deserialize_for_parcelable!(r#ComponentInfo);
impl binder::binder_impl::ParcelableMetadata for r#ComponentInfo {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.ComponentInfo" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#ComponentInfo as _7_android_8_hardware_10_biometrics_6_common_13_ComponentInfo;
}
