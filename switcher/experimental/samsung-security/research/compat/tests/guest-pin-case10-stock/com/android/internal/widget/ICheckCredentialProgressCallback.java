package com.android.internal.widget;

import android.os.RemoteException;

public interface ICheckCredentialProgressCallback {
    void onCredentialVerified() throws RemoteException;
}
