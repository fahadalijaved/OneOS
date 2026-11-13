package com.android.server;

import com.android.server.locksettings.LockSettingsInternal;
import com.android.server.locksettings.LockSettingsService;
import com.android.server.locksettings.LockSettingsService$LocalService;

/** Authored graph only: none of these modeled services is an OEM implementation. */
public final class LocalOwnerWorld {
    public static LockSettingsService$LocalService local;

    public static void init() throws Exception {
        FamilyWorld.init();
        local = new LockSettingsService$LocalService(FamilyWorld.lss);
        synchronized (LocalServices.modelMap()) {
            LocalServices.entries.put(LockSettingsInternal.class, local);
        }
    }

    public static Object[] expected() {
        return new Object[] {LocalServices.modelMap(), local, FamilyWorld.lss};
    }

    public static Object userLock() { return FamilyWorld.lss.mUserCreationAndRemovalLock; }

    public static void replaceLocal() {
        synchronized (LocalServices.modelMap()) {
            LocalServices.entries.put(LockSettingsInternal.class,
                    new LockSettingsService$LocalService(FamilyWorld.lss));
        }
    }

    public static void replaceParent() {
        synchronized (LocalServices.modelMap()) { local.this$0 = FamilyWorld.otherLss; }
    }

    public static void change(String kind) {
        synchronized (LocalServices.modelMap()) {
            if (kind.equals("missing")) LocalServices.entries.remove(LockSettingsInternal.class);
            else if (kind.equals("wrong-key")) {
                LocalServices.entries.remove(LockSettingsInternal.class);
                LocalServices.entries.put(String.class, local);
            } else if (kind.equals("wrong-class")) {
                LocalServices.entries.put(LockSettingsInternal.class, new Object());
            } else if (kind.equals("null-parent")) local.this$0 = null;
            else if (kind.equals("other-parent")) local.this$0 = FamilyWorld.otherLss;
            else if (kind.equals("same-parent-new-local")) replaceLocal();
            else throw new AssertionError("unknown authored local mutation");
        }
    }
}
