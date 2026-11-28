package android.system;
import java.io.*;
/** Synthetic proc routing plus repo-only file fixture; no host /proc or syscall. */
public final class Os {
 public static final ErrnoException closeFailure=SessionOs.closeFailure;
 public static StructStat lstat(String path)throws IOException,ErrnoException{return FixtureFileOs.lstat(path);}
 public static StructStat fstat(FileDescriptor fd)throws IOException{return FixtureFileOs.fstat(fd);}
 public static String readlink(String path)throws ErrnoException{return SessionOs.readlink(path);}
 public static FileDescriptor open(String path,int flags,int mode)throws IOException,ErrnoException{return path.startsWith("/proc/self/fdinfo/")?SessionOs.open(path,flags,mode):FixtureFileOs.open(path,flags,mode);}
 public static int read(FileDescriptor fd,byte[] b,int off,int n)throws IOException,ErrnoException{return FixtureFileOs.owns(fd)?FixtureFileOs.read(fd,b,off,n):SessionOs.read(fd,b,off,n);}
 public static void close(FileDescriptor fd)throws IOException,ErrnoException{if(FixtureFileOs.owns(fd))FixtureFileOs.close(fd);else SessionOs.close(fd);}
 public static int poll(StructPollfd[] fds,int timeout)throws ErrnoException{return SessionOs.poll(fds,timeout);}
 public static int activeDescriptors(){return FixtureFileOs.activeDescriptors();}public static void fixtureCleanup()throws IOException{FixtureFileOs.fixtureCleanup();}
}
