        protected VerifyCredentialResponse checkCredentialFromBinder(LockscreenCredential credential,
                int userId, ICheckCredentialProgressCallback callback) throws android.os.RemoteException {
            return checkCredential(credential, userId, callback);
        }
