package com.android.internal.widget;

import android.os.*;

/** Authored AIDL envelope only; no native Binder scheduling or delivery. */
public interface ICheckCredentialProgressCallback extends IInterface {
    void onCredentialVerified() throws RemoteException;
    abstract class Stub extends Binder implements ICheckCredentialProgressCallback {
        private static final String DESCRIPTOR="com.android.internal.widget.ICheckCredentialProgressCallback";
        public Stub(){attachInterface(this,DESCRIPTOR);}
        public IBinder asBinder(){return this;}
        public static ICheckCredentialProgressCallback asInterface(IBinder binder) {
            if(binder==null)return null;
            IInterface local=binder.queryLocalInterface(DESCRIPTOR);
            return local instanceof ICheckCredentialProgressCallback?(ICheckCredentialProgressCallback)local:new Proxy(binder);
        }
        protected boolean onTransact(int code,Parcel data,Parcel reply,int flags)throws RemoteException {
            if(code!=IBinder.FIRST_CALL_TRANSACTION)return super.onTransact(code,data,reply,flags);
            data.enforceInterface(DESCRIPTOR);onCredentialVerified();return true;
        }
        private static final class Proxy implements ICheckCredentialProgressCallback {
            private final IBinder remote;
            Proxy(IBinder remote){this.remote=remote;}
            public IBinder asBinder(){return remote;}
            public void onCredentialVerified()throws RemoteException {
                Parcel data=Parcel.obtain(remote);
                try {
                    data.writeInterfaceToken(DESCRIPTOR);
                    // The original one-way sender discards transact's boolean.
                    remote.transact(IBinder.FIRST_CALL_TRANSACTION,data,null,IBinder.FLAG_ONEWAY);
                } finally {data.recycle();}
            }
        }
    }
}
