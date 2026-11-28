package android.os;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
/** Authored typed token stream; no native exception or byte serialization claim. */
public final class Parcel {
    public static final AtomicInteger obtained = new AtomicInteger(), recycled = new AtomicInteger();
    private final List<Object> values = new ArrayList<Object>();
    private final boolean borrowed;
    private int offset;
    private boolean dead;
    private Parcel(boolean borrowed) { this.borrowed = borrowed; }
    public static Parcel obtain() { obtained.incrementAndGet(); return new Parcel(false); }
    private void live() { if (dead) throw new AssertionError("recycled parcel"); }
    private Object next() { live(); if (offset >= values.size()) throw new IllegalArgumentException("short tokens"); return values.get(offset++); }
    public void writeInterfaceToken(String value) { writeString(value); }
    public void enforceInterface(String expected) { if (!expected.equals(readString())) throw new SecurityException("descriptor"); }
    public void writeString(String value) { live(); values.add(value); }
    public String readString() { return (String) next(); }
    public void writeInt(int value) { live(); values.add(value); }
    public int readInt() { return (Integer) next(); }
    public void writeLong(long value) { live(); values.add(value); }
    public long readLong() { return (Long) next(); }
    public void writeStrongBinder(IBinder value) { live(); values.add(value); }
    public IBinder readStrongBinder() { return (IBinder) next(); }
    public void enforceNoDataAvail() { live(); if (offset != values.size()) throw new IllegalArgumentException("tail"); }
    public void writeNoException() { writeInt(0); }
    public void readException() { if (readInt() != 0) throw new IllegalStateException("modeled exception token"); }
    public void recycle() { live(); if (borrowed) throw new AssertionError("borrowed recycle"); dead = true; recycled.incrementAndGet(); }
    Parcel fixtureBorrow() { Parcel copy = new Parcel(true); copy.values.addAll(values); return copy; }
    static Parcel fixtureReply() { return new Parcel(true); }
    void fixtureReceive(Parcel other) { live(); values.clear(); values.addAll(other.values); offset = 0; }
}
