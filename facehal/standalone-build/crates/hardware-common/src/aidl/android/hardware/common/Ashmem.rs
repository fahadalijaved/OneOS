/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=2 --hash=c32ddfdeb69c6e4a8a45519e6f9a39c4b66fd99f -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/hardware-common /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2/android/hardware/common/Ashmem.aidl /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2/android/hardware/common/MappableFile.aidl /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2/android/hardware/common/NativeHandle.aidl
 *
 * DO NOT CHECK THIS FILE INTO A CODE TREE (e.g. git, etc..).
 * ALWAYS GENERATE THIS FILE FROM UPDATED AIDL COMPILER
 * AS A BUILD INTERMEDIATE ONLY. THIS IS NOT SOURCE CODE.
 */
#![forbid(unsafe_code)]
#![cfg_attr(rustfmt, rustfmt_skip)]
#[derive(Debug)]
pub struct r#Ashmem {
  pub r#fd: Option<binder::ParcelFileDescriptor>,
  pub r#size: i64,
}
impl Default for r#Ashmem {
  fn default() -> Self {
    Self {
      r#fd: Default::default(),
      r#size: 0,
    }
  }
}
impl binder::Parcelable for r#Ashmem {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      let __field_ref = self.r#fd.as_ref().ok_or(binder::StatusCode::UNEXPECTED_NULL)?;
      subparcel.write(__field_ref)?;
      subparcel.write(&self.r#size)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#fd = Some(subparcel.read()?);
      }
      if subparcel.has_more_data() {
        self.r#size = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#Ashmem);
binder::impl_deserialize_for_parcelable!(r#Ashmem);
impl binder::binder_impl::ParcelableMetadata for r#Ashmem {
  fn get_descriptor() -> &'static str { "android.hardware.common.Ashmem" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#Ashmem as _7_android_8_hardware_6_common_6_Ashmem;
}
