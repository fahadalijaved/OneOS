package com.android.internal.widget;

/** Credential kind and cleanup identity only. This model has no secret bytes. */
public final class LockscreenCredential {
    private final boolean pin;
    private final boolean fromParcel;
    private int cleanupCalls;

    public LockscreenCredential(boolean pin) { this(pin, true); }

    public LockscreenCredential(boolean pin, boolean fromParcel) {
        this.pin = pin;
        this.fromParcel = fromParcel;
    }

    public boolean isPin() {
        if (isZeroized()) throw new IllegalStateException("Modeled credential was zeroized");
        return pin;
    }

    public void zeroize() { cleanupCalls++; }
    public boolean isZeroized() { return cleanupCalls != 0; }
    public int zeroizeCalls() { return cleanupCalls; }

    public static void zeroizeIfFromParcel(LockscreenCredential credential) {
        if (credential != null && credential.fromParcel) credential.zeroize();
    }
}
