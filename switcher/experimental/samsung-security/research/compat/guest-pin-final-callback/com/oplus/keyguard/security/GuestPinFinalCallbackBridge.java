package com.oplus.keyguard.security;

import android.os.AsyncTask;
import com.android.internal.widget.VerifyCredentialResponse;

/** Forwards the original final callback while observing a task-owned receipt. */
final class GuestPinFinalCallbackBridge {
    private GuestPinFinalCallbackBridge() {}

    static void forwardOriginal(GuestPinCheckRequest request, AsyncTask<?, ?, ?> actualTask,
            OplusLockPatternChecker$OplusOnCheckCallback callback, VerifyCredentialResponse response,
            int timeout, boolean duplicate) throws Throwable {
        GuestPinCheckRequest.TerminalDelivery receipt = null;
        if (request != null) {
            try {
                receipt = request.beginOriginalFinalDelivery(actualTask, callback, response, timeout, duplicate);
            } catch (Throwable observerFailure) {
                // Observation must leave the original callback reachable.
            }
        }

        Throwable callbackFailure = null;
        try {
            callback.onChecked(response, timeout, duplicate);
        } catch (Throwable failure) {
            callbackFailure = failure;
            throw failure;
        } finally {
            if (receipt != null) {
                try {
                    receipt.finish(callbackFailure);
                } catch (Throwable observerFailure) {
                    // The original return or exception owns the continuation.
                }
            }
        }
    }
}
