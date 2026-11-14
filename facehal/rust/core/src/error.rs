use std::fmt::{Display, Formatter};
use std::io;

#[derive(Debug)]
pub enum FaceError {
    Busy,
    Cancelled,
    InvalidArgument,
    NoEnrollment,
    BackendUnavailable,
    Io(io::Error),
    CorruptStore,
}

impl Display for FaceError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Busy => write!(formatter, "another operation is active"),
            Self::Cancelled => write!(formatter, "operation cancelled"),
            Self::InvalidArgument => write!(formatter, "invalid argument"),
            Self::NoEnrollment => write!(formatter, "no enrolled face"),
            Self::BackendUnavailable => write!(formatter, "algorithm backend unavailable"),
            Self::Io(error) => write!(formatter, "I/O error: {error}"),
            Self::CorruptStore => write!(formatter, "template store is corrupt"),
        }
    }
}

impl std::error::Error for FaceError {}

impl From<io::Error> for FaceError {
    fn from(value: io::Error) -> Self {
        Self::Io(value)
    }
}
