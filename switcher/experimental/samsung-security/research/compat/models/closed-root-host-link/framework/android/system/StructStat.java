package android.system;
/** Authored immutable metadata values, NOT host or Android ownership evidence. */
public final class StructStat {
 public final long st_dev,st_ino,st_nlink,st_size,st_mtime,st_ctime;
 public final int st_mode,st_uid,st_gid;
 public final StructTimespec st_mtim,st_ctim;
 public StructStat(long dev,long ino,int mode,int uid,int gid,long links,long size,long modified,long changed){
  st_dev=dev;st_ino=ino;st_mode=mode;st_uid=uid;st_gid=gid;st_nlink=links;st_size=size;st_mtime=modified;st_ctime=changed;st_mtim=new StructTimespec(modified,0);st_ctim=new StructTimespec(changed,0);
 }
}
