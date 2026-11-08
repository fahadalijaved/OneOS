package model;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Authored syscall-shaped fixture controls, never Android/process evidence. */
public final class ForkControl {
    private static Path repo, data;
    public static int forkResult, forks, inits, opens, pidReads, permitOpens;
    public static int selfCloses, requestCloses, directoryCloses, runnableCalls;
    public static int pid = 1234;
    public static boolean unsupported, invalidFd, throwOpen, throwPid, throwSelfClose, throwPermitClose;
    public static Error forkError, initError;
    public static Runnable duringOpen, duringInit;
    public static int uid, gid, flags, sdk;
    public static int[] gids;
    public static int[][] limits;
    public static long permitted, effective;
    public static long[] disabled, enabled;
    public static String[] argv;
    public static ClassLoader loader;
    public static Runnable result = new Result();
    public static final IdentityHashMap<FileDescriptor, Handle> handles = new IdentityHashMap<FileDescriptor, Handle>();
    public static final class Result implements Runnable { public void run() { runnableCalls++; } }
    public static final class Handle {
        public final FileInputStream stream;
        public final String role;
        public Handle(FileInputStream stream, String role) { this.stream=stream; this.role=role; }
    }
    public static void configure(Path root,Path own) throws IOException {
        if(repo!=null || data!=null)throw new IOException("fixture already configured");
        Path normalizedRoot=root.toAbsolutePath().normalize(), normalizedOwn=own.toAbsolutePath().normalize();
        if(!normalizedOwn.startsWith(normalizedRoot.resolve("out")))throw new IOException("fixture outside repository out");
        if(!Files.isRegularFile(normalizedRoot.resolve("tools/test_guest_system_server_fork.py")))
            throw new IOException("normal repository runner marker missing");
        Path actualRoot=normalizedRoot.toRealPath(), actualOwn=normalizedOwn.toRealPath();
        if(!actualOwn.equals(normalizedOwn) || !actualOwn.startsWith(actualRoot.resolve("out")))
            throw new IOException("fixture path alias refused");
        repo=actualRoot;data=actualOwn;
    }
    public static Path data() throws IOException {
        if(data==null)throw new IOException("unconfigured fixture");return data;
    }
    public static Path owned(Path path) throws IOException {
        Path normalized=path.toAbsolutePath().normalize();
        if(repo==null || data==null || !normalized.startsWith(data))
            throw new IOException("fixture lexical path outside owned data");
        Path canonical=normalized.toRealPath();
        if (!canonical.startsWith(repo) || !canonical.startsWith(data))
            throw new IOException("fixture path outside owned repository data");
        return canonical;
    }
    public static FileDescriptor selfFd() throws IOException {
        opens++;
        if (duringOpen!=null) duringOpen.run();
        if (throwOpen) throw new IOException("modeled open fault");
        if (unsupported) return null;
        if (invalidFd) return new FileDescriptor();
        FileInputStream input=new FileInputStream(owned(data.resolve("self-fd")).toFile());
        FileDescriptor fd=input.getFD(); handles.put(fd,new Handle(input,"self")); return fd;
    }
    public static void cleanup() throws IOException {
        IOException primary=null;
        for (Handle handle:handles.values()) try { handle.stream.close(); }
        catch(IOException failure) { if(primary==null)primary=failure; else primary.addSuppressed(failure); }
        for (Handle handle:handles.values()) if(handle.stream.getChannel().isOpen())
            throw new IOException("fixture stream remained open");
        handles.clear();
        if(primary!=null)throw primary;
    }
}
