#![allow(non_snake_case, non_camel_case_types, non_upper_case_globals)]
#![allow(clippy::all)]
pub mod aidl;

pub mod mangled {
    pub use crate::r#aidl::r#android::r#hardware::r#common::r#Ashmem::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#common::r#MappableFile::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#common::r#NativeHandle::mangled::*;
}
