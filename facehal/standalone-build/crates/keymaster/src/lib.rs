#![allow(non_snake_case, non_camel_case_types, non_upper_case_globals)]
#![allow(clippy::all)]
pub mod aidl;

pub mod mangled {
    pub use crate::r#aidl::r#android::r#hardware::r#keymaster::r#HardwareAuthToken::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#keymaster::r#HardwareAuthenticatorType::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#keymaster::r#SecurityLevel::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#keymaster::r#Timestamp::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#keymaster::r#VerificationToken::mangled::*;
}
