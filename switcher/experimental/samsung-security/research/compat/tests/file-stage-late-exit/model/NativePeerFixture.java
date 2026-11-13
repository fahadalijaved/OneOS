package model;

import android.system.OsConstants;
import com.fahadali.oneos.core.root.RetainedHostControlProtocol;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Authored native peer with explicit exit and callback gates; no actual pidfd. */
public final class NativePeerFixture {
    private static final int PID = 765, DUP_NUMBER = 42;
    public static final String NAME = "oneos.orh.0123456789abcdef0123456789abcdef";
    public static final String mode = "file_stage_late_exit";
    public static final CountDownLatch pollEntered = new CountDownLatch(1);
    public static final CountDownLatch releasePoll = new CountDownLatch(1);
    public static volatile Thread watcher;
    public static volatile int connects, socketCloses;
    public static volatile int dupCloses, rawCloses, procCloses, watcherPolls;
    public static volatile short pollEvents;

    private static final byte[] PROC = ("Pid:\t" + PID + "\n").getBytes(StandardCharsets.US_ASCII);
    private static Held raw, dup, proc;
    private static Path directory;
    private static byte[] reply;
    private static int responseOffset, procOffset;
    private static boolean identityRead, rightsTaken;
    private static long nextSequence = 1;

    public static final class Held {
        public final FileDescriptor fd;
        public final int number;
        private final FileInputStream stream;

        private Held(Path path, int number) throws IOException {
            Files.write(path, new byte[] { 1 }, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            stream = new FileInputStream(path.toFile());
            fd = stream.getFD();
            this.number = number;
        }
    }

    public static void configure(Path ownedDirectory) {
        directory = ownedDirectory;
        reply = response(RetainedHostControlProtocol.IDENTITY, 0);
        RetainedHostControlProtocol.putU32(reply, 16, PID);
    }

    private static byte[] response(int kind, long sequence) {
        return RetainedHostControlProtocol.frame(kind, sequence, RetainedHostControlProtocol.ADMISSION_CLOSED);
    }

    public static void observe() { }

    public static int read(byte[] bytes, int offset, int size) throws IOException {
        if (reply == null || size <= 0) throw new IOException("unexpected modeled frame read");
        int count = Math.min(size, reply.length - responseOffset);
        System.arraycopy(reply, responseOffset, bytes, offset, count);
        responseOffset += count;
        if (responseOffset == reply.length) {
            if ((reply[7] & 255) == RetainedHostControlProtocol.IDENTITY) identityRead = true;
            reply = null;
            responseOffset = 0;
        }
        return count;
    }

    public static void write(byte[] frame) throws IOException {
        long sequence = nextSequence++;
        if (reply != null || sequence > 3) throw new IOException("unexpected modeled frame write");
        int kind = sequence == 1 ? RetainedHostControlProtocol.COMMIT
                : sequence == 2 ? RetainedHostControlProtocol.VIEW_PREPARE : RetainedHostControlProtocol.VIEW_QUERY;
        RetainedHostControlProtocol.check(frame, kind, sequence, RetainedHostControlProtocol.REQUEST);
        RetainedHostControlProtocol.zeroTail(frame, 16);
        if (sequence == 1) {
            reply = response(RetainedHostControlProtocol.COMMITTED, sequence);
        } else {
            reply = response(RetainedHostControlProtocol.VIEW_STATE, sequence);
            RetainedHostControlProtocol.putU32(reply, 16, sequence == 2 ? 3 : 6);
        }
    }

    public static FileDescriptor[] ancillary() throws IOException {
        if (!identityRead || rightsTaken) return null;
        rightsTaken = true;
        raw = new Held(directory.resolve("raw-fd"), 41);
        return new FileDescriptor[] { raw.fd };
    }

    public static FileDescriptor duplicate(FileDescriptor actual) throws IOException {
        if (raw == null || actual != raw.fd || !actual.valid() || dup != null) {
            throw new IOException("unexpected modeled duplicate");
        }
        dup = new Held(directory.resolve("dup-fd"), DUP_NUMBER);
        return dup.fd;
    }

    public static Held held(FileDescriptor actual) throws IOException {
        for (Held candidate : new Held[] { raw, dup, proc }) {
            if (candidate != null && actual == candidate.fd) return candidate;
        }
        throw new IOException("unknown modeled descriptor");
    }

    public static void requireProcPath(String path, String prefix) throws IOException {
        if (dup == null || !dup.fd.valid() || !path.equals(prefix + DUP_NUMBER)) {
            throw new IOException("unexpected synthetic proc path");
        }
    }

    public static FileDescriptor openProc() throws IOException {
        if (proc != null) throw new IOException("unexpected second synthetic proc open");
        proc = new Held(directory.resolve("proc-fd"), 43);
        return proc.fd;
    }

    public static int readProc(FileDescriptor fd, byte[] bytes, int offset, int size) throws IOException {
        if (proc == null || fd != proc.fd || !fd.valid()) throw new IOException("unexpected proc descriptor");
        int count = Math.min(size, PROC.length - procOffset);
        System.arraycopy(PROC, procOffset, bytes, offset, count);
        procOffset += count;
        return count;
    }

    public static void socketClosed() { socketCloses++; }

    public static void close(FileDescriptor actual) throws IOException {
        Held owner = held(actual);
        if (owner == dup) dupCloses++;
        else if (owner == raw) rawCloses++;
        else procCloses++;
        if (!actual.valid()) throw new IOException("duplicate modeled close");
        owner.stream.close();
    }

    public static boolean dupLive() { return dup != null && dup.fd.valid(); }

    public static short poll(FileDescriptor actual, int timeout) throws InterruptedException {
        if (dup == null || actual != dup.fd || !actual.valid()) throw new AssertionError("wrong watched descriptor");
        if (timeout == 0) return 0;
        if (watcher != null) throw new AssertionError("unexpected second modeled watcher poll");
        watcher = Thread.currentThread();
        watcherPolls++;
        pollEntered.countDown();
        if (!releasePoll.await(40, TimeUnit.SECONDS)) throw new AssertionError("modeled exit gate timed out");
        if (pollEvents != OsConstants.POLLIN && pollEvents != (OsConstants.POLLIN | OsConstants.POLLERR)) {
            throw new AssertionError("unexpected scripted exit bits");
        }
        return pollEvents;
    }

    public static boolean exchangeComplete() { return nextSequence == 4 && reply == null; }

    public static void cleanup() throws IOException {
        for (Held candidate : new Held[] { raw, dup, proc }) if (candidate != null) candidate.stream.close();
        for (String leaf : new String[] { "raw-fd", "dup-fd", "proc-fd" }) Files.deleteIfExists(directory.resolve(leaf));
    }
}
