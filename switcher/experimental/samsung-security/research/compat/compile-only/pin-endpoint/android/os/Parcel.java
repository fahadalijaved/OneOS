package android.os;

/** Authored compiler-only ABI subset; markSensitive is source-pinned hidden ABI.
 * Never package, load or execute this projection. SDK supplies unrelated types.
 */
public final class Parcel {
    private Parcel(long nativePtr) { throw new UnsupportedOperationException("compile only"); }
    public static Parcel obtain() { throw new UnsupportedOperationException("compile only"); }
    public static Parcel obtain(IBinder binder) {
        throw new UnsupportedOperationException("compile only");
    }
    public final void markSensitive() { throw new UnsupportedOperationException("compile only"); }
    public final void writeInterfaceToken(String token) {
        throw new UnsupportedOperationException("compile only");
    }
    public final void enforceInterface(String token) {
        throw new UnsupportedOperationException("compile only");
    }
    public void enforceNoDataAvail() {
        throw new UnsupportedOperationException("compile only");
    }
    public final void writeTypedObject(Parcelable value, int flags) {
        throw new UnsupportedOperationException("compile only");
    }
    public final <T> T readTypedObject(Parcelable.Creator<T> creator) {
        throw new UnsupportedOperationException("compile only");
    }
    public final void writeInt(int value) { throw new UnsupportedOperationException("compile only"); }
    public final int readInt() { throw new UnsupportedOperationException("compile only"); }
    public final IBinder readStrongBinder() { throw new UnsupportedOperationException("compile only"); }
    public final void writeStrongBinder(IBinder binder) { throw new UnsupportedOperationException("compile only"); }
    public final void writeNoException() { throw new UnsupportedOperationException("compile only"); }
    public final void readException() { throw new UnsupportedOperationException("compile only"); }
    public final void recycle() { throw new UnsupportedOperationException("compile only"); }
}
