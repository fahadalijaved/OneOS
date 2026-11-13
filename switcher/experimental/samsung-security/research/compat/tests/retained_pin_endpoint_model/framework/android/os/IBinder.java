package android.os;
/** Authored API model. Not Binder/kernel implementation. */
public interface IBinder {
    int FIRST_CALL_TRANSACTION = 1;
    boolean transact(int code, Parcel request, Parcel reply, int flags) throws RemoteException;
}
