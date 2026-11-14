#![allow(non_snake_case, non_camel_case_types, non_upper_case_globals)]
#![allow(clippy::all)]
pub mod aidl;

pub mod mangled {
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#AuthenticateReason::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#CommonProps::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#ComponentInfo::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#DisplayState::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#FoldState::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#ICancellationSignal::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#OperationContext::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#OperationReason::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#OperationState::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#SensorStrength::mangled::*;
    pub use crate::r#aidl::r#android::r#hardware::r#biometrics::r#common::r#WakeReason::mangled::*;
}
