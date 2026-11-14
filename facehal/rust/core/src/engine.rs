use crate::{AlgorithmBackend, FaceError, MatchResult, TemplateRecord, TemplateStore};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OperationKind {
    Enrollment,
    Authentication,
    Interaction,
}

#[derive(Clone)]
pub struct Operation {
    id: u64,
    kind: OperationKind,
    cancelled: Arc<AtomicBool>,
}

impl Operation {
    pub fn id(&self) -> u64 {
        self.id
    }
    pub fn kind(&self) -> OperationKind {
        self.kind
    }
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Release);
    }
    pub fn check_cancelled(&self) -> Result<(), FaceError> {
        if self.cancelled.load(Ordering::Acquire) {
            Err(FaceError::Cancelled)
        } else {
            Ok(())
        }
    }
}

pub struct Engine<B: AlgorithmBackend> {
    backend: B,
    store: TemplateStore,
    active: Mutex<Option<Operation>>,
    next_operation: AtomicU64,
}

impl<B: AlgorithmBackend> Engine<B> {
    pub fn new(backend: B, store: TemplateStore) -> Self {
        Self {
            backend,
            store,
            active: Mutex::new(None),
            next_operation: AtomicU64::new(1),
        }
    }

    pub fn begin(&self, kind: OperationKind) -> Result<Operation, FaceError> {
        let mut active = self.active.lock().unwrap();
        if active.is_some() {
            return Err(FaceError::Busy);
        }
        let operation = Operation {
            id: self.next_operation.fetch_add(1, Ordering::Relaxed),
            kind,
            cancelled: Arc::new(AtomicBool::new(false)),
        };
        *active = Some(operation.clone());
        Ok(operation)
    }

    pub fn finish(&self, operation: &Operation) {
        let mut active = self.active.lock().unwrap();
        if active.as_ref().map(Operation::id) == Some(operation.id()) {
            *active = None;
        }
    }

    pub fn cancel_active(&self) -> bool {
        let active = self.active.lock().unwrap();
        if let Some(operation) = active.as_ref() {
            operation.cancel();
            true
        } else {
            false
        }
    }

    pub fn enroll_embedding(
        &self,
        operation: &Operation,
        id: i32,
        frame: &[u8],
    ) -> Result<(), FaceError> {
        operation.check_cancelled()?;
        let embedding = self
            .backend
            .extract_embedding(frame)
            .map_err(map_backend_error)?;
        operation.check_cancelled()?;
        self.store.put(&TemplateRecord { id, embedding })
    }

    pub fn authenticate_frame(
        &self,
        operation: &Operation,
        frame: &[u8],
        threshold: f32,
    ) -> Result<Option<(i32, MatchResult)>, FaceError> {
        operation.check_cancelled()?;
        let probe = self
            .backend
            .extract_embedding(frame)
            .map_err(map_backend_error)?;
        let mut best: Option<(i32, MatchResult)> = None;
        for record in self.store.list()? {
            operation.check_cancelled()?;
            let result = self
                .backend
                .compare(&probe, &record.embedding)
                .map_err(map_backend_error)?;
            if result.matched
                && result.score >= threshold
                && best
                    .as_ref()
                    .map(|(_, current)| result.score > current.score)
                    .unwrap_or(true)
            {
                best = Some((record.id, result));
            }
        }
        Ok(best)
    }

    pub fn store(&self) -> &TemplateStore {
        &self.store
    }
}

fn map_backend_error(error: crate::BackendError) -> FaceError {
    match error {
        crate::BackendError::Unavailable => FaceError::BackendUnavailable,
        _ => FaceError::InvalidArgument,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::BackendError;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TestBackend;
    impl AlgorithmBackend for TestBackend {
        fn name(&self) -> &'static str {
            "test"
        }
        fn extract_embedding(&self, frame: &[u8]) -> Result<Vec<f32>, BackendError> {
            Ok(frame.iter().map(|value| *value as f32 / 255.0).collect())
        }
        fn compare(&self, probe: &[f32], enrolled: &[f32]) -> Result<MatchResult, BackendError> {
            let distance: f32 = probe.iter().zip(enrolled).map(|(a, b)| (a - b).abs()).sum();
            let score = 1.0 - distance / probe.len().max(1) as f32;
            Ok(MatchResult {
                matched: score >= 0.9,
                score,
            })
        }
    }

    fn temp_root() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("facehal-engine-{suffix}"))
    }

    #[test]
    fn enroll_authenticate_and_reject() {
        let root = temp_root();
        let engine = Engine::new(TestBackend, TemplateStore::new(&root, 0).unwrap());
        let enroll = engine.begin(OperationKind::Enrollment).unwrap();
        engine.enroll_embedding(&enroll, 42, &[10, 20, 30]).unwrap();
        engine.finish(&enroll);
        let auth = engine.begin(OperationKind::Authentication).unwrap();
        assert_eq!(
            engine
                .authenticate_frame(&auth, &[10, 20, 30], 0.9)
                .unwrap()
                .unwrap()
                .0,
            42
        );
        assert!(engine
            .authenticate_frame(&auth, &[250, 250, 250], 0.9)
            .unwrap()
            .is_none());
        engine.finish(&auth);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn cancellation_is_observed() {
        let root = temp_root();
        let engine = Engine::new(TestBackend, TemplateStore::new(&root, 0).unwrap());
        let operation = engine.begin(OperationKind::Authentication).unwrap();
        operation.cancel();
        assert!(matches!(
            engine.authenticate_frame(&operation, &[1], 0.9),
            Err(FaceError::Cancelled)
        ));
        engine.finish(&operation);
        std::fs::remove_dir_all(root).unwrap();
    }
}
