package android.system;
public final class OsConstants {
    public static final int O_RDONLY=0,O_NOFOLLOW=0x20000,O_CLOEXEC=0x80000,O_NONBLOCK=0x800;
    public static boolean S_ISDIR(int mode) { return (mode&0170000)==0040000; }
    public static boolean S_ISREG(int mode) { return (mode&0170000)==0100000; }
}
