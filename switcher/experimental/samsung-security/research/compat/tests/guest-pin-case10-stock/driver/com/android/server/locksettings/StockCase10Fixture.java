package com.android.server.locksettings;

import android.os.Binder;
import android.os.Process;
import android.os.RemoteException;
import com.android.internal.widget.ICheckCredentialProgressCallback;
import com.android.internal.widget.ILockSettings;
import com.android.internal.widget.LockscreenCredential;
import com.android.internal.widget.TypedCredentialCall;
import com.android.internal.widget.VerifyCredentialResponse;

/** Authored model of the selected decoded case-10 call and unchanged caller frame. */
public final class StockCase10Fixture {
    private static final int PID = 77, UID = 10237, USER = 4;
    private static final int SELF_PID = 10, SELF_UID = 1000;
    private static final VerifyCredentialResponse RESPONSE = new VerifyCredentialResponse(37);

    private static void require(boolean condition, String detail) {
        if (!condition) throw new AssertionError(detail);
    }

    private interface Call { void invoke() throws Throwable; }

    private static void throwsExact(Throwable expected, Call call) {
        try {
            call.invoke();
        } catch (Throwable thrown) {
            require(thrown == expected && thrown.getSuppressed().length == 0, "exact original Throwable");
            return;
        }
        throw new AssertionError("original Throwable lost");
    }

    private static final class Callback implements ICheckCredentialProgressCallback {
        int calls;
        @Override public void onCredentialVerified() { calls++; }
    }

    private static final class Ordinary extends ILockSettings.Stub {
        int calls, user, pid, uid;
        LockscreenCredential pin;
        ICheckCredentialProgressCallback callback;
        VerifyCredentialResponse response;
        RemoteException failure;

        @Override public VerifyCredentialResponse checkCredential(LockscreenCredential actualPin, int actualUser,
                ICheckCredentialProgressCallback actualCallback) throws RemoteException {
            calls++;
            pin = actualPin;
            user = actualUser;
            callback = actualCallback;
            pid = Binder.peekCallingPid();
            uid = Binder.peekCallingUid();
            if (failure != null) throw failure;
            return response;
        }
    }

    private static boolean matches(LockSettingsService service, LockscreenCredential pin, int user,
            ICheckCredentialProgressCallback callback, int pid, int uid) {
        return GuestPinCallerFrame.matchesIncomingIdentity(service, pin, user, callback, pid, uid);
    }

    private static void counters(LockSettingsService service, int operations) {
        require(service.checkCalls == 1 && service.permissionChecks == 1
                && service.identityClears == operations && service.operationCalls == operations
                && service.identityRestores == operations && service.cleanupCalls == operations,
                "only one original call owns permission, identity, operation and cleanup");
    }

    private static void sameArgs(LockSettingsService service, LockscreenCredential pin, int user,
            ICheckCredentialProgressCallback callback, int pid, int uid) {
        require(service.lastPin == pin && service.lastUser == user && service.lastCallback == callback
                && service.incomingPid == pid && service.incomingUid == uid,
                "original service sees exact receiver arguments and incoming identity");
    }

    private static void ordinaryDefault() throws Exception {
        Binder.set(PID, UID);
        int clears = Binder.clearCalls(), restores = Binder.restoreCalls();
        Ordinary service = new Ordinary();
        LockscreenCredential pin = new LockscreenCredential(true);
        Callback callback = new Callback();
        service.response = RESPONSE;
        require(service.dispatchDecodedCase10(new TypedCredentialCall(pin, USER, callback)) == RESPONSE
                && service.calls == 1 && service.pin == pin && service.user == USER && service.callback == callback
                && service.pid == PID && service.uid == UID, "default slot forwards same arguments and return once");

        service.response = null;
        require(service.dispatchDecodedCase10(null, -1, null) == null && service.calls == 2
                && service.pin == null && service.user == -1 && service.callback == null, "default slot preserves nulls");
        RemoteException exact = new RemoteException("authored ordinary exception");
        service.failure = exact;
        throwsExact(exact, () -> service.dispatchDecodedCase10(pin, USER, callback));
        require(service.calls == 3, "default slot calls one throwing original");
        try {
            service.dispatchDecodedCase10(new TypedCredentialCall(pin, USER, callback, true));
            throw new AssertionError("trailing payload reached case-10 slot");
        } catch (IllegalArgumentException expected) {
            require(service.calls == 3, "modeled trailing-data refusal precedes virtual call");
        }
        require(pin.zeroizeCalls() == 0 && callback.calls == 0 && Binder.clearCalls() == clears
                && Binder.restoreCalls() == restores, "default slot performs no original cleanup or identity changes itself");
    }

    private static void exactFrame() throws Exception {
        Binder.set(PID, UID);
        int clears = Binder.clearCalls(), restores = Binder.restoreCalls();
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true);
        Callback callback = new Callback();
        service.response = RESPONSE;
        service.beforeClear = () -> {
            require(service.permissionChecks == 0 && Binder.clearCalls() == clears, "observation before permission and clear");
            require(matches(service, pin, USER, callback, PID, UID), "same receiver has the original incoming frame");
            require(!matches(new LockSettingsService(), pin, USER, callback, PID, UID), "wrong service cannot match");
            require(!matches(service, new LockscreenCredential(true), USER, callback, PID, UID), "wrong PIN cannot match");
            require(!matches(service, pin, USER + 1, callback, PID, UID), "wrong user cannot match");
            require(!matches(service, pin, USER, new Callback(), PID, UID), "wrong callback cannot match");
        };
        service.afterClear = () -> require(Binder.peekCallingPid() == SELF_PID && Binder.peekCallingUid() == SELF_UID
                && !matches(service, pin, USER, callback, PID, UID), "post-clear original cannot corroborate incoming frame");
        service.duringCleanup = () -> require(Binder.peekCallingPid() == PID && Binder.peekCallingUid() == UID
                && pin.zeroizeCalls() == 0, "original restores before parcel cleanup");
        require(service.dispatchDecodedCase10(pin, USER, callback) == RESPONSE, "original response reference");
        counters(service, 1);
        sameArgs(service, pin, USER, callback, PID, UID);
        require(service.operationPid == SELF_PID && service.operationUid == SELF_UID && pin.zeroizeCalls() == 1
                && callback.calls == 0 && Binder.clearCalls() == clears + 1 && Binder.restoreCalls() == restores + 1,
                "original operation owns exactly one identity clear, restore and cleanup");
        require(!matches(service, pin, USER, callback, PID, UID), "returned call leaves no active frame");
    }

    private static void unavailableObservation() throws Exception {
        for (int example = 0; example < 4; example++) {
            int pid = example == 0 ? SELF_PID : PID;
            int user = example == 1 ? -1 : USER;
            LockscreenCredential pin = example == 2 ? null : new LockscreenCredential(true);
            Binder.set(pid, UID);
            if (example == 3) Binder.fail();
            LockSettingsService service = new LockSettingsService();
            service.beforeClear = () -> require(!matches(service, pin, user, null, pid, UID), "observation unavailable");
            require(service.dispatchDecodedCase10(pin, user, null) == null, "original null survives unavailable observation");
            counters(service, 1);
            sameArgs(service, pin, user, null, pid, UID);
            require(pin == null || pin.zeroizeCalls() == 1, "original retains its nullable cleanup semantics");
        }
    }

    private static void deniedPermission() {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true);
        Callback callback = new Callback();
        SecurityException denied = new SecurityException("authored original permission denial");
        service.permissionFailure = denied;
        service.beforeClear = () -> require(matches(service, pin, USER, callback, PID, UID), "frame before denied original permission");
        throwsExact(denied, () -> service.dispatchDecodedCase10(pin, USER, callback));
        counters(service, 0);
        sameArgs(service, pin, USER, callback, PID, UID);
        require(pin.zeroizeCalls() == 0 && callback.calls == 0
                && !matches(service, pin, USER, callback, PID, UID), "permission failure stays before identity and cleanup");
    }

    private static void throwingOperation() {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true);
        Error operation = new AssertionError("authored original operation failure");
        service.operationFailure = operation;
        throwsExact(operation, () -> service.dispatchDecodedCase10(pin, USER, null));
        counters(service, 1);
        require(pin.zeroizeCalls() == 1 && Binder.peekCallingPid() == PID && Binder.peekCallingUid() == UID
                && !matches(service, pin, USER, null, PID, UID), "throwing original performs restore/cleanup before exact failure escapes");
    }

    private static void nestedSelected() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService outer = new LockSettingsService(), inner = new LockSettingsService();
        LockscreenCredential outerPin = new LockscreenCredential(true), innerPin = new LockscreenCredential(true);
        Callback callback = new Callback();
        outer.response = RESPONSE;
        inner.beforeClear = () -> require(!matches(inner, innerPin, USER + 1, null, PID, UID), "nested observation is unavailable");
        outer.beforeClear = () -> {
            require(matches(outer, outerPin, USER, callback, PID, UID), "outer observation before reentry");
            try {
                require(inner.dispatchDecodedCase10(innerPin, USER + 1, null) == null, "nested original null return");
            } catch (RemoteException unexpected) {
                throw new AssertionError(unexpected);
            }
            require(Binder.peekCallingPid() == PID && Binder.peekCallingUid() == UID
                    && !matches(outer, outerPin, USER, callback, PID, UID), "nested original restores caller but cannot revive outer observation");
        };
        require(outer.dispatchDecodedCase10(outerPin, USER, callback) == RESPONSE, "outer original result remains exact");
        counters(outer, 1);
        counters(inner, 1);
        sameArgs(outer, outerPin, USER, callback, PID, UID);
        sameArgs(inner, innerPin, USER + 1, null, PID, UID);
        require(outerPin.zeroizeCalls() == 1 && innerPin.zeroizeCalls() == 1 && callback.calls == 0,
                "each actual original owns its own cleanup only");
    }

    private static void directLocal() throws Exception {
        // Even remote-shaped numbers do not make the ordinary Java path a decoded Binder entry.
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true, false);
        Callback callback = new Callback();
        service.response = RESPONSE;
        service.beforeClear = () -> require(!matches(service, pin, USER, callback, PID, UID), "direct call has no special frame");
        require(service.checkCredential(pin, USER, callback) == RESPONSE, "direct original result");
        counters(service, 1);
        sameArgs(service, pin, USER, callback, PID, UID);
        require(pin.zeroizeCalls() == 0 && callback.calls == 0, "borrowed local credential keeps its original treatment");
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 0, "no model arguments expected");
        ClassLoader services = LockSettingsService.class.getClassLoader();
        require(services == GuestPinCallerFrame.class.getClassLoader() && services == StockCase10Fixture.class.getClassLoader()
                && services != ILockSettings.Stub.class.getClassLoader(), "actual helper shares child services realm only");
        Process.set(SELF_PID, SELF_UID);
        ordinaryDefault(); exactFrame(); unavailableObservation(); deniedPermission();
        throwingOperation(); nestedSelected(); directLocal();
        System.out.println("PASS_AUTHORED_GUEST_PIN_CASE10_STOCK_MODEL 7 cases");
    }
}
