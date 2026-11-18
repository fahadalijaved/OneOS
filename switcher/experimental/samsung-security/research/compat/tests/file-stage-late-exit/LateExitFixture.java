package com.appleexploit.oneos.security.authority;

import android.system.OsConstants;
import com.fahadali.oneos.core.root.RetainedViewAppProtocol;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;
import model.NativePeerFixture;

/** JDK-only run of the complete authored worker using a gated modeled peer. */
public final class LateExitFixture {
    private static void require(boolean actual, String description) {
        if (!actual) throw new AssertionError(description);
    }

    private static void await(CountDownLatch latch, String description) throws InterruptedException {
        require(latch.await(4, TimeUnit.SECONDS), description);
    }

    private static void awaitJoin(Thread worker, Thread.State state) throws InterruptedException {
        long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(4);
        while (System.nanoTime() < until) {
            if (NativePeerFixture.rawCloses == 1 && NativePeerFixture.socketCloses == 1
                    && worker.getState() == state) return;
            Thread.sleep(1);
        }
        throw new AssertionError("actual worker did not reach observer join");
    }

    private static void join(Thread actual, long timeoutMillis) throws InterruptedException {
        if (actual == null) return;
        actual.join(timeoutMillis);
        require(!actual.isAlive(), "thread did not terminate: " + actual.getName());
    }

    private static void status(RetainedHostNativeControlV2 control, int expected) {
        for (int i = 0; i < 3; i++) {
            require(control.appViewStatus() == expected, "unexpected app status, expected " + expected);
        }
        require(control.cleanupComplete() == (expected == RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED),
                "cleanup status disagrees with the worker's actual cleanup observation");
    }

    private static void retained() {
        require(NativePeerFixture.dupLive() && NativePeerFixture.dupCloses == 0, "exact duplicate still retained");
        require(NativePeerFixture.rawCloses == 1 && NativePeerFixture.procCloses == 1
                && NativePeerFixture.socketCloses == 1 && NativePeerFixture.exchangeComplete(),
                "other owned resources settled with exact modeled wire exchange");
    }

    private static void run(boolean successor, boolean late, PreparedRetainedHostNativeBindingV2 owner) throws Throwable {
        RetainedHostNativeControlV2 control = owner.control;
        control.start();
        await(owner.identityProgress, "actual identity progress missing");
        await(NativePeerFixture.pollEntered, "exact watcher did not start poll");
        control.commitFromMain();
        await(owner.commitProgress, "actual COMMIT progress missing");
        control.preparePrivateViewFromMain();
        awaitJoin(owner.worker, successor ? Thread.State.WAITING : Thread.State.TIMED_WAITING);
        status(control, RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL);
        retained();
        Thread watcher = NativePeerFixture.watcher;
        require(watcher != null && watcher.isAlive() && watcher != owner.worker, "real separate observer alive");

        if (late) {
            if (successor) {
                Thread.sleep(31_000);
                require(owner.worker.isAlive() && watcher.isAlive(), "owners stay live beyond old join budget");
                status(control, RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL);
            } else {
                join(owner.worker, 32_000);
                require(watcher.isAlive(), "baseline worker stopped while its watcher remained live");
                status(control, RetainedViewAppProtocol.STATUS_CLEANUP_UNCONFIRMED);
            }
            retained();
        }

        NativePeerFixture.pollEvents = (short) (late ? OsConstants.POLLIN : OsConstants.POLLIN | OsConstants.POLLERR);
        NativePeerFixture.releasePoll.countDown();
        await(owner.watcherProgress, "exact observer never reached terminal progress callback");
        require(watcher.isAlive() && NativePeerFixture.watcherPolls == 1,
                "POLLIN or error has returned but exact watcher stack is still held");
        retained();
        if (late && successor) status(control, RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL);
        owner.releaseWatcherProgress.countDown();
        join(watcher, 4_000);
        join(owner.worker, 4_000);

        if (late && successor) {
            require(owner.failure == null && !NativePeerFixture.dupLive() && NativePeerFixture.dupCloses == 1,
                    "validated late exit closes its exact FD once after watcher ended");
            status(control, RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED);
            require(NativePeerFixture.dupCloses == 1, "status reads do not close again");
        } else {
            require(late == (owner.failure == null), "uncertain poll preserved the worker's observed failure");
            NativePeerFixture.pollEvents = (short) OsConstants.POLLIN;
            status(control, RetainedViewAppProtocol.STATUS_CLEANUP_UNCONFIRMED);
            retained();
            require(NativePeerFixture.watcherPolls == 1, "no replacement watcher or retry after terminal evidence");
        }
    }

    public static void main(String[] args) throws Throwable {
        if (args.length != 4 || !(args[0].equals("baseline") || args[0].equals("successor"))
                || !(args[1].equals("late") || args[1].equals("uncertain"))) {
            throw new IllegalArgumentException("cohort, case, repo and case directory required");
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
            run(args[0].equals("successor"), args[1].equals("late"), owner);
        } catch (Throwable failure) {
            primary = failure;
            throw failure;
        } finally {
            if (NativePeerFixture.pollEvents == 0) NativePeerFixture.pollEvents = (short) (OsConstants.POLLIN | OsConstants.POLLERR);
            NativePeerFixture.releasePoll.countDown();
            owner.releaseWatcherProgress.countDown();
            owner.control.requestClose();
            try {
                join(owner.worker, 4_000);
                join(NativePeerFixture.watcher, 4_000);
                NativePeerFixture.cleanup(); // Only the JDK fixture owns fallback cleanup.
            } catch (Throwable cleanup) {
                if (primary == null) throw cleanup;
                if (primary != cleanup) primary.addSuppressed(cleanup);
            }
        }
        System.out.println("FILE_STAGE_LATE_EXIT " + args[0] + " " + args[1] + " PASS");
    }
}

/** ABI boundary model. All status, transport and cleanup logic belongs to the actual worker. */
final class PreparedRetainedHostNativeBindingV2 {
    final RetainedHostNativeControlV2 control = new RetainedHostNativeControlV2(this, 765, NativePeerFixture.NAME);
    final CountDownLatch identityProgress = new CountDownLatch(1), commitProgress = new CountDownLatch(1);
    final CountDownLatch watcherProgress = new CountDownLatch(1), releaseWatcherProgress = new CountDownLatch(1);
    private final Thread main = Thread.currentThread();
    volatile Thread worker;
    volatile Throwable failure;

    private void exact(RetainedHostNativeControlV2 actual, Thread caller) {
        if (actual != control || Thread.currentThread() != caller) throw new AssertionError("wrong modeled owner");
    }

    void checkNativeStart(RetainedHostNativeControlV2 actual) { exact(actual, main); }
    void checkNativeCommit(RetainedHostNativeControlV2 actual) { exact(actual, main); }
    void checkNativeViewPrepare(RetainedHostNativeControlV2 actual) { exact(actual, main); }
    void checkNativeViewClose(RetainedHostNativeControlV2 actual) { exact(actual, main); }
    void checkNativeViewQuery(RetainedHostNativeControlV2 actual) { exact(actual, main); }

    void checkNativeWorkerIdentity(RetainedHostNativeControlV2 actual) {
        if (actual != control || Thread.currentThread() == main || worker != null) {
            throw new AssertionError("wrong modeled worker");
        }
        worker = Thread.currentThread();
    }

    void nativeProgress(RetainedHostNativeControlV2 actual) {
        if (Thread.currentThread() == NativePeerFixture.watcher) {
            exact(actual, NativePeerFixture.watcher);
            watcherProgress.countDown();
            try {
                if (!releaseWatcherProgress.await(4, TimeUnit.SECONDS)) throw new AssertionError("watcher callback gate expired");
            } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
                throw new AssertionError(failure);
            }
        } else {
            exact(actual, worker);
            if (actual.identityReady()) identityProgress.countDown();
            if (actual.committed()) commitProgress.countDown();
        }
    }

    void nativeFailed(RetainedHostNativeControlV2 actual, Throwable problem) {
        Thread caller = Thread.currentThread();
        exact(actual, caller == worker ? worker : NativePeerFixture.watcher);
        if (failure == null) failure = problem;
    }
}
