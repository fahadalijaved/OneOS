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
pub struct r#OperationContext {
  pub r#id: i32,
  pub r#reason: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_15_OperationReason,
  #[deprecated = "use displayState instead."]
  pub r#isAod: bool,
  pub r#isCrypto: bool,
  pub r#wakeReason: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_10_WakeReason,
  pub r#displayState: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_12_DisplayState,
  pub r#authenticateReason: Option<crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason>,
  pub r#foldState: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_9_FoldState,
  pub r#operationState: Option<crate::mangled::_7_android_8_hardware_10_biometrics_6_common_14_OperationState>,
}
impl Default for r#OperationContext {
  fn default() -> Self {
    Self {
      r#id: 0,
      r#reason: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_15_OperationReason::UNKNOWN,
      r#isAod: false,
      r#isCrypto: false,
      r#wakeReason: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_10_WakeReason::UNKNOWN,
      r#displayState: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_12_DisplayState::UNKNOWN,
      r#authenticateReason: Default::default(),
      r#foldState: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_9_FoldState::UNKNOWN,
      r#operationState: Default::default(),
    }
  }
}
impl binder::Parcelable for r#OperationContext {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#id)?;
      subparcel.write(&self.r#reason)?;
      subparcel.write(&self.r#isAod)?;
      subparcel.write(&self.r#isCrypto)?;
      subparcel.write(&self.r#wakeReason)?;
      subparcel.write(&self.r#displayState)?;
      subparcel.write(&self.r#authenticateReason)?;
      subparcel.write(&self.r#foldState)?;
      subparcel.write(&self.r#operationState)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#id = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#reason = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#isAod = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#isCrypto = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#wakeReason = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#displayState = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#authenticateReason = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#foldState = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#operationState = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#OperationContext);
binder::impl_deserialize_for_parcelable!(r#OperationContext);
impl binder::binder_impl::ParcelableMetadata for r#OperationContext {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.OperationContext" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#OperationContext as _7_android_8_hardware_10_biometrics_6_common_16_OperationContext;
}
