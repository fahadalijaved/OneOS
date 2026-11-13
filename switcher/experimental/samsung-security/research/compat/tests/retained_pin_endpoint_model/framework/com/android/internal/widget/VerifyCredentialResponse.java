package com.android.internal.widget;

import android.os.Parcel;
import android.os.Parcelable;
import model.EndpointProbe;

/** Authored marker transport only; no HAT, authentication or original wire algorithm. */
public final class VerifyCredentialResponse implements Parcelable {
    public final int modelMarker;
    private VerifyCredentialResponse(int marker) { modelMarker=marker; }
    public static final Parcelable.Creator<VerifyCredentialResponse> CREATOR=new Parcelable.Creator<VerifyCredentialResponse>() {
        public VerifyCredentialResponse createFromParcel(Parcel data) {
            EndpointProbe.responseReads.incrementAndGet();EndpointProbe.hit("response.read");
            return new VerifyCredentialResponse(data.readInt());
        }
        public VerifyCredentialResponse[] newArray(int size) { return new VerifyCredentialResponse[size]; }
    };
    static { model.HostPinProbe.responseInitializations.incrementAndGet(); }
    public static VerifyCredentialResponse modelCreate(int marker) { return new VerifyCredentialResponse(marker); }
    public void writeToParcel(Parcel data,int flags) {
        EndpointProbe.responseWrites.incrementAndGet();EndpointProbe.responseWriterFlags=flags;
        EndpointProbe.hit("response.write");data.writeInt(modelMarker);
    }
    public int describeContents() { return 0; }
}
