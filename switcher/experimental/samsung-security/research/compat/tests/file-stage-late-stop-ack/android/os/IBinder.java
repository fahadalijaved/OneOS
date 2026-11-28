package android.os;

public interface IBinder {
    interface DeathRecipient { void binderDied(); }

    void linkToDeath(DeathRecipient recipient, int flags) throws RemoteException;
    boolean isBinderAlive();
    boolean transact(int code, Parcel data, Parcel reply, int flags) throws RemoteException;
}
