package com.android.server.am;

import android.app.IApplicationThread;
import android.os.Binder;
import android.os.Process;

/** Closed snapshot for the ordinary AMS finish-attach edge. */
final class PreparedGuestFingerprintAttach {
    private PreparedGuestFingerprintAttach() {}

    static Observation snapshot(ProcessRecord record, IApplicationThread thread,
            long startSequence, int uid, int pid) {
        if (record == null || thread == null || startSequence <= 0 || uid <= 0 || pid <= 0) {
            return null;
        }
        try {
            ClassLoader serviceLoader = ActivityManagerService.class.getClassLoader();
            ClassLoader frameworkLoader = Binder.class.getClassLoader();
            if (PreparedGuestFingerprintAttach.class.getClassLoader() != serviceLoader
                    || ProcessRecord.class.getClassLoader() != serviceLoader
                    || record.getClass() != ProcessRecord.class
                    || IApplicationThread.class.getClassLoader() != frameworkLoader) {
                return null;
            }
            return new Observation(record, thread, Thread.currentThread(), startSequence, uid, pid);
        } catch (Throwable unavailable) {
            return null;
        }
    }

    static boolean matchesAfterRestore(Observation observation, ProcessRecord current,
            IApplicationThread currentThread, long startSequence, int uid, int pid) {
        return observation != null && observation.matches(current, currentThread, startSequence, uid, pid);
    }

    static final class Observation {
        private final ProcessRecord record;
        private final IApplicationThread thread;
        private final Thread sourceThread;
        private final long startSequence;
        private final int uid;
        private final int pid;
        private boolean consumed;

        private Observation(ProcessRecord record, IApplicationThread thread, Thread sourceThread,
                long startSequence, int uid, int pid) {
            this.record = record;
            this.thread = thread;
            this.sourceThread = sourceThread;
            this.startSequence = startSequence;
            this.uid = uid;
            this.pid = pid;
        }

        private boolean matches(ProcessRecord current, IApplicationThread currentThread,
                long startSequence, int uid, int pid) {
            if (Thread.currentThread() != sourceThread || consumed) {
                return false;
            }
            // Only the creating thread can consume this snapshot, even on a mismatch.
            consumed = true;
            if (current != record || currentThread != thread || startSequence != this.startSequence
                    || uid != this.uid || pid != this.pid) {
                return false;
            }
            try {
                return Binder.getCallingUid() == uid && Binder.getCallingPid() == pid
                        && pid != Process.myPid();
            } catch (Throwable unavailable) {
                return false;
            }
        }
    }
}
