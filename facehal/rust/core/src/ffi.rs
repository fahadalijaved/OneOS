use crate::{LockoutState, LockoutTracker, TemplateStore};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

const OK: i32 = 0;
const INVALID_ARGUMENT: i32 = -1;
const IO_ERROR: i32 = -2;
const BUFFER_TOO_SMALL: i32 = -3;
const BUSY: i32 = -4;
const LOCKOUT_NONE: i32 = 0;
const LOCKOUT_TIMED: i32 = 1;
const LOCKOUT_PERMANENT: i32 = 2;

static NEXT_OPERATION_ID: AtomicU64 = AtomicU64::new(1);

pub struct StoreHandle {
    store: TemplateStore,
}

pub struct LockoutHandle {
    tracker: LockoutTracker,
}

struct ActiveOperation {
    id: u64,
    cancelled: bool,
    terminal_claimed: bool,
}

pub struct SessionHandle {
    active: Mutex<Option<ActiveOperation>>,
}

#[no_mangle]
pub extern "C" fn facehal_session_create() -> *mut SessionHandle {
    Box::into_raw(Box::new(SessionHandle {
        active: Mutex::new(None),
    }))
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_destroy(handle: *mut SessionHandle) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_begin(
    handle: *const SessionHandle,
    operation_id: *mut u64,
) -> i32 {
    if handle.is_null() || operation_id.is_null() {
        return INVALID_ARGUMENT;
    }
    let mut active = (*handle).active.lock().unwrap();
    if active.is_some() {
        return BUSY;
    }
    let mut id = NEXT_OPERATION_ID.fetch_add(1, Ordering::Relaxed);
    if id == 0 {
        id = NEXT_OPERATION_ID.fetch_add(1, Ordering::Relaxed);
    }
    *active = Some(ActiveOperation {
        id,
        cancelled: false,
        terminal_claimed: false,
    });
    *operation_id = id;
    OK
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_is_idle(handle: *const SessionHandle) -> bool {
    if handle.is_null() {
        return false;
    }
    (*handle).active.lock().unwrap().is_none()
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_create(
    root: *const u8,
    root_len: usize,
    user_id: i32,
) -> *mut LockoutHandle {
    if root.is_null() || root_len == 0 {
        return std::ptr::null_mut();
    }
    let bytes = std::slice::from_raw_parts(root, root_len);
    let Ok(path) = std::str::from_utf8(bytes) else {
        return std::ptr::null_mut();
    };
    match LockoutTracker::new(Path::new(path), user_id) {
        Ok(tracker) => Box::into_raw(Box::new(LockoutHandle { tracker })),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_destroy(handle: *mut LockoutHandle) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_status(
    handle: *const LockoutHandle,
    remaining_millis: *mut u64,
) -> i32 {
    if handle.is_null() || remaining_millis.is_null() {
        return INVALID_ARGUMENT;
    }
    lockout_result((*handle).tracker.status(), remaining_millis)
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_record_failure(
    handle: *const LockoutHandle,
    remaining_millis: *mut u64,
) -> i32 {
    if handle.is_null() || remaining_millis.is_null() {
        return INVALID_ARGUMENT;
    }
    lockout_result((*handle).tracker.record_failure(), remaining_millis)
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_record_success(handle: *const LockoutHandle) -> i32 {
    if handle.is_null() {
        return INVALID_ARGUMENT;
    }
    if (*handle).tracker.record_success().is_ok() {
        OK
    } else {
        IO_ERROR
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_lockout_reset(handle: *const LockoutHandle) -> i32 {
    if handle.is_null() {
        return INVALID_ARGUMENT;
    }
    if (*handle).tracker.reset().is_ok() {
        OK
    } else {
        IO_ERROR
    }
}

unsafe fn lockout_result(
    result: Result<LockoutState, crate::FaceError>,
    remaining_millis: *mut u64,
) -> i32 {
    match result {
        Ok(LockoutState::None) => {
            *remaining_millis = 0;
            LOCKOUT_NONE
        }
        Ok(LockoutState::Timed {
            remaining_millis: value,
        }) => {
            *remaining_millis = value;
            LOCKOUT_TIMED
        }
        Ok(LockoutState::Permanent) => {
            *remaining_millis = 0;
            LOCKOUT_PERMANENT
        }
        Err(_) => IO_ERROR,
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_cancel(
    handle: *const SessionHandle,
    operation_id: u64,
) -> i32 {
    if handle.is_null() {
        return INVALID_ARGUMENT;
    }
    let mut active = (*handle).active.lock().unwrap();
    match active.as_mut() {
        Some(operation) if operation.id == operation_id && !operation.terminal_claimed => {
            operation.cancelled = true;
            OK
        }
        _ => INVALID_ARGUMENT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_claim_terminal(
    handle: *const SessionHandle,
    operation_id: u64,
) -> i32 {
    if handle.is_null() {
        return INVALID_ARGUMENT;
    }
    let mut active = (*handle).active.lock().unwrap();
    match active.as_mut() {
        Some(operation) if operation.id == operation_id && !operation.terminal_claimed => {
            operation.terminal_claimed = true;
            if operation.cancelled {
                1
            } else {
                OK
            }
        }
        _ => INVALID_ARGUMENT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_finish(
    handle: *const SessionHandle,
    operation_id: u64,
) -> i32 {
    if handle.is_null() {
        return INVALID_ARGUMENT;
    }
    let mut active = (*handle).active.lock().unwrap();
    match active.as_ref() {
        Some(operation) if operation.id == operation_id => {
            *active = None;
            OK
        }
        _ => INVALID_ARGUMENT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_session_is_cancelled(
    handle: *const SessionHandle,
    operation_id: u64,
) -> bool {
    if handle.is_null() {
        return true;
    }
    (*handle)
        .active
        .lock()
        .unwrap()
        .as_ref()
        .map(|operation| operation.id == operation_id && operation.cancelled)
        .unwrap_or(true)
}

#[no_mangle]
pub unsafe extern "C" fn facehal_store_create(
    root: *const u8,
    root_len: usize,
    user_id: i32,
) -> *mut StoreHandle {
    if root.is_null() || root_len == 0 {
        return std::ptr::null_mut();
    }
    let bytes = std::slice::from_raw_parts(root, root_len);
    let Ok(path) = std::str::from_utf8(bytes) else {
        return std::ptr::null_mut();
    };
    match TemplateStore::new(Path::new(path), user_id) {
        Ok(store) => Box::into_raw(Box::new(StoreHandle { store })),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_store_destroy(handle: *mut StoreHandle) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_store_list(
    handle: *const StoreHandle,
    output: *mut i32,
    capacity: usize,
    count: *mut usize,
) -> i32 {
    if handle.is_null() || count.is_null() {
        return INVALID_ARGUMENT;
    }
    let Ok(records) = (*handle).store.list() else {
        return IO_ERROR;
    };
    *count = records.len();
    if records.len() > capacity || (output.is_null() && !records.is_empty()) {
        return BUFFER_TOO_SMALL;
    }
    for (index, record) in records.iter().enumerate() {
        *output.add(index) = record.id;
    }
    OK
}

#[no_mangle]
pub unsafe extern "C" fn facehal_store_remove(
    handle: *const StoreHandle,
    ids: *const i32,
    count: usize,
) -> i32 {
    if handle.is_null() || (ids.is_null() && count != 0) {
        return INVALID_ARGUMENT;
    }
    if count == 0 {
        return OK;
    }
    let result = (*handle)
        .store
        .remove(std::slice::from_raw_parts(ids, count));
    if result.is_ok() {
        OK
    } else {
        IO_ERROR
    }
}

#[no_mangle]
pub unsafe extern "C" fn facehal_store_authenticator_id(
    handle: *const StoreHandle,
    output: *mut u64,
) -> i32 {
    if handle.is_null() || output.is_null() {
        return INVALID_ARGUMENT;
    }
    match (*handle).store.authenticator_id() {
        Ok(value) => {
            *output = value;
            OK
        }
        Err(_) => IO_ERROR,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TemplateRecord;
    use std::sync::{Arc, Barrier};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn ffi_lists_and_removes_templates() {
        let root = std::env::temp_dir().join(format!(
            "facehal-ffi-{}",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let path = root.to_string_lossy();
        let handle = unsafe { facehal_store_create(path.as_ptr(), path.len(), 0) };
        assert!(!handle.is_null());
        unsafe {
            (*handle)
                .store
                .put(&TemplateRecord {
                    id: 9,
                    embedding: vec![0.25],
                })
                .unwrap();
            let mut output = [0i32; 2];
            let mut count = 0usize;
            assert_eq!(facehal_store_remove(handle, std::ptr::null(), 0), OK);
            assert_eq!(
                facehal_store_list(handle, output.as_mut_ptr(), 2, &mut count),
                OK
            );
            assert_eq!((&output[..count]), &[9]);
            assert_eq!(facehal_store_remove(handle, output.as_ptr(), count), OK);
            facehal_store_destroy(handle);
        }
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn ffi_session_serializes_and_cancels_operations() {
        let handle = facehal_session_create();
        let mut first = 0;
        let mut second = 0;
        unsafe {
            assert_eq!(facehal_session_begin(handle, &mut first), OK);
            assert!(!facehal_session_is_idle(handle));
            assert_eq!(facehal_session_begin(handle, &mut second), BUSY);
            assert_eq!(facehal_session_cancel(handle, first), OK);
            assert!(facehal_session_is_cancelled(handle, first));
            assert_eq!(facehal_session_claim_terminal(handle, first), 1);
            assert_eq!(
                facehal_session_claim_terminal(handle, first),
                INVALID_ARGUMENT
            );
            assert_eq!(facehal_session_cancel(handle, first), INVALID_ARGUMENT);
            assert_eq!(facehal_session_finish(handle, first), OK);
            assert_eq!(facehal_session_begin(handle, &mut second), OK);
            assert_ne!(first, second);
            assert_eq!(facehal_session_claim_terminal(handle, second), OK);
            assert_eq!(facehal_session_cancel(handle, second), INVALID_ARGUMENT);
            assert_eq!(facehal_session_finish(handle, second), OK);
            assert!(facehal_session_is_idle(handle));
            facehal_session_destroy(handle);
        }
    }

    #[test]
    fn ffi_operation_ids_are_unique_across_sessions() {
        let first_handle = facehal_session_create();
        let second_handle = facehal_session_create();
        let mut first = 0;
        let mut second = 0;
        unsafe {
            assert_eq!(facehal_session_begin(first_handle, &mut first), OK);
            assert_eq!(facehal_session_begin(second_handle, &mut second), OK);
            assert_ne!(first, second);
            facehal_session_destroy(first_handle);
            facehal_session_destroy(second_handle);
        }
    }

    #[test]
    fn ffi_cancel_and_terminal_claim_are_atomic() {
        for _ in 0..256 {
            let handle = Arc::new(SessionHandle {
                active: Mutex::new(None),
            });
            let mut operation_id = 0;
            unsafe {
                assert_eq!(
                    facehal_session_begin(Arc::as_ptr(&handle), &mut operation_id),
                    OK
                );
            }
            let barrier = Arc::new(Barrier::new(3));
            let cancel_handle = Arc::clone(&handle);
            let cancel_barrier = Arc::clone(&barrier);
            let cancel = std::thread::spawn(move || {
                cancel_barrier.wait();
                unsafe { facehal_session_cancel(Arc::as_ptr(&cancel_handle), operation_id) }
            });
            let terminal_handle = Arc::clone(&handle);
            let terminal_barrier = Arc::clone(&barrier);
            let terminal = std::thread::spawn(move || {
                terminal_barrier.wait();
                unsafe {
                    facehal_session_claim_terminal(Arc::as_ptr(&terminal_handle), operation_id)
                }
            });
            barrier.wait();
            let result = (cancel.join().unwrap(), terminal.join().unwrap());
            assert!(result == (OK, 1) || result == (INVALID_ARGUMENT, OK));
            unsafe {
                assert_eq!(
                    facehal_session_finish(Arc::as_ptr(&handle), operation_id),
                    OK
                );
            }
        }
    }
}
