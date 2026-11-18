package model;

import java.util.concurrent.atomic.AtomicInteger;
import com.android.internal.widget.VerifyCredentialResponse;

/** Authored observations/faults only. No source/native/currentness admission. */
public final class HostPinProbe {
    public static final AtomicInteger calls = new AtomicInteger();
    public static final AtomicInteger pinQueries = new AtomicInteger();
    public static final AtomicInteger pinInitializations = new AtomicInteger();
    public static final AtomicInteger responseInitializations = new AtomicInteger();
    public static final AtomicInteger pinConstructions = new AtomicInteger();
    public static volatile int lastUser = -1, lastFlags = -1;
    public static volatile long callerIdentity;
    public static volatile Thread originalThread;
    public static volatile VerifyCredentialResponse response;
    public static volatile Throwable failure;
    public static volatile Runnable inside;
    public static void reset() {
        calls.set(0); pinQueries.set(0); pinConstructions.set(0);
        lastUser = lastFlags = -1; callerIdentity = -1; originalThread = null;
        response = null; failure = null; inside = null;
    }
}
