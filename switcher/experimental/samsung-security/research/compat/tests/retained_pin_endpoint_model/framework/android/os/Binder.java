package android.os;

import model.EndpointProbe;

/** Authored direct dispatch/identity model; no native Binder or remote exception codec. */
public class Binder implements IBinder {
    private static final ThreadLocal<Long> identity = new ThreadLocal<Long>() {
        @Override protected Long initialValue() { return Long.valueOf(0x123456789abL); }
    };
    private static final ThreadLocal<Integer> caller = new ThreadLocal<Integer>() {
        @Override protected Integer initialValue() { return Integer.valueOf(1000); }
    };
    public static int clears, restores;
    public static long lastRestored;
    public static Throwable clearFailure, restoreFailure;
    public static Runnable afterRestore;
    private String descriptor;
    public static void modelReset() {
        clears=restores=0; lastRestored=0; clearFailure=restoreFailure=null; afterRestore=null;
        identity.set(Long.valueOf(0x123456789abL)); caller.set(Integer.valueOf(1000));
    }
    public static long modelIdentity() { return identity.get().longValue(); }
    public static int getCallingUid() { return caller.get().intValue(); }
    public static int getCallingPid() { return 321; }
    public static void modelCaller(int uid) { caller.set(Integer.valueOf(uid)); }
    @SuppressWarnings("unchecked") private static <T extends Throwable> void raise(Throwable failure) throws T { throw (T) failure; }
    public static void modelThrow(Throwable failure) { if (failure != null) Binder.<RuntimeException>raise(failure); }
    public static long clearCallingIdentity() {
        clears++; Throwable failure=clearFailure; clearFailure=null; modelThrow(failure);
        long previous=modelIdentity(); identity.set(Long.valueOf(0)); return previous;
    }
    public static void restoreCallingIdentity(long previous) {
        restores++; lastRestored=previous; identity.set(Long.valueOf(previous));
        Runnable hook=afterRestore; afterRestore=null; if(hook!=null)hook.run();
        Throwable failure=restoreFailure; restoreFailure=null; modelThrow(failure);
    }
    public void attachInterface(IInterface ignoredOwner, String descriptor) { this.descriptor=descriptor; }
    protected boolean onTransact(int code, Parcel request, Parcel reply, int flags) throws RemoteException {
        return false;
    }
    public final boolean transact(int code, Parcel request, Parcel reply, int flags) throws RemoteException {
        EndpointProbe.transacts.incrementAndGet(); EndpointProbe.lastCode=code; EndpointProbe.lastFlags=flags;
        EndpointProbe.hit("transact"); if(EndpointProbe.returnFalse)return false;
        int previous=getCallingUid();
        if(EndpointProbe.serverUid!=null)modelCaller(EndpointProbe.serverUid.intValue());
        try {
            Parcel borrowedRequest=request.modelBorrowedRequest();
            Parcel borrowedReply=reply.modelBorrowedReply();
            boolean handled=onTransact(code,borrowedRequest,borrowedReply,
                EndpointProbe.flagsOverride==null?flags:EndpointProbe.flagsOverride.intValue());
            // This hook is deliberately OUTSIDE the endpoint's Java stack counter.
            // No native delivery, kernel ownership or error serialization is modeled.
            EndpointProbe.hit("framework.after.onTransact");
            reply.modelReceive(borrowedReply);return handled;
        } finally { modelCaller(previous); }
    }
}
