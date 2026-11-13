package android.os;

public class Binder implements IBinder {
    public static int getCallingPid() { return 314; }
    public static int getCallingUid() { return 1000; }

    public void attachInterface(IInterface owner, String descriptor) {}
    @Override public void linkToDeath(DeathRecipient recipient, int flags) {}
    @Override public boolean isBinderAlive() { return true; }

    @Override public final boolean transact(int code, Parcel data, Parcel reply, int flags)
            throws RemoteException {
        return onTransact(code, data, reply, flags);
    }

    protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
            throws RemoteException {
        return false;
    }
}
