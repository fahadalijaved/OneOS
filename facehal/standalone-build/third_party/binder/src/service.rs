/*
 * Copyright (C) 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

use crate::binder::{AsNative, FromIBinder, Strong};
use crate::error::{status_result, Result, StatusCode};
use crate::proxy::SpIBinder;
use crate::sys;

use std::ffi::{c_void, CStr, CString};
use std::os::raw::c_char;
use std::sync::Mutex;

/// Register a new service with the default service manager.
///
/// Registers the given binder object with the given identifier. If successful,
/// this service can then be retrieved using that identifier.
///
/// This function will panic if the identifier contains a 0 byte (NUL).
pub fn add_service(identifier: &str, mut binder: SpIBinder) -> Result<()> {
    let instance = CString::new(identifier).unwrap();
    let status =
    // Safety: `AServiceManager_addService` expects valid `AIBinder` and C
    // string pointers. Caller retains ownership of both pointers.
    // `AServiceManager_addService` creates a new strong reference and copies
    // the string, so both pointers need only be valid until the call returns.
        unsafe { sys::AServiceManager_addService(binder.as_native_mut(), instance.as_ptr()) };
    status_result(status)
}

/// Register a dynamic service via the LazyServiceRegistrar.
///
/// Registers the given binder object with the given identifier. If successful,
/// this service can then be retrieved using that identifier. The service process
/// will be shut down once all registered services are no longer in use.
///
/// If any service in the process is registered as lazy, all should be, otherwise
/// the process may be shut down while a service is in use.
///
/// This function will panic if the identifier contains a 0 byte (NUL).
pub fn register_lazy_service(identifier: &str, mut binder: SpIBinder) -> Result<()> {
    let instance = CString::new(identifier).unwrap();
    // Safety: `AServiceManager_registerLazyService` expects valid `AIBinder` and C
    // string pointers. Caller retains ownership of both
    // pointers. `AServiceManager_registerLazyService` creates a new strong reference
    // and copies the string, so both pointers need only be valid until the
    // call returns.
    let status = unsafe {
        sys::AServiceManager_registerLazyService(binder.as_native_mut(), instance.as_ptr())
    };
    status_result(status)
}

/// Prevent a process which registers lazy services from being shut down even when none
/// of the services is in use.
///
/// If persist is true then shut down will be blocked until this function is called again with
/// persist false. If this is to be the initial state, call this function before calling
/// register_lazy_service.
///
/// Consider using [`LazyServiceGuard`] rather than calling this directly.
pub fn force_lazy_services_persist(persist: bool) {
    // Safety: No borrowing or transfer of ownership occurs here.
    unsafe { sys::AServiceManager_forceLazyServicesPersist(persist) }
}

/// An RAII object to ensure a process which registers lazy services is not killed. During the
/// lifetime of any of these objects the service manager will not kill the process even if none
/// of its lazy services are in use.
#[must_use]
#[derive(Debug)]
pub struct LazyServiceGuard {
    // Prevent construction outside this module.
    _private: (),
}

// Count of how many LazyServiceGuard objects are in existence.
static GUARD_COUNT: Mutex<u64> = Mutex::new(0);

impl LazyServiceGuard {
    /// Create a new LazyServiceGuard to prevent the service manager prematurely killing this
    /// process.
    pub fn new() -> Self {
        let mut count = GUARD_COUNT.lock().unwrap();
        *count += 1;
        if *count == 1 {
            // It's important that we make this call with the mutex held, to make sure
            // that multiple calls (e.g. if the count goes 1 -> 0 -> 1) are correctly
            // sequenced. (That also means we can't just use an AtomicU64.)
            force_lazy_services_persist(true);
        }
        Self { _private: () }
    }
}

impl Drop for LazyServiceGuard {
    fn drop(&mut self) {
        let mut count = GUARD_COUNT.lock().unwrap();
        *count -= 1;
        if *count == 0 {
            force_lazy_services_persist(false);
        }
    }
}

impl Clone for LazyServiceGuard {
    fn clone(&self) -> Self {
        Self::new()
    }
}

impl Default for LazyServiceGuard {
    fn default() -> Self {
        Self::new()
    }
}

/// Determine whether the current thread is currently executing an incoming
/// transaction.
pub fn is_handling_transaction() -> bool {
    // Safety: This method is always safe to call.
    unsafe { sys::AIBinder_isHandlingTransaction() }
}

fn interface_cast<T: FromIBinder + ?Sized>(service: Option<SpIBinder>) -> Result<Strong<T>> {
    if let Some(service) = service {
        FromIBinder::try_from(service)
    } else {
        Err(StatusCode::NAME_NOT_FOUND)
    }
}

/// Retrieve an existing service, blocking for a few seconds if it doesn't yet
/// exist.
#[deprecated = "this polls 5s, use wait_for_service or check_service"]
pub fn get_service(name: &str) -> Option<SpIBinder> {
    let name = CString::new(name).ok()?;
    // Safety: `AServiceManager_getService` returns either a null pointer or a
    // valid pointer to an owned `AIBinder`. Either of these values is safe to
    // pass to `SpIBinder::from_raw`.
    unsafe { SpIBinder::from_raw(sys::AServiceManager_getService(name.as_ptr())) }
}

/// Retrieve an existing service. Returns `None` immediately if the service is not available.
pub fn check_service(name: &str) -> Option<SpIBinder> {
    let name = CString::new(name).ok()?;
    // Safety: `AServiceManager_checkService` returns either a null pointer or
    // a valid pointer to an owned `AIBinder`. Either of these values is safe to
    // pass to `SpIBinder::from_raw`.
    unsafe { SpIBinder::from_raw(sys::AServiceManager_checkService(name.as_ptr())) }
}

/// Retrieve an existing service, or start it if it is configured as a dynamic
/// service and isn't yet started.
pub fn wait_for_service(name: &str) -> Option<SpIBinder> {
    let name = CString::new(name).ok()?;
    // Safety: `AServiceManager_waitforService` returns either a null pointer or
    // a valid pointer to an owned `AIBinder`. Either of these values is safe to
    // pass to `SpIBinder::from_raw`.
    unsafe { SpIBinder::from_raw(sys::AServiceManager_waitForService(name.as_ptr())) }
}

/// Retrieve an existing service for a particular interface, blocking for a few
/// seconds if it doesn't yet exist.
#[deprecated = "this polls 5s, use wait_for_interface or check_interface"]
pub fn get_interface<T: FromIBinder + ?Sized>(name: &str) -> Result<Strong<T>> {
    #[allow(deprecated)]
    interface_cast(get_service(name))
}

/// Retrieve an existing service for a particular interface. Returns
/// `Err(StatusCode::NAME_NOT_FOUND)` immediately if the service is not available.
pub fn check_interface<T: FromIBinder + ?Sized>(name: &str) -> Result<Strong<T>> {
    interface_cast(check_service(name))
}

/// Retrieve an existing service for a particular interface, or start it if it
/// is configured as a dynamic service and isn't yet started.
pub fn wait_for_interface<T: FromIBinder + ?Sized>(name: &str) -> Result<Strong<T>> {
    interface_cast(wait_for_service(name))
}

/// Check if a service is declared (e.g. in a VINTF manifest)
pub fn is_declared(interface: &str) -> Result<bool> {
    let interface = CString::new(interface).or(Err(StatusCode::UNEXPECTED_NULL))?;

    // Safety: `interface` is a valid null-terminated C-style string and is only
    // borrowed for the lifetime of the call. The `interface` local outlives
    // this call as it lives for the function scope.
    unsafe { Ok(sys::AServiceManager_isDeclared(interface.as_ptr())) }
}

/// Retrieve all declared instances for a particular interface
///
/// For instance, if 'android.foo.IFoo/foo' is declared, and 'android.foo.IFoo'
/// is passed here, then ["foo"] would be returned.
pub fn get_declared_instances(interface: &str) -> Result<Vec<String>> {
    unsafe extern "C" fn callback(instance: *const c_char, opaque: *mut c_void) {
        // Safety: opaque was a mutable pointer created below from a Vec of
        // CString, and outlives this callback. The null handling here is just
        // to avoid the possibility of unwinding across C code if this crate is
        // ever compiled with panic=unwind.
        if let Some(instances) = unsafe { opaque.cast::<Vec<CString>>().as_mut() } {
            // Safety: instance is a valid null-terminated C string with a
            // lifetime at least as long as this function, and we immediately
            // copy it into an owned CString.
            unsafe {
                instances.push(CStr::from_ptr(instance).to_owned());
            }
        } else {
            eprintln!("Opaque pointer was null in get_declared_instances callback!");
        }
    }

    let interface = CString::new(interface).or(Err(StatusCode::UNEXPECTED_NULL))?;
    let mut instances: Vec<CString> = vec![];
    // Safety: `interface` and `instances` are borrowed for the length of this
    // call and both outlive the call. `interface` is guaranteed to be a valid
    // null-terminated C-style string.
    unsafe {
        sys::AServiceManager_forEachDeclaredInstance(
            interface.as_ptr(),
            &mut instances as *mut _ as *mut c_void,
            Some(callback),
        );
    }

    instances
        .into_iter()
        .map(CString::into_string)
        .collect::<std::result::Result<Vec<String>, _>>()
        .map_err(|e| {
            eprintln!("An interface instance name was not a valid UTF-8 string: {}", e);
            StatusCode::BAD_VALUE
        })
}
