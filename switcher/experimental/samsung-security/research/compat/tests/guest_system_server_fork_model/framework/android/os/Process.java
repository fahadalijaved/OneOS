package android.os;
import java.io.*;
import model.ForkControl;
public final class Process {
    public static int myPid() { ForkControl.pidReads++; if(ForkControl.throwPid)throw new AssertionError("modeled pid fault"); return ForkControl.pid; }
    public static FileDescriptor openPidFd(int pid,int flags) {
        if(pid!=ForkControl.pid || flags!=0)throw new AssertionError("self-only fixture call");
        try { return ForkControl.selfFd(); } catch(IOException failure) { throw new IllegalStateException(failure); }
    }
}
