package com.appleexploit.oneos.security.authority;

import android.system.OsConstants;
import android.system.StructPollfd;
import com.fahadali.oneos.core.root.RetainedViewAppProtocol;
import java.io.FileDescriptor;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.stream.Stream;
import model.NativePeerFixture;

/** Actual worker with an authored terminal poll before observer construction. */
public final class EarlyExitFixture {
    private static final IOException POLL_FAILURE = new IOException("modeled initial poll failure");
    private static final IOException CLOSE_FAILURE = new IOException("modeled duplicate close uncertainty");
    private static String scenario;
    private static FileDescriptor duplicate;
    private static int polls, closeAttempts;

    private static void require(boolean condition, String description) {
        if (!condition) throw new AssertionError(description);
    }

    public static int firstPoll(StructPollfd[] requested, int timeout) throws IOException, InterruptedException {
        polls++;
        require(polls == 1 && timeout == 0 && requested.length == 1
                && requested[0].events == OsConstants.POLLIN && requested[0].revents == 0,
                "only the initial zero-timeout liveness sample is allowed");
        require(NativePeerFixture.procCloses == 1 && NativePeerFixture.dupCloses == 0,
                "exact proc identity readback is already closed");
        duplicate = requested[0].fd;
        require(NativePeerFixture.poll(duplicate, timeout) == 0, "poll must use exact validated modeled duplicate");
        if (scenario.equals("thrown-poll")) throw POLL_FAILURE;
        requested[0].revents = (short) (scenario.equals("mixed-error")
                ? OsConstants.POLLIN | OsConstants.POLLERR : OsConstants.POLLIN);
        return 1;
    }

    public static void beforeClose(FileDescriptor actual) throws IOException {
        if (actual != duplicate) return;
        closeAttempts++;
        if (scenario.equals("close-uncertain")) throw CLOSE_FAILURE;
    }

    private static void join(Thread actual) throws InterruptedException {
        actual.join(4_000);
        require(!actual.isAlive(), "fixture worker did not terminate");
    }

    private static void run(boolean successor, PreparedRetainedHostNativeBindingV2 owner) throws Throwable {
        RetainedHostNativeControlV2 control = owner.control;
        control.start();
        require(owner.started.await(4, java.util.concurrent.TimeUnit.SECONDS), "actual worker did not start");
        join(owner.worker);
        require(owner.progress == 1 && polls == 1 && NativePeerFixture.watcherPolls == 0
                && NativePeerFixture.watcher == null && !NativePeerFixture.exchangeComplete(),
                "no observer or additional liveness sample for a command was started");
        require(NativePeerFixture.connects == 1 && NativePeerFixture.socketCloses == 1
                && NativePeerFixture.rawCloses == 1 && NativePeerFixture.procCloses == 1,
                "socket, received right and proc descriptor settle once");
        require(owner.firstFailure != null, "original early liveness refusal was lost");
        if (scenario.equals("thrown-poll")) {
            require(owner.firstFailure == POLL_FAILURE, "original thrown poll failure must be retained");
        } else {
            require(owner.firstFailure instanceof IllegalStateException
                    && "Native process is not observed live".equals(owner.firstFailure.getMessage()),
                    "original early liveness refusal must remain primary");
        }

        boolean closed = successor && scenario.equals("positive");
        boolean uncertainClose = successor && scenario.equals("close-uncertain");
        int expectedAttempts = closed || uncertainClose ? 1 : 0;
        require(duplicate != null && NativePeerFixture.dupLive() != closed
                && NativePeerFixture.dupCloses == (closed ? 1 : 0),
                "exact duplicate closes only with supported, non-error evidence");
        require(owner.failures == (uncertainClose ? 2 : 1)
                && (!uncertainClose || owner.lastFailure == CLOSE_FAILURE),
                "uncertain close reports separately without replacing first failure");
        for (int sample = 0; sample < 3; sample++) {
            require(control.finished() && !control.identityReady() && !control.committed() && !control.cleanupComplete()
                    && control.appViewStatus() == RetainedViewAppProtocol.STATUS_UNAVAILABLE,
                    "pre-observer exit grants no app readiness or cleanup status");
            control.requestClose();
        }
        require(polls == 1 && closeAttempts == expectedAttempts, "no retry after refusal or ambiguous close");
    }

    public static void main(String[] args) throws Throwable {
        if (args.length != 4 || !(args[0].equals("baseline") || args[0].equals("successor"))) {
            throw new IllegalArgumentException("cohort, scenario, repo and empty case directory required");
        }
        scenario = args[1];
        if (!scenario.equals("positive") && !scenario.equals("mixed-error")
                && !scenario.equals("thrown-poll") && !scenario.equals("close-uncertain")) {
            throw new IllegalArgumentException("unknown early-exit scenario");
        }
        Path root = Paths.get(args[2]).toRealPath();
        Path selected = Paths.get(args[3]).toAbsolutePath().normalize(), data = selected.toRealPath();
        require(data.equals(selected) && data.startsWith(root.resolve("out")) && !data.equals(root.resolve("out"))
                && Files.isRegularFile(root.resolve("tools/test_retained_root_handoff.py")), "owned case directory required");
        try (Stream<Path> entries = Files.list(data)) {
            require(!entries.findAny().isPresent(), "case directory must be empty");
        }
        NativePeerFixture.configure(data);
        PreparedRetainedHostNativeBindingV2 owner = new PreparedRetainedHostNativeBindingV2();
        Throwable primary = null;
        try {
            run(args[0].equals("successor"), owner);
        } catch (Throwable failure) {
            primary = failure;
            throw failure;
        } finally {
            owner.control.requestClose();
            try {
                if (owner.worker != null) join(owner.worker);
                if (NativePeerFixture.watcher != null) join(NativePeerFixture.watcher);
                NativePeerFixture.cleanup();
            } catch (Throwable cleanup) {
                if (primary == null) throw cleanup;
                if (primary != cleanup) primary.addSuppressed(cleanup);
            }
        }
        System.out.println("FILE_STAGE_EARLY_EXIT " + args[0] + " " + scenario + " PASS");
    }
}

/** Models owner callbacks, with the complete actual worker retaining its own state. */
final class PreparedRetainedHostNativeBindingV2 {
    final RetainedHostNativeControlV2 control = new RetainedHostNativeControlV2(this, 765, NativePeerFixture.NAME);
    final java.util.concurrent.CountDownLatch started = new java.util.concurrent.CountDownLatch(1);
    private final Thread main = Thread.currentThread();
    volatile Thread worker;
    int progress, failures;
    Throwable firstFailure, lastFailure;

    void checkNativeStart(RetainedHostNativeControlV2 actual) {
        if (actual != control || Thread.currentThread() != main) throw new AssertionError("wrong modeled start");
    }

    void checkNativeCommit(RetainedHostNativeControlV2 actual) { throw new AssertionError("unexpected commit"); }
    void checkNativeViewPrepare(RetainedHostNativeControlV2 actual) { throw new AssertionError("unexpected prepare"); }
    void checkNativeViewClose(RetainedHostNativeControlV2 actual) { throw new AssertionError("unexpected view close"); }
    void checkNativeViewQuery(RetainedHostNativeControlV2 actual) { throw new AssertionError("unexpected query"); }

    void checkNativeWorkerIdentity(RetainedHostNativeControlV2 actual) {
        if (actual != control || Thread.currentThread() == main || worker != null) {
            throw new AssertionError("wrong modeled worker");
        }
        worker = Thread.currentThread();
        started.countDown();
    }

    void nativeProgress(RetainedHostNativeControlV2 actual) {
        if (actual != control || Thread.currentThread() != worker) throw new AssertionError("unexpected observer progress");
        progress++;
    }

    void nativeFailed(RetainedHostNativeControlV2 actual, Throwable problem) {
        if (actual != control || Thread.currentThread() != worker) throw new AssertionError("unexpected observer failure");
        if (failures++ == 0) firstFailure = problem;
        lastFailure = problem;
    }
}
