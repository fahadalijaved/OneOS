package android.os;

import java.io.FileDescriptor;
import java.io.IOException;
import model.ForkControl;

/** Authored process model with one reentrant PID read. */
public final class Process {
    public static Runnable duringNextPidRead;

    public static int myPid() {
        ForkControl.pidReads++;
        if (ForkControl.throwPid) throw new AssertionError("modeled PID fault");
        int sampled = ForkControl.pid;
        Runnable callback = duringNextPidRead;
        duringNextPidRead = null;
        if (callback != null) callback.run();
        return sampled;
    }

    public static FileDescriptor openPidFd(int pid, int flags) {
        if (pid != ForkControl.pid || flags != 0) throw new AssertionError("expected self only");
        try {
            return ForkControl.selfFd();
        } catch (IOException failure) {
            throw new IllegalStateException(failure);
        }
    }
}
