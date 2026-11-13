package com.android.server;

import com.android.server.locksettings.LockSettingsService;
import com.android.server.biometrics.BiometricService;
import com.android.server.biometrics.AuthService;
import com.android.server.biometrics.sensors.fingerprint.FingerprintService;
import java.lang.reflect.Field;
import java.util.ArrayList;

/** Authored adversarial graph; no OEM implementation or real service is loaded. */
public final class FamilyWorld {
    public static LockSettingsService lss, otherLss;
    public static LockSettingsService.Lifecycle life;
    public static StorageManagerService.Lifecycle storageLife;
    public static FingerprintService fp, otherFp;
    public static BiometricService bio, otherBio;
    public static AuthService auth, otherAuth;
    public static int listCalls;

    public static void init() throws Exception {
        World.init();
        lss = new LockSettingsService(World.s);
        otherLss = new LockSettingsService(World.s);
        life = new LockSettingsService.Lifecycle(lss);
        storageLife = new StorageManagerService.Lifecycle(World.s);
        fp = new FingerprintService(); otherFp = new FingerprintService();
        bio = new BiometricService(); otherBio = new BiometricService();
        auth = new AuthService(bio); otherAuth = new AuthService(otherBio);
        World.m.mServices.add(life); World.m.mServices.add(storageLife);
        World.m.mServices.add(fp); World.m.mServices.add(bio); World.m.mServices.add(auth);
        listCalls = 0;
    }

    public static Object get(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }

    private static void put(Object object, String name, Object value) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(object, value);
    }

    public static Object[] expected() throws Exception {
        return new Object[] {World.m.mServices, life, storageLife, fp, bio, auth, lss, World.s,
                lss.mStrongAuth, lss.mStrongAuthTracker, lss.mSpManager, get(lss,"mStorage"),
                lss.mContext, lss.mUserCreationAndRemovalLock, lss.mStorageManagerInternal,
                get(fp,"mServiceWrapper"), fp.mRegistry, get(bio,"mImpl"), get(auth,"mImpl")};
    }

    public static void change(String key) throws Exception {
        Object spm = get(lss,"mSpManager"), store = get(lss,"mStorage");
        if (key.equals("missing-lss")) World.m.mServices.remove(life);
        else if (key.equals("missing-sms")) World.m.mServices.remove(storageLife);
        else if (key.equals("missing-fp")) World.m.mServices.remove(fp);
        else if (key.equals("missing-bio")) World.m.mServices.remove(bio);
        else if (key.equals("missing-auth")) World.m.mServices.remove(auth);
        else if (key.equals("duplicate")) World.m.mServices.add(fp);
        else if (key.equals("null-entry")) World.m.mServices.add(null);
        else if (key.equals("list-replaced")) World.m.mServices = new ArrayList<SystemService>(World.m.mServices);
        else if (key.equals("list-subclass")) World.m.mServices = new TrappingList(World.m.mServices);
        else if (key.equals("list-linked")) World.m.mServices = new java.util.LinkedList<SystemService>(World.m.mServices);
        else if (key.equals("lss-null")) life.mLockSettingsService = null;
        else if (key.equals("lss-replaced")) life.mLockSettingsService = otherLss;
        else if (key.equals("sms-null")) storageLife.mStorageManagerService = null;
        else if (key.equals("strong")) put(lss,"mStrongAuth",otherLss.mStrongAuth);
        else if (key.equals("tracker")) put(lss,"mStrongAuthTracker",otherLss.mStrongAuthTracker);
        else if (key.equals("spm")) put(lss,"mSpManager",get(otherLss,"mSpManager"));
        else if (key.equals("store")) put(lss,"mStorage",get(otherLss,"mStorage"));
        else if (key.equals("context")) put(lss,"mContext",new android.content.Context());
        else if (key.equals("spm-context")) put(spm,"mContext",new android.content.Context());
        else if (key.equals("store-context")) put(store,"mContext",new android.content.Context());
        else if (key.equals("strong-context")) put(lss.mStrongAuth,"mContext",new android.content.Context());
        else if (key.equals("spm-store")) put(spm,"mStorage",get(otherLss,"mStorage"));
        else if (key.equals("marker-false")) lss.mThirdPartyAppsStarted = false;
        else if (key.equals("marker-created")) lss.mEarlyCreatedUsers = new android.util.SparseIntArray();
        else if (key.equals("marker-removed")) lss.mEarlyRemovedUsers = new android.util.SparseIntArray();
        else if (key.equals("lock")) put(lss,"mUserCreationAndRemovalLock",new Object());
        else if (key.equals("storage-interface")) put(lss,"mStorageManager",new android.os.storage.IStorageManager.Stub(){});
        else if (key.equals("lss-smi")) put(lss,"mStorageManagerInternal",World.t.mStorageManagerInternal);
        else if (key.equals("smi-parent")) lss.mStorageManagerInternal.this$0 = World.t;
        else if (key.equals("sms-internal")) World.s.mStorageManagerInternal = World.t.mStorageManagerInternal;
        else if (key.equals("fp-wrapper")) put(fp,"mServiceWrapper",get(otherFp,"mServiceWrapper"));
        else if (key.equals("fp-registry")) put(fp,"mRegistry",otherFp.mRegistry);
        else if (key.equals("fp-parent")) put(get(fp,"mServiceWrapper"),"this$0",otherFp);
        else if (key.equals("registry-wrapper")) put(fp.mRegistry,"mService",get(otherFp,"mServiceWrapper"));
        else if (key.equals("bio-wrapper")) put(bio,"mImpl",get(otherBio,"mImpl"));
        else if (key.equals("bio-parent")) put(get(bio,"mImpl"),"this$0",otherBio);
        else if (key.equals("auth-wrapper")) put(auth,"mImpl",get(otherAuth,"mImpl"));
        else if (key.equals("auth-parent")) put(get(auth,"mImpl"),"this$0",otherAuth);
        else if (key.equals("auth-biometric")) auth.mBiometricService = otherAuth.mBiometricService;
        else if (key.equals("auth-null")) auth.mBiometricService = null;
        else if (key.equals("cross-storage")) {
            // Graph A is internally coherent; registry still retains graph B.
            storageLife.mStorageManagerService = World.t;
            put(lss,"mStorageManager",World.t);
            put(lss,"mStorageManagerInternal",World.t.mStorageManagerInternal);
        } else if (key.equals("extra")) World.m.mServices.add(new Extra());
        else if (key.equals("max")) {
            Extra e = new Extra(); while(World.m.mServices.size()<1024) World.m.mServices.add(e);
        } else if (key.equals("over-max")) {
            Extra e = new Extra(); while(World.m.mServices.size()<1025) World.m.mServices.add(e);
        } else if (key.equals("phase")) World.m.mCurrentPhase = 999;
        else throw new AssertionError("unknown authored mutation");
    }

    public static final class Extra extends SystemService {}
    public static final class TrappingList extends ArrayList<SystemService> {
        public TrappingList(java.util.Collection<SystemService> source) {super(source);}
        @Override public SystemService get(int index) {listCalls++;throw new AssertionError("foreign list invoked");}
    }
}
