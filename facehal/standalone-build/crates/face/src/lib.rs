#![allow(non_snake_case, non_camel_case_types, non_upper_case_globals)]
#![allow(clippy::all)]
pub mod aidl;

pub mod mangled {
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#AcquiredInfo::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#AuthenticationFrame::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#BaseFrame::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#Cell::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#EnrollmentFrame::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#EnrollmentStage::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#EnrollmentStageConfig::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#EnrollmentType::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#Error::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#FaceEnrollOptions::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#FaceSensorType::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#Feature::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#IFace::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#ISession::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#ISessionCallback::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#face::r#SensorProps::mangled::*;
    pub use android_hardware_biometrics_common::mangled::*;
    pub use android_hardware_common::mangled::*;
    pub use android_hardware_keymaster::mangled::*;
}
