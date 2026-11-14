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
  ISession["android.hardware.biometrics.face.ISession"] {
    native: BnSession(on_transact),
    proxy: BpSession {
      cached_version: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(-1),
      cached_hash: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None)
    },
    async: ISessionAsync(try_into_local_async),
    stability: binder::binder_impl::Stability::Vintf,
  }
}
pub trait ISession: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISession" }
  fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()>;
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()>;
  fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  fn r#getFeatures<'a, >(&'a self) -> binder::Result<()>;
  fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()>;
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()>;
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()>;
  fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()>;
  fn r#close<'a, >(&'a self) -> binder::Result<()>;
  fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()>;
  fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> {
    Ok(VERSION)
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> {
    Ok(HASH.into())
  }
  fn getDefaultImpl() -> ISessionDefaultRef where Self: Sized {
    DEFAULT_IMPL.lock().unwrap().clone()
  }
  fn setDefaultImpl(d: ISessionDefaultRef) -> ISessionDefaultRef where Self: Sized {
    std::mem::replace(&mut *DEFAULT_IMPL.lock().unwrap(), d)
  }
  fn try_as_async_server<'a>(&'a self) -> Option<&'a (dyn ISessionAsyncServer + Send + Sync)> {
    None
  }
}
pub trait ISessionAsync<P>: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISession" }
  fn r#generateChallenge<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  fn r#enroll<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#detectInteraction<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#removeEnrollments<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#getFeatures<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#setFeature<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#resetLockout<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#close<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#authenticateWithContext<'a, >(&'a self, _arg_operationId: i64, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  fn r#enrollWithContext<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#detectInteractionWithContext<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#onContextChanged<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<()>>;
  fn r#enrollWithOptions<'a, >(&'a self, _arg_options: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>>;
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<i32>> {
    Box::pin(async move { Ok(VERSION) })
  }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<String>> {
    Box::pin(async move { Ok(HASH.into()) })
  }
}
#[::async_trait::async_trait]
pub trait ISessionAsyncServer: binder::Interface + Send {
  fn get_descriptor() -> &'static str where Self: Sized { "android.hardware.biometrics.face.ISession" }
  async fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()>;
  async fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()>;
  async fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  async fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  async fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  async fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  async fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()>;
  async fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()>;
  async fn r#getFeatures<'a, >(&'a self) -> binder::Result<()>;
  async fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()>;
  async fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()>;
  async fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()>;
  async fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()>;
  async fn r#close<'a, >(&'a self) -> binder::Result<()>;
  async fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  #[deprecated = "use {@link enrollWithOptions} instead."]
  async fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  async fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
  async fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()>;
  async fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>;
}
impl BnSession {
  /// Create a new async binder service.
  pub fn new_async_binder<T, R>(inner: T, rt: R, features: binder::BinderFeatures) -> binder::Strong<dyn ISession>
  where
    T: ISessionAsyncServer + binder::Interface + Send + Sync + 'static,
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
    impl<T, R> ISession for Wrapper<T, R>
    where
      T: ISessionAsyncServer + Send + Sync + 'static,
      R: binder::binder_impl::BinderAsyncRuntime + Send + Sync + 'static,
    {
      fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#generateChallenge())
      }
      fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#revokeChallenge(_arg_challenge))
      }
      fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>> {
        self._rt.block_on(self._inner.r#getEnrollmentConfig(_arg_enrollmentType))
      }
      fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface))
      }
      fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#authenticate(_arg_operationId))
      }
      fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#detectInteraction())
      }
      fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#enumerateEnrollments())
      }
      fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#removeEnrollments(_arg_enrollmentIds))
      }
      fn r#getFeatures<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#getFeatures())
      }
      fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#setFeature(_arg_hat, _arg_feature, _arg_enabled))
      }
      fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#getAuthenticatorId())
      }
      fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#invalidateAuthenticatorId())
      }
      fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#resetLockout(_arg_hat))
      }
      fn r#close<'a, >(&'a self) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#close())
      }
      fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#authenticateWithContext(_arg_operationId, _arg_context))
      }
      fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context))
      }
      fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#detectInteractionWithContext(_arg_context))
      }
      fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()> {
        self._rt.block_on(self._inner.r#onContextChanged(_arg_context))
      }
      fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
        self._rt.block_on(self._inner.r#enrollWithOptions(_arg_options))
      }
      fn try_as_async_server(&self) -> Option<&(dyn ISessionAsyncServer + Send + Sync)> {
        Some(&self._inner)
      }
    }
    let wrapped = Wrapper { _inner: inner, _rt: rt };
    Self::new_binder(wrapped, features)
  }
  pub fn try_into_local_async<P: binder::BinderAsyncPool + 'static>(_native: binder::binder_impl::Binder<Self>) -> Option<binder::Strong<dyn ISessionAsync<P>>> {
    struct Wrapper {
      _native: binder::binder_impl::Binder<BnSession>
    }
    impl binder::Interface for Wrapper {}
    impl<P: binder::BinderAsyncPool> ISessionAsync<P> for Wrapper {
      fn r#generateChallenge<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#generateChallenge())
      }
      fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#revokeChallenge(_arg_challenge))
      }
      fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#getEnrollmentConfig(_arg_enrollmentType))
      }
      fn r#enroll<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface))
      }
      fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#authenticate(_arg_operationId))
      }
      fn r#detectInteraction<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#detectInteraction())
      }
      fn r#enumerateEnrollments<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#enumerateEnrollments())
      }
      fn r#removeEnrollments<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#removeEnrollments(_arg_enrollmentIds))
      }
      fn r#getFeatures<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#getFeatures())
      }
      fn r#setFeature<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#setFeature(_arg_hat, _arg_feature, _arg_enabled))
      }
      fn r#getAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#getAuthenticatorId())
      }
      fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#invalidateAuthenticatorId())
      }
      fn r#resetLockout<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#resetLockout(_arg_hat))
      }
      fn r#close<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#close())
      }
      fn r#authenticateWithContext<'a, >(&'a self, _arg_operationId: i64, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#authenticateWithContext(_arg_operationId, _arg_context))
      }
      fn r#enrollWithContext<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context))
      }
      fn r#detectInteractionWithContext<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#detectInteractionWithContext(_arg_context))
      }
      fn r#onContextChanged<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<()>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#onContextChanged(_arg_context))
      }
      fn r#enrollWithOptions<'a, >(&'a self, _arg_options: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
        Box::pin(self._native.try_as_async_server().unwrap().r#enrollWithOptions(_arg_options))
      }
    }
    if _native.try_as_async_server().is_some() {
      Some(binder::Strong::new(Box::new(Wrapper { _native }) as Box<dyn ISessionAsync<P>>))
    } else {
      None
    }
  }
}
pub trait ISessionDefault: Send + Sync {
  fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#getFeatures<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#close<'a, >(&'a self) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
  fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    Err(binder::StatusCode::UNKNOWN_TRANSACTION.into())
  }
}
pub mod transactions {
  pub const r#generateChallenge: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 0;
  pub const r#revokeChallenge: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 1;
  pub const r#getEnrollmentConfig: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 2;
  pub const r#enroll: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 3;
  pub const r#authenticate: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 4;
  pub const r#detectInteraction: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 5;
  pub const r#enumerateEnrollments: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 6;
  pub const r#removeEnrollments: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 7;
  pub const r#getFeatures: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 8;
  pub const r#setFeature: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 9;
  pub const r#getAuthenticatorId: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 10;
  pub const r#invalidateAuthenticatorId: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 11;
  pub const r#resetLockout: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 12;
  pub const r#close: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 13;
  pub const r#authenticateWithContext: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 14;
  pub const r#enrollWithContext: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 15;
  pub const r#detectInteractionWithContext: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16;
  pub const r#onContextChanged: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 17;
  pub const r#enrollWithOptions: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 18;
  pub const r#getInterfaceVersion: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777214;
  pub const r#getInterfaceHash: binder::binder_impl::TransactionCode = binder::binder_impl::FIRST_CALL_TRANSACTION + 16777213;
}
pub type ISessionDefaultRef = Option<std::sync::Arc<dyn ISessionDefault>>;
static DEFAULT_IMPL: std::sync::Mutex<ISessionDefaultRef> = std::sync::Mutex::new(None);
pub const VERSION: i32 = 4;
pub const HASH: &str = "c43fbb9be4a662cc9ace640dba21cccdb84c6c21";
impl BpSession {
  fn build_parcel_generateChallenge(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_generateChallenge(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#generateChallenge();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_revokeChallenge(&self, _arg_challenge: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_challenge)?;
    Ok(aidl_data)
  }
  fn read_response_revokeChallenge(&self, _arg_challenge: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#revokeChallenge(_arg_challenge);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_getEnrollmentConfig(&self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_enrollmentType)?;
    Ok(aidl_data)
  }
  fn read_response_getEnrollmentConfig(&self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#getEnrollmentConfig(_arg_enrollmentType);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_enroll(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_hat)?;
    aidl_data.write(&_arg_type)?;
    aidl_data.write(_arg_features)?;
    aidl_data.write(&_arg_previewSurface)?;
    Ok(aidl_data)
  }
  fn read_response_enroll(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_authenticate(&self, _arg_operationId: i64) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_operationId)?;
    Ok(aidl_data)
  }
  fn read_response_authenticate(&self, _arg_operationId: i64, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#authenticate(_arg_operationId);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_detectInteraction(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_detectInteraction(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#detectInteraction();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_enumerateEnrollments(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_enumerateEnrollments(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#enumerateEnrollments();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_removeEnrollments(&self, _arg_enrollmentIds: &[i32]) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_enrollmentIds)?;
    Ok(aidl_data)
  }
  fn read_response_removeEnrollments(&self, _arg_enrollmentIds: &[i32], _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#removeEnrollments(_arg_enrollmentIds);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_getFeatures(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_getFeatures(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#getFeatures();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_setFeature(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_hat)?;
    aidl_data.write(&_arg_feature)?;
    aidl_data.write(&_arg_enabled)?;
    Ok(aidl_data)
  }
  fn read_response_setFeature(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#setFeature(_arg_hat, _arg_feature, _arg_enabled);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_getAuthenticatorId(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_getAuthenticatorId(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#getAuthenticatorId();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_invalidateAuthenticatorId(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_invalidateAuthenticatorId(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#invalidateAuthenticatorId();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_resetLockout(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_hat)?;
    Ok(aidl_data)
  }
  fn read_response_resetLockout(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#resetLockout(_arg_hat);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_close(&self) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    Ok(aidl_data)
  }
  fn read_response_close(&self, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#close();
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_authenticateWithContext(&self, _arg_operationId: i64, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(&_arg_operationId)?;
    aidl_data.write(_arg_context)?;
    Ok(aidl_data)
  }
  fn read_response_authenticateWithContext(&self, _arg_operationId: i64, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#authenticateWithContext(_arg_operationId, _arg_context);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_enrollWithContext(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_hat)?;
    aidl_data.write(&_arg_type)?;
    aidl_data.write(_arg_features)?;
    aidl_data.write(&_arg_previewSurface)?;
    aidl_data.write(_arg_context)?;
    Ok(aidl_data)
  }
  fn read_response_enrollWithContext(&self, _arg_hat: &crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &[crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_detectInteractionWithContext(&self, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_context)?;
    Ok(aidl_data)
  }
  fn read_response_detectInteractionWithContext(&self, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#detectInteractionWithContext(_arg_context);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
    Ok(_aidl_return)
  }
  fn build_parcel_onContextChanged(&self, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_context)?;
    Ok(aidl_data)
  }
  fn read_response_onContextChanged(&self, _arg_context: &crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<()> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#onContextChanged(_arg_context);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    Ok(())
  }
  fn build_parcel_enrollWithOptions(&self, _arg_options: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::binder_impl::Parcel> {
    let mut aidl_data = self.binder.prepare_transact()?;
    aidl_data.write(_arg_options)?;
    Ok(aidl_data)
  }
  fn read_response_enrollWithOptions(&self, _arg_options: &crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions, _aidl_reply: std::result::Result<binder::binder_impl::Parcel, binder::StatusCode>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    if let Err(binder::StatusCode::UNKNOWN_TRANSACTION) = _aidl_reply {
      if let Some(_aidl_default_impl) = <Self as ISession>::getDefaultImpl() {
        return _aidl_default_impl.r#enrollWithOptions(_arg_options);
      }
    }
    let _aidl_reply = _aidl_reply?;
    let _aidl_status: binder::Status = _aidl_reply.read()?;
    if !_aidl_status.is_ok() { return Err(_aidl_status); }
    let _aidl_return: binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal> = _aidl_reply.read()?;
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
impl ISession for BpSession {
  fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_generateChallenge()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#generateChallenge, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_generateChallenge(_aidl_reply)
  }
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_revokeChallenge(_arg_challenge)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#revokeChallenge, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_revokeChallenge(_arg_challenge, _aidl_reply)
  }
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>> {
    let _aidl_data = self.build_parcel_getEnrollmentConfig(_arg_enrollmentType)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getEnrollmentConfig, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getEnrollmentConfig(_arg_enrollmentType, _aidl_reply)
  }
  fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#enroll, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _aidl_reply)
  }
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_authenticate(_arg_operationId)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#authenticate, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_authenticate(_arg_operationId, _aidl_reply)
  }
  fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_detectInteraction()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#detectInteraction, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_detectInteraction(_aidl_reply)
  }
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_enumerateEnrollments()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#enumerateEnrollments, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_enumerateEnrollments(_aidl_reply)
  }
  fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_removeEnrollments(_arg_enrollmentIds)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#removeEnrollments, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_removeEnrollments(_arg_enrollmentIds, _aidl_reply)
  }
  fn r#getFeatures<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_getFeatures()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getFeatures, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getFeatures(_aidl_reply)
  }
  fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_setFeature(_arg_hat, _arg_feature, _arg_enabled)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#setFeature, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_setFeature(_arg_hat, _arg_feature, _arg_enabled, _aidl_reply)
  }
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_getAuthenticatorId()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#getAuthenticatorId, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_getAuthenticatorId(_aidl_reply)
  }
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_invalidateAuthenticatorId()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#invalidateAuthenticatorId, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_invalidateAuthenticatorId(_aidl_reply)
  }
  fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_resetLockout(_arg_hat)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#resetLockout, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_resetLockout(_arg_hat, _aidl_reply)
  }
  fn r#close<'a, >(&'a self) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_close()?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#close, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_close(_aidl_reply)
  }
  fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_authenticateWithContext(_arg_operationId, _arg_context)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#authenticateWithContext, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_authenticateWithContext(_arg_operationId, _arg_context, _aidl_reply)
  }
  fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#enrollWithContext, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context, _aidl_reply)
  }
  fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_detectInteractionWithContext(_arg_context)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#detectInteractionWithContext, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_detectInteractionWithContext(_arg_context, _aidl_reply)
  }
  fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()> {
    let _aidl_data = self.build_parcel_onContextChanged(_arg_context)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#onContextChanged, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_onContextChanged(_arg_context, _aidl_reply)
  }
  fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> {
    let _aidl_data = self.build_parcel_enrollWithOptions(_arg_options)?;
    let _aidl_reply = self.binder.submit_transact(transactions::r#enrollWithOptions, _aidl_data, FLAG_PRIVATE_LOCAL);
    self.read_response_enrollWithOptions(_arg_options, _aidl_reply)
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
impl<P: binder::BinderAsyncPool> ISessionAsync<P> for BpSession {
  fn r#generateChallenge<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_generateChallenge() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#generateChallenge, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_generateChallenge(_aidl_reply)
      }
    )
  }
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_revokeChallenge(_arg_challenge) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#revokeChallenge, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_revokeChallenge(_arg_challenge, _aidl_reply)
      }
    )
  }
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::BoxFuture<'a, binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>>> {
    let _aidl_data = match self.build_parcel_getEnrollmentConfig(_arg_enrollmentType) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getEnrollmentConfig, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getEnrollmentConfig(_arg_enrollmentType, _aidl_reply)
      }
    )
  }
  fn r#enroll<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#enroll, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _aidl_reply)
      }
    )
  }
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_authenticate(_arg_operationId) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#authenticate, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_authenticate(_arg_operationId, _aidl_reply)
      }
    )
  }
  fn r#detectInteraction<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_detectInteraction() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#detectInteraction, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_detectInteraction(_aidl_reply)
      }
    )
  }
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_enumerateEnrollments() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#enumerateEnrollments, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_enumerateEnrollments(_aidl_reply)
      }
    )
  }
  fn r#removeEnrollments<'a, >(&'a self, _arg_enrollmentIds: &'a [i32]) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_removeEnrollments(_arg_enrollmentIds) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#removeEnrollments, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_removeEnrollments(_arg_enrollmentIds, _aidl_reply)
      }
    )
  }
  fn r#getFeatures<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_getFeatures() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getFeatures, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getFeatures(_aidl_reply)
      }
    )
  }
  fn r#setFeature<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_setFeature(_arg_hat, _arg_feature, _arg_enabled) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#setFeature, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_setFeature(_arg_hat, _arg_feature, _arg_enabled, _aidl_reply)
      }
    )
  }
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_getAuthenticatorId() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#getAuthenticatorId, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_getAuthenticatorId(_aidl_reply)
      }
    )
  }
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_invalidateAuthenticatorId() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#invalidateAuthenticatorId, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_invalidateAuthenticatorId(_aidl_reply)
      }
    )
  }
  fn r#resetLockout<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_resetLockout(_arg_hat) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#resetLockout, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_resetLockout(_arg_hat, _aidl_reply)
      }
    )
  }
  fn r#close<'a, >(&'a self) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_close() {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#close, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_close(_aidl_reply)
      }
    )
  }
  fn r#authenticateWithContext<'a, >(&'a self, _arg_operationId: i64, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_authenticateWithContext(_arg_operationId, _arg_context) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#authenticateWithContext, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_authenticateWithContext(_arg_operationId, _arg_context, _aidl_reply)
      }
    )
  }
  fn r#enrollWithContext<'a, >(&'a self, _arg_hat: &'a crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'a [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'a crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#enrollWithContext, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context, _aidl_reply)
      }
    )
  }
  fn r#detectInteractionWithContext<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_detectInteractionWithContext(_arg_context) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#detectInteractionWithContext, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_detectInteractionWithContext(_arg_context, _aidl_reply)
      }
    )
  }
  fn r#onContextChanged<'a, >(&'a self, _arg_context: &'a crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::BoxFuture<'a, binder::Result<()>> {
    let _aidl_data = match self.build_parcel_onContextChanged(_arg_context) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#onContextChanged, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_onContextChanged(_arg_context, _aidl_reply)
      }
    )
  }
  fn r#enrollWithOptions<'a, >(&'a self, _arg_options: &'a crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::BoxFuture<'a, binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>>> {
    let _aidl_data = match self.build_parcel_enrollWithOptions(_arg_options) {
      Ok(_aidl_data) => _aidl_data,
      Err(err) => return Box::pin(std::future::ready(Err(err))),
    };
    let binder = self.binder.clone();
    P::spawn(
      move || binder.submit_transact(transactions::r#enrollWithOptions, _aidl_data, FLAG_PRIVATE_LOCAL),
      move |_aidl_reply| async move {
        self.read_response_enrollWithOptions(_arg_options, _aidl_reply)
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
impl ISession for binder::binder_impl::Binder<BnSession> {
  fn r#generateChallenge<'a, >(&'a self) -> binder::Result<()> { self.0.r#generateChallenge() }
  fn r#revokeChallenge<'a, >(&'a self, _arg_challenge: i64) -> binder::Result<()> { self.0.r#revokeChallenge(_arg_challenge) }
  fn r#getEnrollmentConfig<'a, >(&'a self, _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType) -> binder::Result<Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_21_EnrollmentStageConfig>> { self.0.r#getEnrollmentConfig(_arg_enrollmentType) }
  fn r#enroll<'a, 'l1, 'l2, 'l3, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#enroll(_arg_hat, _arg_type, _arg_features, _arg_previewSurface) }
  fn r#authenticate<'a, >(&'a self, _arg_operationId: i64) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#authenticate(_arg_operationId) }
  fn r#detectInteraction<'a, >(&'a self) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#detectInteraction() }
  fn r#enumerateEnrollments<'a, >(&'a self) -> binder::Result<()> { self.0.r#enumerateEnrollments() }
  fn r#removeEnrollments<'a, 'l1, >(&'a self, _arg_enrollmentIds: &'l1 [i32]) -> binder::Result<()> { self.0.r#removeEnrollments(_arg_enrollmentIds) }
  fn r#getFeatures<'a, >(&'a self) -> binder::Result<()> { self.0.r#getFeatures() }
  fn r#setFeature<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature, _arg_enabled: bool) -> binder::Result<()> { self.0.r#setFeature(_arg_hat, _arg_feature, _arg_enabled) }
  fn r#getAuthenticatorId<'a, >(&'a self) -> binder::Result<()> { self.0.r#getAuthenticatorId() }
  fn r#invalidateAuthenticatorId<'a, >(&'a self) -> binder::Result<()> { self.0.r#invalidateAuthenticatorId() }
  fn r#resetLockout<'a, 'l1, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken) -> binder::Result<()> { self.0.r#resetLockout(_arg_hat) }
  fn r#close<'a, >(&'a self) -> binder::Result<()> { self.0.r#close() }
  fn r#authenticateWithContext<'a, 'l1, >(&'a self, _arg_operationId: i64, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#authenticateWithContext(_arg_operationId, _arg_context) }
  fn r#enrollWithContext<'a, 'l1, 'l2, 'l3, 'l4, >(&'a self, _arg_hat: &'l1 crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken, _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType, _arg_features: &'l2 [crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature], _arg_previewSurface: Option<&'l3 crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle>, _arg_context: &'l4 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#enrollWithContext(_arg_hat, _arg_type, _arg_features, _arg_previewSurface, _arg_context) }
  fn r#detectInteractionWithContext<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#detectInteractionWithContext(_arg_context) }
  fn r#onContextChanged<'a, 'l1, >(&'a self, _arg_context: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext) -> binder::Result<()> { self.0.r#onContextChanged(_arg_context) }
  fn r#enrollWithOptions<'a, 'l1, >(&'a self, _arg_options: &'l1 crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions) -> binder::Result<binder::Strong<dyn crate::mangled::_7_android_8_hardware_10_biometrics_6_common_19_ICancellationSignal>> { self.0.r#enrollWithOptions(_arg_options) }
  fn r#getInterfaceVersion<'a, >(&'a self) -> binder::Result<i32> { self.0.r#getInterfaceVersion() }
  fn r#getInterfaceHash<'a, >(&'a self) -> binder::Result<String> { self.0.r#getInterfaceHash() }
}
fn on_transact(_aidl_service: &dyn ISession, _aidl_code: binder::binder_impl::TransactionCode, _aidl_data: &binder::binder_impl::BorrowedParcel<'_>, _aidl_reply: &mut binder::binder_impl::BorrowedParcel<'_>) -> std::result::Result<(), binder::StatusCode> {
  match _aidl_code {
    transactions::r#generateChallenge => {
      let _aidl_return = _aidl_service.r#generateChallenge();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#revokeChallenge => {
      let _arg_challenge: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#revokeChallenge(_arg_challenge);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#getEnrollmentConfig => {
      let _arg_enrollmentType: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#getEnrollmentConfig(_arg_enrollmentType);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#enroll => {
      let _arg_hat: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken = _aidl_data.read()?;
      let _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType = _aidl_data.read()?;
      let _arg_features: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature> = _aidl_data.read()?;
      let _arg_previewSurface: Option<crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#enroll(&_arg_hat, _arg_type, &_arg_features, _arg_previewSurface.as_ref());
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#authenticate => {
      let _arg_operationId: i64 = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#authenticate(_arg_operationId);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#detectInteraction => {
      let _aidl_return = _aidl_service.r#detectInteraction();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#enumerateEnrollments => {
      let _aidl_return = _aidl_service.r#enumerateEnrollments();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#removeEnrollments => {
      let _arg_enrollmentIds: Vec<i32> = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#removeEnrollments(&_arg_enrollmentIds);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#getFeatures => {
      let _aidl_return = _aidl_service.r#getFeatures();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#setFeature => {
      let _arg_hat: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken = _aidl_data.read()?;
      let _arg_feature: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature = _aidl_data.read()?;
      let _arg_enabled: bool = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#setFeature(&_arg_hat, _arg_feature, _arg_enabled);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#getAuthenticatorId => {
      let _aidl_return = _aidl_service.r#getAuthenticatorId();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#invalidateAuthenticatorId => {
      let _aidl_return = _aidl_service.r#invalidateAuthenticatorId();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#resetLockout => {
      let _arg_hat: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#resetLockout(&_arg_hat);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#close => {
      let _aidl_return = _aidl_service.r#close();
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#authenticateWithContext => {
      let _arg_operationId: i64 = _aidl_data.read()?;
      let _arg_context: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#authenticateWithContext(_arg_operationId, &_arg_context);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#enrollWithContext => {
      let _arg_hat: crate::mangled::_7_android_8_hardware_9_keymaster_17_HardwareAuthToken = _aidl_data.read()?;
      let _arg_type: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_14_EnrollmentType = _aidl_data.read()?;
      let _arg_features: Vec<crate::mangled::_7_android_8_hardware_10_biometrics_4_face_7_Feature> = _aidl_data.read()?;
      let _arg_previewSurface: Option<crate::mangled::_7_android_8_hardware_6_common_12_NativeHandle> = _aidl_data.read()?;
      let _arg_context: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#enrollWithContext(&_arg_hat, _arg_type, &_arg_features, _arg_previewSurface.as_ref(), &_arg_context);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#detectInteractionWithContext => {
      let _arg_context: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#detectInteractionWithContext(&_arg_context);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
          _aidl_reply.write(_aidl_return)?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#onContextChanged => {
      let _arg_context: crate::mangled::_7_android_8_hardware_10_biometrics_6_common_16_OperationContext = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#onContextChanged(&_arg_context);
      match &_aidl_return {
        Ok(_aidl_return) => {
          _aidl_reply.write(&binder::Status::from(binder::StatusCode::OK))?;
        }
        Err(_aidl_status) => _aidl_reply.write(_aidl_status)?
      }
      Ok(())
    }
    transactions::r#enrollWithOptions => {
      let _arg_options: crate::mangled::_7_android_8_hardware_10_biometrics_4_face_17_FaceEnrollOptions = _aidl_data.read()?;
      let _aidl_return = _aidl_service.r#enrollWithOptions(&_arg_options);
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
 pub use super::r#ISession as _7_android_8_hardware_10_biometrics_4_face_8_ISession;
}
