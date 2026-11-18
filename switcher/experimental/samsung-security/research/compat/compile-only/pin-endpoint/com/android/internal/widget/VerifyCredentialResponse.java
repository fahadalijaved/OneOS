package com.android.internal.widget;

/** Authored compiler-only ABI projection. Never package, load or execute. */
public final class VerifyCredentialResponse implements android.os.Parcelable {
    private VerifyCredentialResponse(int code, java.time.Duration timeout, byte[] hat, long handle) {
        throw new UnsupportedOperationException("compile only");
    }
    public static final android.os.Parcelable.Creator<VerifyCredentialResponse> CREATOR = null;
    public void writeToParcel(android.os.Parcel parcel, int flags) {
        throw new UnsupportedOperationException("compile only");
    }
    public int describeContents() { throw new UnsupportedOperationException("compile only"); }
}
