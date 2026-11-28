package com.fahadali.oneos.core.root;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;

/** Separate v2 offer relay. The app never acquires native control authority. */
public final class RetainedRootHostServiceV2 extends Service {
    private static final Object STARTUP_LOCK = new Object();
    private static Startup startup;
    private final Broker broker = new Broker(this);
    private volatile boolean destroyed;

    @Override public IBinder onBind(Intent intent) { return broker; }
    @Override public void onDestroy() {
        destroyed = true;
        Startup retained;
        synchronized (STARTUP_LOCK) { retained = startup; }
        try { if (retained != null && retained.service == this) retained.retireDelivery(); }
        finally { super.onDestroy(); }
    }

    /** Created only in the actual validated Binder BEGIN entry, never from wire fields. */
    static final class Caller {
        private final int pid, uid;
        private Caller(int pid, int uid) { this.pid = pid; this.uid = uid; }
        int pid() { return pid; }
        int uid() { return uid; }
    }

    private void begin(Caller caller, IBinder callback, String sha, long bytes) {
        if (callback == null || sha == null || !sha.matches("[0-9a-f]{64}") || bytes < 1 || bytes > 2097152) {
            throw new IllegalArgumentException("Fixed v2 build and actual callback required");
        }
        Startup created = new Startup(this, caller, callback, sha, bytes);
        synchronized (STARTUP_LOCK) {
            if (destroyed || startup != null) throw new IllegalStateException("V2 startup already owned");
            startup = created;
        }
        created.start();
    }

    private static final class Broker extends Binder {
        private final RetainedRootHostServiceV2 service;
        Broker(RetainedRootHostServiceV2 service) { this.service = service; attachInterface(null, RetainedHostControlProtocol.BROKER); }
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {
            if (code != RetainedHostControlProtocol.BEGIN) return super.onTransact(code, data, reply, flags);
            int uid = Binder.getCallingUid();
            int pid = Binder.getCallingPid();
            if (uid != 1000 || pid <= 0) throw new SecurityException("Actual system Binder caller required");
            if (Build.VERSION.SDK_INT != 37) throw new IllegalStateException("SDK 37 source profile required");
            if (flags != 0 || reply == null) throw new IllegalArgumentException("Synchronous BEGIN required");
            Caller caller = new Caller(pid, uid);
            data.enforceInterface(RetainedHostControlProtocol.BROKER);
            if (data.readInt() != RetainedHostControlProtocol.VERSION) throw new IllegalArgumentException("V2 version differs");
            IBinder callback = data.readStrongBinder();
            String sha = data.readString(); long bytes = data.readLong(); data.enforceNoDataAvail();
            service.begin(caller, callback, sha, bytes);
            reply.writeNoException(); reply.writeInt(RetainedHostControlProtocol.QUEUED);
            return true;
        }
    }

    private static final class Startup implements Runnable {
        private final Object lock = new Object();
        final RetainedRootHostServiceV2 service;
        private final Caller caller;
        private final IBinder callback;
        private final String sha;
        private final long bytes;
        private final IBinder.DeathRecipient death;
        private Thread worker;
        private RetainedRootOfferLaunch launch;
        private RetainedRootOfferLaunch.Offer offer;
        private boolean retired, deathAttempted, workerStartAttempted, launchAdmitted;
        private boolean callbackAttempted, callbackReturned, callbackUncertain, workerFinished;
        Startup(RetainedRootHostServiceV2 service, Caller caller, IBinder callback, String sha, long bytes) {
            this.service = service; this.caller = caller; this.callback = callback; this.sha = sha; this.bytes = bytes;
            death = new IBinder.DeathRecipient() {
                @Override public void binderDied() { retireDelivery(); }
            };
        }
        void start() {
            try {
                synchronized (lock) { deathAttempted = true; }
                callback.linkToDeath(death, 0);
                if (!mayDeliver()) { notifyHost(null); return; }
                Thread created = new Thread(this, "oneos-host-v2-relay");
                synchronized (lock) { worker = created; workerStartAttempted = true; }
                created.start();
            } catch (Throwable problem) { retireDelivery(); notifyHost(null); }
        }
        private boolean mayDeliver() { synchronized (lock) { return !retired && !service.destroyed; } }
        @Override public void run() {
            try {
                boolean admitted;
                synchronized (lock) {
                    admitted = !retired && !service.destroyed;
                    if (admitted) launchAdmitted = true;
                }
                if (!admitted) { notifyHost(null); return; }
                RetainedRootOfferLaunch actual = RetainedRootOfferLaunch.prepare(caller, sha, bytes);
                synchronized (lock) { launch = actual; }
                actual.start();
                RetainedRootOfferLaunch.Offer returned = actual.awaitOffer();
                synchronized (lock) { offer = returned; }
                notifyHost(returned);
            } catch (Throwable problem) { retireDelivery(); notifyHost(null); }
            finally { synchronized (lock) { workerFinished = true; } }
        }
        void retireDelivery() {
            synchronized (lock) { retired = true; }
            // Never destroy/signal the child, close its pipes, or send native CLOSE.
            // An offer may already have reached a host which committed control.
        }
        private void notifyHost(RetainedRootOfferLaunch.Offer actual) {
            boolean sendOffer;
            synchronized (lock) {
                if (callbackAttempted) return;
                callbackAttempted = true;
                sendOffer = actual != null && actual == offer && !retired && !service.destroyed;
            }
            Parcel data = null, reply = null;
            boolean returned = false;
            try {
                data = Parcel.obtain(); reply = Parcel.obtain();
                data.writeInterfaceToken(RetainedHostControlProtocol.CALLBACK);
                data.writeInt(RetainedHostControlProtocol.VERSION);
                if (sendOffer) { data.writeInt(actual.nativePid()); data.writeString(actual.address()); }
                else data.writeInt(RetainedHostControlProtocol.UNAVAILABLE);
                if (!callback.transact(sendOffer ? RetainedHostControlProtocol.OFFER : RetainedHostControlProtocol.FAILED,
                        data, reply, 0)) throw new IllegalStateException("V2 callback unhandled");
                reply.readException();
                if (reply.readInt() != RetainedHostControlProtocol.QUEUED) throw new IllegalStateException("V2 callback not queued");
                reply.enforceNoDataAvail(); returned = true;
            } catch (Throwable problem) {
                synchronized (lock) { callbackUncertain = true; }
                retireDelivery();
            } finally {
                try {
                    try { if (reply != null) reply.recycle(); }
                    finally { if (data != null) data.recycle(); }
                } catch (Throwable problem) {
                    synchronized (lock) { callbackUncertain = true; }
                    retireDelivery(); returned = false;
                }
                synchronized (lock) { callbackReturned = returned; }
            }
        }
    }
}
