package android.os;

import java.io.FileDescriptor;
import java.io.IOException;

/** Missing SDK API declarations only; must never enter runtime or program DEX. */
public class Process {
    private Process() { }
    public static final int myPid() { throw new AssertionError("compiler declaration only"); }
    public static FileDescriptor openPidFd(int pid, int flags) throws IOException {
        throw new AssertionError("compiler declaration only");
    }
}
