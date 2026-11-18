package com.fahadali.oneos.core.root;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;

/** App-owned closed-root association only. No host authority or guest operation. */
public final class RetainedRootHostService extends Service {
    private static final Object STARTUP_LOCK = new Object();
    // A tombstone for this actual app Class/process lifetime. Never reset on
    // service destruction: a spawning failure need not mean that no child exists.
    private static Startup startup;
    private final Broker broker = new Broker(this);
    private volatile boolean destroyed;

    @Override public IBinder onBind(Intent intent) {
        return broker; // Binding alone performs no root/session operation.
    }

    @Override public void onDestroy() {
        destroyed = true;
        Startup retained;
        synchronized (STARTUP_LOCK) { retained = startup; }
        try {
            if (retained != null && retained.service == this) retained.retire();
        } finally { super.onDestroy(); }
    }

    private void begin(IBinder callback, String sha256, long bytes) {
        if (callback == null || !validHash(sha256) || bytes < 1 || bytes > 2097152) {
            throw new IllegalArgumentException("Fixed root build and callback required");
        }
        Startup created = new Startup(this, callback, sha256, bytes);
        synchronized (STARTUP_LOCK) {
            if (destroyed || startup != null) {
                throw new IllegalStateException("Root startup already owned or service retired");
            }
            startup = created; // Before linkToDeath, Thread.start or begin.
        }
        created.start();
    }

    private static boolean validHash(String value) {
        if (value == null || value.length() != 64) return false;
        for (int n = 0; n < value.length(); n++) {
            char c = value.charAt(n);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
        }
        return true;
    }

    private static void requireCall(int flags, Parcel reply) {
        if (Binder.getCallingUid() != 1000) throw new SecurityException("System caller required");
        if (flags != 0 || reply == null) throw new IllegalArgumentException("Synchronous call required");
    }

    private static void requireVersion(Parcel data, String token) {
        data.enforceInterface(token);
        if (data.readInt() != ClosedRootLinkProtocol.VERSION) {
            throw new IllegalArgumentException("Closed root protocol version mismatch");
        }
    }

    private static final class Broker extends Binder {
        private final RetainedRootHostService service;
        Broker(RetainedRootHostService actual) {
            service = actual;
            attachInterface(null, ClosedRootLinkProtocol.BROKER);
        }
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code != ClosedRootLinkProtocol.BEGIN) return super.onTransact(code, data, reply, flags);
            requireCall(flags, reply);
            requireVersion(data, ClosedRootLinkProtocol.BROKER);
            IBinder callback = data.readStrongBinder();
            String sha256 = data.readString();
            long bytes = data.readLong();
            data.enforceNoDataAvail();
            service.begin(callback, sha256, bytes);
            reply.writeNoException();
            reply.writeInt(ClosedRootLinkProtocol.QUEUED); // Requested, never ready.
            return true;
        }
    }

    private static final class Startup implements Runnable {
        final RetainedRootHostService service;
        private final Object lock = new Object();
        private final IBinder callback;
        private final String sha256;
        private final long bytes;
        private final IBinder.DeathRecipient death;
        private Thread worker;
        private RetainedRootSession.Attempt attempt;
        private Control control;
        private boolean deathLinkAttempted, deathLinked, workerStartAttempted;
        private boolean beginAdmitted, workerFinished, retired;
        private boolean callbackClaimed, callbackReturned, callbackUncertain;
        private boolean closeUncertain;

        Startup(RetainedRootHostService actual, IBinder actualCallback, String sha, long count) {
            service = actual;
            callback = actualCallback;
            sha256 = sha;
            bytes = count;
            death = new IBinder.DeathRecipient() {
                @Override public void binderDied() { retire(); }
            };
        }

        void start() {
            try {
                synchronized (lock) { deathLinkAttempted = true; }
                callback.linkToDeath(death, 0);
                synchronized (lock) { deathLinked = true; }
                if (!mayContinue()) { notifyHost(null); return; }
                Thread created = new Thread(this, "oneos-retained-root-begin");
                synchronized (lock) { worker = created; workerStartAttempted = true; }
                created.start();
            } catch (Throwable unavailable) {
                retire();
                notifyHost(null);
            }
        }

        private boolean mayContinue() {
            synchronized (lock) { return !retired && !service.destroyed; }
        }

        @Override public void run() {
            try {
                boolean admitted;
                synchronized (lock) {
                    admitted = !retired && !service.destroyed;
                    // Retirement after this credit cannot claim no birth.
                    if (admitted) beginAdmitted = true;
                }
                if (!admitted) { notifyHost(null); return; }
                RetainedRootSession.Attempt returned = RetainedRootSession.begin(sha256, bytes);
                synchronized (lock) { attempt = returned; } // Before any check or wrapper allocation.
                if (returned == null) throw new IllegalStateException("No actual root attempt returned");
                Control created = new Control(this, returned);
                synchronized (lock) { control = created; }
                if (!mayContinue() || returned.state() != RetainedRootSession.State.ADMISSION_CLOSED) {
                    retire();
                    notifyHost(null);
                    return;
                }
                notifyHost(created);
            } catch (Throwable unavailable) {
                // begin may have spawned before throwing. Its own static current
                // owner retains that failure. Never wrap/close a currentAttempt()
                // observation, which could belong to another caller.
                retire();
                notifyHost(null);
            } finally {
                boolean cut;
                synchronized (lock) { workerFinished = true; cut = retired || service.destroyed; }
                if (cut) retire();
            }
        }

        void retire() {
            RetainedRootSession.Attempt retained;
            synchronized (lock) { retired = true; retained = closeUncertain ? null : attempt; }
            if (retained != null) {
                try { retained.requestClose(); }
                catch (Throwable unavailable) { synchronized (lock) { closeUncertain = true; } }
            }
            // No reset/unlink/reap inference. Keep callback, thread, exact Attempt
            // and Control, including uncertain or still-running foreign stacks.
        }

        void closeFromControl(RetainedRootSession.Attempt retained, Control actual) {
            synchronized (lock) {
                retired = true;
                if (attempt != retained || control != actual || closeUncertain) {
                    throw new IllegalStateException("Actual root cutoff unavailable");
                }
            }
            retained.requestClose(); // Wire caller must observe an actual failure.
        }

        void closeFailed() {
            synchronized (lock) { retired = true; closeUncertain = true; }
        }

        boolean permitsPing(RetainedRootSession.Attempt retained, Control actual) {
            synchronized (lock) {
                return !retired && !service.destroyed && attempt == retained && control == actual;
            }
        }

        private void notifyHost(Control captured) {
            boolean sendCapture;
            synchronized (lock) {
                if (callbackClaimed) return;
                callbackClaimed = true; // At most one callback attempt, including failure-after-delivery.
                sendCapture = captured != null && captured == control && !retired && !service.destroyed;
            }
            Parcel data = null;
            Parcel reply = null;
            boolean delivered = false;
            try {
                data = Parcel.obtain();
                reply = Parcel.obtain();
                data.writeInterfaceToken(ClosedRootLinkProtocol.CALLBACK);
                data.writeInt(ClosedRootLinkProtocol.VERSION);
                if (sendCapture) data.writeStrongBinder(captured);
                else data.writeInt(ClosedRootLinkProtocol.UNAVAILABLE);
                int code = sendCapture ? ClosedRootLinkProtocol.CAPTURED : ClosedRootLinkProtocol.FAILED;
                if (!callback.transact(code, data, reply, 0)) {
                    throw new IllegalStateException("Closed root callback not handled");
                }
                reply.readException();
                if (reply.readInt() != ClosedRootLinkProtocol.QUEUED) {
                    throw new IllegalStateException("Closed root callback not queued");
                }
                reply.enforceNoDataAvail();
                delivered = true;
            } catch (Throwable unavailable) {
                synchronized (lock) { callbackUncertain = true; }
                retire(); // Host may already have adopted the actual Control before the failure.
            } finally {
                try {
                    try { if (reply != null) reply.recycle(); }
                    finally { if (data != null) data.recycle(); }
                } catch (Throwable unavailable) {
                    synchronized (lock) { callbackUncertain = true; }
                    retire();
                    delivered = false;
                }
                synchronized (lock) { callbackReturned = delivered; }
            }
        }
    }

    private static final class Control extends Binder {
        private final Startup startup;
        private final RetainedRootSession.Attempt attempt;
        Control(Startup actualStartup, RetainedRootSession.Attempt actualReturned) {
            startup = actualStartup;
            attempt = actualReturned;
            attachInterface(null, ClosedRootLinkProtocol.CONTROL);
        }
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code != ClosedRootLinkProtocol.PING && code != ClosedRootLinkProtocol.REQUEST_CLOSE
                    && code != ClosedRootLinkProtocol.QUERY_STATE) {
                return super.onTransact(code, data, reply, flags);
            }
            requireCall(flags, reply);
            requireVersion(data, ClosedRootLinkProtocol.CONTROL);
            data.enforceNoDataAvail();
            final int state;
            boolean closeAttempted = false;
            try {
                if (code == ClosedRootLinkProtocol.PING) {
                    if (!startup.permitsPing(attempt, this)) {
                        throw new IllegalStateException("Closed root control retired");
                    }
                    attempt.ping(); // Actual Binder worker; no owned lock spans the call.
                    if (!startup.permitsPing(attempt, this)) {
                        throw new IllegalStateException("Closed root control retired during ping");
                    }
                } else if (code == ClosedRootLinkProtocol.REQUEST_CLOSE) {
                    closeAttempted = true;
                    startup.closeFromControl(attempt, this);
                }
                state = wireState(attempt.state());
            } catch (Throwable unavailable) {
                if (closeAttempted) startup.closeFailed();
                else startup.retire();
                // IOException is not a supported Parcel exception type. Never
                // encode a failed actual operation as a successful state reply.
                reply.writeException(new IllegalStateException("Closed root control unavailable"));
                return true;
            }
            reply.writeNoException();
            reply.writeInt(state);
            return true;
        }
    }

    private static int wireState(RetainedRootSession.State actual) {
        if (actual == RetainedRootSession.State.STARTING) return ClosedRootLinkProtocol.STARTING;
        if (actual == RetainedRootSession.State.ADMISSION_CLOSED) return ClosedRootLinkProtocol.ADMISSION_CLOSED;
        if (actual == RetainedRootSession.State.CLOSING) return ClosedRootLinkProtocol.CLOSING;
        if (actual == RetainedRootSession.State.CLOSED) return ClosedRootLinkProtocol.CLOSED;
        if (actual == RetainedRootSession.State.UNRESOLVED) return ClosedRootLinkProtocol.UNRESOLVED;
        throw new IllegalStateException("Unknown actual root state");
    }
}
