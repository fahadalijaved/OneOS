package android.net;
import java.io.*;
import model.NativePeerFixture;
/** Direct authored native-peer streams; no AF_UNIX or native process. */
public final class LocalSocket implements Closeable {
    public void connect(LocalSocketAddress address)throws IOException {
        NativePeerFixture.observe();
        if(address.getNamespace()!=LocalSocketAddress.Namespace.ABSTRACT||!NativePeerFixture.NAME.equals(address.getName()))throw new IOException("exact abstract offer required");
        NativePeerFixture.connects++;
    }
    public void connect(LocalSocketAddress address,int timeout)throws IOException { throw new UnsupportedOperationException("Samsung overload unsupported"); }
    public void setSoTimeout(int timeout)throws IOException { if(timeout<1||timeout>30000)throw new IOException("bounded frame deadline required"); }
    public Credentials getPeerCredentials(){return new Credentials(NativePeerFixture.mode.equals("wrong_peer_pid")?766:765,NativePeerFixture.mode.equals("wrong_peer_uid")?1000:0,0);}
    public InputStream getInputStream(){return new InputStream(){
        public int read()throws IOException{byte[] b=new byte[1];int n=read(b,0,1);return n<0?-1:b[0]&255;}
        public int read(byte[] b,int o,int n)throws IOException{return NativePeerFixture.read(b,o,n);}
        public void close(){throw new AssertionError("borrowed socket input must not be closed independently");}
    };}
    public OutputStream getOutputStream(){return new OutputStream(){
        public void write(int b){throw new AssertionError("actual whole-frame write required");}
        public void write(byte[] b,int o,int n)throws IOException{NativePeerFixture.write(java.util.Arrays.copyOfRange(b,o,o+n));}
        public void close(){throw new AssertionError("borrowed socket output must not be closed independently");}
    };}
    public FileDescriptor[] getAncillaryFileDescriptors()throws IOException{return NativePeerFixture.ancillary();}
    public void close(){NativePeerFixture.socketClosed();}
}
