use std::ffi::c_void;
use std::ptr::NonNull;

use binder::ProcessState;


#[repr(C)]
struct NativeCamera(c_void);

unsafe extern "C" {
    fn facehal_camera_worker_main(
        width: i32,
        height: i32,
        socket_fd: i32,
        frame_fd: i32,
        window_mode: i32,
    ) -> i32;
    fn facehal_camera_open(width: i32, height: i32) -> *mut NativeCamera;
    fn facehal_camera_close(camera: *mut NativeCamera);
    fn facehal_camera_next_nv21(
        camera: *mut NativeCamera,
        output: *mut u8,
        capacity: usize,
        timeout_ms: i32,
    ) -> i32;
    fn facehal_camera_frame_size(camera: *const NativeCamera) -> i32;
    fn facehal_camera_sensor_orientation(camera: *const NativeCamera) -> i32;
}

pub fn run_worker_from_args() -> Option<i32> {
    let mut arguments = std::env::args();
    let _executable = arguments.next();
    if arguments.next().as_deref() != Some("--facehal-camera-worker") {
        return None;
    }
    let parse = |argument: Option<String>| argument.and_then(|value| value.parse::<i32>().ok());
    let (Some(width), Some(height), Some(socket_fd), Some(frame_fd), Some(window_mode)) = (
        parse(arguments.next()),
        parse(arguments.next()),
        parse(arguments.next()),
        parse(arguments.next()),
        parse(arguments.next()),
    ) else {
        return Some(2);
    };
    if arguments.next().is_some() {
        return Some(2);
    }
    ProcessState::set_thread_pool_max_thread_count(2);
    ProcessState::start_thread_pool();
    eprintln!("FaceHAL camera worker v2: Binder thread pool started");
    Some(unsafe { facehal_camera_worker_main(width, height, socket_fd, frame_fd, window_mode) })
}

pub struct Camera {
    native: NonNull<NativeCamera>,
    frame_size: usize,
    sensor_orientation: i32,
}

unsafe impl Send for Camera {}

impl Camera {
    pub fn open(width: i32, height: i32) -> Result<Self, CameraError> {
        let native = NonNull::new(unsafe { facehal_camera_open(width, height) })
            .ok_or(CameraError::Unavailable)?;
        let frame_size = unsafe { facehal_camera_frame_size(native.as_ptr()) };
        let sensor_orientation = unsafe { facehal_camera_sensor_orientation(native.as_ptr()) };
        if frame_size <= 0 || !matches!(sensor_orientation, 0 | 90 | 180 | 270) {
            unsafe { facehal_camera_close(native.as_ptr()) };
            return Err(CameraError::Unavailable);
        }
        Ok(Self {
            native,
            frame_size: frame_size as usize,
            sensor_orientation,
        })
    }

    pub fn sensor_orientation(&self) -> i32 {
        self.sensor_orientation
    }

    pub fn next_frame(&mut self, timeout_ms: i32) -> Result<Vec<u8>, CameraError> {
        let mut frame = vec![0; self.frame_size];
        let result = unsafe {
            facehal_camera_next_nv21(
                self.native.as_ptr(),
                frame.as_mut_ptr(),
                frame.len(),
                timeout_ms,
            )
        };
        match result {
            value if value == self.frame_size as i32 => Ok(frame),
            -3 => Err(CameraError::Timeout),
            -4 => Err(CameraError::BadFrame),
            _ => Err(CameraError::Unavailable),
        }
    }
}

impl Drop for Camera {
    fn drop(&mut self) {
        unsafe { facehal_camera_close(self.native.as_ptr()) };
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CameraError {
    Unavailable,
    Timeout,
    BadFrame,
}
