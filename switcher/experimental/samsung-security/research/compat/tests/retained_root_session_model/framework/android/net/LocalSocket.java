package android.net;
import java.io.*;
import model.*;
/** Direct authored streams and synthetic peer facts; no AF_UNIX syscall. */
public final class LocalSocket implements Closeable {
    private final SessionModel.ModelSocket actual;
    public LocalSocket()throws IOException {actual=new SessionModel.ModelSocket();SessionModel.socket=actual;}
    public void connect(LocalSocketAddress address)throws IOException {
        if(address.getNamespace()!=LocalSocketAddress.Namespace.ABSTRACT || !address.getName().equals(SessionWire.ADDRESS))
            throw new IOException("unexpected modeled socket address");
    }
    public void connect(LocalSocketAddress address,int timeout)throws IOException {
        throw new UnsupportedOperationException("captured Samsung two-argument connect is unimplemented");
    }
    public void setSoTimeout(int value)throws IOException {if(value<=0 || value>30000)throw new IOException("modeled bounded timeout required");}
    public Credentials getPeerCredentials()throws IOException {
        Runnable hook=SessionModel.peerHook;if(hook!=null)hook.run();
        return new Credentials(SessionModel.scenario==5?SessionModel.nativePid+1:SessionModel.nativePid,SessionModel.scenario==4?1000:0,0);
    }
    public InputStream getInputStream(){return actual.input;}
    public OutputStream getOutputStream(){return actual.output;}
    public FileDescriptor[] getAncillaryFileDescriptors()throws IOException {
        FileDescriptor[] result=actual.input.ancillary;actual.input.ancillary=null;SessionModel.delivered(result);return result;
    }
    public void close(){actual.close();}
}
