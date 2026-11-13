package android.system;

import com.appleexploit.oneos.security.authority.EarlyExitFixture;
import java.io.FileDescriptor;
import java.io.IOException;
import model.NativePeerFixture;

/** Proc/close model with one scripted poll before observer birth. */
public final class Os {
    public static String readlink(String path) throws IOException {
        NativePeerFixture.requireProcPath(path, "/proc/self/fd/");
        return "anon_inode:[pidfd]";
    }

    public static FileDescriptor open(String path, int flags, int mode) throws IOException {
        NativePeerFixture.requireProcPath(path, "/proc/self/fdinfo/");
        if (flags != (OsConstants.O_RDONLY | OsConstants.O_CLOEXEC) || mode != 0) {
            throw new IOException("unexpected proc open flags");
        }
        return NativePeerFixture.openProc();
    }

    public static int read(FileDescriptor fd, byte[] bytes, int offset, int count) throws IOException {
        return NativePeerFixture.readProc(fd, bytes, offset, count);
    }

    public static void close(FileDescriptor fd) throws IOException {
        EarlyExitFixture.beforeClose(fd);
        NativePeerFixture.close(fd);
    }

    public static int poll(StructPollfd[] requested, int timeout) throws IOException, InterruptedException {
        return EarlyExitFixture.firstPoll(requested, timeout);
    }
}
