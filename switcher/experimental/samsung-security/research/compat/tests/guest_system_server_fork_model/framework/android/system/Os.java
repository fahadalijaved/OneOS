package android.system;
import java.io.*;
import java.nio.file.*;
import model.ForkControl;
public final class Os {
    private static String role(Path path) throws IOException {
        String expected="system/oneos-guest-system-server-fork-capture";
        String relative=ForkControl.data().relativize(ForkControl.owned(path)).toString().replace('\\','/');
        if(relative.equals(expected))return "directory";
        if(relative.equals(expected+"/request-v1"))return "request";
        throw new IOException("unexpected fixture permit path");
    }
    private static StructStat stat(String role) throws IOException {
        return role.equals("directory") ? new StructStat(1,0040750,0)
            : new StructStat(2,0100440,Files.size(ForkControl.owned(ForkControl.data().resolve("system/oneos-guest-system-server-fork-capture/request-v1"))));
    }
    public static StructStat lstat(String path) throws IOException { return stat(role(Paths.get(path))); }
    public static FileDescriptor open(String path,int flags,int mode) throws IOException {
        if(flags!=(OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK) || mode!=0)
            throw new IOException("fixture flags changed");
        String role=role(Paths.get(path));
        Path backing=role.equals("directory") ? ForkControl.data().resolve("directory-fd") : Paths.get(path);
        FileInputStream input=new FileInputStream(ForkControl.owned(backing).toFile());
        FileDescriptor fd=input.getFD();ForkControl.handles.put(fd,new ForkControl.Handle(input,role));ForkControl.permitOpens++;
        return fd;
    }
    public static StructStat fstat(FileDescriptor fd) throws IOException {
        ForkControl.Handle handle=ForkControl.handles.get(fd);
        if(handle==null || !fd.valid())throw new IOException("unknown fixture descriptor");
        return stat(handle.role);
    }
    public static int read(FileDescriptor fd,byte[] bytes,int offset,int count) throws IOException {
        ForkControl.Handle handle=ForkControl.handles.get(fd);
        if(handle==null || !handle.role.equals("request"))throw new IOException("not request");
        int got=handle.stream.read(bytes,offset,count);return got<0?0:got;
    }
    public static void close(FileDescriptor fd) throws IOException {
        ForkControl.Handle handle=ForkControl.handles.get(fd);
        if(handle==null) { ForkControl.selfCloses++; return; } // modeled invalid self FD
        if(handle.role.equals("self")) { ForkControl.selfCloses++; if(ForkControl.throwSelfClose)throw new IOException("modeled uncertain close"); }
        else if(handle.role.equals("request")) { ForkControl.requestCloses++; if(ForkControl.throwPermitClose)throw new IOException("modeled permit close fault"); }
        else ForkControl.directoryCloses++;
        handle.stream.close();
    }
}
