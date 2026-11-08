package com.fahadali.oneos.core.root;

import android.os.Looper;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/** Owns actual launch/stdio observations, never the native control socket. */
final class RetainedRootOfferLaunch implements Runnable {
    enum Observation { PREPARED, STARTING, OFFER_OBSERVED, WRAPPER_REAP_OBSERVED, UNRESOLVED }
    private static final Object CURRENT_LOCK = new Object();
    private static RetainedRootOfferLaunch current;
    private final Object lock = new Object();
    private final RetainedRootHostServiceV2.Caller caller;
    private final String sha256;
    private final long bytes;
    private Thread worker;
    private Process process;
    private InputStream stdout, stderr;
    private OutputStream stdin;
    private Pump outputPump, errorPump;
    private Offer offer;
    private Throwable failure;
    private int suppressionAttempts;
    private boolean startAttempted, processAttempted, reaped, workerFinished;
    private boolean outputJoined, errorJoined;
    private boolean stdinCloseAttempted, stdoutCloseAttempted, stderrCloseAttempted;
    private boolean localCloseUncertain;
    private Observation observation = Observation.PREPARED;

    private RetainedRootOfferLaunch(RetainedRootHostServiceV2.Caller caller, String sha256, long bytes) {
        this.caller = caller; this.sha256 = sha256; this.bytes = bytes;
    }

    static RetainedRootOfferLaunch prepare(RetainedRootHostServiceV2.Caller actualCaller,
            String expectedSha256, long expectedBytes) {
        if (actualCaller == null || actualCaller.uid() != 1000 || actualCaller.pid() <= 0
                || expectedSha256 == null || !expectedSha256.matches("[0-9a-f]{64}")
                || expectedBytes < 1 || expectedBytes > 2097152) {
            throw new IllegalArgumentException("Captured caller and fixed v2 build required");
        }
        RetainedRootOfferLaunch created = new RetainedRootOfferLaunch(actualCaller, expectedSha256, expectedBytes);
        synchronized (CURRENT_LOCK) {
            if (current != null) throw new IllegalStateException("V2 launch already owned");
            current = created;
        }
        return created;
    }

    /** Startup retains this object before this first possible thread start. */
    void start() {
        synchronized (lock) {
            if (startAttempted) throw new IllegalStateException("V2 launch is one shot");
            startAttempted = true; observation = Observation.STARTING;
        }
        try {
            Thread owned = new Thread(this, "oneos-root-v2-offer");
            synchronized (lock) { worker = owned; }
            owned.start();
        } catch (Throwable problem) { fail(problem); throw RetainedRootOfferLaunch.<RuntimeException>rethrow(problem); }
    }

    Offer awaitOffer() throws Throwable {
        Looper main = Looper.getMainLooper();
        if (main == null || Looper.myLooper() == main) throw new IllegalStateException("Offer wait requires worker");
        long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(30);
        synchronized (lock) {
            while (offer == null && failure == null && !workerFinished) {
                long remaining = until - System.nanoTime();
                if (remaining <= 0) {
                    IOException problem = new IOException("Native offer observation timed out");
                    failLocked(problem); throw problem;
                }
                try { TimeUnit.NANOSECONDS.timedWait(lock, remaining); }
                catch (InterruptedException problem) { failLocked(problem); throw problem; }
            }
            if (failure != null) throw failure;
            if (offer == null) throw new IOException("Native offer unavailable");
            return offer;
        }
    }

    Observation observation() { synchronized (lock) { return observation; } }

    @Override public void run() {
        try {
            synchronized (lock) { processAttempted = true; }
            process = RetainedRootOfferSpawn.start(sha256, bytes);
            stdin = process.getOutputStream();
            stdout = process.getInputStream();
            stderr = process.getErrorStream();
            outputPump = new Pump(stdout, true);
            outputPump.start();
            errorPump = new Pump(stderr, false);
            errorPump.start();
            byte[] init = RetainedHostControlProtocol.frame(RetainedHostControlProtocol.INIT, 0,
                    RetainedHostControlProtocol.REQUEST);
            RetainedHostControlProtocol.putU32(init, 16, caller.pid());
            RetainedHostControlProtocol.putU32(init, 20, caller.uid());
            stdin.write(init); stdin.flush();
            // Keep stdin open. Before COMMIT, app EOF can end native association.
            byte[] frame = outputPump.awaitFrame();
            RetainedHostControlProtocol.check(frame, RetainedHostControlProtocol.NATIVE_OFFER, 0,
                    RetainedHostControlProtocol.ADMISSION_CLOSED);
            int pid = RetainedHostControlProtocol.positivePid(RetainedHostControlProtocol.readU32(frame, 16));
            String name = new String(frame, 20, RetainedHostControlProtocol.NAME_BYTES, StandardCharsets.US_ASCII);
            RetainedHostControlProtocol.validateOffer(pid, name);
            RetainedHostControlProtocol.zeroTail(frame, 62);
            Offer actual = new Offer(pid, name);
            synchronized (lock) {
                if (failure == null) {
                    offer = actual; observation = Observation.OFFER_OBSERVED;
                }
                lock.notifyAll();
            }
        } catch (Throwable problem) { fail(problem); }
        finally {
            // Reap only the actual returned Java child. Never signal/destroy it,
            // close app pipes to cancel it, or infer native exit from this wrapper.
            if (process != null) {
                for (;;) {
                    try { process.waitFor(); reaped = true; break; }
                    catch (InterruptedException problem) { fail(problem); }
                    catch (Throwable problem) { fail(problem); break; }
                }
                joinPump(outputPump, true);
                joinPump(errorPump, false);
                // Only normal EOF on both actual readers, after a full OFFER,
                // and actual wrapper reap permit retiring these local views.
                // Read failure or a timed-out observer never authorizes close.
                if (reaped && outputJoined && errorJoined && outputPump.normalEof
                        && errorPump.normalEof && offer != null) closeLocalStreams();
            }
            synchronized (lock) {
                workerFinished = true;
                if (reaped && outputJoined && errorJoined && failure == null) {
                    observation = Observation.WRAPPER_REAP_OBSERVED;
                } else observation = Observation.UNRESOLVED;
                lock.notifyAll();
            }
            // All process/stream/pump references and close dispositions remain.
            // No app native
            // pidfd or commit receipt exists, so there is no app CLOSED claim.
        }
    }

    private void joinPump(Pump pump, boolean output) {
        if (pump == null) return;
        try {
            if (!pump.startReturned) throw new IOException("App stream observer start uncertain");
            pump.thread.join(30000);
            if (pump.thread.isAlive() || !pump.finished) throw new IOException("App stream observer still running");
            if (output) outputJoined = true; else errorJoined = true;
        } catch (Throwable problem) { fail(problem); }
    }

    private void closeLocalStreams() {
        // Consume each distinct owned stream's close disposition before calling
        // it. A throw retains uncertainty and never leads to a retry.
        if (stdin != null && !stdinCloseAttempted) {
            stdinCloseAttempted = true;
            try { stdin.close(); } catch (Throwable problem) { localCloseUncertain = true; fail(problem); }
        }
        if (stdout != null && !stdoutCloseAttempted) {
            stdoutCloseAttempted = true;
            try { stdout.close(); } catch (Throwable problem) { localCloseUncertain = true; fail(problem); }
        }
        if (stderr != null && !stderrCloseAttempted) {
            stderrCloseAttempted = true;
            try { stderr.close(); } catch (Throwable problem) { localCloseUncertain = true; fail(problem); }
        }
    }

    static final class Offer {
        private final int nativePid;
        private final String address;
        private Offer(int pid, String address) { nativePid = pid; this.address = address; }
        int nativePid() { return nativePid; }
        String address() { return address; }
    }

    private final class Pump implements Runnable {
        private final InputStream stream;
        private final boolean output;
        private final byte[] first = new byte[RetainedHostControlProtocol.FRAME_BYTES];
        private int count;
        private boolean finished;
        private boolean normalEof;
        private boolean startReturned;
        private Thread thread;
        Pump(InputStream stream, boolean output) { this.stream = stream; this.output = output; }
        void start() {
            thread = new Thread(this, output ? "oneos-v2-stdout" : "oneos-v2-stderr");
            thread.start();
            startReturned = true;
        }
        @Override public void run() {
            try {
                byte[] block = new byte[256];
                int read;
                while ((read = stream.read(block)) != -1) {
                    if (read <= 0) throw new IOException("App stream made no progress");
                    synchronized (lock) {
                        if (output && count < first.length) {
                            System.arraycopy(block, 0, first, count, Math.min(read, first.length - count));
                        }
                        count = Math.min(4097, count + read);
                        lock.notifyAll();
                    }
                    if (!output || count > RetainedHostControlProtocol.FRAME_BYTES) {
                        throw new IOException("Unexpected v2 launch output");
                    }
                }
                if (output && count != RetainedHostControlProtocol.FRAME_BYTES) {
                    throw new IOException("Short native offer stream");
                }
                normalEof = true;
            } catch (Throwable problem) { fail(problem); }
            finally {
                synchronized (lock) {
                    // Full OFFER EOF and empty stderr EOF are expected when native
                    // commits/detaches, not app authority to close or claim exit.
                    finished = true; lock.notifyAll();
                }
            }
        }
        byte[] awaitFrame() throws Throwable {
            long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(30);
            synchronized (lock) {
                while (count < first.length && !finished && failure == null) {
                    long remaining = until - System.nanoTime();
                    if (remaining <= 0) throw new IOException("Native offer frame timed out");
                    TimeUnit.NANOSECONDS.timedWait(lock, remaining);
                }
                if (failure != null) throw failure;
                if (count != first.length) throw new IOException("Native offer frame incomplete");
                return first.clone();
            }
        }
    }

    private void fail(Throwable problem) { synchronized (lock) { failLocked(problem); } }
    private void failLocked(Throwable problem) {
        if (failure == null) failure = problem;
        else if (failure != problem && suppressionAttempts < 8) {
            suppressionAttempts++;
            try { failure.addSuppressed(problem); } catch (Throwable ignored) { }
        }
        observation = Observation.UNRESOLVED; lock.notifyAll();
    }
    @SuppressWarnings("unchecked") private static <T extends Throwable> RuntimeException rethrow(Throwable problem) throws T {
        throw (T) problem;
    }
}
