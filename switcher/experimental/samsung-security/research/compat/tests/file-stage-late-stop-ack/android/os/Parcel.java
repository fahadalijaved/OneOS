package android.os;

import java.util.ArrayList;

/** Typed local exchange with an independent read cursor at each Binder endpoint. */
public final class Parcel {
    private final ArrayList<Object> words = new ArrayList<>();
    private int cursor;
    private boolean recycled;

    public static Parcel obtain() { return new Parcel(); }
    public void writeInterfaceToken(String value) { writeString(value); }
    public void enforceInterface(String expected) {
        if (!expected.equals(readString())) throw new SecurityException("Wrong interface token");
    }
    public void writeInt(int value) { write(value); }
    public int readInt() { return (Integer) read(); }
    public void writeLong(long value) { write(value); }
    public long readLong() { return (Long) read(); }
    public void writeString(String value) { write(value); }
    public String readString() { return (String) read(); }
    public void writeStrongBinder(IBinder value) { write(value); }
    public IBinder readStrongBinder() { return (IBinder) read(); }
    public void writeNoException() { writeInt(0); }
    public void readException() {
        if (readInt() != 0) throw new IllegalStateException("Remote exception");
    }
    public void enforceNoDataAvail() {
        requireOpen();
        if (cursor != words.size()) throw new IllegalArgumentException("Trailing parcel words");
    }
    public void recycle() {
        requireOpen();
        recycled = true;
        words.clear();
    }

    private void requireOpen() {
        if (recycled) throw new IllegalStateException("Parcel was recycled");
    }
    private void write(Object value) {
        requireOpen();
        words.add(value);
    }
    private Object read() {
        requireOpen();
        return words.get(cursor++);
    }
}
