use std::ffi::{c_char, c_void, CString};
use std::path::Path;
use std::ptr::NonNull;

#[repr(C)]
struct NativeAlgorithm(c_void);

unsafe extern "C" {
    fn facehal_algorithm_open(template_directory: *const c_char) -> *mut NativeAlgorithm;
    fn facehal_algorithm_close(algorithm: *mut NativeAlgorithm);
    fn facehal_algorithm_process_nv21(
        algorithm: *mut NativeAlgorithm,
        image: *const u8,
        image_size: usize,
        width: i32,
        height: i32,
        stride: i32,
        action: i32,
        config: i32,
    ) -> i32;
    fn facehal_algorithm_current_face_id(algorithm: *const NativeAlgorithm) -> i32;
    fn facehal_algorithm_enumerate(
        algorithm: *const NativeAlgorithm,
        enrollment_ids: *mut i32,
        capacity: usize,
    ) -> i32;
    fn facehal_algorithm_slots(
        algorithm: *const NativeAlgorithm,
        enrollment_ids: *mut i32,
        capacity: usize,
    ) -> i32;
    fn facehal_algorithm_remove(algorithm: *mut NativeAlgorithm, enrollment_id: i32) -> i32;
    fn facehal_algorithm_remove_all(algorithm: *mut NativeAlgorithm) -> i32;
    fn facehal_algorithm_set_active_slot(algorithm: *mut NativeAlgorithm, slot: i32) -> i32;
    fn facehal_algorithm_reset(algorithm: *mut NativeAlgorithm) -> i32;
    fn facehal_algorithm_set_orientation(algorithm: *mut NativeAlgorithm, orientation: i32);
}

pub const ACTION_AUTHENTICATE: i32 = 0;
pub const ACTION_ENROLL: i32 = 1;
/// The Xiaomi application leaves every optional function bit enabled and passes zero for both
/// enrollment and authentication. The bundled native implementation also ignores the config
/// argument, but keeping the observed value explicit prevents accidental policy changes.
pub const FUNCTION_CONFIG_DEFAULT: i32 = 0;
pub const STATUS_OK: i32 = 0;
pub const STATUS_ENROLL_OK: i32 = 0x65;
pub const STATUS_UNLOCK_OK: i32 = 0xc9;
pub const STATUS_UNLOCK_FAILED: i32 = 0xca;

pub struct Algorithm {
    native: NonNull<NativeAlgorithm>,
}

unsafe impl Send for Algorithm {}
unsafe impl Sync for Algorithm {}

impl Algorithm {
    pub fn open(template_directory: &Path) -> Result<Self, AlgorithmError> {
        let directory = template_directory
            .to_str()
            .ok_or(AlgorithmError::InvalidPath)?;
        let directory = CString::new(directory).map_err(|_| AlgorithmError::InvalidPath)?;
        let native = NonNull::new(unsafe { facehal_algorithm_open(directory.as_ptr()) })
            .ok_or(AlgorithmError::Unavailable)?;
        Ok(Self { native })
    }

    pub fn process_nv21(&self, image: &[u8], width: i32, height: i32, action: i32) -> i32 {
        unsafe {
            facehal_algorithm_process_nv21(
                self.native.as_ptr(),
                image.as_ptr(),
                image.len(),
                width,
                height,
                width,
                action,
                FUNCTION_CONFIG_DEFAULT,
            )
        }
    }

    pub fn current_face_id(&self) -> i32 {
        unsafe { facehal_algorithm_current_face_id(self.native.as_ptr()) }
    }

    pub fn enumerate(&self) -> Result<Vec<i32>, AlgorithmError> {
        let mut ids = [0; 2];
        let count = unsafe {
            facehal_algorithm_enumerate(self.native.as_ptr(), ids.as_mut_ptr(), ids.len())
        };
        if count < 0 || count as usize > ids.len() {
            return Err(AlgorithmError::OperationFailed(count));
        }
        Ok(ids[..count as usize].to_vec())
    }

    pub fn slots(&self) -> Result<[Option<i32>; 2], AlgorithmError> {
        let mut ids = [0; 2];
        let count =
            unsafe { facehal_algorithm_slots(self.native.as_ptr(), ids.as_mut_ptr(), ids.len()) };
        if count != ids.len() as i32 {
            return Err(AlgorithmError::OperationFailed(count));
        }
        Ok(ids.map(|id| (id >= 1).then_some(id)))
    }

    pub fn remove(&self, enrollment_id: i32) -> Result<(), AlgorithmError> {
        let result = unsafe { facehal_algorithm_remove(self.native.as_ptr(), enrollment_id) };
        if result == 0 {
            Ok(())
        } else {
            Err(AlgorithmError::OperationFailed(result))
        }
    }

    pub fn remove_all(&self) -> Result<(), AlgorithmError> {
        let result = unsafe { facehal_algorithm_remove_all(self.native.as_ptr()) };
        if result == 0 {
            Ok(())
        } else {
            Err(AlgorithmError::OperationFailed(result))
        }
    }

    pub fn set_active_slot(&self, slot: Option<usize>) -> Result<(), AlgorithmError> {
        let slot = match slot {
            Some(slot) if slot < 2 => slot as i32,
            Some(_) => return Err(AlgorithmError::OperationFailed(-1)),
            None => -1,
        };
        let result = unsafe { facehal_algorithm_set_active_slot(self.native.as_ptr(), slot) };
        if result == 0 {
            Ok(())
        } else {
            Err(AlgorithmError::OperationFailed(result))
        }
    }

    pub fn reset(&self) -> Result<(), AlgorithmError> {
        let result = unsafe { facehal_algorithm_reset(self.native.as_ptr()) };
        if result == 0 {
            Ok(())
        } else {
            Err(AlgorithmError::OperationFailed(result))
        }
    }

    pub fn set_sensor_orientation(&self, sensor_orientation: i32) {
        let image_angle = (720 - sensor_orientation).rem_euclid(360);
        let native_orientation = match image_angle {
            0 => 1,
            90 => 8,
            180 => 4,
            270 => 2,
            _ => 15,
        };
        unsafe { facehal_algorithm_set_orientation(self.native.as_ptr(), native_orientation) };
    }
}

impl Drop for Algorithm {
    fn drop(&mut self) {
        unsafe { facehal_algorithm_close(self.native.as_ptr()) };
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AlgorithmError {
    InvalidPath,
    Unavailable,
    OperationFailed(i32),
}
