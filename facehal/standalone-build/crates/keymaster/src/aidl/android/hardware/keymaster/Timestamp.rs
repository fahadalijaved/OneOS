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
pub struct r#Timestamp {
  pub r#milliSeconds: i64,
}
impl Default for r#Timestamp {
  fn default() -> Self {
    Self {
      r#milliSeconds: 0,
    }
  }
}
impl binder::Parcelable for r#Timestamp {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#milliSeconds)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#milliSeconds = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#Timestamp);
binder::impl_deserialize_for_parcelable!(r#Timestamp);
impl binder::binder_impl::ParcelableMetadata for r#Timestamp {
  fn get_descriptor() -> &'static str { "android.hardware.keymaster.Timestamp" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#Timestamp as _7_android_8_hardware_9_keymaster_9_Timestamp;
}
