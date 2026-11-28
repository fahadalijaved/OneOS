package android.os;

import java.util.ArrayList;
import java.util.List;
import model.EndpointProbe;

/**
 * Authored typed token stream. NOT native Parcel, OEM wire/serialization,
 * sidecar or byte layout. Returned codec objects model separate ownership.
 */
public final class Parcel {
    private final List<Object> tokens = new ArrayList<Object>();
    private final String kind;
    private final boolean borrowed;
    private int position;
    private boolean recycled;
    private Parcel(String kind, boolean borrowed) { this.kind = kind; this.borrowed = borrowed; }
    public static Parcel obtain(IBinder endpoint) {
        EndpointProbe.hit("request.obtain");
        EndpointProbe.requestObtains.incrementAndGet();
        return new Parcel("request", false);
    }
    public static Parcel obtain() {
        EndpointProbe.hit("reply.obtain");
        EndpointProbe.replyObtains.incrementAndGet();
        return new Parcel("reply", false);
    }
    private void event(String operation) {
        if (recycled) throw new AssertionError("authored Parcel use after recycle");
        EndpointProbe.hit((borrowed ? "host." : "") + kind + "." + operation);
    }
    public final void markSensitive() { event("sensitive"); EndpointProbe.sensitiveMarks.incrementAndGet(); }
    public final void writeInterfaceToken(String value) { event("token.write"); tokens.add(value); }
    public final void enforceInterface(String expected) {
        event("token.read");
        if (!expected.equals(next())) throw new SecurityException("authored token mismatch");
    }
    public void enforceNoDataAvail() {
        event("trailing");
        if (position != tokens.size()) throw new IllegalArgumentException("authored trailing data");
    }
    public final void writeStrongBinder(IBinder value) {event("binder.write");tokens.add(value);}
    public final IBinder readStrongBinder() {event("binder.read");return (IBinder)next();}
    public final void writeInt(int value) { event("int.write"); tokens.add(Integer.valueOf(value)); }
    public final int readInt() { event("int.read"); return ((Integer) next()).intValue(); }
    public final void writeTypedObject(Parcelable value, int flags) {
        event("typed.write"); writeInt(value == null ? 0 : 1);
        if (value != null) value.writeToParcel(this, flags);
    }
    public final <T> T readTypedObject(Parcelable.Creator<T> creator) {
        event("typed.read"); return readInt() == 0 ? null : creator.createFromParcel(this);
    }
    public final void writeNoException() { event("exception.write"); writeInt(0); }
    public final void readException() {
        event("exception.read"); if (readInt() != 0) throw new IllegalStateException("authored error token");
    }
    public final void recycle() {
        if (borrowed) { EndpointProbe.borrowedRecycles.incrementAndGet(); throw new AssertionError("borrowed Parcel recycled"); }
        if (recycled) throw new AssertionError("owned Parcel recycled twice");
        recycled = true;
        if (kind.equals("request")) EndpointProbe.requestRecycles.incrementAndGet();
        else EndpointProbe.replyRecycles.incrementAndGet();
        EndpointProbe.hit(kind + ".recycle");
    }
    private Object next() {
        if (position >= tokens.size()) throw new IllegalArgumentException("authored truncated token stream");
        return tokens.get(position++);
    }
    Parcel modelBorrowedRequest() {
        Parcel view = new Parcel("request", true); view.tokens.addAll(tokens);
        if (EndpointProbe.versionOverride != null) view.tokens.set(1, EndpointProbe.versionOverride);
        if (EndpointProbe.trailingRequest) view.tokens.add(Integer.valueOf(44));
        return view;
    }
    Parcel modelBorrowedReply() { return new Parcel("reply", true); }
    void modelReceive(Parcel view) {
        tokens.clear(); tokens.addAll(view.tokens); position = 0;
        if (EndpointProbe.trailingResponse) tokens.add(Integer.valueOf(45));
    }
}
