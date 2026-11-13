package com.fahadali.oneos.core.root;

import android.net.Credentials;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructPollfd;
import java.io.Closeable;
import java.io.FileDescriptor;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.TimeUnit;

/** Source-owned, admission-closed control transport. It grants no host/guest authority. */
public final class RetainedRootSession {
    private static final Object CURRENT_LOCK = new Object();
    private static final long TIMEOUT_NANOS = TimeUnit.SECONDS.toNanos(30);
    private static Attempt current;
    private static boolean preparing;
    private RetainedRootSession() { }

    public enum State { STARTING, ADMISSION_CLOSED, CLOSING, CLOSED, UNRESOLVED }

    /** Creates its own retained owner before any process/thread creation. */
    public static Attempt begin(String expectedSha256, long expectedBytes) throws IOException {
        if (expectedSha256 == null || !expectedSha256.matches("[0-9a-f]{64}")
                || expectedBytes < 1 || expectedBytes > 2097152) {
            throw new IllegalArgumentException("Fixed helper build identity required");
        }
        Attempt attempt = new Attempt(expectedSha256, expectedBytes);
        Attempt previous;
        synchronized (CURRENT_LOCK) {
            if (preparing || (current != null && !current.terminalForReplacement())) {
                throw new IllegalStateException("Previous root attempt is not terminal");
            }
            previous = current;
            preparing = true;
            current = attempt;
        }
        try {
            offMain();
            attempt.start();
            attempt.awaitCaptured();
            return attempt;
        } catch (Throwable problem) {
            attempt.fail(problem);
            // No start() call was attempted: no process/thread birth can be pending.
            // This is private preflight rollback, never a supplied-process/reset API.
            if (!attempt.startAttempted()) {
                synchronized (CURRENT_LOCK) { if (current == attempt) current = previous; }
            }
            RetainedRootSession.<IOException>raise(problem);
            throw new AssertionError();
        } finally { synchronized (CURRENT_LOCK) { preparing = false; } }
    }

    /** Includes failed/unresolved owners; possession is not security permission. */
    public static Attempt currentAttempt() {
        synchronized (CURRENT_LOCK) { return current; }
    }

    private static void offMain() {
        Looper main = Looper.getMainLooper();
        if (main == null || Looper.myLooper() == main) {
            throw new IllegalStateException("Existing non-main thread required");
        }
    }

    public static final class Attempt implements Closeable {
        private final Object lock = new Object();
        private final String expectedSha;
        private final long expectedBytes;
        private final ArrayList<FileDescriptor[]> rawRights = new ArrayList<FileDescriptor[]>();
        private FileDescriptor[] pendingRights;
        private State state = State.STARTING;
        private boolean closeRequested, captured, workerFinished, pidfdExited, reaped;
        private boolean acked, cleanupSucceeded, offerJoined, errorJoined, pidfdValidated;
        private boolean threadStartAttempted, procCloseFailed, duplicationUncertain;
        private boolean ancillaryUncertain, socketCloseFailed;
        private boolean pidfdCloseAttempted, pidfdCloseUncertain;
        private int suppressionAttempts;
        private Throwable failure;
        private Thread worker;
        private Process process;
        private InputStream stdout, stderr, controlIn;
        private OutputStream stdin, controlOut;
        private Pump offerPump, errorPump;
        private LocalSocket socket;
        private LocalSocket socketCloseUncertain;
        private ParcelFileDescriptor pidfd;
        private FileDescriptor pidfdClosing;
        private FileDescriptor procRead;
        private FileDescriptor procCloseUncertain;
        private Ping ping;
        private long sequence;

        private Attempt(String sha, long bytes) { expectedSha = sha; expectedBytes = bytes; }
        private boolean terminalForReplacement() { synchronized (lock) { return state == State.CLOSED; } }
        private boolean startAttempted() { synchronized (lock) { return threadStartAttempted; } }

        public State state() {
            Thread actual;
            synchronized (lock) { actual = worker; }
            boolean ended = actual != null && !actual.isAlive();
            synchronized (lock) {
                if (ended && workerFinished && pidfdExited && reaped && pumpsDone() && cleanupSucceeded) {
                    state = State.CLOSED;
                }
                return state;
            }
        }

        /** Only a local admission cutoff; does not claim exit or interrupt blocked I/O. */
        public void requestClose() {
            synchronized (lock) {
                closeRequested = true;
                if (state != State.CLOSED && state != State.UNRESOLVED) state = State.CLOSING;
                lock.notifyAll();
            }
        }

        /** One bounded control request. No source/native-readiness interpretation. */
        public void ping() throws IOException {
            offMain();
            Ping request = new Ping();
            synchronized (lock) {
                if (!captured || closeRequested || state != State.ADMISSION_CLOSED || ping != null) {
                    throw new IllegalStateException("Closed root control or request in flight");
                }
                ping = request;
                lock.notifyAll();
            }
            long until = deadline();
            synchronized (lock) {
                while (!request.done && failure == null && !workerFinished) waitBounded(until);
                if (failure != null) RetainedRootSession.<IOException>raise(failure);
                if (!request.done) {
                    throw new IOException("Root ping incomplete");
                }
            }
        }

        /** ACK alone never closes the attempt. Uncertainty retains this owner. */
        @Override public void close() throws IOException {
            offMain();
            requestClose();
            long until = deadline();
            Thread actual;
            synchronized (lock) { actual = worker; }
            try {
                if (actual != null) join(actual, until);
            } catch (Throwable problem) {
                fail(problem);
                RetainedRootSession.<IOException>raise(problem);
            }
            State observed = state();
            synchronized (lock) {
                if (!workerFinished || observed != State.CLOSED) {
                    if (failure != null) RetainedRootSession.<IOException>raise(failure);
                    throw new IOException("Root closure remains unresolved");
                }
                if (failure != null) RetainedRootSession.<IOException>raise(failure);
            }
        }

        private void start() throws IOException {
            try {
                Thread owned = new Thread(new Runnable() {
                    @Override public void run() { runOwned(); }
                }, "oneos-root-session");
                synchronized (lock) { worker = owned; threadStartAttempted = true; }
                owned.start();
            } catch (Throwable problem) {
                fail(problem);
                RetainedRootSession.<IOException>raise(problem);
            }
        }

        private void awaitCaptured() throws IOException {
            long until = deadline();
            synchronized (lock) {
                while (!captured && failure == null && !workerFinished) waitBounded(until);
                if (!captured || closeRequested || failure != null) {
                    if (failure != null) RetainedRootSession.<IOException>raise(failure);
                    throw new IOException("Root handshake incomplete");
                }
            }
        }

        // Called only while lock is owned. No external objects are queried here.
        private void waitBounded(long until) throws IOException {
            long left = until - System.nanoTime();
            if (left <= 0) {
                IOException timeout = new IOException("Root control observation timed out");
                failLocked(timeout);
                throw timeout;
            }
            try { TimeUnit.NANOSECONDS.timedWait(lock, left); }
            catch (InterruptedException interrupted) {
                failLocked(interrupted);
                // Propagate the exact interruption. Do not call overridable
                // Thread.interrupt while this owner's monitor is held.
                RetainedRootSession.<IOException>raise(interrupted);
            }
        }

        private void runOwned() {
            try {
                // start() can throw after creation. No absence-of-child inference is made.
                Process born = RetainedRootSessionSpawn.start(expectedSha, expectedBytes);
                process = born;
                stdin = born.getOutputStream();
                stdout = born.getInputStream();
                stderr = born.getErrorStream();
                offerPump = new Pump(stdout, true);
                offerPump.start();
                errorPump = new Pump(stderr, false);
                errorPump.start();
                byte[] init = frame(RetainedRootProtocol.INIT, 0, RetainedRootProtocol.REQUEST);
                put(init, 16, android.os.Process.myPid());
                put(init, 20, android.os.Process.myUid());
                stdin.write(init);
                stdin.flush();
                byte[] offer = offerPump.awaitOffer(deadline());
                check(offer, RetainedRootProtocol.OFFER, 0, RetainedRootProtocol.ADMISSION_CLOSED);
                int peerPid = positive(get(offer, 16));
                String name = address(offer);
                socket = new LocalSocket();
                // The captured platform's timeout overload is unimplemented.
                // A caller observation timeout retains this actual blocking owner.
                socket.connect(new LocalSocketAddress(name, LocalSocketAddress.Namespace.ABSTRACT));
                socket.setSoTimeout(30000);
                Credentials peer = socket.getPeerCredentials();
                if (peer.getUid() != 0 || peer.getPid() != peerPid) throw new IOException("Root peer mismatch");
                controlIn = socket.getInputStream();
                controlOut = socket.getOutputStream();
                byte[] identity = receive(true);
                check(identity, RetainedRootProtocol.IDENTITY, 0, RetainedRootProtocol.ADMISSION_CLOSED);
                if (get(identity, 16) != peerPid) throw new IOException("Root identity mismatch");
                zero(identity, 20);
                if (rawRights.size() != 1 || rawRights.get(0).length != 1
                        || rawRights.get(0)[0] == null) throw new IOException("Exactly one root pidfd required");
                duplicationUncertain = true;
                pidfd = ParcelFileDescriptor.dup(rawRights.get(0)[0]);
                duplicationUncertain = false;
                validatePidfd(peerPid);
                pidfdValidated = true;
                synchronized (lock) {
                    if (offerPump.finished || errorPump.finished) {
                        failLocked(new IOException("Root stream ended during capture"));
                    }
                    captured = true;
                    if (failure == null && !closeRequested) state = State.ADMISSION_CLOSED;
                    lock.notifyAll();
                }
                controls();
            } catch (Throwable problem) { fail(problem); }
            finally {
                try { settle(); }
                catch (Throwable problem) { fail(problem); }
                finally {
                    synchronized (lock) {
                        workerFinished = true;
                        if (pidfdExited && reaped && pumpsDone() && cleanupSucceeded) state = State.CLOSING;
                        else state = State.UNRESOLVED;
                        lock.notifyAll();
                    }
                }
            }
        }

        private void controls() throws IOException {
            for (;;) {
                Ping request;
                boolean closing;
                synchronized (lock) {
                    while (!closeRequested && ping == null && failure == null) {
                        try { lock.wait(); }
                        catch (InterruptedException interrupted) { failLocked(interrupted); }
                    }
                    closing = closeRequested || failure != null;
                    request = ping;
                }
                if (sequence == 0xffffffffL) throw new IOException("Root sequence exhausted");
                long next = ++sequence;
                int kind = closing ? RetainedRootProtocol.CLOSE : RetainedRootProtocol.PING;
                controlOut.write(frame(kind, next, RetainedRootProtocol.REQUEST));
                controlOut.flush();
                byte[] reply = receive(false);
                check(reply, closing ? RetainedRootProtocol.CLOSED : RetainedRootProtocol.PONG, next,
                        closing ? RetainedRootProtocol.LOCAL_CLOSED : RetainedRootProtocol.ADMISSION_CLOSED);
                zero(reply, 16);
                synchronized (lock) {
                    if (closing) { acked = true; return; }
                    if (request != ping) throw new IOException("Root request owner changed");
                    request.done = true;
                    ping = null;
                    lock.notifyAll();
                }
            }
        }

        private byte[] receive(boolean initial) throws IOException {
            byte[] bytes = new byte[RetainedRootProtocol.FRAME_BYTES];
            int offset = 0;
            long until = deadline();
            while (offset < bytes.length) {
                if (System.nanoTime() >= until) throw new IOException("Root frame timed out");
                socket.setSoTimeout(remainingMillis(until));
                int read = -1;
                Throwable readFailure = null;
                Throwable rightsFailure = null;
                try { read = controlIn.read(bytes, offset, bytes.length - offset); }
                catch (Throwable problem) { readFailure = problem; }
                // A failed read can still leave an actual received ancillary array.
                try { adoptAncillary(initial); }
                catch (Throwable problem) { rightsFailure = problem; }
                if (readFailure != null || rightsFailure != null) {
                    Throwable primary = readFailure != null ? readFailure : rightsFailure;
                    fail(primary);
                    if (readFailure != null && rightsFailure != null) fail(rightsFailure);
                    RetainedRootSession.<IOException>raise(primary);
                }
                if (read <= 0) throw new IOException("Incomplete root frame");
                offset += read;
            }
            return bytes;
        }

        private void adoptAncillary(boolean initial) throws IOException {
            ancillaryUncertain = true;
            // Adopt the whole actual array before count/type checks or allocation.
            pendingRights = socket.getAncillaryFileDescriptors();
            ancillaryUncertain = false;
            if (pendingRights != null) {
                rawRights.add(pendingRights);
                pendingRights = null;
                if (!initial) throw new IOException("Unexpected root rights");
            }
        }

        private void validatePidfd(int expectedPid) throws IOException, ErrnoException {
            String number = Integer.toString(pidfd.getFd());
            if (!"anon_inode:[pidfd]".equals(Os.readlink("/proc/self/fd/" + number))) {
                throw new IOException("Root descriptor is not a pidfd");
            }
            procRead = Os.open("/proc/self/fdinfo/" + number,
                    OsConstants.O_RDONLY | OsConstants.O_CLOEXEC, 0);
            byte[] bytes = new byte[4097];
            int used = 0;
            while (used < bytes.length) {
                int count = Os.read(procRead, bytes, used, bytes.length - used);
                if (count == 0) break;
                if (count < 0) throw new IOException("Invalid pidfd metadata read");
                used += count;
            }
            if (used == bytes.length) throw new IOException("Oversized pidfd metadata");
            String info = new String(bytes, 0, used, StandardCharsets.US_ASCII);
            int matches = 0;
            for (String line : info.split("\n", -1)) {
                if (line.startsWith("Pid:")) {
                    String value = line.substring(4).trim();
                    if (!value.equals(Integer.toString(expectedPid))) throw new IOException("Pidfd target mismatch");
                    matches++;
                }
            }
            if (matches != 1) throw new IOException("Unique pidfd target required");
            FileDescriptor consumed = procRead;
            procRead = null;
            try { Os.close(consumed); }
            catch (Throwable problem) {
                procCloseUncertain = consumed;
                procCloseFailed = true;
                RetainedRootSession.<IOException>raise(problem);
            }
        }

        private void settle() {
            long until = deadline();
            // Cut the local channel even when a protocol ACK cannot be obtained.
            // EOF is not proof of helper death; keep its validated pidfd until observed exit.
            boolean okay = true;
            if (socket != null) {
                if (!ancillaryUncertain && pendingRights == null) {
                    try { adoptAncillary(false); }
                    catch (Throwable problem) { fail(problem); okay = false; }
                }
                // Input/output streams are borrowed views of this one socket FD.
                // Consume its sole close authority before the fallible close;
                // never retry it through either stream alias.
                LocalSocket consumed = socket;
                socket = null;
                try { consumed.close(); }
                catch (Throwable problem) {
                    socketCloseUncertain = consumed;
                    socketCloseFailed = true;
                    fail(problem); okay = false;
                }
            }
            okay &= closeOwned(stdin);
            if (procRead != null) {
                FileDescriptor consumed = procRead;
                procRead = null;
                try { Os.close(consumed); }
                catch (Throwable problem) {
                    procCloseUncertain = consumed;
                    procCloseFailed = true;
                    fail(problem); okay = false;
                }
            }
            try { closeRawRights(); }
            catch (Throwable problem) { fail(problem); okay = false; }
            try {
                if (pidfd != null && pidfdValidated) {
                    StructPollfd item = new StructPollfd();
                    item.fd = pidfd.getFileDescriptor();
                    item.events = (short) OsConstants.POLLIN;
                    int count = Os.poll(new StructPollfd[] {item}, remainingMillis(until));
                    if (count > 0 && (item.revents & OsConstants.POLLIN) != 0
                            && (item.revents & (OsConstants.POLLERR | OsConstants.POLLNVAL)) == 0) pidfdExited = true;
                }
            } catch (Throwable problem) { fail(problem); }
            try { if (process != null) reaped = process.waitFor(remainingMillis(until), TimeUnit.MILLISECONDS); }
            catch (Throwable problem) { fail(problem); }
            try { if (offerPump != null) { offerPump.join(until); offerJoined = true; } }
            catch (Throwable problem) { fail(problem); }
            try { if (errorPump != null) { errorPump.join(until); errorJoined = true; } }
            catch (Throwable problem) { fail(problem); }
            // No numeric signal, cancellation-as-reap or forced resource reset.
            // Unresolved native/stream custody remains retained, with no automatic retry.
            if (reaped && offerJoined && errorJoined) {
                okay &= closeOwned(stdout);
                okay &= closeOwned(stderr);
            } else okay = false;
            if (pidfd != null && (!pidfdValidated || pidfdExited)) okay &= closePidfd();
            else if (pidfd != null) okay = false;
            cleanupSucceeded = okay && !procCloseFailed && !duplicationUncertain
                    && !ancillaryUncertain && !socketCloseFailed && !pidfdCloseUncertain;
        }

        private boolean closePidfd() {
            if (pidfdCloseAttempted) return false;
            pidfdCloseUncertain = true;
            try {
                pidfdClosing = pidfd.getFileDescriptor();
                pidfdCloseAttempted = true;
                Os.close(pidfdClosing);
                if (pidfdClosing.valid()) throw new IOException("Consumed pidfd remains valid");
                // The same FD is now invalid: wrapper cleanup cannot retry a live FD.
                pidfd.close();
                pidfdCloseUncertain = false;
                return true;
            } catch (Throwable problem) { fail(problem); return false; }
        }

        private boolean closeOwned(Closeable resource) {
            if (resource == null) return true;
            try { resource.close(); return true; }
            catch (Throwable problem) { fail(problem); return false; }
        }

        private void closeRawRights() throws IOException {
            boolean okay = closeRightsArray(pendingRights);
            for (int n = 0; n < rawRights.size(); n++) okay &= closeRightsArray(rawRights.get(n));
            if (!okay) throw new IOException("Root rights cleanup unresolved");
        }

        // Invoked only once from final cleanup; every actual raw FD is attempted independently.
        private boolean closeRightsArray(FileDescriptor[] array) {
            boolean okay = true;
            if (array != null) for (FileDescriptor fd : array) {
                if (fd == null) { okay = false; continue; }
                try { Os.close(fd); }
                catch (Throwable problem) { fail(problem); okay = false; }
            }
            return okay;
        }

        private boolean pumpsDone() {
            return offerPump != null && errorPump != null && offerJoined && errorJoined
                    && offerPump.finished && errorPump.finished;
        }

        private void fail(Throwable problem) { synchronized (lock) { failLocked(problem); } }
        private void failLocked(Throwable problem) {
            if (failure == null) failure = problem;
            else if (failure != problem && suppressionAttempts < 8) {
                suppressionAttempts++;
                try { failure.addSuppressed(problem); } catch (Throwable ignored) { }
            }
            closeRequested = true;
            if (state != State.CLOSED) state = State.UNRESOLVED;
            lock.notifyAll();
        }

        private final class Pump implements Runnable {
            private final InputStream stream;
            private final boolean offer;
            private final byte[] first = new byte[64];
            private int count;
            private boolean finished;
            private Thread thread;
            Pump(InputStream source, boolean hasOffer) { stream = source; offer = hasOffer; }
            void start() {
                thread = new Thread(this, offer ? "oneos-root-offer" : "oneos-root-stderr");
                thread.start();
            }
            @Override public void run() {
                try {
                    byte[] block = new byte[256];
                    int read;
                    while ((read = stream.read(block)) != -1) {
                        if (read == 0) throw new IOException("Root stream made no progress");
                        synchronized (lock) {
                            if (offer && count < first.length) {
                                System.arraycopy(block, 0, first, count, Math.min(read, first.length - count));
                            }
                            count = Math.min(4097, count + read);
                            lock.notifyAll();
                        }
                        if ((!offer && count != 0) || (offer && count > 64)) {
                            throw new IOException("Unexpected root process output");
                        }
                    }
                } catch (Throwable problem) { fail(problem); }
                finally {
                    synchronized (lock) {
                        finished = true;
                        if (captured && !closeRequested) failLocked(new IOException("Root process stream ended"));
                        lock.notifyAll();
                    }
                }
            }
            byte[] awaitOffer(long until) throws IOException {
                synchronized (lock) {
                    while (count < 64 && !finished && failure == null) waitBounded(until);
                    if (failure != null) RetainedRootSession.<IOException>raise(failure);
                    if (count != 64) throw new IOException("Root OFFER incomplete");
                    return first.clone();
                }
            }
            void join(long until) throws InterruptedException, IOException { RetainedRootSession.join(thread, until); }
        }
    }

    private static final class Ping { boolean done; }
    private static long deadline() { return System.nanoTime() + TIMEOUT_NANOS; }
    private static int remainingMillis(long until) throws IOException {
        long left = until - System.nanoTime();
        if (left <= 0) throw new IOException("Root observation deadline elapsed");
        return (int) Math.min(30000, Math.max(1, TimeUnit.NANOSECONDS.toMillis(left)));
    }
    private static void join(Thread thread, long until) throws InterruptedException, IOException {
        if (thread != null) thread.join(remainingMillis(until));
        if (thread != null && thread.isAlive()) throw new IOException("Root thread completion unresolved");
    }
    private static byte[] frame(int kind, long sequence, int status) {
        byte[] result = new byte[RetainedRootProtocol.FRAME_BYTES];
        result[0] = 'O'; result[1] = 'R'; result[2] = 'S'; result[3] = 'C';
        result[4] = 0; result[5] = 1; result[6] = (byte) (kind >>> 8); result[7] = (byte) kind;
        put(result, 8, sequence); put(result, 12, status);
        return result;
    }
    private static void check(byte[] bytes, int kind, long sequence, int status) throws IOException {
        if (bytes.length != 64 || bytes[0] != 'O' || bytes[1] != 'R' || bytes[2] != 'S' || bytes[3] != 'C'
                || bytes[4] != 0 || bytes[5] != RetainedRootProtocol.VERSION
                || (bytes[6] & 255) != (kind >>> 8) || (bytes[7] & 255) != (kind & 255)
                || get(bytes, 8) != sequence || get(bytes, 12) != status) {
            throw new IOException("Root frame protocol mismatch");
        }
    }
    private static String address(byte[] frame) throws IOException {
        int end = 20;
        while (end < 64 && frame[end] != 0) {
            int value = frame[end] & 255;
            if (!((value >= 'a' && value <= 'z') || (value >= '0' && value <= '9') || value == '.')) {
                throw new IOException("Invalid root abstract address");
            }
            end++;
        }
        if (end == 20 || end == 64) throw new IOException("Bounded root address required");
        zero(frame, end);
        return new String(frame, 20, end - 20, StandardCharsets.US_ASCII);
    }
    private static void zero(byte[] bytes, int begin) throws IOException {
        for (int n = begin; n < bytes.length; n++) if (bytes[n] != 0) throw new IOException("Nonzero root padding");
    }
    private static long get(byte[] bytes, int offset) {
        return ((bytes[offset] & 255L) << 24) | ((bytes[offset + 1] & 255L) << 16)
                | ((bytes[offset + 2] & 255L) << 8) | (bytes[offset + 3] & 255L);
    }
    private static void put(byte[] bytes, int offset, long value) {
        for (int n = 3; n >= 0; n--) { bytes[offset + n] = (byte) value; value >>>= 8; }
    }
    private static int positive(long value) throws IOException {
        if (value < 1 || value > Integer.MAX_VALUE) throw new IOException("Invalid root peer PID");
        return (int) value;
    }
    @SuppressWarnings("unchecked") private static <T extends Throwable> void raise(Throwable failure) throws T {
        throw (T) failure;
    }
}
