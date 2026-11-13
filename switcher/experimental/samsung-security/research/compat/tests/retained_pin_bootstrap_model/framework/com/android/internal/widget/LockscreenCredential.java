package com.android.internal.widget;

/** Authored boolean/type/lifetime model. Contains no credential bytes or OEM code. */
public class LockscreenCredential {
    static { model.HostPinProbe.pinInitializations.incrementAndGet(); }
    private final boolean pin;
    private final boolean parcel;
    private boolean zeroized;
    private LockscreenCredential(boolean pin, boolean parcel) {
        this.pin = pin; this.parcel = parcel;
        model.HostPinProbe.pinConstructions.incrementAndGet();
    }
    public static LockscreenCredential modelCreate(boolean pin, boolean parcel) {
        return new LockscreenCredential(pin, parcel);
    }
    public boolean isPin() {
        model.HostPinProbe.pinQueries.incrementAndGet();
        if (zeroized) throw new IllegalStateException("authored zeroized PIN");
        return pin;
    }
    public void modelZeroizeIfParcel() { if (parcel) zeroized = true; }
    public boolean modelZeroized() { return zeroized; }
}
