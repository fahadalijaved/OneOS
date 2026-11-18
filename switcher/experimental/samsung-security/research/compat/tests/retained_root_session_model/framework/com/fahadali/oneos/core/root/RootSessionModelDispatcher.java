package com.fahadali.oneos.core.root;

import android.os.Looper;
import java.io.IOException;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import model.SessionModel;

/** Uses the real public controller API, never its private state or constructors. */
public final class RootSessionModelDispatcher {
    private static final String SHA="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private static int checks;
    private interface Action {Object run()throws Throwable;}
    private static void check(boolean value){checks++;if(!value)throw new AssertionError("session model check "+checks);}
    private static final class Job {
        final AtomicReference<Object> result=new AtomicReference<Object>();final AtomicReference<Throwable> error=new AtomicReference<Throwable>();
        final Thread thread;
        Job(final Action action){thread=new Thread(new Runnable(){public void run(){try{result.set(action.run());}catch(Throwable failure){error.set(failure);}}},"authored-session-caller");thread.setDaemon(true);}
        Object await()throws Throwable {thread.join(4000);check(!thread.isAlive());if(error.get()!=null)throw error.get();return result.get();}
    }
    private static Object worker(Action action)throws Throwable {Job job=new Job(action);job.thread.start();return job.await();}
    private static Throwable refusal(Action action)throws Throwable {try{action.run();}catch(Throwable failure){return failure;}throw new AssertionError("expected authored refusal");}
    private static RetainedRootSession.Attempt begin()throws Throwable {
        return (RetainedRootSession.Attempt)worker(new Action(){public Object run()throws Throwable{return RetainedRootSession.begin(SHA,128);}});
    }
    private static void close(final RetainedRootSession.Attempt attempt)throws Throwable {
        worker(new Action(){public Object run()throws Throwable{attempt.close();return null;}});
    }
    private static void finished()throws InterruptedException {
        Thread actual=SessionModel.workerObserved;if(actual!=null){actual.join(4000);check(!actual.isAlive());}
    }
    private static void positive(RetainedRootSession.Attempt attempt)throws Throwable {
        check(attempt==RetainedRootSession.currentAttempt());
        check(attempt.state()==RetainedRootSession.State.ADMISSION_CLOSED);
        check(SessionModel.spawns==1 && SessionModel.retainedBeforeSpawn && SessionModel.initCorrect && SessionModel.commandCorrect);
    }
    private static void noRearm()throws Throwable {
        int before=SessionModel.spawns;
        check(refusal(new Action(){public Object run()throws Throwable{return begin();}}) instanceof IllegalStateException);
        check(SessionModel.spawns==before);
    }
    public static int runCase(final int selected,String repo,String directory)throws Throwable {
        SessionModel.configure(repo,directory,selected);Looper.main=new Looper(Thread.currentThread());
        Throwable primary=null;
        try {
            if(selected==1) {
                check(refusal(new Action(){public Object run()throws Throwable{return RetainedRootSession.begin(SHA,128);}}) instanceof IllegalStateException);
                check(refusal(new Action(){public Object run()throws Throwable{return worker(new Action(){public Object run()throws Throwable{return RetainedRootSession.begin("bad",128);}});}}) instanceof IllegalArgumentException);
                check(SessionModel.spawns==0 && RetainedRootSession.currentAttempt()==null);
            } else if(selected==0) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                worker(new Action(){public Object run()throws Throwable{attempt.ping();return null;}});
                close(attempt);check(attempt.state()==RetainedRootSession.State.CLOSED);
                check(SessionModel.live()==0 && SessionModel.deliveredRaw()==1 && SessionModel.deliveredRawAttempted());
                check(SessionModel.polls==1 && SessionModel.reaps==1 && SessionModel.rawCloses==1 && SessionModel.dupCloses==1 && SessionModel.procCloses==1);
                check(SessionModel.stdinCloses==1 && SessionModel.stdoutCloses==1 && SessionModel.stderrCloses==1 && SessionModel.socketCloses==1);
                check(SessionModel.controlInCloses==0 && SessionModel.controlOutCloses==0);
                check(SessionModel.wrapperFdCloses==1);
            } else if(selected>=2 && selected<=11 || selected==17 || selected==18 || selected==23) {
                Throwable actual=refusal(new Action(){public Object run()throws Throwable{return begin();}});
                RetainedRootSession.Attempt attempt=RetainedRootSession.currentAttempt();check(attempt!=null && SessionModel.retainedBeforeSpawn);
                finished();check(attempt.state()==RetainedRootSession.State.UNRESOLVED);
                if(selected==2 || selected==10 || selected==17)check(actual==SessionModel.exact);
                if(selected==11)check(actual==android.system.Os.readFailure);
                if(selected==8)check(SessionModel.polls==0); // A regular-file POLLIN cannot be pidfd exit proof.
                if(selected==6 || selected==7 || selected==9 || selected==10 || selected==11 || selected==17)
                    check(SessionModel.deliveredRaw()>0 && SessionModel.deliveredRawAttempted());
                if(selected==7 || selected==17)check(SessionModel.deliveredRaw()==3 && SessionModel.rawCloses==3);
                if(selected==18)check(SessionModel.stdinCloses==1 && SessionModel.spawns==1 && SessionModel.reaps==1);
                if(selected==23)check(SessionModel.deliveredRaw()==0 && SessionModel.dupCloses==0);
                check(refusal(new Action(){public Object run()throws Throwable{close(RetainedRootSession.currentAttempt());return null;}})==actual);
                noRearm();
            } else if(selected==12 || selected==13 || selected==22) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                check(refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}}) instanceof IOException);
                finished();check(attempt.state()==RetainedRootSession.State.UNRESOLVED);
                if(selected==12 || selected==22)check(SessionModel.dupCloses==0 && SessionModel.live()==1);
                if(selected==13)check(!SessionModel.wrapperExited && SessionModel.stdoutCloses==0 && SessionModel.stderrCloses==0);
                noRearm();
            } else if(selected==14) {
                SessionModel.allowStderr=false;
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);attempt.requestClose();
                check(SessionModel.reapEntered.await(2,TimeUnit.SECONDS));
                check(attempt.state()!=RetainedRootSession.State.CLOSED && SessionModel.workerObserved.isAlive());
                SessionModel.allowStderr=true;SessionModel.process.wake();close(attempt);
                check(attempt.state()==RetainedRootSession.State.CLOSED && SessionModel.live()==0);
            } else if(selected==15) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                Throwable original=refusal(new Action(){public Object run()throws Throwable{return worker(new Action(){public Object run()throws Throwable{attempt.ping();return null;}});}});
                finished();check(attempt.state()==RetainedRootSession.State.UNRESOLVED && SessionModel.deliveredRaw()==2);
                check(SessionModel.deliveredRawAttempted() && SessionModel.dupCloses==0);
                check(refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}})==original);noRearm();
            } else if(selected==16) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                check(refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}})==android.system.Os.closeFailure);
                check(attempt.state()==RetainedRootSession.State.UNRESOLVED && SessionModel.wrapperFdCloses==0 && SessionModel.live()==1);noRearm();
            } else if(selected==19) {
                final boolean[] refused={false};
                SessionModel.spawnHook=new Runnable(){public void run(){SessionModel.spawnHook=null;
                    try {RetainedRootSession.begin(SHA,128);throw new AssertionError("reentrant begin admitted");}
                    catch(IllegalStateException expected){refused[0]=true;}catch(IOException failure){throw new AssertionError(failure);}}};
                RetainedRootSession.Attempt attempt=begin();positive(attempt);check(refused[0]);close(attempt);
                check(attempt.state()==RetainedRootSession.State.CLOSED);
            } else if(selected==20) {
                final boolean[] completed={false};
                SessionModel.peerHook=new Runnable(){public void run(){SessionModel.peerHook=null;
                    Thread foreign=new Thread(new Runnable(){public void run(){RetainedRootSession.currentAttempt().requestClose();completed[0]=true;}},"authored-cutoff");
                    foreign.setDaemon(true);foreign.start();try{foreign.join(1000);}catch(InterruptedException failure){throw new AssertionError(failure);}
                    if(foreign.isAlive())throw new AssertionError("framework query held controller lock");}};
                check(refusal(new Action(){public Object run()throws Throwable{return begin();}}) instanceof IOException);
                finished();check(completed[0] && RetainedRootSession.currentAttempt().state()==RetainedRootSession.State.CLOSED);
            } else if(selected==21) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                final Throwable first=refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}});
                check(attempt.state()==RetainedRootSession.State.CLOSED); // Terminal resources, but the protocol error is retained.
                check(refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}})==first);
            } else if(selected==24) {
                final RetainedRootSession.Attempt attempt=begin();positive(attempt);
                SessionModel.lateError=true;SessionModel.process.wake();
                long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(2);
                while(attempt.state()==RetainedRootSession.State.ADMISSION_CLOSED && System.nanoTime()<until)Thread.sleep(1);
                check(attempt.state()!=RetainedRootSession.State.ADMISSION_CLOSED);
                check(refusal(new Action(){public Object run()throws Throwable{close(attempt);return null;}})==SessionModel.exact);
            } else throw new AssertionError("unknown case");
            return checks;
        } catch(Throwable failure){primary=failure;throw failure;}
        finally {
            Throwable cleanup=null;
            try {RetainedRootSession.Attempt attempt=RetainedRootSession.currentAttempt();if(attempt!=null)attempt.requestClose();}
            catch(Throwable failure){cleanup=failure;}
            try{SessionModel.cleanup();}catch(Throwable failure){if(cleanup==null)cleanup=failure;else cleanup.addSuppressed(failure);}
            if(cleanup!=null){if(primary!=null)primary.addSuppressed(cleanup);else throw cleanup;}
        }
    }
}
