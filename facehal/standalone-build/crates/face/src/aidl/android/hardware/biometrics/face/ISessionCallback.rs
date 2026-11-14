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
  ISessionCallback["android.hardware.biometrics.face.ISessionCallback"] {
    native: BnSessionCallback(on_transact),
    proxy: BpSessionCallback {
      cached_version: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(-1),
      cached_hash: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None)
    },
    async: ISessionCallbackAsync(try_into_local_async),
    stability: binder::binder_impl::Stability::Vintf,
  }
}
pub trait ISessionCallback: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISessionCallback" }
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()>;
  fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()>;
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()>;
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()>;
  fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()>;
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()>;
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()>;
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()>;
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()>;
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()>;
  fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()>;
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()>;
  fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()>;
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()>;
  fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> {
    Ok(VERSION)
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> {
    Ok(HASH.into())
  }
  fn getDefaultImpl() -> ISessionCallbackDefaultRef where Self: Sized {
    DEFAULT_IMPL.lock().unwrap().clone()
  }
  fn setDefaultImpl(d: ISessionCallbackDefaultRef) -> ISessionCallbackDefaultRef where Self: Sized {
    std::mem::replace(&mut *DEFAULT_IMPL.lock().unwrap(), d)
  }
  fn try_as_async_server<'a>(&'a self) -> Option<&'a (dyn ISessionCallbackAsyncServer + Send + Sync)> {
    None
  }
}
pub trait ISessionCallbackAsync<P>: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISessionCallback" }
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onAuthenticationFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onEnrollmentFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onAuthenticationSucceeded<'a, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onEnrollmentsEnumerated<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onFeaturesRetrieved<'a, >(&'a self, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onEnrollmentsRemoved<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#onSessionClosed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<i32>> {
    Box::pin(async move { Ok(VERSION) })
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<String>> {
    Box::pin(async move { Ok(HASH.into()) })
  }
}
#[::async_trait::async_trait]
pub trait ISessionCallbackAsyncServer: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISessionCallback" }
  async fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  async fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  async fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()>;
  async fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()>;
  async fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()>;
  async fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()>;
  async fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()>;
  async fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()>;
  async fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()>;
  async fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()>;
  async fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()>;
  async fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()>;
  async fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  async fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()>;
  async fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()>;
  async fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  async fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()>;
  async fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()>;
  async fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()>;
}
impl BnSessionCallback {
  /// Create a new async binder service.
  pub fn new_async_binder<T, R>(inner: T, rt: R, features: binder::BinderFeatures) -> binder::Strong<dyn ISessionCallback>
  where
    T: ISessionCallbackAsyncServer + binder::Interface + Send + Sync + 'static,
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
    impl<T, R> ISessionCallback for Wrapper<T, R>
    where
      T: ISessionCallbackAsyncServer + Send + Sync + 'static,
      R: binder::binder_impl::BinderAsyncRuntime + Send + Sync + 'static,
    {
      fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onChallengeGenerated(_arg_challenge))
      }
      fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onChallengeRevoked(_arg_challenge))
      }
      fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onAuthenticationFrame(_arg_frame))
      }
      fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onEnrollmentFrame(_arg_frame))
      }
      fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onError(_arg_error, _arg_vendorCode))
      }
      fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onEnrollmentProgress(_arg_enrollmentId, _arg_remaining))
      }
      fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat))
      }
      fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onAuthenticationFailed())
      }
      fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onLockoutTimed(_arg_durationMillis))
      }
      fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onLockoutPermanent())
      }
      fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onLockoutCleared())
      }
      fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onInteractionDetected())
      }
      fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onEnrollmentsEnumerated(_arg_enrollmentIds))
      }
      fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onFeaturesRetrieved(_arg_features))
      }
      fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onFeatureSet(_arg_feature))
      }
      fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onEnrollmentsRemoved(_arg_enrollmentIds))
      }
      fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onAuthenticatorIdRetrieved(_arg_authenticatorId))
      }
      fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onAuthenticatorIdInvalidated(_arg_newAuthenticatorId))
      }
      fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onSessionClosed())
      }
      fn try_as_async_server(&self) -> Option<&(dyn ISessionCallbackAsyncServer + Send + Sync)> {
        Some(&self._inner)
      }
    }
    let wrapped = Wrapper { _inner: inner, _rt: rt };
    Self::new_binder(wrapped, features)
  }
  pub fn try_into_local_async<P: binder::BinderAsyncPool + 'static>(_native: binder::binder_impl::Binder<Self>) -> Option<binder::Strong<dyn ISessionCallbackAsync<P>>> {
    struct Wrapper {
      _native: binder::binder_impl::Binder<BnSessionCallback>
    }
    impl binder::Interface for Wrapper {}
    impl<P: binder::BinderAsyncPool> ISessionCallbackAsync<P> for Wrapper {
      fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onChallengeGenerated(_arg_challenge))
      }
      fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onChallengeRevoked(_arg_challenge))
      }
      fn r#onAuthenticationFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onAuthenticationFrame(_arg_frame))
      }
      fn r#onEnrollmentFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onEnrollmentFrame(_arg_frame))
      }
      fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onError(_arg_error, _arg_vendorCode))
      }
      fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onEnrollmentProgress(_arg_enrollmentId, _arg_remaining))
      }
      fn r#onAuthenticationSucceeded<'a, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat))
      }
      fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onAuthenticationFailed())
      }
      fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onLockoutTimed(_arg_durationMillis))
      }
      fn r#onLockoutPermanent<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onLockoutPermanent())
      }
      fn r#onLockoutCleared<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onLockoutCleared())
      }
      fn r#onInteractionDetected<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onInteractionDetected())
      }
      fn r#onEnrollmentsEnumerated<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onEnrollmentsEnumerated(_arg_enrollmentIds))
      }
      fn r#onFeaturesRetrieved<'a, >(&'a self, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onFeaturesRetrieved(_arg_features))
      }
      fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onFeatureSet(_arg_feature))
      }
      fn r#onEnrollmentsRemoved<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onEnrollmentsRemoved(_arg_enrollmentIds))
      }
      fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onAuthenticatorIdRetrieved(_arg_authenticatorId))
      }
      fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onAuthenticatorIdInvalidated(_arg_newAuthenticatorId))
      }
      fn r#onSessionClosed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onSessionClosed())
      }
    }
    if _native.try_as_async_server().is_some() {
      Some(binder::Strong::new(Box::new(Wrapper { _native }) as Box<dyn ISessionCallbackAsync<P>>))
    } else {
      None
    }
  }
}
pub trait ISessionCallbackDefault: Send + Sync {
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
}
pub mod transactions {
  pub const r#onChallengeGenerated: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 0;
  pub const r#onChallengeRevoked: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 1;
  pub const r#onAuthenticationFrame: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 2;
  pub const r#onEnrollmentFrame: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 3;
  pub const r#onError: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 4;
  pub const r#onEnrollmentProgress: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 5;
  pub const r#onAuthenticationSucceeded: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 6;
  pub const r#onAuthenticationFailed: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 7;
  pub const r#onLockoutTimed: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 8;
  pub const r#onLockoutPermanent: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 9;
  pub const r#onLockoutCleared: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 10;
  pub const r#onInteractionDetected: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 11;
  pub const r#onEnrollmentsEnumerated: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 12;
  pub const r#onFeaturesRetrieved: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 13;
  pub const r#onFeatureSet: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 14;
  pub const r#onEnrollmentsRemoved: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 15;
  pub const r#onAuthenticatorIdRetrieved: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16;
  pub const r#onAuthenticatorIdInvalidated: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 17;
  pub const r#onSessionClosed: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 18;
  pub const r#getInterfaceVersion: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777214;
  pub const r#getInterfaceHash: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777213;
}
pub type ISessionCallbackDefaultRef = Option<std::sync::Arc<dyn ISessionCallbackDefault>>;
static DEFAULT_IMPL: std::sync::Mutex<ISessionCallbackDefaultRef> = std::sync::Mutex::new(None);
pub const VERSION: i32 = 4;
pub const HASH: &str = "c43fbb9be4a662cc9ace640dba21cccdb84c6c21";
impl BpSessionCallback {
  fn build_parcel_onChallengeGenerated(&self, _arg_challenge: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_challenge)?;
    Ok(aidl_data)
  }
  fn read_response_onChallengeGenerated(&self, _arg_challenge: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onChallengeGenerated(_arg_challenge);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onChallengeRevoked(&self, _arg_challenge: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_challenge)?;
    Ok(aidl_data)
  }
  fn read_response_onChallengeRevoked(&self, _arg_challenge: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onChallengeRevoked(_arg_challenge);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onAuthenticationFrame(&self, _arg_frame: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_frame)?;
    Ok(aidl_data)
  }
  fn read_response_onAuthenticationFrame(&self, _arg_frame: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onAuthenticationFrame(_arg_frame);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onEnrollmentFrame(&self, _arg_frame: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_frame)?;
    Ok(aidl_data)
  }
  fn read_response_onEnrollmentFrame(&self, _arg_frame: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onEnrollmentFrame(_arg_frame);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onError(&self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_error)?;
    aidl_data.write(&_arg_vendorCode)?;
    Ok(aidl_data)
  }
  fn read_response_onError(&self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onError(_arg_error, _arg_vendorCode);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onEnrollmentProgress(&self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_enrollmentId)?;
    aidl_data.write(&_arg_remaining)?;
    Ok(aidl_data)
  }
  fn read_response_onEnrollmentProgress(&self, _arg_enrollmentId: i32, _arg_remaining: i32, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onEnrollmentProgress(_arg_enrollmentId, _arg_remaining);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onAuthenticationSucceeded(&self, _arg_enrollmentId: i32, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_enrollmentId)?;
    aidl_data.write(_arg_hat)?;
    Ok(aidl_data)
  }
  fn read_response_onAuthenticationSucceeded(&self, _arg_enrollmentId: i32, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onAuthenticationFailed(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_onAuthenticationFailed(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onAuthenticationFailed();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onLockoutTimed(&self, _arg_durationMillis: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_durationMillis)?;
    Ok(aidl_data)
  }
  fn read_response_onLockoutTimed(&self, _arg_durationMillis: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onLockoutTimed(_arg_durationMillis);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onLockoutPermanent(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_onLockoutPermanent(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onLockoutPermanent();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onLockoutCleared(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_onLockoutCleared(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onLockoutCleared();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onInteractionDetected(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_onInteractionDetected(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onInteractionDetected();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onEnrollmentsEnumerated(&self, _arg_enrollmentIds: &[i32]) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_enrollmentIds)?;
    Ok(aidl_data)
  }
  fn read_response_onEnrollmentsEnumerated(&self, _arg_enrollmentIds: &[i32], _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onEnrollmentsEnumerated(_arg_enrollmentIds);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onFeaturesRetrieved(&self, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_features)?;
    Ok(aidl_data)
  }
  fn read_response_onFeaturesRetrieved(&self, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onFeaturesRetrieved(_arg_features);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onFeatureSet(&self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_feature)?;
    Ok(aidl_data)
  }
  fn read_response_onFeatureSet(&self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onFeatureSet(_arg_feature);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onEnrollmentsRemoved(&self, _arg_enrollmentIds: &[i32]) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_enrollmentIds)?;
    Ok(aidl_data)
  }
  fn read_response_onEnrollmentsRemoved(&self, _arg_enrollmentIds: &[i32], _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onEnrollmentsRemoved(_arg_enrollmentIds);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onAuthenticatorIdRetrieved(&self, _arg_authenticatorId: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_authenticatorId)?;
    Ok(aidl_data)
  }
  fn read_response_onAuthenticatorIdRetrieved(&self, _arg_authenticatorId: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onAuthenticatorIdRetrieved(_arg_authenticatorId);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onAuthenticatorIdInvalidated(&self, _arg_newAuthenticatorId: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_newAuthenticatorId)?;
    Ok(aidl_data)
  }
  fn read_response_onAuthenticatorIdInvalidated(&self, _arg_newAuthenticatorId: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onAuthenticatorIdInvalidated(_arg_newAuthenticatorId);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_onSessionClosed(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_onSessionClosed(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISessionCallback>::getDefaultImpl() {
        return _aidl_default_impl.r#onSessionClosed();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
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
impl ISessionCallback for BpSessionCallback {
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onChallengeGenerated(_arg_challenge)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onChallengeGenerated, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onChallengeGenerated(_arg_challenge, _aidl_reply)
  }
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onChallengeRevoked(_arg_challenge)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onChallengeRevoked, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onChallengeRevoked(_arg_challenge, _aidl_reply)
  }
  fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onAuthenticationFrame(_arg_frame)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onAuthenticationFrame, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onAuthenticationFrame(_arg_frame, _aidl_reply)
  }
  fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onEnrollmentFrame(_arg_frame)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onEnrollmentFrame, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onEnrollmentFrame(_arg_frame, _aidl_reply)
  }
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onError(_arg_error, _arg_vendorCode)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onError, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onError(_arg_error, _arg_vendorCode, _aidl_reply)
  }
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onEnrollmentProgress(_arg_enrollmentId, _arg_remaining)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onEnrollmentProgress, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onEnrollmentProgress(_arg_enrollmentId, _arg_remaining, _aidl_reply)
  }
  fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onAuthenticationSucceeded, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat, _aidl_reply)
  }
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onAuthenticationFailed()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onAuthenticationFailed, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onAuthenticationFailed(_aidl_reply)
  }
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onLockoutTimed(_arg_durationMillis)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onLockoutTimed, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onLockoutTimed(_arg_durationMillis, _aidl_reply)
  }
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onLockoutPermanent()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onLockoutPermanent, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onLockoutPermanent(_aidl_reply)
  }
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onLockoutCleared()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onLockoutCleared, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onLockoutCleared(_aidl_reply)
  }
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onInteractionDetected()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onInteractionDetected, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onInteractionDetected(_aidl_reply)
  }
  fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onEnrollmentsEnumerated(_arg_enrollmentIds)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onEnrollmentsEnumerated, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onEnrollmentsEnumerated(_arg_enrollmentIds, _aidl_reply)
  }
  fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onFeaturesRetrieved(_arg_features)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onFeaturesRetrieved, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onFeaturesRetrieved(_arg_features, _aidl_reply)
  }
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onFeatureSet(_arg_feature)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onFeatureSet, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onFeatureSet(_arg_feature, _aidl_reply)
  }
  fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onEnrollmentsRemoved(_arg_enrollmentIds)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onEnrollmentsRemoved, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onEnrollmentsRemoved(_arg_enrollmentIds, _aidl_reply)
  }
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onAuthenticatorIdRetrieved(_arg_authenticatorId)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onAuthenticatorIdRetrieved, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onAuthenticatorIdRetrieved(_arg_authenticatorId, _aidl_reply)
  }
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onAuthenticatorIdInvalidated(_arg_newAuthenticatorId)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onAuthenticatorIdInvalidated, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onAuthenticatorIdInvalidated(_arg_newAuthenticatorId, _aidl_reply)
  }
  fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onSessionClosed()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onSessionClosed, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onSessionClosed(_aidl_reply)
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
impl<P: binder::BinderAsyncPool> ISessionCallbackAsync<P> for BpSessionCallback {
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onChallengeGenerated(_arg_challenge) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onChallengeGenerated, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onChallengeGenerated(_arg_challenge, _aidl_reply)
      }
    )
  }
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onChallengeRevoked(_arg_challenge) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onChallengeRevoked, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onChallengeRevoked(_arg_challenge, _aidl_reply)
      }
    )
  }
  fn r#onAuthenticationFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onAuthenticationFrame(_arg_frame) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onAuthenticationFrame, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onAuthenticationFrame(_arg_frame, _aidl_reply)
      }
    )
  }
  fn r#onEnrollmentFrame<'a, >(&'a self, _arg_frame: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onEnrollmentFrame(_arg_frame) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onEnrollmentFrame, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onEnrollmentFrame(_arg_frame, _aidl_reply)
      }
    )
  }
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onError(_arg_error, _arg_vendorCode) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onError, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onError(_arg_error, _arg_vendorCode, _aidl_reply)
      }
    )
  }
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onEnrollmentProgress(_arg_enrollmentId, _arg_remaining) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onEnrollmentProgress, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onEnrollmentProgress(_arg_enrollmentId, _arg_remaining, _aidl_reply)
      }
    )
  }
  fn r#onAuthenticationSucceeded<'a, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onAuthenticationSucceeded, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat, _aidl_reply)
      }
    )
  }
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onAuthenticationFailed() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onAuthenticationFailed, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onAuthenticationFailed(_aidl_reply)
      }
    )
  }
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onLockoutTimed(_arg_durationMillis) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onLockoutTimed, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onLockoutTimed(_arg_durationMillis, _aidl_reply)
      }
    )
  }
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onLockoutPermanent() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onLockoutPermanent, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onLockoutPermanent(_aidl_reply)
      }
    )
  }
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onLockoutCleared() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onLockoutCleared, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onLockoutCleared(_aidl_reply)
      }
    )
  }
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onInteractionDetected() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onInteractionDetected, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onInteractionDetected(_aidl_reply)
      }
    )
  }
  fn r#onEnrollmentsEnumerated<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onEnrollmentsEnumerated(_arg_enrollmentIds) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onEnrollmentsEnumerated, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onEnrollmentsEnumerated(_arg_enrollmentIds, _aidl_reply)
      }
    )
  }
  fn r#onFeaturesRetrieved<'a, >(&'a self, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onFeaturesRetrieved(_arg_features) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onFeaturesRetrieved, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onFeaturesRetrieved(_arg_features, _aidl_reply)
      }
    )
  }
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onFeatureSet(_arg_feature) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onFeatureSet, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onFeatureSet(_arg_feature, _aidl_reply)
      }
    )
  }
  fn r#onEnrollmentsRemoved<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onEnrollmentsRemoved(_arg_enrollmentIds) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onEnrollmentsRemoved, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onEnrollmentsRemoved(_arg_enrollmentIds, _aidl_reply)
      }
    )
  }
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onAuthenticatorIdRetrieved(_arg_authenticatorId) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onAuthenticatorIdRetrieved, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onAuthenticatorIdRetrieved(_arg_authenticatorId, _aidl_reply)
      }
    )
  }
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onAuthenticatorIdInvalidated(_arg_newAuthenticatorId) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onAuthenticatorIdInvalidated, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onAuthenticatorIdInvalidated(_arg_newAuthenticatorId, _aidl_reply)
      }
    )
  }
  fn r#onSessionClosed<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onSessionClosed() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onSessionClosed, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onSessionClosed(_aidl_reply)
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
impl ISessionCallback for binder::binder_impl::Binder<BnSessionCallback> {
  fn r#onChallengeGenerated<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> { self.0.r#onChallengeGenerated(_arg_challenge) }
  fn r#onChallengeRevoked<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> { self.0.r#onChallengeRevoked(_arg_challenge) }
  fn r#onAuthenticationFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame) -> binder::Result<()> { self.0.r#onAuthenticationFrame(_arg_frame) }
  fn r#onEnrollmentFrame<'a, 'l1, >(&'a self, _arg_frame: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame) -> binder::Result<()> { self.0.r#onEnrollmentFrame(_arg_frame) }
  fn r#onError<'a, >(&'a self, _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error, _arg_vendorCode: i32) -> binder::Result<()> { self.0.r#onError(_arg_error, _arg_vendorCode) }
  fn r#onEnrollmentProgress<'a, >(&'a self, _arg_enrollmentId: i32, _arg_remaining: i32) -> binder::Result<()> { self.0.r#onEnrollmentProgress(_arg_enrollmentId, _arg_remaining) }
  fn r#onAuthenticationSucceeded<'a, 'l1, >(&'a self, _arg_enrollmentId: i32, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> { self.0.r#onAuthenticationSucceeded(_arg_enrollmentId, _arg_hat) }
  fn r#onAuthenticationFailed<'a, >(&'a self) -> binder::Result<()> { self.0.r#onAuthenticationFailed() }
  fn r#onLockoutTimed<'a, >(&'a self, _arg_durationMillis: i64) -> binder::Result<()> { self.0.r#onLockoutTimed(_arg_durationMillis) }
  fn r#onLockoutPermanent<'a, >(&'a self) -> binder::Result<()> { self.0.r#onLockoutPermanent() }
  fn r#onLockoutCleared<'a, >(&'a self) -> binder::Result<()> { self.0.r#onLockoutCleared() }
  fn r#onInteractionDetected<'a, >(&'a self) -> binder::Result<()> { self.0.r#onInteractionDetected() }
  fn r#onEnrollmentsEnumerated<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> { self.0.r#onEnrollmentsEnumerated(_arg_enrollmentIds) }
  fn r#onFeaturesRetrieved<'a, 'l1, >(&'a self, _arg_features: &'l1 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature]) -> binder::Result<()> { self.0.r#onFeaturesRetrieved(_arg_features) }
  fn r#onFeatureSet<'a, >(&'a self, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature) -> binder::Result<()> { self.0.r#onFeatureSet(_arg_feature) }
  fn r#onEnrollmentsRemoved<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> { self.0.r#onEnrollmentsRemoved(_arg_enrollmentIds) }
  fn r#onAuthenticatorIdRetrieved<'a, >(&'a self, _arg_authenticatorId: i64) -> binder::Result<()> { self.0.r#onAuthenticatorIdRetrieved(_arg_authenticatorId) }
  fn r#onAuthenticatorIdInvalidated<'a, >(&'a self, _arg_newAuthenticatorId: i64) -> binder::Result<()> { self.0.r#onAuthenticatorIdInvalidated(_arg_newAuthenticatorId) }
  fn r#onSessionClosed<'a, >(&'a self) -> binder::Result<()> { self.0.r#onSessionClosed() }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> { self.0.r#getInterfaceVersion() }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> { self.0.r#getInterfaceHash() }
}
fn on_transact(_aidl_service: &dyn ISessionCallback, _aidl_code: binder::binder_impl::TransactionCode, _aidl_data: &binder::binder_impl::BorrowedParcel<'_>, _aidl_reply: &mut binder::binder_impl::BorrowedParcel<'_>) -> std::result::Result<(), binder::StatusCode> {
  match _aidl_code {
    transactions::r#onChallengeGenerated => {
      let _arg_challenge: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onChallengeGenerated(_arg_challenge);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onChallengeRevoked => {
      let _arg_challenge: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onChallengeRevoked(_arg_challenge);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onAuthenticationFrame => {
      let _arg_frame: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_19_AuthenticationFrame = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onAuthenticationFrame(&_arg_frame);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onEnrollmentFrame => {
      let _arg_frame: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_15_EnrollmentFrame = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onEnrollmentFrame(&_arg_frame);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onError => {
      let _arg_error: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_5_Error = _aidl_data.read()?;
      let _arg_vendorCode: i32 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onError(_arg_error, _arg_vendorCode);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onEnrollmentProgress => {
      let _arg_enrollmentId: i32 = _aidl_data.read()?;
      let _arg_remaining: i32 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onEnrollmentProgress(_arg_enrollmentId, _arg_remaining);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onAuthenticationSucceeded => {
      let _arg_enrollmentId: i32 = _aidl_data.read()?;
      let _arg_hat: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onAuthenticationSucceeded(_arg_enrollmentId, &_arg_hat);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onAuthenticationFailed => {
      let _aidl_return = _aidl_service.r#onAuthenticationFailed();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onLockoutTimed => {
      let _arg_durationMillis: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onLockoutTimed(_arg_durationMillis);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onLockoutPermanent => {
      let _aidl_return = _aidl_service.r#onLockoutPermanent();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onLockoutCleared => {
      let _aidl_return = _aidl_service.r#onLockoutCleared();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onInteractionDetected => {
      let _aidl_return = _aidl_service.r#onInteractionDetected();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onEnrollmentsEnumerated => {
      let _arg_enrollmentIds: Vec<i32> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onEnrollmentsEnumerated(&_arg_enrollmentIds);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onFeaturesRetrieved => {
      let _arg_features: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onFeaturesRetrieved(&_arg_features);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onFeatureSet => {
      let _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onFeatureSet(_arg_feature);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onEnrollmentsRemoved => {
      let _arg_enrollmentIds: Vec<i32> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onEnrollmentsRemoved(&_arg_enrollmentIds);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onAuthenticatorIdRetrieved => {
      let _arg_authenticatorId: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onAuthenticatorIdRetrieved(_arg_authenticatorId);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onAuthenticatorIdInvalidated => {
      let _arg_newAuthenticatorId: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onAuthenticatorIdInvalidated(_arg_newAuthenticatorId);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onSessionClosed => {
      let _aidl_return = _aidl_service.r#onSessionClosed();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
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
 pub use super::r#ISessionCallback as _7_android_8_hardware_10_biometrics_4_face_16_ISessionCallback;
}
