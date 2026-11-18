package android.system;
import java.io.*;
import java.nio.charset.StandardCharsets;
import model.NativePeerFixture;
/** Repo file profile + synthetic proc/pidfd ABI, never host /proc or syscalls. */
public final class Os {
    public static StructStat lstat(String p)throws IOException,ErrnoException{return FixtureFileOs.lstat(p);}
    public static StructStat fstat(FileDescriptor fd)throws IOException{return FixtureFileOs.fstat(fd);}
    public static String readlink(String p)throws IOException{
        if(!p.matches("/proc/self/fd/[0-9]+"))throw new IOException("bounded synthetic proc only");
        NativePeerFixture.number(Integer.parseInt(p.substring(p.lastIndexOf('/')+1)));
        return NativePeerFixture.mode.equals("wrong_fd_kind")?"socket:[model]":"anon_inode:[pidfd]";
    }
    public static FileDescriptor open(String p,int flags,int mode)throws IOException,ErrnoException{
        if(!p.startsWith("/proc/self/fdinfo/"))return FixtureFileOs.open(p,flags,mode);
        if(flags!=(OsConstants.O_RDONLY|OsConstants.O_CLOEXEC)||mode!=0)throw new IOException("exact proc read profile");
        NativePeerFixture.Held h=NativePeerFixture.create("proc");
        h.metadata=("Pid:\t"+(NativePeerFixture.mode.equals("wrong_fd_target")?766:765)+"\n").getBytes(StandardCharsets.US_ASCII);
        return h.fd;
    }
    public static int read(FileDescriptor fd,byte[] b,int o,int n)throws IOException{
        if(FixtureFileOs.owns(fd))return FixtureFileOs.read(fd,b,o,n);
        NativePeerFixture.Held h=NativePeerFixture.held(fd);if(h.metadata==null)throw new IOException("not proc metadata");
        int len=Math.min(n,h.metadata.length-h.offset);System.arraycopy(h.metadata,h.offset,b,o,len);h.offset+=len;return len;
    }
    public static void close(FileDescriptor fd)throws IOException{if(FixtureFileOs.owns(fd))FixtureFileOs.close(fd);else NativePeerFixture.close(fd);}
    public static int poll(StructPollfd[] fds,int timeout)throws ErrnoException {
        NativePeerFixture.observe();if(fds.length!=1||fds[0].events!=OsConstants.POLLIN||timeout<0||timeout>250)throw new AssertionError("specific pidfd poll required");
        try{NativePeerFixture.held(fds[0].fd);}catch(IOException e){throw new AssertionError(e);}
        if(timeout>0&&NativePeerFixture.mode.equals("unexpected_poll")){fds[0].revents=16;return 1;}
        if(timeout>0&&!NativePeerFixture.exited)try{Thread.sleep(Math.min(timeout,10));}catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}
        fds[0].revents=(short)(NativePeerFixture.exited?OsConstants.POLLIN:0);return NativePeerFixture.exited?1:0;
    }
    public static int activeDescriptors(){return FixtureFileOs.activeDescriptors();}
    public static void fixtureCleanup()throws IOException{FixtureFileOs.fixtureCleanup();}
}
