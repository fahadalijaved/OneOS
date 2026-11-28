package com.android.server.locksettings;

import android.os.Binder;
import android.os.Process;
import com.android.internal.widget.ICheckCredentialProgressCallback;
import com.android.internal.widget.LockscreenCredential;
import com.android.internal.widget.VerifyCredentialResponse;

/** Pre-clear observation for the selected original Binder ingress. */
final class GuestPinCallerFrame {
    private static final ThreadLocal<Frame> CURRENT = new ThreadLocal<>();

    private GuestPinCallerFrame() { }

    // Only a separately reviewed case-10 source bridge can select this entry.
    static VerifyCredentialResponse invokeOriginal(LockSettingsService actualService,
            LockscreenCredential parcelPin, int requestedUser,
            ICheckCredentialProgressCallback originalCallback) {
        Frame owned = null;
        try {
            Frame active = CURRENT.get();
            if (active != null) {
                // A nested source entry cannot replace the previous observation.
                active.unavailable = true;
            } else {
                owned = new Frame(actualService, parcelPin, requestedUser, originalCallback);
                CURRENT.set(owned);
                int pid = Binder.getCallingPid();
                int uid = Binder.getCallingUid();
                if (actualService == null || parcelPin == null || requestedUser < 0
                        || pid <= 0 || uid < 0 || pid == Process.myPid()) {
                    owned.unavailable = true;
                } else {
                    owned.callerPid = pid;
                    owned.callerUid = uid;
                }
            }
        } catch (Throwable observationFailure) {
            if (owned != null) owned.unavailable = true;
        }
        try {
            // Original permission, identity, operation, result and cleanup are its own.
            return actualService.checkCredential(parcelPin, requestedUser, originalCallback);
        } finally {
            if (owned != null) {
                // Revoke first, including when ThreadLocal cleanup itself fails.
                owned.unavailable = true;
                owned.service = null;
                owned.pin = null;
                owned.callback = null;
                try {
                    CURRENT.remove();
                } catch (Throwable ignored) {
                    // An inert record must not mask an original failure.
                }
            }
        }
    }

    /**
     * Corroborates the active Java frame against an independently obtained caller.
     * The source consumer must run before the original identity clear. A matching
     * snapshot does not establish caller provenance, a physical subject or a lease.
     */
    static boolean matchesIncomingIdentity(LockSettingsService actualService,
            LockscreenCredential parcelPin, int requestedUser,
            ICheckCredentialProgressCallback originalCallback, int expectedPid, int expectedUid) {
        Frame frame = null;
        try {
            frame = CURRENT.get();
            if (frame == null || frame.unavailable || frame.callerPid <= 0
                    || frame.service != actualService || frame.pin != parcelPin
                    || frame.callback != originalCallback || frame.user != requestedUser
                    || frame.callerPid != expectedPid || frame.callerUid != expectedUid) {
                return false;
            }
            boolean matches = Binder.getCallingPid() == expectedPid
                    && Binder.getCallingUid() == expectedUid;
            if (!matches) frame.unavailable = true;
            return CURRENT.get() == frame && !frame.unavailable;
        } catch (Throwable observationFailure) {
            if (frame != null) frame.unavailable = true;
            return false;
        }
    }

    private static final class Frame {
        LockSettingsService service;
        LockscreenCredential pin;
        final int user;
        ICheckCredentialProgressCallback callback;
        int callerPid;
        int callerUid;
        boolean unavailable;

        Frame(LockSettingsService service, LockscreenCredential pin, int user,
                ICheckCredentialProgressCallback callback) {
            this.service = service;
            this.pin = pin;
            this.user = user;
            this.callback = callback;
        }
    }
}
