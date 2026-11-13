package android.system;

import java.io.FileDescriptor;
import java.io.IOException;
import model.NativePeerFixture;

/** Synthetic proc and poll observations for repository-owned JDK descriptors. */
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

    public static void close(FileDescriptor fd) throws IOException { NativePeerFixture.close(fd); }

    public static int poll(StructPollfd[] requested, int timeout) throws InterruptedException {
        if (requested.length != 1 || requested[0].events != OsConstants.POLLIN
                || (timeout != 0 && timeout != 250)) {
            throw new AssertionError("unexpected poll shape");
        }
        StructPollfd descriptor = requested[0];
        descriptor.revents = NativePeerFixture.poll(descriptor.fd, timeout);
        return descriptor.revents == 0 ? 0 : 1;
    }
}
