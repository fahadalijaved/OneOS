package com.android.server.locksettings;

import android.os.Binder;
import android.os.Process;
import android.os.RemoteException;
import com.android.internal.widget.ICheckCredentialProgressCallback;
import com.android.internal.widget.ILockSettings;
import com.android.internal.widget.LockscreenCredential;
import com.android.internal.widget.VerifyCredentialResponse;
import com.android.server.locksettings.GuestPinCallerFrame.PreClearObservation;
import java.util.function.Consumer;

/** Models a synchronous observation at the selected post-permission source edge. */
public final class StockCase10Fixture {
    private static final int PID = 77, UID = 10237, USER = 4;
    private static final int SELF_PID = 10, SELF_UID = 1000;
    private static final VerifyCredentialResponse RESPONSE = new VerifyCredentialResponse(37);
    private static final ICheckCredentialProgressCallback CALLBACK = () -> {
        throw new AssertionError("unexpected progress callback");
    };

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

    private static boolean legacy(LockSettingsService service, LockscreenCredential pin) {
        return GuestPinCallerFrame.matchesIncomingIdentity(service, pin, USER, CALLBACK, PID, UID);
    }

    private static int observe(LockSettingsService service, LockscreenCredential pin,
            Consumer<PreClearObservation> checks) {
        int[] calls = {0};
        Throwable[] failure = new Throwable[1];
        GuestPinCallerFrame.observeAfterPermission(service, pin, USER, CALLBACK, PID, UID, token -> {
            calls[0]++;
            try {
                checks.accept(token);
            } catch (Throwable problem) {
                failure[0] = problem;
            }
        });
        if (failure[0] != null) throw new AssertionError("authored observer assertion", failure[0]);
        return calls[0];
    }

    private static void original(LockSettingsService service, LockscreenCredential pin, int calls, int operations) {
        require(service.lastPin == pin && service.lastUser == USER && service.lastCallback == CALLBACK
                && service.incomingPid == PID && service.incomingUid == UID, "same original arguments and caller");
        require(service.checkCalls == calls && service.permissionChecks == calls
                && service.identityClears == operations && service.operationCalls == operations
                && service.identityRestores == operations && service.cleanupCalls == operations,
                "only the original owns permission, operation, restore and cleanup");
        require(Binder.peekCallingPid() == PID && Binder.peekCallingUid() == UID, "original incoming identity restored");
    }

    private static void restoredTail() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true);
        PreClearObservation[] held = new PreClearObservation[1];
        service.response = RESPONSE;
        service.beforeClear = () -> require(service.permissionChecks == 0 && service.identityClears == 0
                && held[0] == null && legacy(service, pin), "caller frame exists before permission but no observer ran");
        service.afterPermission = () -> {
            require(service.permissionChecks == 1 && service.identityClears == 0, "selected hook follows successful permission");
            require(observe(service, pin, token -> {
                held[0] = token;
                require(token.isCurrent() && token.isCurrent(), "token is current in its exact callback");
            }) == 1 && !held[0].isCurrent(), "callback return revokes token before original clear");
            require(observe(service, pin, token -> { }) == 0, "same frame cannot open a second observation");
        };
        service.afterClear = () -> require(!held[0].isCurrent() && Binder.peekCallingPid() == SELF_PID,
                "original clear sees no current scoped token");
        service.duringCleanup = () -> require(legacy(service, pin) && !held[0].isCurrent(),
                "restored tuple may match legacy check but cannot revive callback scope");
        require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == RESPONSE && !held[0].isCurrent(), "original exact return");
        original(service, pin, 1, 1);
        require(pin.zeroizeCalls() == 1, "original parcel cleanup only");
    }

    private static void deniedAndDirect() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService denied = new LockSettingsService();
        LockscreenCredential parcel = new LockscreenCredential(true);
        SecurityException originalFailure = new SecurityException("authored permission refusal");
        denied.permissionFailure = originalFailure;
        denied.afterPermission = () -> { throw new AssertionError("denied permission reached post-permission hook"); };
        throwsExact(originalFailure, () -> denied.dispatchDecodedCase10(parcel, USER, CALLBACK));
        original(denied, parcel, 1, 0);
        require(parcel.zeroizeCalls() == 0 && !legacy(denied, parcel), "denial leaves no scope or original cleanup");

        LockSettingsService direct = new LockSettingsService();
        LockscreenCredential borrowed = new LockscreenCredential(true, false);
        direct.afterPermission = () -> require(observe(direct, borrowed, token -> { }) == 0,
                "same-tuple direct Java path has no decoded frame");
        require(direct.checkCredential(borrowed, USER, CALLBACK) == null, "direct original null preserved");
        original(direct, borrowed, 1, 1);
        require(borrowed.zeroizeCalls() == 0, "nonparcel original treatment preserved");
    }

    private static void sameTupleAcrossRequests() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        // Deliberately reuse the same modeled object without parcel cleanup changing it.
        LockscreenCredential pin = new LockscreenCredential(true, false);
        PreClearObservation[] held = new PreClearObservation[2];
        service.response = RESPONSE;
        for (int n = 0; n < held.length; n++) {
            int slot = n;
            service.afterPermission = () -> require(observe(service, pin, token -> {
                held[slot] = token;
                require(token.isCurrent(), "fresh exact request token current");
                if (slot == 1) require(held[0] != token && !held[0].isCurrent(),
                        "identical tuple cannot revive prior request token");
            }) == 1, "one observation per actual request");
            require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == RESPONSE && !held[slot].isCurrent(),
                    "each callback scope retires by return");
        }
        original(service, pin, 2, 2);
        require(pin.zeroizeCalls() == 0 && !held[0].isCurrent() && !held[1].isCurrent(), "no completed token remains live");
    }

    private static void wrongThread() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true);
        service.afterPermission = () -> require(observe(service, pin, token -> {
            boolean[] foreignCurrent = {true};
            Thread stranger = new Thread(() -> {
                Binder.set(PID, UID);
                foreignCurrent[0] = token.isCurrent();
            }, "authored-foreign-observer");
            stranger.setDaemon(true);
            stranger.start();
            try {
                stranger.join(2_000);
            } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
                throw new AssertionError(failure);
            }
            require(!stranger.isAlive() && !foreignCurrent[0] && token.isCurrent(),
                    "same IDs on foreign thread refuse without poisoning owner");
        }) == 1, "one scoped callback");
        require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == null, "wrong-thread probe preserves original");
        original(service, pin, 1, 1);
    }

    private static void nestedSelected() throws Exception {
        Binder.set(PID, UID);
        LockSettingsService service = new LockSettingsService();
        LockscreenCredential pin = new LockscreenCredential(true, false);
        service.response = RESPONSE;
        service.afterPermission = () -> require(observe(service, pin, token -> {
            require(token.isCurrent(), "outer callback scope current before selected nesting");
            Runnable outer = service.afterPermission;
            service.afterPermission = () -> require(observe(service, pin, inner -> { }) == 0,
                    "nested same-tuple entry cannot mint a token");
            try {
                require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == RESPONSE, "exact inner original return");
            } catch (RemoteException unexpected) {
                throw new AssertionError(unexpected);
            } finally {
                service.afterPermission = outer;
            }
            require(!token.isCurrent() && !legacy(service, pin), "nested selected entry poisons exact outer scope");
        }) == 1, "one outer callback");
        require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == RESPONSE, "exact outer original return");
        original(service, pin, 2, 2);
    }

    private static void driftAndReadFailure() throws Exception {
        for (int example = 0; example < 3; example++) {
            int mode = example;
            Binder.set(PID, UID);
            LockSettingsService service = new LockSettingsService();
            LockscreenCredential pin = new LockscreenCredential(true);
            if (mode == 2) Binder.fail();
            service.afterPermission = () -> require(observe(service, pin, token -> {
                require(mode != 2 && token.isCurrent(), "only successful capture enters callback");
                if (mode == 0) Binder.set(PID + 1, UID);
                else Binder.fail();
                require(!token.isCurrent(), "observed mismatch or getter fault refuses token");
                Binder.set(PID, UID);
                require(!token.isCurrent(), "restoring scalars cannot clear observed uncertainty");
            }) == (mode == 2 ? 0 : 1), "failed initial capture cannot run observer");
            require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == null, "uncertain read preserves original null");
            original(service, pin, 1, 1);
            require(pin.zeroizeCalls() == 1, "uncertain observation leaves original cleanup intact");
        }
    }

    private static void observerFailure() throws Exception {
        for (int example = 0; example < 2; example++) {
            Binder.set(PID, UID);
            LockSettingsService service = new LockSettingsService();
            LockscreenCredential pin = new LockscreenCredential(true);
            PreClearObservation[] held = new PreClearObservation[1];
            int[] callbacks = {0};
            service.response = RESPONSE;
            Error observerProblem = new AssertionError("authored passive observer failure");
            service.afterPermission = () -> GuestPinCallerFrame.observeAfterPermission(service, pin, USER,
                    CALLBACK, PID, UID, token -> {
                        held[0] = token;
                        callbacks[0]++;
                        throw observerProblem;
                    });
            if (example == 0) {
                require(service.dispatchDecodedCase10(pin, USER, CALLBACK) == RESPONSE, "observer failure preserves exact original result");
            } else {
                Error originalProblem = new AssertionError("authored original operation failure");
                service.operationFailure = originalProblem;
                throwsExact(originalProblem, () -> service.dispatchDecodedCase10(pin, USER, CALLBACK));
            }
            require(callbacks[0] == 1 && held[0] != null && !held[0].isCurrent() && pin.zeroizeCalls() == 1,
                    "throwing observer is contained, revoked and never retries");
            original(service, pin, 1, 1);
        }
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 0, "no model arguments expected");
        ClassLoader services = LockSettingsService.class.getClassLoader();
        require(services == GuestPinCallerFrame.class.getClassLoader() && services == StockCase10Fixture.class.getClassLoader()
                && services != ILockSettings.Stub.class.getClassLoader(), "actual helper belongs to child services realm");
        require(PreClearObservation.class.getDeclaredFields().length == 0, "scoped token carries no fields");
        Process.set(SELF_PID, SELF_UID);
        restoredTail(); deniedAndDirect(); sameTupleAcrossRequests(); wrongThread();
        nestedSelected(); driftAndReadFailure(); observerFailure();
        System.out.println("PASS_AUTHORED_GUEST_PIN_PRECLEAR_OBSERVATION_MODEL 7 cases");
    }
}
