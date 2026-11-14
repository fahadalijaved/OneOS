use android_hardware_biometrics_common::aidl::android::hardware::biometrics::common::ICancellationSignal::{
    BnCancellationSignal, ICancellationSignal,
};
use binder::{BinderFeatures, Interface, Strong};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

#[derive(Clone, Default)]
pub struct CancellationState {
    cancelled: Arc<AtomicBool>,
    terminal_claimed: Arc<AtomicBool>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TerminalClaim {
    Proceed,
    Cancelled,
    AlreadyClaimed,
}

impl CancellationState {
    pub fn binder(&self) -> Strong<dyn ICancellationSignal> {
        BnCancellationSignal::new_binder(self.clone(), BinderFeatures::default())
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::Acquire)
    }

    pub fn request_cancel(&self) {
        self.cancelled.store(true, Ordering::Release);
    }

    pub fn claim_terminal(&self) -> TerminalClaim {
        if self
            .terminal_claimed
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            return TerminalClaim::AlreadyClaimed;
        }
        if self.is_cancelled() {
            TerminalClaim::Cancelled
        } else {
            TerminalClaim::Proceed
        }
    }
}

impl Interface for CancellationState {}

impl ICancellationSignal for CancellationState {
    fn r#cancel(&self) -> binder::Result<()> {
        self.request_cancel();
        Ok(())
    }
}
