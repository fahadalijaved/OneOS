package android.os;
/** Authored thread placement only, not an Android message loop. */
public final class Looper {
    private static final Looper MAIN = new Looper(Thread.currentThread());
    private final Thread thread;
    private Looper(Thread thread) { this.thread = thread; }
    public static Looper getMainLooper() { return MAIN; }
    public static Looper myLooper() { return Thread.currentThread() == MAIN.thread ? MAIN : null; }
    public Thread getThread() { return thread; }
}
