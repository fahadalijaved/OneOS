package oneos.camera;

import android.media.MediaRecorder;
import android.system.ErrnoException;
import android.system.Os;
import android.util.Log;
import java.io.FileDescriptor;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.io.RandomAccessFile;
import java.util.WeakHashMap;

/**
 * One UI's camera sets a video's orientation when recording starts, after MediaRecorder.prepare();
 * AOSP's recorder refuses every parameter once prepared (oneos.semcompat.OneOSRecorder caught it),
 * so guest videos had no rotation tag and played sideways while photos were fine (owner, 0.4.59).
 * This remembers the orientation the recorder refused and the recording's output (a path or a
 * descriptor), and after the camera's stop (OneOSRecordProgress.stop, then the real stop) writes
 * it into the finished file's video track header (OneOSMp4: 36 bytes in place). The recording
 * itself is not touched; a recorder that took the orientation is left alone.
 */
public final class OneOSRotation {
    private static final String TAG = "OneOSCamera";
    private static final WeakHashMap<MediaRecorder, Object> OUT = new WeakHashMap<>();
    private static final WeakHashMap<MediaRecorder, Integer> ROT = new WeakHashMap<>();

    private OneOSRotation() {}

    public static void setOutputFile(MediaRecorder r, String path) {
        r.setOutputFile(path);
        synchronized (OUT) { OUT.put(r, path); }
    }

    public static void setOutputFile(MediaRecorder r, FileDescriptor fd) {
        r.setOutputFile(fd);
        synchronized (OUT) { OUT.put(r, fd); }
    }

    /** In place of OneOSRecorder.setOrientationHint: the recorder first, else after the stop. */
    public static void setOrientationHint(MediaRecorder r, int degrees) {
        try {
            r.setOrientationHint(degrees);
            synchronized (ROT) { ROT.remove(r); }
        } catch (RuntimeException e) {
            synchronized (ROT) { ROT.put(r, degrees); }
        }
    }

    /** In place of OneOSRecordProgress.stop: that stop, then the rotation into the file. */
    public static void stop(MediaRecorder r) {
        OneOSRecordProgress.stop(r);
        Integer deg;
        Object out;
        synchronized (ROT) { deg = ROT.remove(r); }
        synchronized (OUT) { out = OUT.get(r); }
        if (deg == null || OneOSMp4.matrix(deg) == null) return;
        if (out == null) {
            Log.w(TAG, "video rotation " + deg + ": the output is not known, not written");
            return;
        }
        try {
            boolean ok;
            if (out instanceof String) {
                try (RandomAccessFile f = new RandomAccessFile((String) out, "rw")) { ok = OneOSMp4.setRotation(file(f), deg); }
            } else {
                ok = OneOSMp4.setRotation(fd((FileDescriptor) out), deg);
            }
            Log.i(TAG, "video rotation " + deg + (ok ? " written into the video track" : ": no video track header at the identity matrix, left alone"));
        } catch (IOException | RuntimeException e) {
            Log.w(TAG, "video rotation " + deg + " not written", e);
        }
    }

    private static OneOSMp4.Io file(final RandomAccessFile f) {
        return new OneOSMp4.Io() {
            public int read(long pos, byte[] b, int n) throws IOException { f.seek(pos); return f.read(b, 0, n); }
            public void write(long pos, byte[] b) throws IOException { f.seek(pos); f.write(b); }
            public long size() throws IOException { return f.length(); }
        };
    }

    private static OneOSMp4.Io fd(final FileDescriptor fd) {
        return new OneOSMp4.Io() {
            public int read(long pos, byte[] b, int n) throws IOException {
                try { return Os.pread(fd, b, 0, n, pos); } catch (ErrnoException e) { throw new IOException(e); }
            }
            public void write(long pos, byte[] b) throws IOException {
                try {
                    if (Os.pwrite(fd, b, 0, b.length, pos) != b.length) throw new InterruptedIOException("short write");
                } catch (ErrnoException e) { throw new IOException(e); }
            }
            public long size() throws IOException {
                try { return Os.fstat(fd).st_size; } catch (ErrnoException e) { throw new IOException(e); }
            }
        };
    }
}
