package com.android.internal.widget;

/** Authored compiler-only ABI projection. Never package, load or execute. */
public class LockscreenCredential implements android.os.Parcelable, AutoCloseable {
    private LockscreenCredential(int type, CharSequence value) {
        throw new UnsupportedOperationException("compile only");
    }
    public static final android.os.Parcelable.Creator<LockscreenCredential> CREATOR = null;
    public boolean isPin() { throw new UnsupportedOperationException("compile only"); }
    public void writeToParcel(android.os.Parcel parcel, int flags) {
        throw new UnsupportedOperationException("compile only");
    }
    public int describeContents() { throw new UnsupportedOperationException("compile only"); }
    public void close() { throw new UnsupportedOperationException("compile only"); }
}
