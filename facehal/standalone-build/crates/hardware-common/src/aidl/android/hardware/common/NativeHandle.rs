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
pub struct r#NativeHandle {
  pub r#fds: Vec<binder::ParcelFileDescriptor>,
  pub r#ints: Vec<i32>,
}
impl Default for r#NativeHandle {
  fn default() -> Self {
    Self {
      r#fds: Default::default(),
      r#ints: Default::default(),
    }
  }
}
impl binder::Parcelable for r#NativeHandle {
  fn write_to_parcel(&self, parcel: &mut binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_write(|subparcel| {
      subparcel.write(&self.r#fds)?;
      subparcel.write(&self.r#ints)?;
      Ok(())
    })
  }
  fn read_from_parcel(&mut self, parcel: &binder::binder_impl::BorrowedParcel) -> std::result::Result<(), binder::StatusCode> {
    parcel.sized_read(|subparcel| {
      if subparcel.has_more_data() {
        self.r#fds = subparcel.read()?;
      }
      if subparcel.has_more_data() {
        self.r#ints = subparcel.read()?;
      }
      Ok(())
    })
  }
}
binder::impl_serialize_for_parcelable!(r#NativeHandle);
binder::impl_deserialize_for_parcelable!(r#NativeHandle);
impl binder::binder_impl::ParcelableMetadata for r#NativeHandle {
  fn get_descriptor() -> &'static str { "android.hardware.common.NativeHandle" }
  fn get_stability(&self) -> binder::binder_impl::Stability { binder::binder_impl::Stability::Vintf }
}
pub(crate) mod mangled {
 pub use super::r#NativeHandle as _7_android_8_hardware_6_common_12_NativeHandle;
}
