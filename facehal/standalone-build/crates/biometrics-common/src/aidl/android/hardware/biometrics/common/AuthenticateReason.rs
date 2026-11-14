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
pub enum r#AuthenticateReason {
  VendorAuthenticateReason(crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_6_Vendor),
  FaceAuthenticateReason(crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_4_Face),
  FingerprintAuthenticateReason(crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_11_Fingerprint),
}
impl Default for r#AuthenticateReason {
  fn default() -> Self {
    Self::VendorAuthenticateReason(Default::default())
  }
}
impl binder::Parcelable for r#AuthenticateReason {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    match self {
      Self::VendorAuthenticateReason(v) => {
        parcel.write(&0i32)?;
        parcel.write(v)
      }
      Self::FaceAuthenticateReason(v) => {
        parcel.write(&1i32)?;
        parcel.write(v)
      }
      Self::FingerprintAuthenticateReason(v) => {
        parcel.write(&2i32)?;
        parcel.write(v)
      }
    }
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    let tag: i32 = parcel.read()?;
    match tag {
      0 => {
        let value: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_6_Vendor = parcel.read()?;
        *self = Self::VendorAuthenticateReason(value);
        Ok(())
      }
      1 => {
        let value: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_4_Face = parcel.read()?;
        *self = Self::FaceAuthenticateReason(value);
        Ok(())
      }
      2 => {
        let value: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_11_Fingerprint = parcel.read()?;
        *self = Self::FingerprintAuthenticateReason(value);
        Ok(())
      }
      _ => {
        Err(binder::StatusCode::BAD_VALUE)
      }
    }
  }
}
binder::impl_serialize_for_parcelable!(r#AuthenticateReason);
binder::impl_deserialize_for_parcelable!(r#AuthenticateReason);
impl binder::binder_impl::ParcelableMetadata for r#AuthenticateReason {
  fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.AuthenticateReason" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub mod r#Vendor {
  #[derive(Debug)]
  pub struct r#Vendor {
    pub r#extension: binder::ParcelableHolder<binder::binder_impl::VintfStabilityType>,
  }
  impl Default for r#Vendor {
    fn default() -> Self {
      Self {
        r#extension: Default::default(),
      }
    }
  }
  impl binder::Parcelable for r#Vendor {
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
  binder::impl_serialize_for_parcelable!(r#Vendor);
  binder::impl_deserialize_for_parcelable!(r#Vendor);
  impl binder::binder_impl::ParcelableMetadata for r#Vendor {
    fn get_descriptor() -> &'static str { "android.hardware.biometrics.common.AuthenticateReason.Vendor" }
    fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
  }
}
pub mod r#Fingerprint {
  #![allow(non_upper_case_globals)]
  use binder::declare_binder_enum;
  declare_binder_enum! {
    #[repr(C, align(4))]
    r#Fingerprint : [i32; 1] {
      r#UNKNOWN = 0,
    }
  }
}
pub mod r#Face {
  #![allow(non_upper_case_globals)]
  use binder::declare_binder_enum;
  declare_binder_enum! {
    #[repr(C, align(4))]
    r#Face : [i32; 11] {
      r#UNKNOWN = 0,
      r#STARTED_WAKING_UP = 1,
      r#PRIMARY_BOUNCER_SHOWN = 2,
      r#ASSISTANT_VISIBLE = 3,
      r#ALTERNATE_BIOMETRIC_BOUNCER_SHOWN = 4,
      r#NOTIFICATION_PANEL_CLICKED = 5,
      r#OCCLUDING_APP_REQUESTED = 6,
      r#PICK_UP_GESTURE_TRIGGERED = 7,
      r#QS_EXPANDED = 8,
      r#SWIPE_UP_ON_BOUNCER = 9,
      r#UDFPS_POINTER_DOWN = 10,
    }
  }
}
pub mod r#Tag {
  #![allow(non_upper_case_globals)]
  use binder::declare_binder_enum;
  declare_binder_enum! {
    #[repr(C, align(4))]
    r#Tag : [i32; 3] {
      r#vendorAuthenticateReason = 0,
      r#faceAuthenticateReason = 1,
      r#fingerprintAuthenticateReason = 2,
    }
  }
}
pub(crate) mod mangled {
 pub use super::r#AuthenticateReason as _7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason;
 pub use super::r#Vendor::r#Vendor as _7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_6_Vendor;
 pub use super::r#Fingerprint::r#Fingerprint as _7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_11_Fingerprint;
 pub use super::r#Face::r#Face as _7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_4_Face;
 pub use super::r#Tag::r#Tag as _7_android_8_hardware_10_biometrics_6_common_18_AuthenticateReason_3_Tag;
}
