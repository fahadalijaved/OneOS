package android.os;

/** Minimal JVM fixture with one main thread and no prepared worker loopers. */
public final class Looper {
    private static final Thread MAIN_THREAD = Thread.currentThread();
    private static final Looper MAIN = new Looper();

    private Looper() {}

    public static Looper getMainLooper() {
        return MAIN;
    }

    public static Looper myLooper() {
        return Thread.currentThread() == MAIN_THREAD ? MAIN : null;
    }
}
