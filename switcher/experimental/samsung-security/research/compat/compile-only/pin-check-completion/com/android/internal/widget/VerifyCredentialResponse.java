package com.android.internal.widget;

/** Exact used ABI subset only. Never package, load or execute this declaration. */
public final class VerifyCredentialResponse implements android.os.Parcelable {
    private VerifyCredentialResponse(int code, java.time.Duration timeout, byte[] hat, long handle) {
        throw new UnsupportedOperationException("compile only");
    }
    public boolean isMatched() { throw new UnsupportedOperationException("compile only"); }
    public boolean hasTimeout() { throw new UnsupportedOperationException("compile only"); }
    public boolean isOtherError() { throw new UnsupportedOperationException("compile only"); }
    public void writeToParcel(android.os.Parcel parcel, int flags) {
        throw new UnsupportedOperationException("compile only");
    }
    public int describeContents() { throw new UnsupportedOperationException("compile only"); }
}
