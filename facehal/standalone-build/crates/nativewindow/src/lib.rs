use binder::{
    binder_impl::{BorrowedParcel, UnstructuredParcelable},
    impl_deserialize_for_unstructured_parcelable, impl_serialize_for_unstructured_parcelable,
    unstable_api::{status_result, AParcel, AsNative},
    StatusCode,
};
use std::{fmt, ptr::NonNull};

#[repr(C)]
struct ANativeWindow {
    _private: [u8; 0],
}

#[link(name = "nativewindow")]
extern "C" {
    fn ANativeWindow_acquire(window: *mut ANativeWindow);
    fn ANativeWindow_release(window: *mut ANativeWindow);
    fn ANativeWindow_readFromParcel(
        parcel: *const AParcel,
        out_window: *mut *mut ANativeWindow,
    ) -> i32;
    fn ANativeWindow_writeToParcel(window: *mut ANativeWindow, parcel: *mut AParcel) -> i32;
}

#[derive(PartialEq, Eq)]
pub struct Surface(NonNull<ANativeWindow>);

impl Clone for Surface {
    fn clone(&self) -> Self {
        unsafe { ANativeWindow_acquire(self.0.as_ptr()) };
        Self(self.0)
    }
}

impl Drop for Surface {
    fn drop(&mut self) {
        unsafe { ANativeWindow_release(self.0.as_ptr()) };
    }
}

impl fmt::Debug for Surface {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.debug_tuple("Surface").field(&self.0).finish()
    }
}

impl UnstructuredParcelable for Surface {
    fn write_to_parcel(&self, parcel: &mut BorrowedParcel) -> Result<(), StatusCode> {
        status_result(unsafe {
            ANativeWindow_writeToParcel(self.0.as_ptr(), parcel.as_native_mut())
        })
    }

    fn from_parcel(parcel: &BorrowedParcel) -> Result<Self, StatusCode> {
        let mut window = std::ptr::null_mut();
        status_result(unsafe { ANativeWindow_readFromParcel(parcel.as_native(), &mut window) })?;
        Ok(Self(NonNull::new(window).expect(
            "ANativeWindow_readFromParcel succeeded with a null window",
        )))
    }
}

impl_deserialize_for_unstructured_parcelable!(Surface);
impl_serialize_for_unstructured_parcelable!(Surface);

unsafe impl Send for Surface {}
unsafe impl Sync for Surface {}
