package android.os;
/** Authored API model. Not Binder/kernel implementation. */
public interface IBinder {
    int FIRST_CALL_TRANSACTION = 1;
    int FLAG_ONEWAY = 1;
    IInterface queryLocalInterface(String descriptor);
    boolean transact(int code, Parcel request, Parcel reply, int flags) throws RemoteException;
}
