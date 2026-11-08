package android.net;
/** Synthetic peer observations from the authored socket fixture. */
public final class Credentials {
    private final int pid,uid,gid;
    public Credentials(int pid,int uid,int gid){this.pid=pid;this.uid=uid;this.gid=gid;}
    public int getPid(){return pid;}
    public int getUid(){return uid;}
    public int getGid(){return gid;}
}
