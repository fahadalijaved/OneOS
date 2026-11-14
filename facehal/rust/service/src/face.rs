use crate::session::{AlgorithmCache, ChallengeCache, FaceSession};
use android_hardware_biometrics_common::aidl::android::hardware::biometrics::common::{
    CommonProps::CommonProps, SensorStrength::SensorStrength,
};
use android_hardware_biometrics_face::aidl::android::hardware::biometrics::face::{
    FaceSensorType::FaceSensorType,
    IFace::IFace,
    ISession::{BnSession, ISession},
    ISessionCallback::ISessionCallback,
    SensorProps::SensorProps,
};
use binder::{BinderFeatures, Interface, StatusCode, Strong};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

const SENSOR_ID: i32 = 1;
const MAX_ENROLLMENTS: i32 = 2;

pub struct FaceService {
    session_active: Arc<AtomicBool>,
    algorithm_cache: Arc<AlgorithmCache>,
    challenge_cache: Arc<ChallengeCache>,
}

impl FaceService {
    pub fn new() -> Self {
        Self {
            session_active: Arc::new(AtomicBool::new(false)),
            algorithm_cache: Arc::new(AlgorithmCache::new()),
            challenge_cache: Arc::new(ChallengeCache::new()),
        }
    }
}

impl Interface for FaceService {}

impl IFace for FaceService {
    fn r#getSensorProps(&self) -> binder::Result<Vec<SensorProps>> {
        let mut common = CommonProps::default();
        common.sensorId = SENSOR_ID;
        common.sensorStrength = SensorStrength::WEAK;
        common.maxEnrollmentsPerUser = MAX_ENROLLMENTS;

        let mut props = SensorProps::default();
        props.commonProps = common;
        props.sensorType = FaceSensorType::RGB;
        props.halControlsPreview = true;
        props.previewDisplayId = 0;
        props.enrollPreviewWidth = 640;
        props.enrollPreviewHeight = 480;
        props.enrollPreviewScale = 1.0;
        props.supportsDetectInteraction = false;
        Ok(vec![props])
    }

    fn r#createSession(
        &self,
        sensor_id: i32,
        user_id: i32,
        callback: &Strong<dyn ISessionCallback>,
    ) -> binder::Result<Strong<dyn ISession>> {
        if sensor_id != SENSOR_ID || user_id < 0 {
            return Err(StatusCode::BAD_VALUE.into());
        }
        if self
            .session_active
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            eprintln!("FaceHAL createSession: previous session is still active");
            return Err(StatusCode::ALREADY_EXISTS.into());
        }
        let session = match FaceSession::new(
            user_id,
            callback.clone(),
            self.session_active.clone(),
            self.algorithm_cache.clone(),
            self.challenge_cache.clone(),
        ) {
            Ok(session) => session,
            Err(error) => {
                eprintln!("FaceHAL createSession: session initialization failed: {error:?}");
                self.session_active.store(false, Ordering::Release);
                return Err(StatusCode::UNKNOWN_ERROR.into());
            }
        };
        Ok(BnSession::new_binder(session, BinderFeatures::default()))
    }
}
