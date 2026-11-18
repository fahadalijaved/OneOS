package com.android.server;

import android.os.Binder;
import model.HostPinProbe;

/** Public authored graph controls only. No private SDK data/reflection or real auth. */
public final class HostPinOperationWorld {
    public static void init(int user, int serial, int state) throws Exception {
        PinBindingWorld.init(user, serial, state);
        Binder.modelReset(); HostPinProbe.reset();
    }
    public static void enter(int user, int flags) {
        if (Thread.holdsLock(World.p.mUserManager.mUsersLock)
                || Thread.holdsLock(World.a.mUserController.mLock)
                || Thread.holdsLock(LocalServices.modelMap()) || Thread.holdsLock(FamilyWorld.lss))
            throw new AssertionError("authored outer original monitor retained");
        HostPinProbe.calls.incrementAndGet();
        HostPinProbe.lastUser = user; HostPinProbe.lastFlags = flags;
        HostPinProbe.callerIdentity = Binder.modelIdentity();
        HostPinProbe.originalThread = Thread.currentThread();
    }
    public static void response(com.android.internal.widget.VerifyCredentialResponse value) {
        HostPinProbe.response = value;
    }
    public static void fail(Throwable failure) { HostPinProbe.failure = failure; }
    public static void inside(Runnable hook) { HostPinProbe.inside = hook; }
    public static void anchor(Runnable hook) { LocalServices.modelObserver = hook; }
    public static void state(int value) throws Exception { PinBindingWorld.change("state:" + value); }
    public static void identityFailure(String which, Throwable failure) {
        if (which.equals("clear")) Binder.clearFailure = failure;
        else if (which.equals("restore")) Binder.restoreFailure = failure;
        else throw new AssertionError("authored identity fault name");
    }
    public static long[] observations() {
        return new long[] {HostPinProbe.calls.get(), HostPinProbe.pinQueries.get(),
            HostPinProbe.pinInitializations.get(), HostPinProbe.responseInitializations.get(),
            HostPinProbe.pinConstructions.get(), Binder.clears, Binder.restores,
            HostPinProbe.lastUser, HostPinProbe.lastFlags, HostPinProbe.callerIdentity,
            model.Forbidden.constructions, model.Forbidden.calls};
    }
    public static Thread originalThread() { return HostPinProbe.originalThread; }
    public static long identity() { return Binder.modelIdentity(); }
}
