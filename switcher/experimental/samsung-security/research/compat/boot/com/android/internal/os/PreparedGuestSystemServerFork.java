package com.android.internal.os;

import android.os.Process;
import android.system.Os;
import java.io.FileDescriptor;

/** Source-selected BOOT observation only; no authentication or delivery API. */
final class PreparedGuestSystemServerFork {
    // No allocating field initializer or observer monitor is inherited across fork.
    private static volatile ChildRecord child;
    private static volatile boolean childSeen;

    private PreparedGuestSystemServerFork() { }

    /** Exact original nine-word ABI; all arguments are forwarded untouched. */
    static int invokeOriginalForkSystemServer(int uid, int gid, int[] gids,
            int runtimeFlags, int[][] rlimits, long permitted, long effective) {
        // No observation, permit access or owner lock precedes the original call.
        int result = Zygote.forkSystemServer(uid, gid, gids, runtimeFlags, rlimits,
                permitted, effective);
        if (result == 0) {
            try { observeZeroChild(); }
            catch (Throwable observationFailure) { failChildSafely(); }
        }
        return result;
    }

    /** Exact normal handoff ABI; returns the identical original Runnable. */
    static Runnable invokeOriginalZygoteInit(int targetSdk, long[] disabled,
            long[] enabled, String[] argv, ClassLoader actualLoader) {
        Runnable result = null;
        boolean normal = false;
        try {
            result = ZygoteInit.zygoteInit(targetSdk, disabled, enabled, argv, actualLoader);
            normal = true;
            return result;
        } finally {
            try {
                if (normal) observeNormalHandoff(result, actualLoader);
                else failChildSafely();
            } catch (Throwable observationFailure) {
                // Never replace an original return or original Throwable.
                failChildSafely();
            }
        }
    }

    private static void observeZeroChild() throws java.io.IOException {
        if (childSeen) { failChildSafely(); return; }
        childSeen = true; // A failed allocation cannot make this occurrence retryable.
        ChildRecord record = new ChildRecord(Thread.currentThread());
        child = record; // Retain before any descriptor acquisition, including the permit.
        requireBootCohort(record);
        record.selfPid = Process.myPid();
        GuestForkCapturePermit permit = new GuestForkCapturePermit();
        record.permit = permit;
        if (!permit.readAndClose()) {
            record.off = true;
            record.failed = true;
            return;
        }
        requireCurrent(record);
        // This private scalar comes only from this zero child's own Process API.
        record.selfPidfd = Process.openPidFd(record.selfPid, 0);
        // Adopt first, then check. Null is genuine unsupported/unavailable, never success.
        requireCurrent(record);
        require(record.selfPidfd != null && record.selfPidfd.valid());
        record.selfOwned = true;
    }

    private static void observeNormalHandoff(Runnable actual, ClassLoader actualLoader) {
        ChildRecord record = child;
        if (record == null || record.off) return;
        requireCurrent(record);
        require(record.selfOwned && !record.handoffSeen && actual != null);
        record.handoffSeen = true;
        requireBootCohort(record);
        requireCurrent(record);
        // No invocation, replacement or wrapper of the actual returned object.
        record.runnable = actual;
        record.actualLoader = actualLoader; // Original nullable value is preserved.
        record.linked = true;
        // failed is sticky and is never cleared by a later local observation.
        requireCurrent(record);
    }

    private static void requireCurrent(ChildRecord record) {
        require(child == record && !record.failed
                && Thread.currentThread() == record.sourceThread
                && Process.myPid() == record.selfPid);
    }

    private static void requireBootCohort(ChildRecord record) {
        // Android may expose BootClassLoader.getInstance(), rather than JDK null.
        ClassLoader boot = Process.class.getClassLoader();
        require(PreparedGuestSystemServerFork.class.getClassLoader() == boot
                && GuestForkCapturePermit.class.getClassLoader() == boot
                && Zygote.class.getClassLoader() == boot
                && ZygoteInit.class.getClassLoader() == boot);
        if (record.cohortSampled) require(record.bootLoader == boot);
        else { record.bootLoader = boot; record.cohortSampled = true; }
    }

    private static void require(boolean condition) {
        if (!condition) throw new IllegalStateException("guest fork observation unavailable");
    }

    private static void failChildSafely() {
        try {
            ChildRecord record = child;
            if (record == null) return;
            record.failed = true;
            // Initial ownership is source-thread confined. Foreign calls can poison,
            // but cannot race a close against that thread's still-returning open.
            if (Thread.currentThread() != record.sourceThread) return;
            FileDescriptor owned = record.selfPidfd;
            if (owned == null || record.closeAttempted) return;
            record.closeAttempted = true; // Never retry an uncertain close.
            try { Os.close(owned); record.closeReturned = true; }
            catch (Throwable closeFailure) { record.closeUncertain = true; }
        } catch (Throwable ignored) { /* No observer fault escapes forwarding. */ }
    }

    /** No public accessor. Strong references do not assert a live native lease. */
    private static final class ChildRecord {
        final Thread sourceThread;
        int selfPid;
        ClassLoader bootLoader;
        boolean cohortSampled;
        GuestForkCapturePermit permit;
        FileDescriptor selfPidfd;
        boolean off;
        boolean selfOwned;
        boolean handoffSeen;
        boolean linked;
        boolean closeAttempted;
        boolean closeReturned;
        boolean closeUncertain;
        volatile boolean failed;
        Runnable runnable;
        ClassLoader actualLoader;

        ChildRecord(Thread sourceThread) { this.sourceThread = sourceThread; }
    }
}
