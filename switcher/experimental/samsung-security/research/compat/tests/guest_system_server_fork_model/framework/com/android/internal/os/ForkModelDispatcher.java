package com.android.internal.os;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import model.ForkControl;

/** Same modeled BOOT package calls package-private APIs; no helper reflection. */
public final class ForkModelDispatcher {
    private static int checks, forkEntries, initEntries;
    private static final int[] GIDS={3,4};
    private static final int[][] LIMITS={{1,2,3}};
    private static final long[] DISABLED={7,8}, ENABLED={9};
    private static final String[] ARGV={"system_server","fixture"};
    private static void check(boolean value) { checks++;if(!value)throw new AssertionError("model check "+checks); }
    private static int fork() {
        forkEntries++;
        try {return PreparedGuestSystemServerFork.invokeOriginalForkSystemServer(1000,1000,GIDS,12,LIMITS,13L,14L);}
        finally {check(ForkControl.forks==forkEntries);}
    }
    private static Runnable handoff(ClassLoader loader) {
        initEntries++;
        Runnable result;
        try {result=PreparedGuestSystemServerFork.invokeOriginalZygoteInit(37,DISABLED,ENABLED,ARGV,loader);}
        finally {check(ForkControl.inits==initEntries);}
        check(result==ForkControl.result);
        check(ForkControl.sdk==37 && ForkControl.disabled==DISABLED && ForkControl.enabled==ENABLED
                && ForkControl.argv==ARGV && ForkControl.loader==loader);
        return result;
    }
    private static void writePermit(String marker) throws Exception {
        Path directory=ForkControl.data().resolve("system/oneos-guest-system-server-fork-capture");
        Files.createDirectories(directory);
        Files.write(directory.resolve("request-v1"),marker.getBytes(StandardCharsets.US_ASCII));
    }
    public static int runCase(int number,String repo,String data) throws Throwable {
        ForkControl.configure(Paths.get(repo),Paths.get(data));
        check(ForkControl.data().startsWith(Paths.get(repo).toRealPath().resolve("out")));
        check(ForkModelDispatcher.class.getClassLoader()!=null
                && ForkModelDispatcher.class.getClassLoader()==android.os.Process.class.getClassLoader()
                && ForkModelDispatcher.class.getClassLoader()==PreparedGuestSystemServerFork.class.getClassLoader());
        Files.write(ForkControl.data().resolve("self-fd"),new byte[]{1});
        Files.write(ForkControl.data().resolve("directory-fd"),new byte[]{2});
        Throwable primary=null;
        try {
            if(number!=3)writePermit(number==4?"WRONG\n":"CAPTURE_GUEST_SYSTEM_SERVER_FORK_V1\n");
            Error original=new AssertionError("exact original failure");
            if(number==0) {
                ForkControl.forkResult=42;check(fork()==42);
                check(ForkControl.permitOpens==0 && ForkControl.opens==0 && ForkControl.pidReads==0);
                handoff(null);check(ForkControl.selfCloses==0);
            } else if(number==1) {
                ForkControl.forkError=original;
                try { fork();throw new AssertionError("missing original exception"); }
                catch(Error actual) { check(actual==original); }
                check(ForkControl.permitOpens==0 && ForkControl.opens==0 && ForkControl.pidReads==0);
            } else {
                if(number==7)ForkControl.unsupported=true;
                if(number==8)ForkControl.throwOpen=true;
                if(number==14)ForkControl.throwPermitClose=true;
                if(number==15)ForkControl.throwPid=true;
                if(number==12)ForkControl.duringOpen=new Runnable(){public void run(){check(fork()==0);}};
                if(number==13)ForkControl.duringOpen=new Runnable(){public void run(){
                    final Throwable[] error={null};
                    Thread thread=new Thread(new Runnable(){public void run(){try{handoff(null);}catch(Throwable failure){error[0]=failure;}}},"authored-foreign");
                    thread.setDaemon(true);thread.start();
                    try {thread.join(2000);}catch(InterruptedException failure){throw new AssertionError(failure);}
                    check(!thread.isAlive() && error[0]==null);
                }};
                check(fork()==0);
                check(ForkControl.forks==(number==12?2:1));
                if(number==2 || number==10) {
                    ForkControl.initError=original;ForkControl.throwSelfClose=number==10;
                    try { handoff(null);throw new AssertionError("missing original init failure"); }
                    catch(Error actual) {check(actual==original);}
                    check(ForkControl.inits==1 && ForkControl.selfCloses==1);
                    ForkControl.initError=null;handoff(null);check(ForkControl.selfCloses==1);
                } else if(number==3 || number==4 || number==14 || number==15) {
                    handoff(null);check(ForkControl.opens==0);
                    int pidReads=ForkControl.pidReads;check(fork()==0);
                    check(ForkControl.opens==0 && ForkControl.pidReads==pidReads);
                    if(number==14)check(ForkControl.requestCloses==1 && ForkControl.directoryCloses==1);
                } else if(number==5 || number==6) {
                    check(ForkControl.opens==1 && ForkControl.selfCloses==0);
                    ClassLoader loader=number==5?null:ForkModelDispatcher.class.getClassLoader();
                    handoff(loader);check(ForkControl.selfCloses==0);
                    handoff(loader);check(ForkControl.selfCloses==1);
                    handoff(loader);check(ForkControl.selfCloses==1 && ForkControl.opens==1);
                } else if(number==7 || number==8) {
                    handoff(null);check(ForkControl.opens==1 && ForkControl.selfCloses==0);
                    check(fork()==0);handoff(null);check(ForkControl.opens==1);
                } else if(number==9) {
                    ForkControl.result=null;handoff(null);check(ForkControl.selfCloses==1);
                    handoff(null);check(ForkControl.selfCloses==1);
                } else if(number==11) {
                    ForkControl.pid++;handoff(null);check(ForkControl.selfCloses==1);
                } else if(number==12 || number==13) {
                    check(ForkControl.opens==1 && ForkControl.selfCloses==1);
                    handoff(null);check(ForkControl.selfCloses==1);
                } else throw new AssertionError("unknown case");
            }
            check(ForkControl.forks>=1 && ForkControl.uid==1000 && ForkControl.gid==1000
                    && ForkControl.gids==GIDS && ForkControl.limits==LIMITS && ForkControl.flags==12
                    && ForkControl.permitted==13L && ForkControl.effective==14L);
            check(GIDS[0]==3 && LIMITS[0][0]==1 && DISABLED[0]==7 && ENABLED[0]==9 && ARGV[0].equals("system_server"));
            check(ForkControl.runnableCalls==0);
            return checks;
        } catch(Throwable failure) {primary=failure;throw failure;}
        finally {
            try {ForkControl.cleanup();}
            catch(Throwable cleanup) {if(primary!=null)primary.addSuppressed(cleanup);else throw cleanup;}
        }
    }
}
