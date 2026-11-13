package com.oplus.keyguard.security;

import android.os.AsyncTask;
import android.os.RemoteException;
import com.android.internal.widget.VerifyCredentialResponse;

/** Observes the original worker exit without changing its returned response. */
final class GuestPinWorkerReturnBridge {
    private GuestPinWorkerReturnBridge() {}

    static void observeNormalWorkerReturn(GuestPinCheckRequest request, AsyncTask<?, ?, ?> task,
            VerifyCredentialResponse response) {
        if (request == null) return;
        try {
            GuestPinCheckRequest.ProgressPost post = request.observeOriginalFinal(task, response);
            if (post != null) post.post();
        } catch (Throwable observerFailure) {
            // The observation and post disposition are separate from the worker's return.
        }
    }

    static void observeCaughtWorkerReturn(GuestPinCheckRequest request, AsyncTask<?, ?, ?> task,
            VerifyCredentialResponse carriedResponse, RemoteException failure) {
        if (request == null) return;
        try {
            request.observeCaughtOriginalRemoteFailure(task, carriedResponse, failure);
        } catch (Throwable observerFailure) {
            // Preserve the original catch continuation and its carried response.
        }
    }
}
