package com.android.internal.os;
import model.ForkControl;
public final class Zygote {
    public static int forkSystemServer(int uid,int gid,int[] gids,int flags,int[][] limits,long permitted,long effective) {
        ForkControl.forks++;ForkControl.uid=uid;ForkControl.gid=gid;ForkControl.gids=gids;ForkControl.flags=flags;
        ForkControl.limits=limits;ForkControl.permitted=permitted;ForkControl.effective=effective;
        if(ForkControl.forkError!=null)throw ForkControl.forkError;return ForkControl.forkResult;
    }
}
