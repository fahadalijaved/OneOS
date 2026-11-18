package android.os;
public interface IBinder {
 int FIRST_CALL_TRANSACTION=1,INTERFACE_TRANSACTION=1598968902,FLAG_ONEWAY=1;
 interface DeathRecipient {void binderDied();}
 boolean transact(int code,Parcel data,Parcel reply,int flags)throws RemoteException;
 void linkToDeath(DeathRecipient recipient,int flags)throws RemoteException;
 boolean unlinkToDeath(DeathRecipient recipient,int flags);
 boolean isBinderAlive(); String getInterfaceDescriptor()throws RemoteException;
 IInterface queryLocalInterface(String descriptor);
}
