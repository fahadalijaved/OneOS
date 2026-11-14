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
#[derive(Debug)]
pub struct r#HardwareAuthToken {
  pub r#challenge: i64,
  pub r#userId: i64,
  pub r#authenticatorId: i64,
  pub r#authenticatorType: crate::mangled::_7_android_8_hardware_9_keymaster_25_HardwareAuthenticatorType,
  pub r#timestamp: crate::mangled::_7_android_8_hardware_9_keymaster_9_Timestamp,
  pub r#mac: Vec<u8>,
}
impl Default for r#HardwareAuthToken {
  fn default() -> Self {
    Self {
      r#challenge: 0,
      r#userId: 0,
      r#authenticatorId: 0,
      r#authenticatorType: crate::mangled::_7_android_8_hardware_9_keymaster_25_HardwareAuthenticatorType::NONE,
      r#timestamp: Default::default(),
      r#mac: Default::default(),
    }
  }
}
impl binder::Parcelable for r#HardwareAuthToken {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#challenge)?;
      subparcel.write(&self.r#userId)?;
      subparcel.write(&self.r#authenticatorId)?;
      subparcel.write(&self.r#authenticatorType)?;
      subparcel.write(&self.r#timestamp)?;
      subparcel.write(&self.r#mac)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#challenge = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#userId = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#authenticatorId = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#authenticatorType = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#timestamp = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#mac = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#HardwareAuthToken);
binder::impl_deserialize_for_parcelable!(r#HardwareAuthToken);
impl binder::binder_impl::ParcelableMetadata for r#HardwareAuthToken {
  fn get_descriptor() -> &'static str { "android.hardware.keymaster.HardwareAuthToken" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#HardwareAuthToken as _7_android_8_hardware_9_keymaster_17_HardwareAuthToken;
}
