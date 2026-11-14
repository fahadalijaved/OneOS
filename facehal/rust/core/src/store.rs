use crate::FaceError;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

const MAGIC: &[u8; 8] = b"FHALTMP1";
const MAX_EMBEDDING_VALUES: usize = 16_384;

#[derive(Clone, Debug, PartialEq)]
pub struct TemplateRecord {
    pub id: i32,
    pub embedding: Vec<f32>,
}

pub struct TemplateStore {
    root: PathBuf,
    user_id: i32,
}

impl TemplateStore {
    pub fn new(root: impl AsRef<Path>, user_id: i32) -> Result<Self, FaceError> {
        if user_id < 0 {
            return Err(FaceError::InvalidArgument);
        }
        let store = Self {
            root: root.as_ref().to_path_buf(),
            user_id,
        };
        fs::create_dir_all(store.face_data_dir())?;
        fs::set_permissions(store.face_data_dir(), fs::Permissions::from_mode(0o770))?;
        fs::create_dir_all(store.facehal_dir())?;
        fs::set_permissions(store.facehal_dir(), fs::Permissions::from_mode(0o700))?;
        fs::create_dir_all(store.user_dir())?;
        fs::set_permissions(store.user_dir(), fs::Permissions::from_mode(0o700))?;
        Ok(store)
    }

    pub fn list(&self) -> Result<Vec<TemplateRecord>, FaceError> {
        let mut records = Vec::new();
        for entry in fs::read_dir(self.user_dir())? {
            let entry = entry?;
            if entry.file_type()?.is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("tmpl")
            {
                records.push(read_record(&entry.path())?);
            }
        }
        records.sort_by_key(|record| record.id);
        Ok(records)
    }

    pub fn put(&self, record: &TemplateRecord) -> Result<(), FaceError> {
        if record.id <= 0
            || record.embedding.is_empty()
            || record.embedding.len() > MAX_EMBEDDING_VALUES
        {
            return Err(FaceError::InvalidArgument);
        }
        let final_path = self.template_path(record.id);
        let temp_path = final_path.with_extension("tmp");
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(0o600)
            .open(&temp_path)?;
        file.write_all(MAGIC)?;
        file.write_all(&record.id.to_le_bytes())?;
        file.write_all(&(record.embedding.len() as u32).to_le_bytes())?;
        for value in &record.embedding {
            file.write_all(&value.to_le_bytes())?;
        }
        file.sync_all()?;
        fs::rename(temp_path, &final_path)?;
        fs::set_permissions(&final_path, fs::Permissions::from_mode(0o600))?;
        sync_dir(&self.user_dir())?;
        Ok(())
    }

    pub fn remove(&self, ids: &[i32]) -> Result<Vec<i32>, FaceError> {
        let mut removed = Vec::new();
        for id in ids {
            let path = self.template_path(*id);
            if path.exists() {
                fs::remove_file(path)?;
                removed.push(*id);
            }
        }
        sync_dir(&self.user_dir())?;
        Ok(removed)
    }

    pub fn remove_all(&self) -> Result<Vec<i32>, FaceError> {
        let ids: Vec<i32> = self.list()?.into_iter().map(|record| record.id).collect();
        self.remove(&ids)
    }

    pub fn authenticator_id(&self) -> Result<u64, FaceError> {
        let mut hash = 0xcbf29ce484222325u64;
        for record in self.list()? {
            for byte in record.id.to_le_bytes() {
                hash = (hash ^ byte as u64).wrapping_mul(0x100000001b3);
            }
            for value in record.embedding {
                for byte in value.to_bits().to_le_bytes() {
                    hash = (hash ^ byte as u64).wrapping_mul(0x100000001b3);
                }
            }
        }
        Ok(hash)
    }

    fn user_dir(&self) -> PathBuf {
        self.facehal_dir().join("templates")
    }

    fn facehal_dir(&self) -> PathBuf {
        self.face_data_dir().join("facehal")
    }

    fn face_data_dir(&self) -> PathBuf {
        self.root.join(self.user_id.to_string()).join("facedata")
    }

    fn template_path(&self, id: i32) -> PathBuf {
        self.user_dir().join(format!("{id}.tmpl"))
    }
}

fn read_record(path: &Path) -> Result<TemplateRecord, FaceError> {
    let mut file = File::open(path)?;
    let mut header = [0u8; 16];
    file.read_exact(&mut header)?;
    if &header[..8] != MAGIC {
        return Err(FaceError::CorruptStore);
    }
    let id = i32::from_le_bytes(header[8..12].try_into().unwrap());
    let count = u32::from_le_bytes(header[12..16].try_into().unwrap()) as usize;
    if id <= 0 || count == 0 || count > MAX_EMBEDDING_VALUES {
        return Err(FaceError::CorruptStore);
    }
    let mut embedding = Vec::with_capacity(count);
    for _ in 0..count {
        let mut bytes = [0u8; 4];
        file.read_exact(&mut bytes)?;
        embedding.push(f32::from_le_bytes(bytes));
    }
    let mut trailing = [0u8; 1];
    if file.read(&mut trailing)? != 0 {
        return Err(FaceError::CorruptStore);
    }
    Ok(TemplateRecord { id, embedding })
}

fn sync_dir(path: &Path) -> Result<(), FaceError> {
    File::open(path)?.sync_all()?;
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
        std::env::temp_dir().join(format!("facehal-store-{suffix}"))
    }

    #[test]
    fn persists_and_isolates_users() {
        let root = temp_root();
        let user_zero = TemplateStore::new(&root, 0).unwrap();
        let user_ten = TemplateStore::new(&root, 10).unwrap();
        user_zero
            .put(&TemplateRecord {
                id: 1,
                embedding: vec![0.1, 0.2],
            })
            .unwrap();
        user_ten
            .put(&TemplateRecord {
                id: 2,
                embedding: vec![0.3, 0.4],
            })
            .unwrap();
        assert_eq!(user_zero.list().unwrap()[0].id, 1);
        assert_eq!(user_ten.list().unwrap()[0].id, 2);
        drop(user_zero);
        assert_eq!(
            TemplateStore::new(&root, 0).unwrap().list().unwrap().len(),
            1
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn removal_updates_authenticator_id() {
        let root = temp_root();
        let store = TemplateStore::new(&root, 0).unwrap();
        let empty = store.authenticator_id().unwrap();
        store
            .put(&TemplateRecord {
                id: 7,
                embedding: vec![1.0],
            })
            .unwrap();
        let enrolled = store.authenticator_id().unwrap();
        assert_ne!(empty, enrolled);
        assert_eq!(store.remove(&[7]).unwrap(), vec![7]);
        assert_eq!(empty, store.authenticator_id().unwrap());
        fs::remove_dir_all(root).unwrap();
    }
}
