package android.os;
import java.io.*;
import model.NativePeerFixture;
/** Ordinary repository stream FD; pidfd semantics exist only in the authored Os peer. */
public final class ParcelFileDescriptor implements Closeable {
    private final NativePeerFixture.Held owned;
    private ParcelFileDescriptor(NativePeerFixture.Held h){owned=h;}
    public static ParcelFileDescriptor dup(FileDescriptor fd)throws IOException{return new ParcelFileDescriptor(NativePeerFixture.held(NativePeerFixture.duplicate(fd)));}
    public int getFd(){return owned.number;}
    public FileDescriptor getFileDescriptor(){return owned.fd;}
    public void close()throws IOException{if(owned.fd.valid())throw new IOException("direct close must first invalidate exact FD");}
}
