package android.os;

/** Fixture process identity, independent of the current Binder caller. */
public final class Process {
    private static int pid = 100;
    private static int uid = 1000;

    private Process() {}

    public static void set(int processPid, int processUid) {
        pid = processPid;
        uid = processUid;
    }

    public static int myPid() { return pid; }
    public static int myUid() { return uid; }
}
