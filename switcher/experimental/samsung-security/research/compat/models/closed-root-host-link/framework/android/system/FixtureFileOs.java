package android.system;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.IdentityHashMap;
/** Real bounded PC file bytes plus authored stat values. Never opens outside own data root. */
final class FixtureFileOs {
 private static final IdentityHashMap<FileDescriptor,Held> held=new IdentityHashMap<FileDescriptor,Held>();
 private static final class Held {final Path path;final FileInputStream stream;final StructStat stat;Held(Path p,FileInputStream s,StructStat st){path=p;stream=s;stat=st;}}
 private static Path path(String name)throws IOException {
  String mapped=name;
  if(name.equals("/")||name.equals("/data"))mapped=model.BootstrapProbe.dataRoot.getPath();
  else if(name.equals("/data/system"))mapped=new java.io.File(model.BootstrapProbe.dataRoot,"system").getPath();
  else if(name.equals("/data/system/oneos_retained_root_link"))mapped=new java.io.File(model.BootstrapProbe.dataRoot,"system/oneos_retained_root_link").getPath();
  Path value=model.BootstrapProbe.fixturePath(mapped);
  model.BootstrapProbe.fileOperations++;return value;
 }
 static boolean owns(FileDescriptor fd){synchronized(held){return held.containsKey(fd);}}
 private static StructStat stat(Path p)throws IOException {
  BasicFileAttributes a=Files.readAttributes(p,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
  if(!a.isDirectory()&&!a.isRegularFile())throw new IOException("regular fixture file/directory only");
  Object key=a.fileKey();long ino=key==null?p.toString().hashCode():key.hashCode();
  int mode=a.isDirectory()?0040000|0750:0100000|0440;
  return new StructStat(1,ino,mode,model.BootstrapProbe.statUid,1000,1,a.isDirectory()?0:a.size(),0,0);
 }
 public static StructStat lstat(String name)throws IOException,ErrnoException{try{return stat(path(name));}catch(java.nio.file.NoSuchFileException absent){throw new ErrnoException("lstat",OsConstants.ENOENT);}}
 public static FileDescriptor open(String name,int flags,int mode)throws IOException {
  if((flags!=(OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC)&&flags!=(OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK))||mode!=0)throw new IOException("unexpected modeled open flags");
  Path p=path(name);StructStat st=stat(p);FileInputStream input=OsConstants.S_ISREG(st.st_mode)?new FileInputStream(p.toFile()):null;
  FileDescriptor descriptor=new FileDescriptor();
  synchronized(held){if(held.size()>=32){if(input!=null)input.close();throw new IOException("fixture FD bound");}held.put(descriptor,new Held(p,input,st));}
  return descriptor;
 }
 public static StructStat fstat(FileDescriptor fd)throws IOException{synchronized(held){Held value=held.get(fd);if(value==null)throw new IOException("unknown fixture descriptor");return value.stat;}}
 public static int read(FileDescriptor fd,byte[] bytes,int offset,int length)throws IOException {
  Held value;synchronized(held){value=held.get(fd);}if(value==null||value.stream==null)throw new IOException("not own regular descriptor");
  int read=value.stream.read(bytes,offset,length);return read<0?0:read;
 }
 public static void close(FileDescriptor fd)throws IOException {
  Held value;synchronized(held){value=held.remove(fd);}if(value==null)throw new IOException("unknown fixture close");
  if(value.stream!=null)value.stream.close();
  if(model.BootstrapProbe.closeFault)throw new IOException("authored close acknowledgement failure");
 }
 public static int activeDescriptors(){synchronized(held){return held.size();}}
 /** Harness cleanup of authored PC streams only, after recording any leaked-descriptor failure. */
 public static void fixtureCleanup()throws IOException {
  java.util.ArrayList<Held> values;synchronized(held){values=new java.util.ArrayList<Held>(held.values());held.clear();}
  IOException primary=null;
  for(Held value:values)if(value.stream!=null)try{value.stream.close();}catch(IOException failure){if(primary==null)primary=failure;else primary.addSuppressed(failure);}
  if(primary!=null)throw primary;
 }
}
