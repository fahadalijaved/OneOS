package com.android.internal.widget;

import android.os.Parcel;
import android.os.Parcelable;
import model.EndpointProbe;

/** Authored boolean token/lifetime model. No PIN bytes or original codec implementation. */
public class LockscreenCredential implements Parcelable, AutoCloseable {
    private final boolean pin, parcel;
    private boolean zeroized, closed;
    private LockscreenCredential(boolean pin, boolean parcel) {
        this.pin=pin;this.parcel=parcel;model.HostPinProbe.pinConstructions.incrementAndGet();
    }
    public static final Parcelable.Creator<LockscreenCredential> CREATOR = new Parcelable.Creator<LockscreenCredential>() {
        public LockscreenCredential createFromParcel(Parcel data) {
            EndpointProbe.hit("pin.decode");
            LockscreenCredential value=new LockscreenCredential(data.readInt()!=0,true);
            EndpointProbe.decoded.incrementAndGet();EndpointProbe.lastDecoded=value;return value;
        }
        public LockscreenCredential[] newArray(int size) { return new LockscreenCredential[size]; }
    };
    static { model.HostPinProbe.pinInitializations.incrementAndGet(); }
    public static LockscreenCredential modelCreate(boolean pin, boolean parcel) { return new LockscreenCredential(pin,parcel); }
    public boolean isPin() {
        model.HostPinProbe.pinQueries.incrementAndGet();
        if(zeroized)throw new IllegalStateException("authored zeroized PIN");return pin;
    }
    public void writeToParcel(Parcel data,int flags) {
        EndpointProbe.hit("pin.write");data.writeInt(pin?1:0);
    }
    public int describeContents() { return 0; }
    public void modelZeroizeIfParcel() { if(parcel)zeroized=true; }
    public boolean modelZeroized() { return zeroized; }
    public boolean modelClosed() { return closed; }
    public void close() {
        if(closed)throw new AssertionError("authored decoded PIN closed twice");closed=true;zeroized=true;
        if(parcel)EndpointProbe.hostCloses.incrementAndGet();else EndpointProbe.guestCloses.incrementAndGet();
        EndpointProbe.hit(parcel?"host.pin.close":"guest.pin.close");
    }
}
