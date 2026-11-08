package com.android.server;

import android.content.pm.UserInfo;
import android.os.UserManager;
import android.util.SparseArray;
import android.util.SparseBooleanArray;
import com.android.server.am.UserController;
import com.android.server.am.UserState;
import java.lang.reflect.Field;
import java.util.ArrayDeque;

/** Authored synthetic object graph only; no PIN bytes, verifier or OEM code. */
public final class PinBindingWorld {
    public static int id;
    public static Object data;
    public static UserInfo info;
    public static UserState state;
    public static int traps;

    public static void init(int user, int serial, int status) throws Exception {
        FamilyWorld.init();
        id = user;
        data = World.p.mUserManager.modelInstall(user, serial);
        info = World.p.mUserManager.modelInfo(user);
        state = new UserState(user, status);
        World.a.mUserController.mCurrentUserId = user;
        World.a.mUserController.mStartedUsers.put(user, state);
        World.a.mUserController.mStartedUsers.expectedLock = World.a.mUserController.mLock;
        World.a.mUserController.mStartedUsers.forbiddenLock = World.p.mUserManager.mUsersLock;
        World.p.mUserManager.mUsers.expectedLock = World.p.mUserManager.mUsersLock;
        World.p.mUserManager.mUsers.forbiddenLock = World.a.mUserController.mLock;
        World.p.mUserManager.mRemovingUserIds.expectedLock = World.p.mUserManager.mUsersLock;
        World.p.mUserManager.mRemovingUserIds.forbiddenLock = World.a.mUserController.mLock;
        traps = 0;
    }

    public static Object[] expected() {
        return new Object[] {FamilyWorld.lss, World.p.mUserManager, World.a.mUserController,
                data, info, state, state.mHandle};
    }

    public static Object get(Object owner, String name) throws Exception {
        Field field = owner.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(owner);
    }

    private static void put(Object owner, String name, Object value) throws Exception {
        Field field = owner.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(owner, value);
    }

    public static Object[] locks() {return new Object[] {
            World.a.mUserController.mLock, World.p.mUserManager.mUsersLock};}

    public static void change(String key) throws Exception {
        UserController c = World.a.mUserController;
        com.android.server.pm.UserManagerService u = World.p.mUserManager;
        if (key.equals("target")) c.mTargetUserId = id + 1;
        else if (key.equals("current")) c.mCurrentUserId = id + 1;
        else if (key.equals("logout")) c.mPendingLogoutTargetUser = true;
        else if (key.equals("pending")) c.mPendingTargetUserIds.add(id + 1);
        else if (key.equals("switching")) state.switching = true;
        else if (key.startsWith("state:")) state.state = Integer.parseInt(key.substring(6));
        else if (key.equals("state-record")) c.mStartedUsers.put(id, new UserState(id, state.state));
        else if (key.equals("handle")) put(state, "mHandle", new android.os.UserHandle(id + 1));
        else if (key.equals("missing-state")) c.mStartedUsers.remove(id);
        else if (key.equals("missing-user")) u.mUsers.remove(id);
        else if (key.equals("data-record")) u.modelInstall(id, info.serialNumber);
        else if (key.equals("info-record")) put(data, "info", new UserInfo(id, info.serialNumber));
        else if (key.equals("info-id")) info.id = id + 1;
        else if (key.equals("serial")) info.serialNumber++;
        else if (key.equals("negative-serial")) info.serialNumber = -1;
        else if (key.equals("non-full")) info.flags = 0;
        else if (key.equals("profile")) info.flags |= 4096;
        else if (key.equals("disabled")) info.flags |= 64;
        else if (key.equals("partial")) info.partial = true;
        else if (key.equals("pre-created")) info.preCreated = true;
        else if (key.equals("removing")) u.mRemovingUserIds.put(id, true);
        else if (key.equals("attributes")) put(info, "attributes", 7);
        else if (key.equals("group")) info.profileGroupId = id;
        else if (key.equals("type")) info.userType = "synthetic.changed";
        else if (key.equals("null-type")) info.userType = null;
        else if (key.equals("user-manager")) put(FamilyWorld.lss, "mUserManager", new UserManager(u));
        else if (key.equals("different-ums")) put(FamilyWorld.lss.mUserManager, "mService", World.q.mUserManager);
        else if (key.equals("proxy-ums")) put(FamilyWorld.lss.mUserManager, "mService", new android.os.IUserManager(){});
        else if (key.equals("controller-lock")) put(c, "mLock", new Object());
        else if (key.equals("users-lock")) put(u, "mUsersLock", new Object());
        else if (key.equals("started-container")) put(c, "mStartedUsers", new SparseArray<UserState>());
        else if (key.equals("users-container")) put(u, "mUsers", new SparseArray<Object>());
        else if (key.equals("removing-container")) put(u, "mRemovingUserIds", new SparseBooleanArray());
        else if (key.equals("queue-container")) put(c, "mPendingTargetUserIds", new ArrayDeque<Integer>());
        else if (key.equals("trap-started")) put(c, "mStartedUsers", new TrapArray());
        else if (key.equals("trap-users")) put(u, "mUsers", new TrapArray());
        else if (key.equals("trap-removing")) put(u, "mRemovingUserIds", new TrapBooleans());
        else if (key.equals("trap-queue")) put(c, "mPendingTargetUserIds", new TrapQueue());
        else throw new AssertionError("unknown synthetic mutation");
    }

    public static class TrapArray extends SparseArray<Object> {
        @Override public Object get(int id) {traps++;throw new AssertionError("foreign get invoked");}
    }
    public static class TrapBooleans extends SparseBooleanArray {
        @Override public boolean get(int id) {traps++;throw new AssertionError("foreign get invoked");}
    }
    public static class TrapQueue extends ArrayDeque<Integer> {
        @Override public boolean isEmpty() {traps++;throw new AssertionError("foreign queue invoked");}
    }
}
