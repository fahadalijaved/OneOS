use crate::FaceError;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CapturePurpose {
    Enrollment,
    Authentication,
    Interaction,
}

pub trait FrameSource: Send {
    fn next_frame(&mut self) -> Result<Vec<u8>, FaceError>;
}

#[derive(Debug)]
pub enum BackendError {
    Unavailable,
    BadFrame,
    NoFace,
    Spoof,
    Internal,
}

impl Display for BackendError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{self:?}")
    }
}

impl std::error::Error for BackendError {}

#[derive(Clone, Debug, PartialEq)]
pub struct MatchResult {
    pub matched: bool,
    pub score: f32,
}

pub trait AlgorithmBackend: Send + Sync {
    fn name(&self) -> &'static str;
    fn extract_embedding(&self, frame: &[u8]) -> Result<Vec<f32>, BackendError>;
    fn compare(&self, probe: &[f32], enrolled: &[f32]) -> Result<MatchResult, BackendError>;
}
