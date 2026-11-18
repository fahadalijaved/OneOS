package com.android.server.locksettings;

import com.android.internal.widget.ICheckCredentialProgressCallback;
import com.android.internal.widget.LockscreenCredential;
import com.android.internal.widget.VerifyCredentialResponse;

/** Compile-only projection of the selected public guest LSS method. */
public abstract class LockSettingsService {
    public abstract VerifyCredentialResponse checkCredential(LockscreenCredential credential,
            int userId, ICheckCredentialProgressCallback callback);
}
