package android.os;
import java.io.*;
import model.SessionModel;
/** Actual valid ordinary-file FD ownership, with explicitly synthetic pidfd semantics. */
public final class ParcelFileDescriptor implements Closeable {
    private final SessionModel.Handle owned;
    private ParcelFileDescriptor(SessionModel.Handle owned){this.owned=owned;}
    public static ParcelFileDescriptor dup(FileDescriptor source)throws IOException {
        SessionModel.handle(source);
        if(SessionModel.scenario==10)throw SessionModel.exact;
        return new ParcelFileDescriptor(SessionModel.create("dup"));
    }
    public int getFd(){return owned.number;}
    public FileDescriptor getFileDescriptor(){return owned.fd;}
    public void close()throws IOException {SessionModel.wrapperFdCloses++;if(owned.fd.valid())SessionModel.closeFd(owned.fd);}
}
