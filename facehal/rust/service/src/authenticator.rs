use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

const ID_SIZE: usize = 8;

#[derive(Clone)]
pub struct AuthenticatorIdStore {
    directory: PathBuf,
    path: PathBuf,
}

impl AuthenticatorIdStore {
    pub fn new(directory: impl AsRef<Path>) -> Self {
        let directory = directory.as_ref().to_path_buf();
        Self {
            path: directory.join("authenticator_id"),
            directory,
        }
    }

    pub fn current_or_create(&self, enrolled: bool) -> io::Result<i64> {
        if !enrolled {
            return Ok(0);
        }
        if self.path.exists() {
            let mut bytes = [0u8; ID_SIZE];
            File::open(&self.path)?.read_exact(&mut bytes)?;
            let value = i64::from_le_bytes(bytes);
            if value > 0 {
                return Ok(value);
            }
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "invalid authenticator id",
            ));
        }
        self.rotate(true)
    }

    pub fn rotate(&self, enrolled: bool) -> io::Result<i64> {
        if !enrolled {
            if self.path.exists() {
                fs::remove_file(&self.path)?;
                File::open(&self.directory)?.sync_all()?;
            }
            return Ok(0);
        }
        let value = random_positive_i64()?;
        let temporary = self
            .directory
            .join(format!(".authenticator_id.{}.tmp", std::process::id()));
        let result = (|| {
            let mut file = OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .mode(0o600)
                .open(&temporary)?;
            file.write_all(&value.to_le_bytes())?;
            file.sync_all()?;
            fs::rename(&temporary, &self.path)?;
            fs::set_permissions(&self.path, fs::Permissions::from_mode(0o600))?;
            File::open(&self.directory)?.sync_all()
        })();
        if result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        result.map(|()| value)
    }
}

fn random_positive_i64() -> io::Result<i64> {
    let mut bytes = [0u8; 8];
    File::open("/dev/urandom")?.read_exact(&mut bytes)?;
    Ok((i64::from_ne_bytes(bytes) & i64::MAX).max(1))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_directory() -> PathBuf {
        std::env::temp_dir().join(format!(
            "facehal-authenticator-{}",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
    }

    #[test]
    fn empty_store_reports_zero_without_creating_id() {
        let directory = temp_directory();
        fs::create_dir_all(&directory).unwrap();
        let store = AuthenticatorIdStore::new(&directory);
        assert_eq!(store.current_or_create(false).unwrap(), 0);
        assert!(!store.path.exists());
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn rotation_persists_and_empty_state_removes_id() {
        let directory = temp_directory();
        fs::create_dir_all(&directory).unwrap();
        let store = AuthenticatorIdStore::new(&directory);
        let first = store.rotate(true).unwrap();
        assert!(first > 0);
        assert_eq!(store.current_or_create(true).unwrap(), first);
        let second = store.rotate(true).unwrap();
        assert!(second > 0);
        assert_ne!(second, first);
        assert_eq!(store.rotate(false).unwrap(), 0);
        assert!(!store.path.exists());
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn corrupt_id_is_rejected() {
        let directory = temp_directory();
        fs::create_dir_all(&directory).unwrap();
        let store = AuthenticatorIdStore::new(&directory);
        fs::write(&store.path, [0u8; ID_SIZE]).unwrap();
        assert_eq!(
            store.current_or_create(true).unwrap_err().kind(),
            io::ErrorKind::InvalidData
        );
        fs::remove_dir_all(directory).unwrap();
    }
}
