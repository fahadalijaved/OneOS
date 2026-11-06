package oneos.camera;

import android.media.MediaRecorder;
import android.os.Handler;
import android.os.SystemClock;
import android.util.Log;
import java.util.WeakHashMap;

/**
 * One UI's MediaRecorder reports the recording's duration while it records (info 0x385,
 * DURATION_IN_PROGRESS, in ms): first a 0, on which the camera starts its own timer
 * (RecordingSession posts its ticker), then the time so far, which the ticker shows. AOSP's
 * recorder sends none, so the timer never started. This sends the 0 just after the start and then
 * the time since the start every 500 ms, until the camera stops that recorder (the session's
 * MediaRecorder.stop() comes here first) or starts it again.
 */
public final class OneOSRecordProgress implements Runnable {
    private static final WeakHashMap<MediaRecorder, OneOSRecordProgress> ACTIVE = new WeakHashMap<>();
    private final MediaRecorder.OnInfoListener session;
    private final MediaRecorder recorder;
    private final Handler handler;
    private final long start = SystemClock.elapsedRealtime();
    private volatile boolean stopped;
    private boolean started;
    private int ticks;

    private OneOSRecordProgress(MediaRecorder.OnInfoListener session, MediaRecorder recorder, Handler handler) {
        this.session = session;
        this.recorder = recorder;
        this.handler = handler;
    }

    public static void start(MediaRecorder.OnInfoListener session, MediaRecorder recorder, Handler handler) {
        OneOSRecordProgress p = new OneOSRecordProgress(session, recorder, handler);
        synchronized (ACTIVE) {
            OneOSRecordProgress old = ACTIVE.put(recorder, p);
            if (old != null) old.stopped = true;
        }
        handler.postDelayed(p, 350);
    }

    /** The session's MediaRecorder.stop(): no more reports for this recording, then the real stop. */
    public static void stop(MediaRecorder recorder) {
        OneOSRecordProgress p;
        synchronized (ACTIVE) { p = ACTIVE.remove(recorder); }
        if (p != null) {
            p.stopped = true;
            Log.i("OneOSCamera", "recording progress: stopped after " + p.ticks + " reports");
        }
        recorder.stop();
    }

    @Override
    public void run() {
        if (stopped) return;
        long ms = SystemClock.elapsedRealtime() - start;
        try {
            session.onInfo(recorder, 0x385, started ? (int) Math.max(ms, 1) : 0);
        } catch (RuntimeException e) {
            Log.w("OneOSCamera", "recording progress report failed", e);
            return;
        }
        started = true;
        ticks++;
        if (ms < 12L * 3600 * 1000) handler.postDelayed(this, started && ticks == 1 ? 150 : 500);
    }
}
