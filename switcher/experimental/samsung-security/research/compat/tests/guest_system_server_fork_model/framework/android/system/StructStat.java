package android.system;
public final class StructStat {
    public final long st_dev,st_ino,st_nlink,st_size,st_mtime,st_ctime;
    public final int st_mode,st_uid,st_gid;
    public StructStat(long ino,int mode,long size) {
        st_dev=1;st_ino=ino;st_mode=mode;st_uid=0;st_gid=1000;st_nlink=1;st_size=size;st_mtime=1;st_ctime=1;
    }
}
