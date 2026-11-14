use crate::algorithm::{
    Algorithm, ACTION_AUTHENTICATE, ACTION_ENROLL, STATUS_ENROLL_OK, STATUS_OK,
    STATUS_UNLOCK_FAILED, STATUS_UNLOCK_OK,
};
use crate::authenticator::AuthenticatorIdStore;
use crate::camera::{Camera, CameraError};
use crate::cancellation::{CancellationState, TerminalClaim};
use crate::dialect::Dialect;
use crate::preview::Preview;
use android_hardware_biometrics_common::aidl::android::hardware::biometrics::common::{
    ICancellationSignal::ICancellationSignal, OperationContext::OperationContext,
};
use android_hardware_biometrics_face::aidl::android::hardware::biometrics::face::{
    AcquiredInfo::AcquiredInfo, AuthenticationFrame::AuthenticationFrame, BaseFrame::BaseFrame,
    EnrollmentFrame::EnrollmentFrame, EnrollmentStage::EnrollmentStage,
    EnrollmentStageConfig::EnrollmentStageConfig, EnrollmentType::EnrollmentType, Error::Error,
    FaceEnrollOptions::FaceEnrollOptions, Feature::Feature, ISession::ISession,
    ISessionCallback::ISessionCallback,
};
use android_hardware_common::aidl::android::hardware::common::NativeHandle::NativeHandle;
use android_hardware_keymaster::aidl::android::hardware::keymaster::HardwareAuthToken::HardwareAuthToken;
use android_hardware_keymaster::aidl::android::hardware::keymaster::HardwareAuthenticatorType::HardwareAuthenticatorType;
use binder::{DeathRecipient, IBinder, Interface, StatusCode, Strong};
use facehal_core::{FeatureStore, LockoutState, LockoutTracker};
use nativewindow::Surface;
use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::Read;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const STORE_ROOT: &str = "/data/vendor_de";
const CAMERA_WIDTH: i32 = 640;
const CAMERA_HEIGHT: i32 = 480;
const FRAME_TIMEOUT_MS: i32 = 1_000;
const CAMERA_OPEN_ATTEMPTS: usize = 1;
const CAMERA_OPEN_RETRY_DELAY: Duration = Duration::from_millis(200);
const AUTHENTICATION_TIMEOUT: Duration = Duration::from_secs(10);
const ENROLLMENT_TIMEOUT: Duration = Duration::from_secs(60);
// The proprietary backend may create a template on its first successful enrollment frame.
// Do not report completion until several subsequent live frames authenticate that candidate.
// The candidate frame plus these four confirmations make the five stages the vendor
// enrollment screens draw: BBK (help 19 + countdown on each stage), MIUI (help 19 per
// stage, one progress callback at the end). Samples are paced so the ring animation can
// keep up.
const ENROLLMENT_CONFIRMATION_SAMPLES: i32 = 4;
// MIUI Settings uses vendor acquired code 19 to advance each of its five ring stages.
// The candidate frame plus four live confirmation frames produce those five stages.
const ENROLLMENT_SAMPLE_INTERVAL: Duration = Duration::from_millis(650);
// MIUI restarts its ring animation for every acquired/help callback. Forward bad-frame
// guidance at most once per second and never send a GOOD/help frame beside progress.
const ENROLLMENT_ACQUIRED_INTERVAL: Duration = Duration::from_secs(1);
const THUMBNAIL_WIDTH: usize = 32;
const THUMBNAIL_HEIGHT: usize = 24;
const THUMBNAIL_SIZE: usize = THUMBNAIL_WIDTH * THUMBNAIL_HEIGHT;
const DARK_FRAME_LUMA: u32 = 46;
const MOTION_FRAME_SCORE: u32 = 12;
const STATUS_TOO_DARK: i32 = 0x7b;
const STATUS_TOO_MUCH_MOTION: i32 = 0x80;
const MAX_MISMATCH_FRAMES: usize = 12;
const CHALLENGE_LIFETIME: Duration = Duration::from_secs(10 * 60);
const MAXIMUM_HAT_AGE_MILLIS: i64 = 10 * 60 * 1_000;
const MAXIMUM_HAT_FUTURE_SKEW_MILLIS: i64 = 5_000;

pub(crate) struct ChallengeCache {
    entries: Mutex<HashMap<i64, ChallengeEntry>>,
}

struct ChallengeEntry {
    user_id: i32,
    expires_at: Instant,
}

impl ChallengeCache {
    pub(crate) fn new() -> Self {
        Self {
            entries: Mutex::new(HashMap::new()),
        }
    }

    fn insert(&self, user_id: i32, challenge: i64) {
        let now = Instant::now();
        let mut entries = self.entries.lock().unwrap();
        entries.retain(|_, entry| entry.expires_at > now);
        entries.insert(
            challenge,
            ChallengeEntry {
                user_id,
                expires_at: now + CHALLENGE_LIFETIME,
            },
        );
    }

    fn contains(&self, user_id: i32, challenge: i64) -> bool {
        let now = Instant::now();
        let mut entries = self.entries.lock().unwrap();
        entries.retain(|_, entry| entry.expires_at > now);
        entries
            .get(&challenge)
            .is_some_and(|entry| entry.user_id == user_id)
    }

    fn remove(&self, user_id: i32, challenge: i64) {
        let mut entries = self.entries.lock().unwrap();
        if entries
            .get(&challenge)
            .is_some_and(|entry| entry.user_id == user_id)
        {
            entries.remove(&challenge);
        }
    }
}

pub(crate) struct AlgorithmCache {
    cached: Mutex<Option<CachedAlgorithm>>,
}

struct CachedAlgorithm {
    user_id: i32,
    instance: Arc<Algorithm>,
}

impl AlgorithmCache {
    pub(crate) fn new() -> Self {
        Self {
            cached: Mutex::new(None),
        }
    }

    fn get_or_open(&self, user_id: i32, directory: &Path) -> Option<Arc<Algorithm>> {
        let mut cached = self.cached.lock().unwrap();
        if let Some(entry) = cached.as_ref() {
            if entry.user_id == user_id {
                return Some(entry.instance.clone());
            }
        }

        if let Some(previous) = cached.take() {
            eprintln!(
                "FaceHAL: releasing cached algorithm for user={} before switching to user={user_id}",
                previous.user_id
            );
        }

        match Algorithm::open(directory) {
            Ok(instance) => {
                let instance = Arc::new(instance);
                *cached = Some(CachedAlgorithm {
                    user_id,
                    instance: instance.clone(),
                });
                eprintln!(
                    "FaceHAL session user={user_id}: algorithm initialized and cached at {}",
                    directory.display()
                );
                Some(instance)
            }
            Err(error) => {
                eprintln!(
                    "FaceHAL session user={user_id}: algorithm initialization failed: {error:?}"
                );
                None
            }
        }
    }
}

pub struct FaceSession {
    callback: Strong<dyn ISessionCallback>,
    user_id: i32,
    algorithm_cache: Arc<AlgorithmCache>,
    algorithm_directory: PathBuf,
    features: FeatureStore,
    authenticator_id: AuthenticatorIdStore,
    lockout: Arc<LockoutTracker>,
    challenge_cache: Arc<ChallengeCache>,
    session_active: Arc<AtomicBool>,
    closed: Arc<AtomicBool>,
    operation_active: Arc<AtomicBool>,
    operation_finished: Arc<(Mutex<()>, Condvar)>,
    current_cancellation: Arc<Mutex<Option<CancellationState>>>,
    _callback_death: Option<DeathRecipient>,
}

impl FaceSession {
    pub fn new(
        user_id: i32,
        callback: Strong<dyn ISessionCallback>,
        session_active: Arc<AtomicBool>,
        algorithm_cache: Arc<AlgorithmCache>,
        challenge_cache: Arc<ChallengeCache>,
    ) -> Result<Self, SessionError> {
        let algorithm_directory = Path::new(STORE_ROOT)
            .join(user_id.to_string())
            .join("facedata")
            .join("facehal");
        fs::create_dir_all(&algorithm_directory).map_err(|_| SessionError::Storage)?;
        fs::set_permissions(&algorithm_directory, fs::Permissions::from_mode(0o700))
            .map_err(|_| SessionError::Storage)?;
        algorithm_cache.get_or_open(user_id, &algorithm_directory);
        let lockout =
            Arc::new(LockoutTracker::new(STORE_ROOT, user_id).map_err(|_| SessionError::Storage)?);
        let closed = Arc::new(AtomicBool::new(false));
        let operation_active = Arc::new(AtomicBool::new(false));
        let operation_finished = Arc::new((Mutex::new(()), Condvar::new()));
        let current_cancellation: Arc<Mutex<Option<CancellationState>>> =
            Arc::new(Mutex::new(None));
        let closed_for_death = closed.clone();
        let session_active_for_death = session_active.clone();
        let operation_active_for_death = operation_active.clone();
        let current_cancellation_for_death = current_cancellation.clone();
        let mut callback_binder = callback.as_binder();
        let mut callback_death = DeathRecipient::new(move || {
            closed_for_death.store(true, Ordering::Release);
            if let Some(cancellation) = current_cancellation_for_death.lock().unwrap().as_ref() {
                cancellation.request_cancel();
            }
            if !operation_active_for_death.load(Ordering::Acquire) {
                session_active_for_death.store(false, Ordering::Release);
            }
        });
        if callback_binder.link_to_death(&mut callback_death).is_err() {
            eprintln!("FaceHAL session user={user_id}: unable to link callback death");
        }

        Ok(Self {
            callback,
            user_id,
            algorithm_cache,
            algorithm_directory,
            features: FeatureStore::new(STORE_ROOT, user_id).map_err(|_| SessionError::Storage)?,
            authenticator_id: AuthenticatorIdStore::new(
                Path::new(STORE_ROOT)
                    .join(user_id.to_string())
                    .join("facedata")
                    .join("facehal"),
            ),
            lockout,
            challenge_cache,
            session_active,
            closed,
            operation_active,
            operation_finished,
            current_cancellation,
            _callback_death: Some(callback_death),
        })
    }

    fn ensure_open(&self) -> binder::Result<()> {
        if self.closed.load(Ordering::Acquire) {
            Err(StatusCode::DEAD_OBJECT.into())
        } else {
            Ok(())
        }
    }

    fn algorithm(&self) -> Option<Arc<Algorithm>> {
        self.algorithm_cache
            .get_or_open(self.user_id, &self.algorithm_directory)
    }

    fn begin_operation(&self) -> binder::Result<Option<(CancellationState, OperationGuard)>> {
        self.ensure_open()?;
        if self
            .operation_active
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            self.callback.onError(Error::UNABLE_TO_PROCESS, 0)?;
            return Ok(None);
        }
        let cancellation = CancellationState::default();
        *self.current_cancellation.lock().unwrap() = Some(cancellation.clone());
        let guard = OperationGuard {
            active: self.operation_active.clone(),
            finished: self.operation_finished.clone(),
            current: self.current_cancellation.clone(),
            closed: self.closed.clone(),
            session_active: self.session_active.clone(),
        };
        Ok(Some((cancellation, guard)))
    }

    fn unavailable_operation(&self) -> binder::Result<Strong<dyn ICancellationSignal>> {
        let cancellation = CancellationState::default();
        self.callback.onError(Error::HW_UNAVAILABLE, 0)?;
        Ok(cancellation.binder())
    }

    fn start_enrollment(
        &self,
        hat: &HardwareAuthToken,
        features: &[Feature],
        preview_surface: Option<Surface>,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.ensure_open()?;
        eprintln!("FaceHAL enroll: request features={features:?}");
        let features_supported = features.iter().all(|feature| {
            matches!(
                *feature,
                Feature::REQUIRE_ATTENTION | Feature::REQUIRE_DIVERSE_POSES
            )
        });
        let challenge_valid = self.challenge_cache.contains(self.user_id, hat.challenge);
        let hat_valid = credential_hat_is_structurally_valid(hat);
        if !features_supported || !challenge_valid || !hat_valid {
            eprintln!(
                "FaceHAL enroll: accepting ColorOS compatibility metadata \
                 features_supported={features_supported} challenge_valid={challenge_valid} \
                 hat_valid={hat_valid} mac_len={}",
                hat.mac.len(),
            );
        }
        let Some(algorithm) = self.algorithm() else {
            return self.unavailable_operation();
        };
        let Some((cancellation, guard)) = self.begin_operation()? else {
            return Ok(CancellationState::default().binder());
        };
        let binder = cancellation.binder();
        let callback = self.callback.clone();
        let closed = self.closed.clone();
        let authenticator_id = self.authenticator_id.clone();

        if thread::Builder::new()
            .name("facehal-enroll".into())
            .spawn(move || {
                let _guard = guard;
                let mut preview = Preview::new(preview_surface);
                if algorithm.reset().is_err() {
                    eprintln!("FaceHAL enroll: unable to reset algorithm state");
                    notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                    return;
                }
                let before = match algorithm.enumerate() {
                    Ok(ids) => {
                        eprintln!("FaceHAL enroll: existing templates={ids:?}");
                        ids
                    }
                    Err(error) => {
                        eprintln!("FaceHAL enroll: initial enumerate failed: {error:?}");
                        notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                        return;
                    }
                };
                if before.len() >= 2 {
                    notify_error(&cancellation, &callback, &closed, Error::NO_SPACE, 0);
                    return;
                }
                if algorithm.set_active_slot(None).is_err() {
                    eprintln!("FaceHAL enroll: unable to select an empty template slot");
                    notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                    return;
                }
                let mut camera = match open_camera_with_retry("enroll") {
                    Ok(camera) => {
                        eprintln!(
                            "FaceHAL enroll: camera opened {}x{} orientation={}",
                            CAMERA_WIDTH,
                            CAMERA_HEIGHT,
                            camera.sensor_orientation()
                        );
                        camera
                    }
                    Err(error) => {
                        eprintln!("FaceHAL enroll: camera open failed: {error:?}");
                        notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                        return;
                    }
                };
                algorithm.set_sensor_orientation(camera.sensor_orientation());
                let deadline = Instant::now() + ENROLLMENT_TIMEOUT;
                let mut frame_count = 0usize;
                let mut timeout_count = 0usize;
                let mut bad_frame_count = 0usize;
                let mut progress_remaining = ENROLLMENT_CONFIRMATION_SAMPLES + 1;
                let mut last_status = None;
                // (enrollment id, physical template slot). Before this is set frames are sent to
                // the vendor enrollment action. Afterwards frames use authentication so a
                // one-frame vendor enrollment cannot be exposed to Android as complete.
                let mut candidate: Option<(i32, usize)> = None;
                let mut next_confirmation_at = Instant::now();
                let mut next_acquired_at = Instant::now();
                let dialect = Dialect::detect();
                eprintln!("FaceHAL enroll: dialect={dialect:?}");
                let mut previous_thumbnail: Option<[u8; THUMBNAIL_SIZE]> = None;
                while Instant::now() < deadline {
                    if should_stop(&cancellation, &closed, &callback) {
                        if let Some((candidate_id, _)) = candidate {
                            let _ = algorithm.remove(candidate_id);
                        }
                        return;
                    }
                    let frame = match camera.next_frame(FRAME_TIMEOUT_MS) {
                        Ok(frame) => frame,
                        Err(CameraError::Timeout) => {
                            timeout_count += 1;
                            if timeout_count == 1 || timeout_count % 10 == 0 {
                                eprintln!("FaceHAL enroll: camera timeout count={timeout_count}");
                            }
                            continue;
                        }
                        Err(CameraError::BadFrame) => {
                            bad_frame_count += 1;
                            if bad_frame_count == 1 || bad_frame_count % 10 == 0 {
                                eprintln!("FaceHAL enroll: bad frame count={bad_frame_count}");
                            }
                            continue;
                        }
                        Err(CameraError::Unavailable) => {
                            eprintln!("FaceHAL enroll: camera became unavailable");
                            if let Some((candidate_id, _)) = candidate {
                                let _ = algorithm.remove(candidate_id);
                            }
                            drop(camera);
                            drop(_guard);
                            notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                            return;
                        }
                    };
                    frame_count += 1;
                    preview.render(&frame, CAMERA_WIDTH, CAMERA_HEIGHT, camera.sensor_orientation());
                    let thumbnail = luma_thumbnail(&frame, CAMERA_WIDTH, CAMERA_HEIGHT);
                    let mean_luma = thumbnail_luma(&thumbnail);
                    let motion_score = previous_thumbnail
                        .map(|previous| thumbnail_motion(&previous, &thumbnail))
                        .unwrap_or(0);
                    previous_thumbnail = Some(thumbnail);

                    // Limit accepted confirmation samples. Camera preview remains continuous, but
                    // progress cannot be completed by a burst of adjacent frames.
                    if candidate.is_some() && Instant::now() < next_confirmation_at {
                        continue;
                    }
                    let action = if candidate.is_some() {
                        ACTION_AUTHENTICATE
                    } else {
                        ACTION_ENROLL
                    };
                    let status = algorithm.process_nv21(&frame, CAMERA_WIDTH, CAMERA_HEIGHT, action);
                    if last_status != Some(status) || frame_count == 1 || frame_count % 30 == 0 {
                        eprintln!(
                            "FaceHAL enroll: frame={frame_count} action={action} status={status} acquired={:?} remaining={progress_remaining}",
                            map_acquired(status)
                        );
                        last_status = Some(status);
                    }
                    let acquire_status = if map_acquired(status) == AcquiredInfo::GOOD {
                        status
                    } else {
                        guidance_status(status, mean_luma, motion_score)
                    };
                    if status < 0 {
                        eprintln!("FaceHAL enroll: algorithm fatal status={status}");
                        if let Some((candidate_id, _)) = candidate {
                            let _ = algorithm.remove(candidate_id);
                        }
                        drop(camera);
                        drop(_guard);
                        notify_error(&cancellation, &callback, &closed, map_error(status), status);
                        return;
                    }

                    if candidate.is_none() && (status == STATUS_OK || status == STATUS_ENROLL_OK) {
                        let after = match algorithm.enumerate() {
                            Ok(ids) => ids,
                            Err(error) => {
                                eprintln!("FaceHAL enroll: candidate enumerate failed: {error:?}");
                                notify_error(&cancellation, &callback, &closed, Error::UNABLE_TO_PROCESS, 0);
                                return;
                            }
                        };
                        let new_id = after.iter().copied().find(|id| !before.contains(id)).or_else(|| {
                            let current = algorithm.current_face_id();
                            (current >= 1 && after.contains(&current) && !before.contains(&current)).then_some(current)
                        });
                        if let Some(enrollment_id) = new_id {
                            let slot = algorithm.slots().ok().and_then(|slots| {
                                slots.iter().position(|id| *id == Some(enrollment_id))
                            });
                            let Some(slot) = slot else {
                                eprintln!("FaceHAL enroll: unable to locate candidate slot id={enrollment_id}");
                                let _ = algorithm.remove(enrollment_id);
                                notify_error(&cancellation, &callback, &closed, Error::UNABLE_TO_PROCESS, 0);
                                return;
                            };
                            if algorithm.reset().is_err() || algorithm.set_active_slot(Some(slot)).is_err() {
                                let _ = algorithm.remove(enrollment_id);
                                notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                                return;
                            }
                            candidate = Some((enrollment_id, slot));
                            progress_remaining -= 1;
                            if dialect.sends_vendor_steps() {
                                send_miui_enrollment_step(&callback);
                            }
                            // BBK screens draw the countdown beside the ring; MIUI
                            // shows its success view on the first progress callback.
                            if dialect.progress_per_stage() {
                                send_enrollment_progress(&callback, enrollment_id, progress_remaining);
                            }
                            next_confirmation_at = Instant::now() + ENROLLMENT_SAMPLE_INTERVAL;
                            eprintln!("FaceHAL enroll: candidate id={enrollment_id} slot={slot}; starting live confirmation");
                        }
                        // Do not send a successful EnrollmentFrame here. Android converts it
                        // to onEnrollmentHelp, which resets this MIUI ring animation.
                        continue;
                    }

                    if let Some((enrollment_id, slot)) = candidate {
                        if status == STATUS_OK || status == STATUS_UNLOCK_OK {
                            progress_remaining -= 1;
                            // ColorOS's enrollment screen starts its round mask and progress
                            // ring on remaining == 4 and only finishes when remaining == 0
                            // arrives after the ring has advanced.
                            if dialect.sends_vendor_steps() {
                                send_miui_enrollment_step(&callback);
                            }
                            eprintln!("FaceHAL enroll: confirmed id={enrollment_id} slot={slot} remaining={progress_remaining}");
                            if progress_remaining > 0 && dialect.progress_per_stage() {
                                send_enrollment_progress(&callback, enrollment_id, progress_remaining);
                            }
                            if progress_remaining == 0 {
                                if authenticator_id.rotate(true).is_err() {
                                    let _ = algorithm.remove(enrollment_id);
                                    let _ = authenticator_id.rotate(false);
                                    drop(camera);
                                    drop(preview);
                                    drop(_guard);
                                    notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                                    return;
                                }
                                if begin_terminal(&cancellation, &callback, &closed) {
                                    drop(camera);
                                    drop(preview);
                                    drop(_guard);
                                    eprintln!("FaceHAL enroll: completed id={enrollment_id} frames={frame_count} after live confirmation");
                                    match callback.onEnrollmentProgress(enrollment_id, 0) {
                                        Ok(()) => eprintln!("FaceHAL enroll: terminal progress delivered"),
                                        Err(_) => eprintln!("FaceHAL enroll: terminal progress failed"),
                                    }
                                } else {
                                    let _ = algorithm.remove(enrollment_id);
                                    let _ = authenticator_id.rotate(
                                        algorithm.enumerate().map(|ids| !ids.is_empty()).unwrap_or(false),
                                    );
                                }
                                return;
                            }
                            next_confirmation_at = Instant::now() + ENROLLMENT_SAMPLE_INTERVAL;
                        } else {
                            // A poor/non-matching frame does not advance enrollment. Keep the
                            // preview and acquired callbacks active until a valid live sample or timeout.
                            if Instant::now() >= next_acquired_at
                                && map_acquired(status) != AcquiredInfo::GOOD
                            {
                                send_enrollment_frame(&callback, acquire_status);
                                next_acquired_at = Instant::now() + ENROLLMENT_ACQUIRED_INTERVAL;
                            }
                            next_confirmation_at = Instant::now() + ENROLLMENT_SAMPLE_INTERVAL;
                        }
                    } else if Instant::now() >= next_acquired_at
                        && map_acquired(status) != AcquiredInfo::GOOD
                    {
                        send_enrollment_frame(&callback, acquire_status);
                        next_acquired_at = Instant::now() + ENROLLMENT_ACQUIRED_INTERVAL;
                    }
                }
                eprintln!(
                    "FaceHAL enroll: timed out frames={frame_count} camera_timeouts={timeout_count} bad_frames={bad_frame_count} last_status={last_status:?}"
                );
                if let Some((candidate_id, _)) = candidate {
                    let _ = algorithm.remove(candidate_id);
                }
                drop(camera);
                drop(_guard);
                notify_error(&cancellation, &callback, &closed, Error::TIMEOUT, 0);
            })
            .is_err()
        {
            self.operation_active.store(false, Ordering::Release);
            *self.current_cancellation.lock().unwrap() = None;
            self.callback.onError(Error::HW_UNAVAILABLE, 0)?;
        }
        Ok(binder)
    }

    fn start_authentication(
        &self,
        _operation_id: i64,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.ensure_open()?;
        match self.lockout.status() {
            Ok(LockoutState::None) => {}
            Ok(state) => {
                let cancellation = CancellationState::default();
                notify_lockout_state(&self.callback, &self.closed, self.lockout.clone(), state);
                return Ok(cancellation.binder());
            }
            Err(_) => return self.unavailable_operation(),
        }
        let Some(algorithm) = self.algorithm() else {
            return self.unavailable_operation();
        };
        let Some((cancellation, guard)) = self.begin_operation()? else {
            return Ok(CancellationState::default().binder());
        };
        let binder = cancellation.binder();
        let callback = self.callback.clone();
        let closed = self.closed.clone();
        let lockout = self.lockout.clone();

        if thread::Builder::new()
            .name("facehal-auth".into())
            .spawn(move || {
                let _guard = guard;
                if algorithm.reset().is_err() {
                    eprintln!("FaceHAL auth: unable to reset algorithm state");
                    notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                    return;
                }
                let enrollment_slots = match algorithm.slots() {
                    Ok(slots) if slots.iter().any(Option::is_some) => {
                        eprintln!("FaceHAL auth: enrollment slots={slots:?}");
                        slots
                    }
                    Ok(_) => {
                        eprintln!("FaceHAL auth: no enrolled templates");
                        if begin_terminal(&cancellation, &callback, &closed) {
                            let _ = callback.onAuthenticationFailed();
                        }
                        return;
                    }
                    Err(error) => {
                        eprintln!("FaceHAL auth: unable to read template slots: {error:?}");
                        notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                        return;
                    }
                };
                let mut camera = match open_camera_with_retry("auth") {
                    Ok(camera) => {
                        eprintln!(
                            "FaceHAL auth: camera opened {}x{} orientation={}",
                            CAMERA_WIDTH,
                            CAMERA_HEIGHT,
                            camera.sensor_orientation()
                        );
                        camera
                    }
                    Err(error) => {
                        eprintln!("FaceHAL auth: camera open failed: {error:?}");
                        notify_error(&cancellation, &callback, &closed, Error::HW_UNAVAILABLE, 0);
                        return;
                    }
                };
                algorithm.set_sensor_orientation(camera.sensor_orientation());
                let deadline = Instant::now() + AUTHENTICATION_TIMEOUT;
                let mut mismatch_frames = 0usize;
                let mut frame_count = 0usize;
                let mut last_status = None;
                while Instant::now() < deadline {
                    if should_stop(&cancellation, &closed, &callback) {
                        return;
                    }
                    let frame = match camera.next_frame(FRAME_TIMEOUT_MS) {
                        Ok(frame) => frame,
                        Err(CameraError::Timeout) => {
                            eprintln!("FaceHAL auth: camera frame timeout");
                            continue;
                        }
                        Err(CameraError::BadFrame) => {
                            eprintln!("FaceHAL auth: bad camera frame");
                            continue;
                        }
                        Err(CameraError::Unavailable) => {
                            eprintln!("FaceHAL auth: camera became unavailable");
                            drop(camera);
                            drop(_guard);
                            notify_error(
                                &cancellation,
                                &callback,
                                &closed,
                                Error::HW_UNAVAILABLE,
                                0,
                            );
                            return;
                        }
                    };
                    frame_count += 1;
                    let mut frame_mismatch = false;
                    let mut quality_status = None;
                    for (slot, enrollment_id) in enrollment_slots
                        .iter()
                        .copied()
                        .enumerate()
                        .filter_map(|(slot, id)| id.map(|id| (slot, id)))
                    {
                        if algorithm.set_active_slot(Some(slot)).is_err() {
                            eprintln!("FaceHAL auth: unable to activate template slot={slot}");
                            drop(camera);
                            drop(_guard);
                            notify_error(
                                &cancellation,
                                &callback,
                                &closed,
                                Error::HW_UNAVAILABLE,
                                0,
                            );
                            return;
                        }
                        let status = algorithm.process_nv21(
                            &frame,
                            CAMERA_WIDTH,
                            CAMERA_HEIGHT,
                            ACTION_AUTHENTICATE,
                        );
                        if last_status != Some(status) || frame_count == 1 {
                            eprintln!(
                                "FaceHAL auth: frame={frame_count} slot={slot} id={enrollment_id} status={status} acquired={:?}",
                                map_acquired(status)
                            );
                            last_status = Some(status);
                        }
                        if status == STATUS_OK || status == STATUS_UNLOCK_OK {
                            if !begin_terminal(&cancellation, &callback, &closed) {
                                return;
                            }
                            if lockout.record_success().is_err() {
                                eprintln!("FaceHAL auth: unable to persist lockout success");
                                if !closed.load(Ordering::Acquire) {
                                    let _ = callback.onError(Error::HW_UNAVAILABLE, 0);
                                }
                                return;
                            }
                            let hat = HardwareAuthToken::default();
                            if !closed.load(Ordering::Acquire) {
                                drop(camera);
                                drop(_guard);
                                eprintln!(
                                    "FaceHAL auth: completed id={enrollment_id} frames={frame_count} camera_released=true"
                                );
                                let _ = callback.onAuthenticationSucceeded(enrollment_id, &hat);
                            }
                            return;
                        }
                        if status < 0 {
                            eprintln!("FaceHAL auth: algorithm fatal status={status}");
                            drop(camera);
                            drop(_guard);
                            notify_error(
                                &cancellation,
                                &callback,
                                &closed,
                                map_error(status),
                                status,
                            );
                            return;
                        }
                        if status == STATUS_UNLOCK_FAILED || status == 0x02 {
                            frame_mismatch = true;
                            continue;
                        }
                        quality_status = Some(status);
                        break;
                    }
                    if let Some(status) = quality_status {
                        send_authentication_frame(&callback, status);
                    } else if frame_mismatch {
                        mismatch_frames += 1;
                        send_authentication_frame(&callback, STATUS_UNLOCK_FAILED);
                        if mismatch_frames >= MAX_MISMATCH_FRAMES {
                            drop(camera);
                            drop(_guard);
                            record_authentication_failure(
                                &cancellation,
                                &callback,
                                &closed,
                                &lockout,
                            );
                            return;
                        }
                    }
                }
                if mismatch_frames > 0 {
                    eprintln!(
                        "FaceHAL auth: failed frames={frame_count} mismatches={mismatch_frames}"
                    );
                    drop(camera);
                    drop(_guard);
                    record_authentication_failure(&cancellation, &callback, &closed, &lockout);
                } else {
                    eprintln!("FaceHAL auth: timed out frames={frame_count}");
                    drop(camera);
                    drop(_guard);
                    notify_error(&cancellation, &callback, &closed, Error::TIMEOUT, 0);
                }
            })
            .is_err()
        {
            self.operation_active.store(false, Ordering::Release);
            *self.current_cancellation.lock().unwrap() = None;
            self.callback.onError(Error::HW_UNAVAILABLE, 0)?;
        }
        Ok(binder)
    }

    fn random_i64() -> binder::Result<i64> {
        random_positive_i64().map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))
    }
}

impl Interface for FaceSession {}

impl ISession for FaceSession {
    fn r#generateChallenge(&self) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let challenge = Self::random_i64()?;
        self.challenge_cache.insert(self.user_id, challenge);
        self.callback.onChallengeGenerated(challenge)
    }

    fn r#revokeChallenge(&self, challenge: i64) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        self.challenge_cache.remove(self.user_id, challenge);
        self.callback.onChallengeRevoked(challenge)
    }

    fn r#getEnrollmentConfig(
        &self,
        _enrollment_type: EnrollmentType,
    ) -> binder::Result<Vec<EnrollmentStageConfig>> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(Vec::new());
        };
        Ok(vec![EnrollmentStageConfig {
            stage: EnrollmentStage::HOLD_STILL_IN_CENTER,
            ..Default::default()
        }])
    }

    fn r#enroll(
        &self,
        _hat: &HardwareAuthToken,
        _enrollment_type: EnrollmentType,
        _features: &[Feature],
        _preview_surface: Option<&NativeHandle>,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.start_enrollment(_hat, _features, None)
    }

    fn r#authenticate(&self, operation_id: i64) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.start_authentication(operation_id)
    }

    fn r#detectInteraction(&self) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.ensure_open()?;
        let Some((_operation_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(CancellationState::default().binder());
        };
        let cancellation = CancellationState::default();
        self.callback.onError(Error::UNABLE_TO_PROCESS, 0)?;
        Ok(cancellation.binder())
    }

    fn r#enumerateEnrollments(&self) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let Some(algorithm) = self.algorithm() else {
            return self.callback.onError(Error::HW_UNAVAILABLE, 0);
        };
        match algorithm.enumerate() {
            Ok(ids) => self.callback.onEnrollmentsEnumerated(&ids),
            Err(_) => self.callback.onError(Error::HW_UNAVAILABLE, 0),
        }
    }

    fn r#removeEnrollments(&self, enrollment_ids: &[i32]) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let Some(algorithm) = self.algorithm() else {
            return self.callback.onError(Error::HW_UNAVAILABLE, 0);
        };
        let before = match algorithm.enumerate() {
            Ok(ids) => ids,
            Err(_) => return self.callback.onError(Error::HW_UNAVAILABLE, 0),
        };
        if enrollment_ids.is_empty() {
            if algorithm.remove_all().is_err() {
                return self.callback.onError(Error::UNABLE_TO_REMOVE, 0);
            }
        } else {
            for enrollment_id in enrollment_ids.iter().copied().collect::<HashSet<_>>() {
                if before.contains(&enrollment_id) {
                    if algorithm.remove(enrollment_id).is_err() {
                        return self.callback.onError(Error::UNABLE_TO_REMOVE, 0);
                    }
                }
            }
        }
        let after = match algorithm.enumerate() {
            Ok(ids) => ids,
            Err(_) => return self.callback.onError(Error::HW_UNAVAILABLE, 0),
        };
        let removed = before
            .iter()
            .copied()
            .filter(|id| !after.contains(id))
            .collect::<Vec<_>>();
        let expected = if enrollment_ids.is_empty() {
            before.len()
        } else {
            enrollment_ids
                .iter()
                .copied()
                .collect::<HashSet<_>>()
                .iter()
                .filter(|id| before.contains(id))
                .count()
        };
        if removed.len() != expected {
            return self.callback.onError(Error::UNABLE_TO_REMOVE, 0);
        }
        if self.authenticator_id.rotate(!after.is_empty()).is_err() {
            return self.callback.onError(Error::HW_UNAVAILABLE, 0);
        }
        self.callback.onEnrollmentsRemoved(&removed)
    }

    fn r#getFeatures(&self) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let has_enrollment = self
            .algorithm()
            .and_then(|algorithm| algorithm.enumerate().ok())
            .is_some_and(|ids| !ids.is_empty());
        if !has_enrollment {
            return self.callback.onError(Error::UNABLE_TO_PROCESS, 0);
        }
        let features = if self
            .features
            .attention_required()
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?
        {
            vec![Feature::REQUIRE_ATTENTION]
        } else {
            Vec::new()
        };
        self.callback.onFeaturesRetrieved(&features)
    }

    fn r#setFeature(
        &self,
        hat: &HardwareAuthToken,
        feature: Feature,
        enabled: bool,
    ) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        if !credential_hat_is_structurally_valid(hat) || feature != Feature::REQUIRE_ATTENTION {
            return self.callback.onError(Error::UNABLE_TO_PROCESS, 0);
        }
        let has_enrollment = self
            .algorithm()
            .and_then(|algorithm| algorithm.enumerate().ok())
            .is_some_and(|ids| !ids.is_empty());
        if !has_enrollment {
            return self.callback.onError(Error::UNABLE_TO_PROCESS, 0);
        }
        self.features
            .set_attention_required(enabled)
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?;
        self.callback.onFeatureSet(feature)
    }

    fn r#getAuthenticatorId(&self) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let Some(algorithm) = self.algorithm() else {
            return self.callback.onError(Error::HW_UNAVAILABLE, 0);
        };
        let enrolled = !algorithm
            .enumerate()
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?
            .is_empty();
        let authenticator_id = self
            .authenticator_id
            .current_or_create(enrolled)
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?;
        self.callback.onAuthenticatorIdRetrieved(authenticator_id)
    }

    fn r#invalidateAuthenticatorId(&self) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        let Some(algorithm) = self.algorithm() else {
            return self.callback.onError(Error::HW_UNAVAILABLE, 0);
        };
        let enrolled = !algorithm
            .enumerate()
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?
            .is_empty();
        let new_id = self
            .authenticator_id
            .rotate(enrolled)
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?;
        self.callback.onAuthenticatorIdInvalidated(new_id)
    }

    fn r#resetLockout(&self, hat: &HardwareAuthToken) -> binder::Result<()> {
        self.ensure_open()?;
        let Some((_cancellation, _guard)) = self.begin_operation()? else {
            return Ok(());
        };
        if !credential_hat_is_structurally_valid(hat) {
            return self.callback.onError(Error::UNABLE_TO_PROCESS, 0);
        }
        self.lockout
            .reset()
            .map_err(|_| binder::Status::from(StatusCode::UNKNOWN_ERROR))?;
        self.callback.onLockoutCleared()
    }

    fn r#close(&self) -> binder::Result<()> {
        if !self.closed.swap(true, Ordering::AcqRel) {
            if let Some(cancellation) = self.current_cancellation.lock().unwrap().as_ref() {
                cancellation.request_cancel();
            }
            let mut completion = self.operation_finished.0.lock().unwrap();
            while self.operation_active.load(Ordering::Acquire) {
                let (next, result) = self
                    .operation_finished
                    .1
                    .wait_timeout(completion, Duration::from_secs(5))
                    .unwrap();
                completion = next;
                if result.timed_out() {
                    eprintln!("FaceHAL session: operation did not stop before close timeout");
                    break;
                }
            }
            drop(completion);
            if self.operation_active.load(Ordering::Acquire) {
                let operation_active = self.operation_active.clone();
                let operation_finished = self.operation_finished.clone();
                let session_active = self.session_active.clone();
                let callback = self.callback.clone();
                if thread::Builder::new()
                    .name("facehal-close-wait".into())
                    .spawn(move || {
                        let mut completion = operation_finished.0.lock().unwrap();
                        while operation_active.load(Ordering::Acquire) {
                            completion = operation_finished.1.wait(completion).unwrap();
                        }
                        session_active.store(false, Ordering::Release);
                        let _ = callback.onSessionClosed();
                    })
                    .is_err()
                {
                    eprintln!("FaceHAL session: unable to start deferred close waiter");
                    let mut completion = self.operation_finished.0.lock().unwrap();
                    while self.operation_active.load(Ordering::Acquire) {
                        completion = self.operation_finished.1.wait(completion).unwrap();
                    }
                    drop(completion);
                    self.session_active.store(false, Ordering::Release);
                    self.callback.onSessionClosed()?;
                }
            } else {
                self.session_active.store(false, Ordering::Release);
                self.callback.onSessionClosed()?;
            }
        }
        Ok(())
    }

    fn r#authenticateWithContext(
        &self,
        operation_id: i64,
        _context: &OperationContext,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.r#authenticate(operation_id)
    }

    fn r#enrollWithContext(
        &self,
        hat: &HardwareAuthToken,
        enrollment_type: EnrollmentType,
        features: &[Feature],
        preview_surface: Option<&NativeHandle>,
        _context: &OperationContext,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.r#enroll(hat, enrollment_type, features, preview_surface)
    }

    fn r#detectInteractionWithContext(
        &self,
        _context: &OperationContext,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.r#detectInteraction()
    }

    fn r#onContextChanged(&self, _context: &OperationContext) -> binder::Result<()> {
        self.ensure_open()
    }

    fn r#enrollWithOptions(
        &self,
        options: &FaceEnrollOptions,
    ) -> binder::Result<Strong<dyn ICancellationSignal>> {
        self.start_enrollment(
            &options.hardwareAuthToken,
            &options.features,
            options.surfacePreview.clone(),
        )
    }
}

impl Drop for FaceSession {
    fn drop(&mut self) {
        self.closed.store(true, Ordering::Release);
        if let Some(cancellation) = self.current_cancellation.lock().unwrap().as_ref() {
            cancellation.request_cancel();
        }
        if !self.operation_active.load(Ordering::Acquire) {
            self.session_active.store(false, Ordering::Release);
        }
    }
}

struct OperationGuard {
    active: Arc<AtomicBool>,
    finished: Arc<(Mutex<()>, Condvar)>,
    current: Arc<Mutex<Option<CancellationState>>>,
    closed: Arc<AtomicBool>,
    session_active: Arc<AtomicBool>,
}

impl Drop for OperationGuard {
    fn drop(&mut self) {
        *self.current.lock().unwrap() = None;
        self.active.store(false, Ordering::Release);
        if self.closed.load(Ordering::Acquire) {
            self.session_active.store(false, Ordering::Release);
        }
        self.finished.1.notify_all();
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SessionError {
    Storage,
}

fn should_stop(
    cancellation: &CancellationState,
    closed: &AtomicBool,
    callback: &Strong<dyn ISessionCallback>,
) -> bool {
    if closed.load(Ordering::Acquire) {
        let _ = cancellation.claim_terminal();
        return true;
    }
    if cancellation.is_cancelled() {
        let _ = begin_terminal(cancellation, callback, closed);
        return true;
    }
    false
}

fn open_camera_with_retry(operation: &str) -> Result<Camera, CameraError> {
    for attempt in 1..=CAMERA_OPEN_ATTEMPTS {
        match Camera::open(CAMERA_WIDTH, CAMERA_HEIGHT) {
            Ok(camera) => return Ok(camera),
            Err(error) if attempt < CAMERA_OPEN_ATTEMPTS => {
                eprintln!("FaceHAL {operation}: camera open attempt={attempt} failed: {error:?}");
                thread::sleep(CAMERA_OPEN_RETRY_DELAY);
            }
            Err(error) => return Err(error),
        }
    }
    unreachable!()
}

fn notify_error(
    cancellation: &CancellationState,
    callback: &Strong<dyn ISessionCallback>,
    closed: &AtomicBool,
    error: Error,
    vendor_code: i32,
) {
    if begin_terminal(cancellation, callback, closed) {
        eprintln!("FaceHAL operation error={error:?} vendor={vendor_code}");
        let _ = callback.onError(error, vendor_code);
    }
}

fn record_authentication_failure(
    cancellation: &CancellationState,
    callback: &Strong<dyn ISessionCallback>,
    closed: &Arc<AtomicBool>,
    lockout: &Arc<LockoutTracker>,
) {
    if !begin_terminal(cancellation, callback, closed) {
        return;
    }
    match lockout.record_failure() {
        Ok(LockoutState::None) => {
            if !closed.load(Ordering::Acquire) {
                let _ = callback.onAuthenticationFailed();
            }
        }
        Ok(state) => notify_lockout_state(callback, closed, lockout.clone(), state),
        Err(_) => {
            if !closed.load(Ordering::Acquire) {
                let _ = callback.onError(Error::HW_UNAVAILABLE, 0);
            }
        }
    }
}

fn begin_terminal(
    cancellation: &CancellationState,
    callback: &Strong<dyn ISessionCallback>,
    closed: &AtomicBool,
) -> bool {
    match cancellation.claim_terminal() {
        TerminalClaim::Proceed => !closed.load(Ordering::Acquire),
        TerminalClaim::Cancelled => {
            if !closed.load(Ordering::Acquire) {
                let _ = callback.onError(Error::CANCELED, 0);
            }
            false
        }
        TerminalClaim::AlreadyClaimed => false,
    }
}

fn notify_lockout_state(
    callback: &Strong<dyn ISessionCallback>,
    closed: &Arc<AtomicBool>,
    lockout: Arc<LockoutTracker>,
    state: LockoutState,
) {
    if closed.load(Ordering::Acquire) {
        return;
    }
    match state {
        LockoutState::None => {}
        LockoutState::Permanent => {
            let _ = callback.onLockoutPermanent();
        }
        LockoutState::Timed { remaining_millis } => {
            let duration = remaining_millis.min(i64::MAX as u64) as i64;
            let _ = callback.onLockoutTimed(duration);
            let callback = callback.clone();
            let closed = closed.clone();
            let _ = thread::Builder::new()
                .name("facehal-lockout".into())
                .spawn(move || {
                    thread::sleep(Duration::from_millis(remaining_millis));
                    if !closed.load(Ordering::Acquire)
                        && matches!(lockout.status(), Ok(LockoutState::None))
                    {
                        let _ = callback.onLockoutCleared();
                    }
                });
        }
    }
}

fn credential_hat_is_structurally_valid(hat: &HardwareAuthToken) -> bool {
    if hat.mac.len() != 32
        || (hat.authenticatorType != HardwareAuthenticatorType::PASSWORD
            && hat.authenticatorType != HardwareAuthenticatorType::ANY)
    {
        return false;
    }
    let Some(now_millis) = boot_time_millis() else {
        return false;
    };
    let timestamp = hat.timestamp.milliSeconds;
    timestamp >= 0
        && timestamp <= now_millis.saturating_add(MAXIMUM_HAT_FUTURE_SKEW_MILLIS)
        && now_millis.saturating_sub(timestamp) <= MAXIMUM_HAT_AGE_MILLIS
}

fn boot_time_millis() -> Option<i64> {
    let uptime = fs::read_to_string("/proc/uptime").ok()?;
    let seconds = uptime.split_whitespace().next()?.parse::<f64>().ok()?;
    if !seconds.is_finite() || seconds < 0.0 || seconds > i64::MAX as f64 / 1_000.0 {
        return None;
    }
    Some((seconds * 1_000.0) as i64)
}

fn base_frame(status: i32) -> BaseFrame {
    let acquired = map_acquired(status);
    BaseFrame {
        acquiredInfo: acquired,
        vendorCode: if acquired == AcquiredInfo::VENDOR {
            status
        } else {
            0
        },
        isCancellable: true,
        ..Default::default()
    }
}

fn send_authentication_frame(callback: &Strong<dyn ISessionCallback>, status: i32) {
    let frame = AuthenticationFrame {
        data: base_frame(status),
    };
    let _ = callback.onAuthenticationFrame(&frame);
}

fn send_enrollment_progress(
    callback: &Strong<dyn ISessionCallback>,
    enrollment_id: i32,
    remaining: i32,
) {
    match callback.onEnrollmentProgress(enrollment_id, remaining) {
        Ok(()) => {}
        Err(_) => eprintln!("FaceHAL enroll: progress remaining={remaining} failed"),
    }
}

fn send_miui_enrollment_step(callback: &Strong<dyn ISessionCallback>) {
    // Framework exposes VENDOR code 19 to FaceManager as help id 1019. MIUI strips
    // 1000 and uses value 19 to enter/advance its five-stage enrollment animation.
    let frame = EnrollmentFrame {
        cell: None,
        stage: EnrollmentStage::HOLD_STILL_IN_CENTER,
        data: BaseFrame {
            acquiredInfo: AcquiredInfo::VENDOR,
            vendorCode: 19,
            isCancellable: true,
            ..Default::default()
        },
    };
    match callback.onEnrollmentFrame(&frame) {
        Ok(()) => {}
        Err(_) => eprintln!("FaceHAL enroll: miui step failed"),
    }
}

fn send_enrollment_frame(callback: &Strong<dyn ISessionCallback>, status: i32) {
    let acquired = map_acquired(status);
    let stage = if status == 0x05 || acquired == AcquiredInfo::GOOD {
        EnrollmentStage::HOLD_STILL_IN_CENTER
    } else {
        EnrollmentStage::WAITING_FOR_CENTERING
    };
    let frame = EnrollmentFrame {
        cell: None,
        stage,
        data: base_frame(status),
    };
    let _ = callback.onEnrollmentFrame(&frame);
}

fn luma_thumbnail(frame: &[u8], width: i32, height: i32) -> [u8; THUMBNAIL_SIZE] {
    let mut thumbnail = [0u8; THUMBNAIL_SIZE];
    let width = width.max(1) as usize;
    let height = height.max(1) as usize;
    for row in 0..THUMBNAIL_HEIGHT {
        let source_y = row * height / THUMBNAIL_HEIGHT;
        for column in 0..THUMBNAIL_WIDTH {
            let source_x = column * width / THUMBNAIL_WIDTH;
            let index = source_y * width + source_x;
            thumbnail[row * THUMBNAIL_WIDTH + column] = frame.get(index).copied().unwrap_or(0);
        }
    }
    thumbnail
}

fn thumbnail_luma(thumbnail: &[u8]) -> u32 {
    let sum: u32 = thumbnail.iter().map(|value| *value as u32).sum();
    sum / thumbnail.len().max(1) as u32
}

fn thumbnail_motion(previous: &[u8], current: &[u8]) -> u32 {
    let sum: u32 = previous
        .iter()
        .zip(current)
        .map(|(a, b)| (*a as i32 - *b as i32).unsigned_abs())
        .sum();
    sum / previous.len().max(1) as u32
}

fn guidance_status(status: i32, luma: u32, motion: u32) -> i32 {
    if luma < DARK_FRAME_LUMA {
        STATUS_TOO_DARK
    } else if motion > MOTION_FRAME_SCORE {
        STATUS_TOO_MUCH_MOTION
    } else {
        status
    }
}

fn map_acquired(status: i32) -> AcquiredInfo {
    match status {
        0x01 | 0x69 | 0x7d | 0x7f => AcquiredInfo::NOT_DETECTED,
        0x04 | 0x66 | 0x70 | 0x75 | 0x77 | 0x81 | STATUS_UNLOCK_FAILED => {
            AcquiredInfo::INSUFFICIENT
        }
        0x07 | 0x7c => AcquiredInfo::TOO_BRIGHT,
        0x7b => AcquiredInfo::TOO_DARK,
        0x79 => AcquiredInfo::TOO_CLOSE,
        0x78 => AcquiredInfo::TOO_FAR,
        0x84 => AcquiredInfo::FACE_TOO_HIGH,
        0x86 => AcquiredInfo::FACE_TOO_LOW,
        0x85 => AcquiredInfo::FACE_TOO_RIGHT,
        0x83 => AcquiredInfo::FACE_TOO_LEFT,
        0x6e | 0x6f | 0x73 | 0x74 => AcquiredInfo::PAN_TOO_EXTREME,
        0x6c | 0x6d | 0x71 | 0x72 => AcquiredInfo::TILT_TOO_EXTREME,
        0x7e => AcquiredInfo::ROLL_TOO_EXTREME,
        0x03 => AcquiredInfo::POOR_GAZE,
        0x67 | 0x7a | 0x82 => AcquiredInfo::FACE_OBSCURED,
        0x68 | 0x76 => AcquiredInfo::MOUTH_COVERING_DETECTED,
        0x06 | 0x6a => AcquiredInfo::TOO_DIFFERENT,
        0x80 => AcquiredInfo::TOO_MUCH_MOTION,
        0x05 | 0x6b => AcquiredInfo::GOOD,
        _ => AcquiredInfo::VENDOR,
    }
}

fn map_error(status: i32) -> Error {
    match status {
        -2 | -13 | -14 | -15 | -25 | -1002 | -1003 | -1005 | -1006 | -1007 | -1010 | -1013 => {
            Error::HW_UNAVAILABLE
        }
        -3 | -1008 => Error::NO_SPACE,
        -1001 => Error::REENROLL_REQUIRED,
        -1004 => Error::UNABLE_TO_REMOVE,
        _ => Error::UNABLE_TO_PROCESS,
    }
}

fn random_positive_i64() -> std::io::Result<i64> {
    let mut bytes = [0u8; 8];
    File::open("/dev/urandom")?.read_exact(&mut bytes)?;
    let value = i64::from_ne_bytes(bytes) & i64::MAX;
    Ok(value.max(1))
}
