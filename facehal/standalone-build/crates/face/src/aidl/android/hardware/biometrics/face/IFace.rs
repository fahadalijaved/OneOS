/*
 * This file is auto-generated.  DO NOT MODIFY.
 * Using: /ANDROID_SDK/build-tools/36.0.0/aidl --lang=rust --structured --stability=vintf --min_sdk_version=35 --version=4 --hash=c43fbb9be4a662cc9ace640dba21cccdb84c6c21 -p /tmp/face-aidl-build/surface.preprocessed -I /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4 -I /tmp/android16-biometrics-common-aidl/aidl_api/android.hardware.biometrics.common/4 -I /tmp/android16-hardware-common-aidl/aidl_api/android.hardware.common/2 -I /tmp/android16-keymaster-aidl/aidl_api/android.hardware.keymaster/4 -o /tmp/facehal-official-rust/face /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/AcquiredInfo.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/AuthenticationFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/BaseFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Cell.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentFrame.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentStage.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentStageConfig.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/EnrollmentType.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Error.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/FaceEnrollOptions.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/FaceSensorType.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/Feature.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/IFace.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/ISession.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/ISessionCallback.aidl /tmp/android16-face-aidl/aidl_api/android.hardware.biometrics.face/4/android/hardware/biometrics/face/SensorProps.aidl
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
  IFace["android.hardware.biometrics.face.IFace"] {
    native: BnFace(on_transact),
    proxy: BpFace {
      cached_version: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(-1),
      cached_hash: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None)
    },
    async: IFaceAsync(try_into_local_async),
    stability: binder::binder_impl::Stability::Vintf,
  }
}
pub trait IFace: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.IFace" }
  fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>>;
  fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> {
    Ok(VERSION)
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> {
    Ok(HASH.into())
  }
  fn getDefaultImpl() -> IFaceDefaultRef where Self: Sized {
    DEFAULT_IMPL.lock().unwrap().clone()
  }
  fn setDefaultImpl(d: IFaceDefaultRef) -> IFaceDefaultRef where Self: Sized {
    std::mem::replace(&mut *DEFAULT_IMPL.lock().unwrap(), d)
  }
  fn try_as_async_server<'a>(&'a self) -> Option<&'a (dyn IFaceAsyncServer + Send + Sync)> {
    None
  }
}
pub trait IFaceAsync<P>: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.IFace" }
  fn r#getSensorProps<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>>>;
  fn r#createSession<'a, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'a binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<i32>> {
    Box::pin(async move { Ok(VERSION) })
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<String>> {
    Box::pin(async move { Ok(HASH.into()) })
  }
}
#[::async_trait::async_trait]
pub trait IFaceAsyncServer: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.IFace" }
  async fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>>;
  async fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>>;
}
impl BnFace {
  /// Create a new async binder service.
  pub fn new_async_binder<T, R>(inner: T, rt: R, features: binder::BinderFeatures) -> binder::Strong<dyn IFace>
  where
    T: IFaceAsyncServer + binder::Interface + Send + Sync + 'static,
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
    impl<T, R> IFace for Wrapper<T, R>
    where
      T: IFaceAsyncServer + Send + Sync + 'static,
      R: binder::binder_impl::BinderAsyncRuntime + Send + Sync + 'static,
    {
      fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>> {
        self._rt.block_on(self._inner.r#getSensorProps())
      }
      fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>> {
        self._rt.block_on(self._inner.r#createSession(_arg_sensorId, _arg_userId, _arg_cb))
      }
      fn try_as_async_server(&self) -> Option<&(dyn IFaceAsyncServer + Send + Sync)> {
        Some(&self._inner)
      }
    }
    let wrapped = Wrapper { _inner: inner, _rt: rt };
    Self::new_binder(wrapped, features)
  }
  pub fn try_into_local_async<P: binder::BinderAsyncPool + 'static>(_native: binder::binder_impl::Binder<Self>) -> Option<binder::Strong<dyn IFaceAsync<P>>> {
    struct Wrapper {
      _native: binder::binder_impl::Binder<BnFace>
    }
    impl binder::Interface for Wrapper {}
    impl<P: binder::BinderAsyncPool> IFaceAsync<P> for Wrapper {
      fn r#getSensorProps<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#getSensorProps())
      }
      fn r#createSession<'a, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'a binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#createSession(_arg_sensorId, _arg_userId, _arg_cb))
      }
    }
    if _native.try_as_async_server().is_some() {
      Some(binder::Strong::new(Box::new(Wrapper { _native }) as Box<dyn IFaceAsync<P>>))
    } else {
      None
    }
  }
}
pub trait IFaceDefault: Send + Sync {
  fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
}
pub mod transactions {
  pub const r#getSensorProps: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 0;
  pub const r#createSession: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 1;
  pub const r#getInterfaceVersion: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777214;
  pub const r#getInterfaceHash: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777213;
}
pub type IFaceDefaultRef = Option<std::sync::Arc<dyn IFaceDefault>>;
static DEFAULT_IMPL: std::sync::Mutex<IFaceDefaultRef> = std::sync::Mutex::new(None);
pub const VERSION: i32 = 4;
pub const HASH: &str = "c43fbb9be4a662cc9ace640dba21cccdb84c6c21";
impl BpFace {
  fn build_parcel_getSensorProps(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_getSensorProps(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as IFace>::getDefaultImpl() {
        return _aidl_default_impl.r#getSensorProps();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_createSession(&self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_sensorId)?;
    aidl_data.write(&_arg_userId)?;
    aidl_data.write(_arg_cb)?;
    Ok(aidl_data)
  }
  fn read_response_createSession(&self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as IFace>::getDefaultImpl() {
        return _aidl_default_impl.r#createSession(_arg_sensorId, _arg_userId, _arg_cb);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession> = _aidl_reply.read()?;
    Ok(_aidl_return)
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
impl IFace for BpFace {
  fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>> {
    let _aidl_data = self.build_parcel_getSensorProps()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getSensorProps, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getSensorProps(_aidl_reply)
  }
  fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>> {
    let _aidl_data = self.build_parcel_createSession(_arg_sensorId, _arg_userId, _arg_cb)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#createSession, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_createSession(_arg_sensorId, _arg_userId, _arg_cb, _aidl_reply)
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
impl<P: binder::BinderAsyncPool> IFaceAsync<P> for BpFace {
  fn r#getSensorProps<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>>> {
    let _aidl_data = match self.build_parcel_getSensorProps() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getSensorProps, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getSensorProps(_aidl_reply)
      }
    )
  }
  fn r#createSession<'a, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'a binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>>> {
    let _aidl_data = match self.build_parcel_createSession(_arg_sensorId, _arg_userId, _arg_cb) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#createSession, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_createSession(_arg_sensorId, _arg_userId, _arg_cb, _aidl_reply)
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
impl IFace for binder::binder_impl::Binder<BnFace> {
  fn r#getSensorProps<'a, >(&'a self) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_11_SensorProps>> { self.0.r#getSensorProps() }
  fn r#createSession<'a, 'l1, >(&'a self, _arg_sensorId: i32, _arg_userId: i32, _arg_cb: &'l1 binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_8_ISession>> { self.0.r#createSession(_arg_sensorId, _arg_userId, _arg_cb) }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> { self.0.r#getInterfaceVersion() }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> { self.0.r#getInterfaceHash() }
}
fn on_transact(_aidl_service: &dyn IFace, _aidl_code: binder::binder_impl::TransactionCode, _aidl_data: &binder::binder_impl::BorrowedParcel<'_>, _aidl_reply: &mut binder::binder_impl::BorrowedParcel<'_>) -> std::result::Result<(), binder::StatusCode> {
  match _aidl_code {
    transactions::r#getSensorProps => {
      let _aidl_return = _aidl_service.r#getSensorProps();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#createSession => {
      let _arg_sensorId: i32 = _aidl_data.read()?;
      let _arg_userId: i32 = _aidl_data.read()?;
      let _arg_cb: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#createSession(_arg_sensorId, _arg_userId, &_arg_cb);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
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
 pub use super::r#IFace as _7_android_8_hardware_10_biometrics_4_face_5_IFace;
}
