package android.os;

/** ThreadLocal identity contract model only, not Binder/kernel code. */
public class Binder implements IBinder {
    private static final ThreadLocal<Long> identity = new ThreadLocal<Long>() {
        @Override protected Long initialValue() { return Long.valueOf(0x123456789abL); }
    };
    public static int clears, restores;
    public static long lastRestored;
    public static Throwable clearFailure, restoreFailure;
    public static Runnable afterRestore;
    public static void modelReset() {
        clears=restores=0; lastRestored=0;
        clearFailure=restoreFailure=null; afterRestore=null;
        identity.set(Long.valueOf(0x123456789abL));
    }
    public static long modelIdentity() { return identity.get().longValue(); }
    @SuppressWarnings("unchecked")
    private static <T extends Throwable> void raise(Throwable failure) throws T {
        throw (T) failure;
    }
    public static void modelThrow(Throwable failure) {
        if (failure != null) Binder.<RuntimeException>raise(failure);
    }
    public static long clearCallingIdentity() {
        clears++;
        Throwable failure=clearFailure; clearFailure=null;
        modelThrow(failure);
        long previous=modelIdentity(); identity.set(Long.valueOf(0));
        return previous;
    }
    public static void restoreCallingIdentity(long previous) {
        restores++; lastRestored=previous; identity.set(Long.valueOf(previous));
        Runnable hook=afterRestore; afterRestore=null;
        if(hook!=null) hook.run();
        Throwable failure=restoreFailure; restoreFailure=null;
        // The selected failure is after modeled restore, not a native guarantee.
        modelThrow(failure);
    }
}
