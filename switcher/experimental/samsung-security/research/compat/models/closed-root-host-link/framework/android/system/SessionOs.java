package android.system;
import java.io.*;
import java.nio.charset.StandardCharsets;
import model.*;
/** Whitelisted synthetic proc records and poll observations; never host /proc. */
final class SessionOs {
    public static final ErrnoException readFailure=new ErrnoException("fdinfo.read",5);
    public static final ErrnoException closeFailure=new ErrnoException("pidfd.close",5);
    public static String readlink(String path)throws ErrnoException {
        try {
            if(!path.startsWith("/proc/self/fd/"))throw new IOException();
            SessionModel.Handle h=SessionModel.number(Integer.parseInt(path.substring(14)));
            if(!h.role.equals("dup"))throw new IOException();
            return SessionModel.scenario==8?"/modeled/regular-file":"anon_inode:[pidfd]";
        }catch(Exception failure){throw new ErrnoException("readlink",9);}
    }
    public static FileDescriptor open(String path,int flags,int mode)throws ErrnoException {
        try {
            String prefix="/proc/self/fdinfo/";
            if(!path.startsWith(prefix) || flags!=(OsConstants.O_RDONLY|OsConstants.O_CLOEXEC) || mode!=0)throw new IOException();
            SessionModel.Handle target=SessionModel.number(Integer.parseInt(path.substring(prefix.length())));
            if(!target.role.equals("dup"))throw new IOException();
            SessionModel.Handle read=SessionModel.create("proc");
            String text="Pid:\t"+(SessionModel.scenario==9?SessionModel.nativePid+1:SessionModel.nativePid)+"\nNSpid:\t"+SessionModel.nativePid+"\n";
            read.bytes=text.getBytes(StandardCharsets.US_ASCII);return read.fd;
        }catch(Exception failure){throw new ErrnoException("open",9);}
    }
    public static int read(FileDescriptor fd,byte[] bytes,int offset,int count)throws ErrnoException {
        if(SessionModel.scenario==11)throw readFailure;
        try {
            SessionModel.Handle h=SessionModel.handle(fd);if(!h.role.equals("proc"))throw new IOException();
            int n=Math.min(count,h.bytes.length-h.offset);System.arraycopy(h.bytes,h.offset,bytes,offset,n);h.offset+=n;return n;
        }catch(Exception failure){throw new ErrnoException("read",9);}
    }
    public static void close(FileDescriptor fd)throws ErrnoException {
        try {SessionModel.closeFd(fd);}catch(IOException failure){if(SessionModel.scenario==16)throw closeFailure;throw new ErrnoException("close",5);}
    }
    public static int poll(StructPollfd[] items,int timeout)throws ErrnoException {
        SessionModel.polls++;SessionModel.pollEntered.countDown();
        try {
            if(items.length!=1 || items[0].events!=OsConstants.POLLIN || timeout<=0)throw new IOException();
            SessionModel.Handle h=SessionModel.handle(items[0].fd);if(!h.role.equals("dup"))throw new IOException();
            if(SessionModel.scenario==22){items[0].revents=(short)(OsConstants.POLLIN|OsConstants.POLLERR);return 1;}
            if(SessionModel.scenario==8 || SessionModel.nativeExited){items[0].revents=(short)OsConstants.POLLIN;return 1;}
            return 0;
        }catch(Exception failure){throw new ErrnoException("poll",9);}
    }
}
