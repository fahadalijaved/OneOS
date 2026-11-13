package com.android.internal.widget;

/** Already-decoded case-10 arguments and the modeled trailing-data boundary. */
public final class TypedCredentialCall {
    final LockscreenCredential credential;
    final int userId;
    final ICheckCredentialProgressCallback callback;
    private final boolean trailingData;

    public TypedCredentialCall(LockscreenCredential credential, int userId,
            ICheckCredentialProgressCallback callback) {
        this(credential, userId, callback, false);
    }

    public TypedCredentialCall(LockscreenCredential credential, int userId,
            ICheckCredentialProgressCallback callback, boolean trailingData) {
        this.credential = credential;
        this.userId = userId;
        this.callback = callback;
        this.trailingData = trailingData;
    }

    void enforceNoDataAvail() {
        if (trailingData) throw new IllegalArgumentException("Modeled trailing case-10 data");
    }
}
