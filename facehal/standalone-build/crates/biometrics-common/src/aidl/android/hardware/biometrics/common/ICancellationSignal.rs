/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=4 --hash=8a6cd86630181a4df6f20056259ec200ffe39209 -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/biometrics-common /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/AuthenticateReason.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/CommonProps.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/ComponentInfo.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/DisplayState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/FoldState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/ICancellationSignal.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationContext.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationReason.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/OperationState.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/SensorStrength.aidl /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4/android/hardware/biometrics/common/WakeReason.aidl
 *
 * DO NOT CHECK THIS FILE INTO A CODE TREE (e.g. git, etc..).
 * ALWAYS GENERATE THIS FILE FROM UPDATED AIDL COMPILER
 * AS A BUILD INTERMEDIATE ONLY. THIS IS NOT SOURCE CODE.
 */
#![forbid(unsafe_code)]
#![cfg_attr(rustfmt, rustfmt_skip)]
#![allow(non_upper_case_globals)]
#![allow(non_snake_case)]
#[allow(unused_imports)] use binder::binder_impl::IBinderInternal;
#[cfg(any(android_vndk, not(android_ndk)))]
const FLAG_PRIVATE_LOCAL: binder::binder_impl::TransactionFlags = binder::binder_impl::FLAG_PRIVATE_LOCAL;
#[cfg(not(any(android_vndk, not(android_ndk))))]
const FLAG_PRIVATE_LOCAL: binder::binder_impl::TransactionFlags = 0;
use binder::declare_binder_interface;
declare_binder_interface! {
  ICancellationSignal["android.hardware.biometrics.common.ICancellationSignal"] {
    native: BnCancellationSignal(on_transact),
    proxy: BpCancellationSignal {
      cached_version: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(-1),
      cached_hash: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None)
    },
    async: ICancellationSignalAsync(try_into_local_async),
    stability: binder::binder_impl::Stability::Vintf,
  }
}
pub trait ICancellationSignal: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.common.ICancellationSignal" }
  fn r#cancel<'a, >(&'a self) -> binder::Result<()>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> {
    Ok(VERSION)
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> {
    Ok(HASH.into())
  }
  fn getDefaultImpl() -> ICancellationSignalDefaultRef where Self: Sized {
    DEFAULT_IMPL.lock().unwrap().clone()
  }
  fn setDefaultImpl(d: ICancellationSignalDefaultRef) -> ICancellationSignalDefaultRef where Self: Sized {
    std::mem::replace(&mut *DEFAULT_IMPL.lock().unwrap(), d)
  }
  fn try_as_async_server<'a>(&'a self) -> Option<&'a (dyn ICancellationSignalAsyncServer + Send + Sync)> {
    None
  }
}
pub trait ICancellationSignalAsync<P>: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.common.ICancellationSignal" }
  fn r#cancel<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<i32>> {
    Box::pin(async move { Ok(VERSION) })
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<String>> {
    Box::pin(async move { Ok(HASH.into()) })
  }
}
#[::async_trait::async_trait]
pub trait ICancellationSignalAsyncServer: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.common.ICancellationSignal" }
  async fn r#cancel<'a, >(&'a self) -> binder::Result<()>;
}
impl BnCancellationSignal {
  /// Create a new async binder service.
  pub fn new_async_binder<T, R>(inner: T, rt: R, features: binder::BinderFeatures) -> binder::Strong<dyn ICancellationSignal>
  where
    T: ICancellationSignalAsyncServer + binder::Interface + Send + Sync + 'static,
    R: binder::binder_impl::BinderAsyncRuntime + Send + Sync + 'static,
  {
    struct Wrapper<T, R> {
      _inner: T,
      _rt: R,
    }
    impl<T, R> binder::Interface for Wrapper<T, R> where T: binder::Interface, R: Send + Sync + 'static {
      fn as_binder(&self) -> binder::SpIBinder { self._inner.as_binder() }
      fn dump(&self, _writer: &mut dyn std::io::Write, _args: &[&std::ffi::CStr]) -> std::result::Result<(), binder::StatusCode> { self._inner.dump(_writer, _args) }
    }
    impl<T, R> ICancellationSignal for Wrapper<T, R>
    where
      T: ICancellationSignalAsyncServer + Send + Sync + 'static,
      R: binder::binder_impl::BinderAsyncRuntime + Send + Sync + 'static,
    {
      fn r#cancel<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#cancel())
      }
      fn try_as_async_server(&self) -> Option<&(dyn ICancellationSignalAsyncServer + Send + Sync)> {
        Some(&self._inner)
      }
    }
    let wrapped = Wrapper { _inner: inner, _rt: rt };
    Self::new_binder(wrapped, features)
  }
  pub fn try_into_local_async<P: binder::BinderAsyncPool + 'static>(_native: binder::binder_impl::Binder<Self>) -> Option<binder::Strong<dyn ICancellationSignalAsync<P>>> {
    struct Wrapper {
      _native: binder::binder_impl::Binder<BnCancellationSignal>
    }
    impl binder::Interface for Wrapper {}
    impl<P: binder::BinderAsyncPool> ICancellationSignalAsync<P> for Wrapper {
      fn r#cancel<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#cancel())
      }
    }
    if _native.try_as_async_server().is_some() {
      Some(binder::Strong::new(Box::new(Wrapper { _native }) as Box<dyn ICancellationSignalAsync<P>>))
    } else {
      None
    }
  }
}
pub trait ICancellationSignalDefault: Send + Sync {
  fn r#cancel<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
}
pub mod transactions {
  pub const r#cancel: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 0;
  pub const r#getInterfaceVersion: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777214;
  pub const r#getInterfaceHash: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777213;
}
pub type ICancellationSignalDefaultRef = Option<std::sync::Arc<dyn ICancellationSignalDefault>>;
static DEFAULT_IMPL: std::sync::Mutex<ICancellationSignalDefaultRef> = std::sync::Mutex::new(None);
pub const VERSION: i32 = 4;
pub const HASH: &str = "8a6cd86630181a4df6f20056259ec200ffe39209";
impl BpCancellationSignal {
  fn build_parcel_cancel(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_cancel(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ICancellationSignal>::getDefaultImpl() {
        return _aidl_default_impl.r#cancel();
      }
    }
    let _aidl_reply = _aidl_reply?;
    Ok(())
  }
  fn build_parcel_getInterfaceVersion(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_getInterfaceVersion(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<i32> {
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: i32 = _aidl_reply.read()?;
    self.cached_version.store(_aidl_return, std::sync::atomic::Ordering::Relaxed);
    Ok(_aidl_return)
  }
  fn build_parcel_getInterfaceHash(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_getInterfaceHash(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<String> {
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: String = _aidl_reply.read()?;
    *self.cached_hash.lock().unwrap() = Some(_aidl_return.clone());
    Ok(_aidl_return)
  }
}
impl ICancellationSignal for BpCancellationSignal {
  fn r#cancel<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_cancel()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#cancel, _aidl_data, binder::binder_impl::FLAG_ONEWAY | FLAG_PRIVATE_LOCAL);
    self.read_response_cancel(_aidl_reply)
  }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> {
    let _aidl_version = self.cached_version.load(std::sync::atomic::Ordering::Relaxed);
    if _aidl_version != -1 { return Ok(_aidl_version); }
    let _aidl_data = self.build_parcel_getInterfaceVersion()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getInterfaceVersion, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getInterfaceVersion(_aidl_reply)
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> {
    {
      let _aidl_hash_lock = self.cached_hash.lock().unwrap();
      if let Some(ref _aidl_hash) = *_aidl_hash_lock {
        return Ok(_aidl_hash.clone());
      }
    }
    let _aidl_data = self.build_parcel_getInterfaceHash()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getInterfaceHash, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getInterfaceHash(_aidl_reply)
  }
}
impl<P: binder::BinderAsyncPool> ICancellationSignalAsync<P> for BpCancellationSignal {
  fn r#cancel<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_cancel() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#cancel, _aidl_data, binder::binder_impl::FLAG_ONEWAY | FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_cancel(_aidl_reply)
      }
    )
  }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<i32>> {
    let _aidl_version = self.cached_version.load(std::sync::atomic::Ordering::Relaxed);
    if _aidl_version != -1 { return Box::pin(std::future::ready(Ok(_aidl_version))); }
    let _aidl_data = match self.build_parcel_getInterfaceVersion() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getInterfaceVersion, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getInterfaceVersion(_aidl_reply)
      }
    )
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<String>> {
    {
      let _aidl_hash_lock = self.cached_hash.lock().unwrap();
      if let Some(ref _aidl_hash) = *_aidl_hash_lock {
        return Box::pin(std::future::ready(Ok(_aidl_hash.clone())));
      }
    }
    let _aidl_data = match self.build_parcel_getInterfaceHash() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getInterfaceHash, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getInterfaceHash(_aidl_reply)
      }
    )
  }
}
impl ICancellationSignal for binder::binder_impl::Binder<BnCancellationSignal> {
  fn r#cancel<'a, >(&'a self) -> binder::Result<()> { self.0.r#cancel() }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> { self.0.r#getInterfaceVersion() }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> { self.0.r#getInterfaceHash() }
}
fn on_transact(_aidl_service: &dyn ICancellationSignal, _aidl_code: binder::binder_impl::TransactionCode, _aidl_data: &binder::binder_impl::BorrowedParcel<'_>, _aidl_reply: &mut binder::binder_impl::BorrowedParcel<'_>) -> std::result::Result<(), binder::StatusCode> {
  match _aidl_code {
    transactions::r#cancel => {
      let _aidl_return = _aidl_service.r#cancel();
      Ok(())
    }
    transactions::r#getInterfaceVersion => {
      let _aidl_return = _aidl_service.r#getInterfaceVersion();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#getInterfaceHash => {
      let _aidl_return = _aidl_service.r#getInterfaceHash();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    _ => Err(binder::StatusCode::UNKNOWN_TRANSACTION)
  }
}
pub(crate) mod mangled {
 pub use super::r#ICancellationSignal as _7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal;
}
