package com.android.server.locksettings; public class LockSettingsService extends com.android.internal.widget.ILockSettings.Stub {
/* Authored check entry: genuine-model progress precedes final/error; no credential algorithm. */
public final com.android.internal.widget.VerifyCredentialResponse checkCredential(
        com.android.internal.widget.LockscreenCredential pin, int user,
        com.android.internal.widget.ICheckCredentialProgressCallback callback) throws android.os.RemoteException {
    model.CheckProbe.original(pin,user,callback);
    com.android.server.HostPinOperationWorld.enter(user,0);
    long previous=android.os.Binder.clearCallingIdentity();
    try {
        Runnable hook=model.HostPinProbe.inside;if(hook!=null)hook.run();
        if(callback!=null)callback.onCredentialVerified();
        model.CheckProbe.finalReached=true;
        android.os.Binder.modelThrow(model.HostPinProbe.failure);
        return model.HostPinProbe.response;
    } finally {
        android.os.Binder.restoreCallingIdentity(previous);
        pin.modelZeroizeIfParcel();
    }
}

/* Authored public-entry envelope model only, no original credential algorithm. */
public final com.android.internal.widget.VerifyCredentialResponse verifyCredential(
        com.android.internal.widget.LockscreenCredential pin, int user, int flags) {
    com.android.server.HostPinOperationWorld.enter(user, flags);
    long previous = android.os.Binder.clearCallingIdentity();
    try {
        Runnable hook = model.HostPinProbe.inside;
        if (hook != null) hook.run();
        android.os.Binder.modelThrow(model.HostPinProbe.failure);
        return model.HostPinProbe.response;
    } finally {
        android.os.Binder.restoreCallingIdentity(previous);
        pin.modelZeroizeIfParcel();
    }
}

 public final android.os.UserManager mUserManager; public final LockSettingsStrongAuth mStrongAuth; public final SynchronizedStrongAuthTracker mStrongAuthTracker=new SynchronizedStrongAuthTracker(); public final SyntheticPasswordManager mSpManager; protected final LockSettingsStorage mStorage; public final android.os.storage.IStorageManager mStorageManager; public final com.android.server.StorageManagerService.StorageManagerInternalImpl mStorageManagerInternal; public final android.content.Context mContext; public final Object mUserCreationAndRemovalLock=new Object(); public boolean mThirdPartyAppsStarted=true; public android.util.SparseIntArray mEarlyCreatedUsers,mEarlyRemovedUsers; public LockSettingsService(com.android.server.StorageManagerService s){model.Forbidden.constructions++;mUserManager=new android.os.UserManager(com.android.server.World.p.mUserManager);mContext=new android.content.Context();mStorage=new LockSettingsStorage(mContext);mStrongAuth=new LockSettingsStrongAuth(mContext);mSpManager=new SyntheticPasswordManager(mContext,mStorage);mStorageManager=s;mStorageManagerInternal=s.mStorageManagerInternal;} public static class SynchronizedStrongAuthTracker {} public static final class Lifecycle extends com.android.server.SystemService { public LockSettingsService mLockSettingsService; public Lifecycle(LockSettingsService s){mLockSettingsService=s;} } public Object getGateKeeperService(){model.Forbidden.calls++;throw new AssertionError("lazy getter forbidden");} } class SyntheticPasswordManager { public android.content.Context mContext; public LockSettingsStorage mStorage; SyntheticPasswordManager(android.content.Context c,LockSettingsStorage s){mContext=c;mStorage=s;} public Object getWeaverService(){model.Forbidden.calls++;throw new AssertionError("weaver forbidden");} }

