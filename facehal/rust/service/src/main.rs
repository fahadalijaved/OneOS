mod algorithm;
mod authenticator;
mod camera;
mod cancellation;
mod dialect;
mod face;
mod preview;
mod session;

use android_hardware_biometrics_face::aidl::android::hardware::biometrics::face::IFace::BnFace;
use binder::{add_service, BinderFeatures, ProcessState};
use face::FaceService;

const INSTANCE: &str = "android.hardware.biometrics.face.IFace/default";

fn main() {
    if let Some(exit_code) = camera::run_worker_from_args() {
        std::process::exit(exit_code);
    }

    ProcessState::set_thread_pool_max_thread_count(4);

    let service = BnFace::new_binder(FaceService::new(), BinderFeatures::default());
    add_service(INSTANCE, service.as_binder()).expect("failed to register Face HAL");

    log::info!("registered {INSTANCE}");
    ProcessState::join_thread_pool();
}
