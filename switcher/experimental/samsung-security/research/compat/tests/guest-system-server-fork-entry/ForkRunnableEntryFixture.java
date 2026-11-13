package com.android.internal.os;

import android.os.Process;
import java.io.FileDescriptor;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.stream.Stream;
import model.ForkControl;

/** Authored JVM models for the exact original Runnable entry. */
public final class ForkRunnableEntryFixture {
    private static final String[] CASES = {
        "exact-normal-owner", "exact-throw-uncertain-close", "wrong-runnable-no-revival",
        "no-linked-child", "pid-read-reentry", "foreign-thread-no-revival"
    };
    private static int checks;

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
        checks++;
    }

    private static final class Original implements Runnable {
        final FileDescriptor owned;
        int calls;
        int entryCloses;
        boolean entryFdValid;
        Runnable duringFirstRun;
        RuntimeException failure;

        Original(FileDescriptor owned) {
            this.owned = owned;
        }

        @Override public void run() {
            calls++;
            entryCloses = ForkControl.selfCloses;
            entryFdValid = owned.valid();
            if (calls == 1 && duringFirstRun != null) duringFirstRun.run();
            if (failure != null) throw failure;
        }
    }

    private static FileDescriptor capture() {
        check(PreparedGuestSystemServerFork.invokeOriginalForkSystemServer(
                1000, 1000, new int[] { 3, 4 }, 12, new int[][] { { 1, 2, 3 } }, 13L, 14L) == 0,
                "zero original fork result");
        check(ForkControl.forks == 1 && ForkControl.opens == 1, "one actual original call and one fixture open");
        FileDescriptor self = null;
        for (Map.Entry<FileDescriptor, ForkControl.Handle> handle : ForkControl.handles.entrySet()) {
            if (!handle.getValue().role.equals("self")) continue;
            check(self == null, "no second self descriptor");
            self = handle.getKey();
        }
        check(self != null && self.valid() && ForkControl.selfCloses == 0, "fixture self descriptor held");
        return self;
    }

    private static void link(Original actual) {
        ForkControl.result = actual;
        check(PreparedGuestSystemServerFork.invokeOriginalZygoteInit(37, new long[0], new long[0],
                new String[] { "system_server" }, ForkRunnableEntryFixture.class.getClassLoader()) == actual,
                "identical original handoff result");
        check(ForkControl.inits == 1 && actual.calls == 0, "handoff has no Runnable invocation");
    }

    private static void invoke(Original actual) {
        PreparedGuestSystemServerFork.invokeOriginalSystemServerRunnable(actual);
    }

    private static void foreignInvoke(Original actual) {
        Throwable[] error = new Throwable[1];
        Thread worker = new Thread(() -> {
            try {
                invoke(actual);
            } catch (Throwable failure) {
                error[0] = failure;
            }
        }, "authored-foreign-entry");
        worker.setDaemon(true);
        worker.start();
        try {
            worker.join(2000);
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw new AssertionError(failure);
        }
        if (worker.isAlive()) throw new AssertionError("foreign fixture did not finish");
        if (error[0] != null) throw new AssertionError("foreign original escaped unexpectedly", error[0]);
    }

    private static void runCase(int index) {
        FileDescriptor self = capture();
        Original actual = new Original(self);
        if (index != 3) link(actual);

        switch (index) {
            case 0:
                actual.duringFirstRun = () -> {
                    check(actual.calls == 1 && actual.entryFdValid && actual.entryCloses == 0,
                            "valid original starts while the self descriptor is live");
                    invoke(actual);
                    check(actual.calls == 2 && actual.entryFdValid && actual.entryCloses == 0,
                            "nested duplicate forwards without closing the active owner's descriptor");
                    check(self.valid() && ForkControl.selfCloses == 0, "outer original retains descriptor after reentry");
                };
                invoke(actual);
                check(actual.calls == 2, "outer and nested wrapper each forward once");
                check(!self.valid() && ForkControl.selfCloses == 1, "normal return closes exact descriptor");
                invoke(actual);
                check(actual.calls == 3 && !actual.entryFdValid, "late duplicate still calls original exactly once");
                break;
            case 1:
                RuntimeException original = new RuntimeException("exact original failure");
                actual.failure = original;
                ForkControl.throwSelfClose = true;
                try {
                    invoke(actual);
                    throw new AssertionError("missing original failure");
                } catch (RuntimeException failure) {
                    check(failure == original && failure.getSuppressed().length == 0, "exact untouched original failure");
                }
                check(actual.calls == 1 && actual.entryFdValid && actual.entryCloses == 0,
                        "throwing original owns descriptor throughout its body");
                check(self.valid() && ForkControl.selfCloses == 1, "uncertain modeled close attempted once");
                actual.failure = null;
                ForkControl.throwSelfClose = false;
                invoke(actual);
                check(actual.calls == 2 && self.valid(), "duplicate original does not retry uncertain close");
                break;
            case 2:
                Original wrong = new Original(self);
                invoke(wrong);
                check(wrong.calls == 1 && actual.calls == 0, "wrong Runnable still runs exactly once");
                check(!self.valid() && ForkControl.selfCloses == 1, "wrong Runnable invalidates owner");
                invoke(actual);
                check(actual.calls == 1 && !actual.entryFdValid, "late exact identity cannot revive the owner");
                break;
            case 3:
                Original unlinked = new Original(self);
                invoke(unlinked);
                check(unlinked.calls == 1 && !self.valid(), "unlinked Runnable runs and retires captured descriptor");
                link(actual);
                invoke(actual);
                check(actual.calls == 1 && !actual.entryFdValid, "late handoff cannot revive the owner");
                break;
            case 4:
                Original duringPid = new Original(self);
                Throwable[] callbackFailure = new Throwable[1];
                Process.duringNextPidRead = () -> {
                    try {
                        foreignInvoke(duringPid);
                    } catch (Throwable failure) {
                        callbackFailure[0] = failure;
                    }
                };
                invoke(actual);
                check(callbackFailure[0] == null && Process.duringNextPidRead == null, "one nested PID observation completed");
                check(duringPid.calls == 1 && duringPid.entryFdValid && duringPid.entryCloses == 0,
                        "foreign reentry runs but cannot close the source descriptor");
                check(actual.calls == 1 && !actual.entryFdValid && actual.entryCloses == 1,
                        "stale positive PID read cannot admit original with a poisoned owner");
                break;
            case 5:
                foreignInvoke(actual);
                check(actual.calls == 1 && actual.entryFdValid && self.valid() && ForkControl.selfCloses == 0,
                        "foreign entry cannot close the source descriptor");
                invoke(actual);
                check(actual.calls == 2 && !actual.entryFdValid && actual.entryCloses == 1,
                        "late source entry still forwards after closing poisoned owner");
                break;
            default:
                throw new AssertionError("invalid fixture case");
        }
        check(ForkControl.selfCloses == 1 && ForkControl.opens == 1, "one descriptor acquisition and one close attempt");
        check(ForkControl.runnableCalls == 0, "unlinked default model Runnable never called");
    }

    public static void main(String[] args) throws Throwable {
        if (args.length != 3) throw new IllegalArgumentException("case index, repo, empty fixture directory required");
        int index = Integer.parseInt(args[0]);
        if (index < 0 || index >= CASES.length) throw new IllegalArgumentException("case outside fixture");
        ForkControl.configure(Paths.get(args[1]), Paths.get(args[2]));
        Path data = ForkControl.data();
        try (Stream<Path> entries = Files.list(data)) {
            if (entries.findAny().isPresent()) throw new IllegalArgumentException("nonempty fixture directory");
        }
        Path system = data.resolve("system");
        Path permit = system.resolve("oneos-guest-system-server-fork-capture");
        Path marker = permit.resolve("request-v1");
        Path directoryFd = data.resolve("directory-fd");
        Path selfFd = data.resolve("self-fd");
        Throwable primary = null;
        try {
            Files.createDirectory(system);
            Files.createDirectory(permit);
            Files.write(marker, "CAPTURE_GUEST_SYSTEM_SERVER_FORK_V1\n".getBytes(StandardCharsets.US_ASCII),
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            Files.write(directoryFd, new byte[] { 1 }, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            Files.write(selfFd, new byte[] { 2 }, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            runCase(index);
        } catch (Throwable failure) {
            primary = failure;
            throw failure;
        } finally {
            try {
                ForkControl.cleanup();
                for (Path path : new Path[] { marker, permit, system, directoryFd, selfFd }) Files.deleteIfExists(path);
            } catch (Throwable cleanup) {
                if (primary == null) throw cleanup;
                if (cleanup != primary) primary.addSuppressed(cleanup);
            }
        }
        System.out.println("MODEL_CASE " + index + " " + CASES[index] + " " + checks);
    }
}
