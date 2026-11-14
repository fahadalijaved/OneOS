use crate::FaceError;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

const MAGIC: &[u8; 8] = b"FHALATT1";

pub struct FeatureStore {
    root: PathBuf,
    user_id: i32,
}

impl FeatureStore {
    pub fn new(root: impl AsRef<Path>, user_id: i32) -> Result<Self, FaceError> {
        if user_id < 0 {
            return Err(FaceError::InvalidArgument);
        }
        Ok(Self {
            root: root.as_ref().to_path_buf(),
            user_id,
        })
    }

    pub fn attention_required(&self) -> Result<bool, FaceError> {
        let path = self.path();
        if !path.exists() {
            return Ok(true);
        }
        if !path.symlink_metadata()?.file_type().is_file() {
            return Err(FaceError::CorruptStore);
        }
        let mut contents = Vec::new();
        OpenOptions::new()
            .read(true)
            .open(path)?
            .read_to_end(&mut contents)?;
        if contents.len() != MAGIC.len() + 1
            || &contents[..MAGIC.len()] != MAGIC
            || contents[MAGIC.len()] > 1
        {
            return Err(FaceError::CorruptStore);
        }
        Ok(contents[MAGIC.len()] == 1)
    }

    pub fn set_attention_required(&self, enabled: bool) -> Result<(), FaceError> {
        let directory = self.directory();
        fs::create_dir_all(&directory)?;
        fs::set_permissions(&directory, fs::Permissions::from_mode(0o700))?;

        let temporary = directory.join(format!(".features-{}.tmp", std::process::id()));
        let result = (|| {
            let mut file = OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .mode(0o600)
                .open(&temporary)?;
            file.write_all(MAGIC)?;
            file.write_all(&[u8::from(enabled)])?;
            file.sync_all()?;
            fs::rename(&temporary, self.path())?;
            fs::set_permissions(self.path(), fs::Permissions::from_mode(0o600))?;
            sync_directory(&directory)
        })();
        if temporary.exists() {
            let _ = fs::remove_file(temporary);
        }
        result
    }

    fn directory(&self) -> PathBuf {
        self.root
            .join(self.user_id.to_string())
            .join("facedata")
            .join("facehal")
    }

    fn path(&self) -> PathBuf {
        self.directory().join("features")
    }
}

fn sync_directory(path: &Path) -> Result<(), FaceError> {
    OpenOptions::new().read(true).open(path)?.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_root() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("facehal-features-{suffix}"))
    }

    #[test]
    fn defaults_enabled_and_persists() {
        let root = temp_root();
        let store = FeatureStore::new(&root, 0).unwrap();
        assert!(store.attention_required().unwrap());
        store.set_attention_required(false).unwrap();
        assert!(!FeatureStore::new(&root, 0)
            .unwrap()
            .attention_required()
            .unwrap());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn isolates_users_and_rejects_corruption() {
        let root = temp_root();
        FeatureStore::new(&root, 0)
            .unwrap()
            .set_attention_required(false)
            .unwrap();
        assert!(FeatureStore::new(&root, 10)
            .unwrap()
            .attention_required()
            .unwrap());
        std::fs::write(
            root.join("0/facedata/facehal/features"),
            b"invalid feature state",
        )
        .unwrap();
        assert!(matches!(
            FeatureStore::new(&root, 0).unwrap().attention_required(),
            Err(FaceError::CorruptStore)
        ));
        std::fs::remove_dir_all(root).unwrap();
    }
}
