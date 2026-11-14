/*
 * Copyright (C) 2023 The Android Open Source Project
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

use binder::{unstable_api::AsNative, SpIBinder};
use libc::size_t;
use std::ffi::{c_char, c_void};
use std::ptr;
use tipc::{ConnectResult, Handle, MessageResult, PortCfg, TipcError, UnbufferedService, Uuid};

pub trait PerSessionCallback: Fn(Uuid) -> Option<SpIBinder> + Send + Sync + 'static {}
impl<T> PerSessionCallback for T where T: Fn(Uuid) -> Option<SpIBinder> + Send + Sync + 'static {}

pub struct RpcServer {
    inner: *mut binder_rpc_server_bindgen::ARpcServerTrusty,
}

/// SAFETY: The opaque handle points to a heap allocation
/// that should be process-wide and not tied to the current thread.
unsafe impl Send for RpcServer {}
/// SAFETY: The underlying C++ RpcServer class is thread-safe.
unsafe impl Sync for RpcServer {}

impl Drop for RpcServer {
    fn drop(&mut self) {
        // SAFETY: `ARpcServerTrusty_delete` is the correct destructor to call
        // on pointers returned by `ARpcServerTrusty_new`.
        unsafe {
            binder_rpc_server_bindgen::ARpcServerTrusty_delete(self.inner);
        }
    }
}

impl RpcServer {
    /// Allocates a new RpcServer object.
    pub fn new(service: SpIBinder) -> RpcServer {
        Self::new_per_session(move |_uuid| Some(service.clone()))
    }

    /// Allocates a new per-session RpcServer object.
    ///
    /// Per-session objects take a closure that gets called once
    /// for every new connection. The closure gets the UUID of
    /// the peer and can accept or reject that connection.
    pub fn new_per_session<F: PerSessionCallback>(f: F) -> RpcServer {
        // SAFETY: Takes ownership of the returned handle, which has correct refcount.
        let inner = unsafe {
            binder_rpc_server_bindgen::ARpcServerTrusty_newPerSession(
                Some(per_session_callback_wrapper::<F>),
                Box::into_raw(Box::new(f)).cast(),
                Some(per_session_callback_deleter::<F>),
            )
        };
        RpcServer { inner }
    }
}

unsafe extern "C" fn per_session_callback_wrapper<F: PerSessionCallback>(
    uuid_ptr: *const c_void,
    len: size_t,
    cb_ptr: *mut c_char,
) -> *mut binder_rpc_server_bindgen::AIBinder {
    // SAFETY: This callback should only get called while the RpcServer is alive.
    let cb = unsafe { &mut *cb_ptr.cast::<F>() };

    if len != std::mem::size_of::<Uuid>() {
        return ptr::null_mut();
    }

    // SAFETY: On the previous lines we check that we got exactly the right amount of bytes.
    let uuid = unsafe {
        let mut uuid = std::mem::MaybeUninit::<Uuid>::uninit();
        uuid.as_mut_ptr().copy_from(uuid_ptr.cast(), 1);
        uuid.assume_init()
    };

    cb(uuid).map_or_else(ptr::null_mut, |b| {
        // Prevent AIBinder_decStrong from being called before AIBinder_toPlatformBinder.
        // The per-session callback in C++ is supposed to call AIBinder_decStrong on the
        // pointer we return here.
        std::mem::ManuallyDrop::new(b).as_native_mut().cast()
    })
}

unsafe extern "C" fn per_session_callback_deleter<F: PerSessionCallback>(cb: *mut c_char) {
    // SAFETY: shared_ptr calls this to delete the pointer we gave it.
    // It should only get called once the last shared reference goes away.
    unsafe {
        drop(Box::<F>::from_raw(cb.cast()));
    }
}

pub struct RpcServerConnection {
    ctx: *mut c_void,
}

// SAFETY: The opaque handle: `ctx` points into a dynamic allocation,
// and not tied to anything specific to the current thread.
unsafe impl Send for RpcServerConnection {}

impl Drop for RpcServerConnection {
    fn drop(&mut self) {
        // We do not need to close handle_fd since we do not own it.
        unsafe {
            binder_rpc_server_bindgen::ARpcServerTrusty_handleChannelCleanup(self.ctx);
        }
    }
}

impl UnbufferedService for RpcServer {
    type Connection = RpcServerConnection;

    fn on_connect(
        &self,
        _port: &PortCfg,
        handle: &Handle,
        peer: &Uuid,
    ) -> tipc::Result<ConnectResult<Self::Connection>> {
        let mut conn = RpcServerConnection { ctx: std::ptr::null_mut() };
        let rc = unsafe {
            binder_rpc_server_bindgen::ARpcServerTrusty_handleConnect(
                self.inner,
                handle.as_raw_fd(),
                peer.as_ptr().cast(),
                &mut conn.ctx,
            )
        };
        if rc < 0 {
            Err(TipcError::from_uapi(rc.into()))
        } else {
            Ok(ConnectResult::Accept(conn))
        }
    }

    fn on_message(
        &self,
        conn: &Self::Connection,
        _handle: &Handle,
        buffer: &mut [u8],
    ) -> tipc::Result<MessageResult> {
        assert!(buffer.is_empty());
        let rc = unsafe { binder_rpc_server_bindgen::ARpcServerTrusty_handleMessage(conn.ctx) };
        if rc < 0 {
            Err(TipcError::from_uapi(rc.into()))
        } else {
            Ok(MessageResult::MaintainConnection)
        }
    }

    fn on_disconnect(&self, conn: &Self::Connection) {
        unsafe { binder_rpc_server_bindgen::ARpcServerTrusty_handleDisconnect(conn.ctx) };
    }
}
