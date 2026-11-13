    @Override
    protected VerifyCredentialResponse checkCredentialFromBinder(LockscreenCredential credential,
            int userId, ICheckCredentialProgressCallback callback) {
        return GuestPinCallerFrame.invokeOriginal(this, credential, userId, callback);
    }
