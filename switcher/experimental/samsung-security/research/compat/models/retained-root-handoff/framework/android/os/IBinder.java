package android.os;
public interface IBinder {
    interface DeathRecipient { void binderDied(); }
    boolean transact(int code, Parcel data, Parcel reply, int flags) throws RemoteException;
    void linkToDeath(DeathRecipient recipient, int flags) throws RemoteException;
    boolean unlinkToDeath(DeathRecipient recipient, int flags);
}
