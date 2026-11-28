package com.android.internal.widget;

/** Authored result identity only, never an authentication/HAT implementation. */
public final class VerifyCredentialResponse {
    static { model.HostPinProbe.responseInitializations.incrementAndGet(); }
    public final int modelMarker;
    private VerifyCredentialResponse(int marker) { modelMarker = marker; }
    public static VerifyCredentialResponse modelCreate(int marker) {
        return new VerifyCredentialResponse(marker);
    }
}
