package android.os;
import java.util.ArrayList;
import java.util.List;
/** Direct synchronous dispatch and authored caller tuple, not kernel Binder. */
public class Binder implements IBinder {
    private static final ThreadLocal<int[]> CALLER = ThreadLocal.withInitial(() -> new int[]{1000,321});
    private final List<DeathRecipient> deaths = new ArrayList<DeathRecipient>();
    private volatile boolean dead;
    public static int getCallingUid() { return CALLER.get()[0]; }
    public static int getCallingPid() { return CALLER.get()[1]; }
    public static void fixtureCaller(int uid, int pid) { CALLER.set(new int[]{uid,pid}); }
    public void attachInterface(IInterface ignored, String descriptor) { }
    public void linkToDeath(DeathRecipient recipient, int flags) throws RemoteException {
        synchronized (deaths) { deaths.add(recipient); }
    }
    public boolean unlinkToDeath(DeathRecipient recipient, int flags) {
        synchronized (deaths) { return deaths.remove(recipient); }
    }
    public void fixtureDie() {
        List<DeathRecipient> copy;
        synchronized (deaths) { dead=true; copy = new ArrayList<DeathRecipient>(deaths); }
        for (DeathRecipient recipient : copy) recipient.binderDied();
    }
    protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) throws RemoteException { return false; }
    public final boolean transact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {
        if(dead)throw new RemoteException("authored Binder death");
        Parcel request = data.fixtureBorrow();
        Parcel response = reply == null ? null : Parcel.fixtureReply();
        boolean handled = onTransact(code, request, response, flags);
        if (reply != null) reply.fixtureReceive(response);
        return handled;
    }
}
