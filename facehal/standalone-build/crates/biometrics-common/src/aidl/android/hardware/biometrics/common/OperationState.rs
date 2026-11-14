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
pub enum r#OperationState {
  FingerprintOperationState(crate::mangled::_7_android_8_hardware_10_biometrics_6_common_14_OperationState_25_FingerprintOperationState),
  FaceOperationState(crate::mangled::_7_android_8_hardware_10_biometrics_6_common_14_OperationState_18_FaceOperationState),
}
impl Default for r#OperationState {
  fn default() -> Self {
    Self::FingerprintOperationState(Default::default())
  }
}
impl binder::Parcelable for r#OperationState {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    match self {
      Self::FingerprintOperationState(v) => {
        parcel.write(&0i32)?;
        parcel.write(v)
      }
      Self::FaceOperationState(v) => {
        parcel.write(&1i32)?;
        parcel.write(v)
      }
    }
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    let tag: i32 = parcel.read()?;
    match tag {
      0 => {
        let value: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_14_OperationState_25_FingerprintOperationState = parcel.read()?;
        *self = Self::FingerprintOperationState(value);
        Ok(())
      }
      1 => {
        let value: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_14_OperationState_18_FaceOperationState = parcel.read()?;
        *self = Self::FaceOperationState(value);
        Ok(())
      }
      _ => {
        Err(binder::StatusCode::BAD_VALUE)
      }
    }
  }
}
binder::impl_serialize_for_parcelable!(r#OperationState);
binder::impl_deserialize_for_parcelable!(r#OperationState);
impl binder::binder_impl::ParcelableMetadata for r#OperationState {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.OperationState" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub mod r#FingerprintOperationState {
  #[derive(Debug)]
  pub struct r#FingerprintOperationState {
    pub r#extension: binder::ParcelableHolder<binder::binder_impl::VintfStabilityType>,
    pub r#isHardwareIgnoringTouches: bool,
  }
  impl Default for r#FingerprintOperationState {
    fn default() -> Self {
      Self {
        r#extension: Default::default(),
        r#isHardwareIgnoringTouches: false,
      }
    }
  }
  impl binder::Parcelable for r#FingerprintOperationState {
    fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
      parcel.sized_write(|subparcel| {
        subparcel.write(&self.r#extension)?;
        subparcel.write(&self.r#isHardwareIgnoringTouches)?;
        Ok(())
      })
    }
    fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
      parcel.sized_read(|subparcel| {
        if subparcel.has_more_data() {
          self.r#extension = subparcel.read()?;
        }
        if subparcel.has_more_data() {
          self.r#isHardwareIgnoringTouches = subparcel.read()?;
        }
        Ok(())
      })
    }
  }
  binder::impl_serialize_for_parcelable!(r#FingerprintOperationState);
  binder::impl_deserialize_for_parcelable!(r#FingerprintOperationState);
  impl binder::binder_impl::ParcelableMetadata for r#FingerprintOperationState {
    fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.OperationState.FingerprintOperationState" }
    fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
  }
}
pub mod r#FaceOperationState {
  #[derive(Debug)]
  pub struct r#FaceOperationState {
    pub r#extension: binder::ParcelableHolder<binder::binder_impl::VintfStabilityType>,
  }
  impl Default for r#FaceOperationState {
    fn default() -> Self {
      Self {
        r#extension: Default::default(),
      }
    }
  }
  impl binder::Parcelable for r#FaceOperationState {
    fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
      parcel.sized_write(|subparcel| {
        subparcel.write(&self.r#extension)?;
        Ok(())
      })
    }
    fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
      parcel.sized_read(|subparcel| {
        if subparcel.has_more_data() {
          self.r#extension = subparcel.read()?;
        }
        Ok(())
      })
    }
  }
  binder::impl_serialize_for_parcelable!(r#FaceOperationState);
  binder::impl_deserialize_for_parcelable!(r#FaceOperationState);
  impl binder::binder_impl::ParcelableMetadata for r#FaceOperationState {
    fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.OperationState.FaceOperationState" }
    fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
  }
}
pub mod r#Tag {
  #![allow(non_upper_case_globals)]
  use binder::declare_binder_enum;
  declare_binder_enum! {
    #[repr(C, align(4))]
    r#Tag : [i32; 2] {
      r#fingerprintOperationState = 0,
      r#faceOperationState = 1,
    }
  }
}
pub(crate) mod mangled {
 pub use super::r#OperationState as _7_android_8_hardware_10_biometrics_6_common_14_OperationState;
 pub use super::r#FingerprintOperationState::r#FingerprintOperationState as _7_android_8_hardware_10_biometrics_6_common_14_OperationState_25_FingerprintOperationState;
 pub use super::r#FaceOperationState::r#FaceOperationState as _7_android_8_hardware_10_biometrics_6_common_14_OperationState_18_FaceOperationState;
 pub use super::r#Tag::r#Tag as _7_android_8_hardware_10_biometrics_6_common_14_OperationState_3_Tag;
}
