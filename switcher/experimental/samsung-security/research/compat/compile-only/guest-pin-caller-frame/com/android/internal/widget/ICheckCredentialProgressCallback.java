package com.android.internal.widget;

import android.os.IInterface;
import android.os.RemoteException;

/** Compile-only declaration of the selected guest framework callback. */
public interface ICheckCredentialProgressCallback extends IInterface {
    void onCredentialVerified() throws RemoteException;
}
