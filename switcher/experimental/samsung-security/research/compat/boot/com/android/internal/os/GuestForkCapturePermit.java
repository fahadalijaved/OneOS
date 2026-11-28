package com.android.internal.os;

import android.os.Environment;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import java.io.File;
import java.io.FileDescriptor;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Fixed read-only operator request. It grants capture, never source authority. */
final class GuestForkCapturePermit {
    private static final String MARKER = "CAPTURE_GUEST_SYSTEM_SERVER_FORK_V1\n";
    private FileDescriptor directory;
    private FileDescriptor request;
    private boolean readAttempted;
    private boolean requestCloseAttempted;
    private boolean directoryCloseAttempted;
    private boolean closeUncertain;

    GuestForkCapturePermit() { }

    boolean readAndClose() {
        if (readAttempted) return false;
        readAttempted = true;
        boolean valid = false;
        try {
            byte[] marker = MARKER.getBytes(StandardCharsets.US_ASCII);
            File data = Environment.getDataDirectory();
            if (data == null) throw new IllegalStateException();
            String path = new File(data,
                    "system/oneos-guest-system-server-fork-capture").getPath();
            String file = new File(path, "request-v1").getPath();
            StructStat namedDirectory = Os.lstat(path);
            requireDirectory(namedDirectory);
            directory = Os.open(path, OsConstants.O_RDONLY | OsConstants.O_NOFOLLOW
                    | OsConstants.O_CLOEXEC | OsConstants.O_NONBLOCK, 0);
            StructStat heldDirectory = Os.fstat(directory);
            requireDirectory(heldDirectory);
            same(namedDirectory, heldDirectory);
            request = Os.open(file, OsConstants.O_RDONLY | OsConstants.O_NOFOLLOW
                    | OsConstants.O_CLOEXEC | OsConstants.O_NONBLOCK, 0);
            StructStat before = Os.fstat(request);
            requireRequest(before, marker.length);
            byte[] read = new byte[marker.length + 1];
            int used = 0;
            for (int calls = 0; calls <= marker.length && used < read.length; calls++) {
                int count = Os.read(request, read, used, read.length - used);
                if (count == 0) break;
                if (count < 0 || count > read.length - used) throw new IllegalStateException();
                used += count;
            }
            if (used != marker.length || !Arrays.equals(marker, Arrays.copyOf(read, used)))
                throw new IllegalStateException();
            if (Os.read(request, read, 0, 1) != 0) throw new IllegalStateException();
            StructStat after = Os.fstat(request);
            requireRequest(after, marker.length);
            same(before, after);
            StructStat namedRequest = Os.lstat(file);
            requireRequest(namedRequest, marker.length);
            same(before, namedRequest);
            StructStat finalDirectory = Os.lstat(path);
            requireDirectory(finalDirectory);
            same(heldDirectory, finalDirectory);
            same(heldDirectory, Os.fstat(directory));
            valid = true;
        } catch (Throwable ignored) { valid = false; }
        finally { if (!closeOwned()) valid = false; }
        return valid;
    }

    private boolean closeOwned() {
        if (request != null && !requestCloseAttempted) {
            requestCloseAttempted = true;
            try { Os.close(request); }
            catch (Throwable ignored) { closeUncertain = true; }
        }
        if (directory != null && !directoryCloseAttempted) {
            directoryCloseAttempted = true;
            try { Os.close(directory); }
            catch (Throwable ignored) { closeUncertain = true; }
        }
        // Descriptor objects and attempted flags remain retained even on uncertainty.
        return !closeUncertain;
    }

    private static void requireDirectory(StructStat stat) {
        if (!OsConstants.S_ISDIR(stat.st_mode) || (stat.st_mode & 07777) != 0750
                || stat.st_uid != 0 || stat.st_gid != 1000) throw new IllegalStateException();
    }

    private static void requireRequest(StructStat stat, int length) {
        if (!OsConstants.S_ISREG(stat.st_mode) || (stat.st_mode & 07777) != 0440
                || stat.st_uid != 0 || stat.st_gid != 1000 || stat.st_nlink != 1
                || stat.st_size != length) throw new IllegalStateException();
    }

    private static void same(StructStat first, StructStat second) {
        if (first.st_dev != second.st_dev || first.st_ino != second.st_ino
                || first.st_mode != second.st_mode || first.st_uid != second.st_uid
                || first.st_gid != second.st_gid || first.st_nlink != second.st_nlink
                || first.st_size != second.st_size || first.st_mtime != second.st_mtime
                || first.st_ctime != second.st_ctime) throw new IllegalStateException();
    }
}
