package model;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/** Authored fault controls/counters. No secrets, native caller or source grant. */
public final class EndpointProbe {
    public static final AtomicInteger requestObtains = new AtomicInteger();
    public static final AtomicInteger replyObtains = new AtomicInteger();
    public static final AtomicInteger requestRecycles = new AtomicInteger();
    public static final AtomicInteger replyRecycles = new AtomicInteger();
    public static final AtomicInteger borrowedRecycles = new AtomicInteger();
    public static final AtomicInteger decoded = new AtomicInteger();
    public static final AtomicInteger hostCloses = new AtomicInteger();
    public static final AtomicInteger guestCloses = new AtomicInteger();
    public static final AtomicInteger transacts = new AtomicInteger();
    public static final AtomicInteger responseWrites = new AtomicInteger();
    public static final AtomicInteger responseReads = new AtomicInteger();
    public static final AtomicInteger sensitiveMarks = new AtomicInteger();
    public static volatile Object lastDecoded;
    public static volatile int lastCode, lastFlags, responseWriterFlags;
    public static volatile boolean returnFalse, trailingRequest, trailingResponse;
    public static volatile Integer versionOverride, flagsOverride, serverUid;
    private static final Map<String, Throwable> failures = new HashMap<String, Throwable>();
    private static final Map<String, Runnable> hooks = new HashMap<String, Runnable>();
    public static synchronized void fault(String stage, Throwable failure) { failures.put(stage, failure); }
    public static synchronized void hook(String stage, Runnable action) {
        if (action == null) hooks.remove(stage); else hooks.put(stage, action);
    }
    public static void hit(String stage) {
        Runnable action; Throwable failure;
        synchronized (EndpointProbe.class) { action = hooks.get(stage); failure = failures.remove(stage); }
        if (action != null) action.run();
        android.os.Binder.modelThrow(failure);
    }
    public static long[] counters() {
        return new long[] {requestObtains.get(),replyObtains.get(),requestRecycles.get(),
            replyRecycles.get(),borrowedRecycles.get(),decoded.get(),hostCloses.get(),
            guestCloses.get(),transacts.get(),responseWrites.get(),responseReads.get(),
            sensitiveMarks.get(),lastCode,lastFlags,responseWriterFlags};
    }
}
