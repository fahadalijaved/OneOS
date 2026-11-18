package android.os;

import java.util.concurrent.TimeUnit;

public final class SystemClock {
    private static final long ORIGIN = System.nanoTime();

    public static long elapsedRealtime() {
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - ORIGIN);
    }
}
