package com.fahadali.oneos.core.root;
import java.io.IOException;
import model.SessionModel;
/** The ONLY replaced production definition: authored process fixture, never su. */
final class RetainedRootSessionSpawn {
    private RetainedRootSessionSpawn(){ }
    static Process start(String sha,long bytes)throws IOException {
        SessionModel.spawns++;SessionModel.recordThread();SessionModel.workerObserved=Thread.currentThread();
        SessionModel.retainedBeforeSpawn=RetainedRootSession.currentAttempt()!=null;
        String command=RetainedRootCommand.build(sha,bytes);
        SessionModel.commandCorrect=command.contains("exec 3<\"$P\"") && command.contains("exec \"$F\" --closed-session-v1")
            && command.contains(sha) && command.contains(" = "+bytes+" ]");
        Runnable hook=SessionModel.spawnHook;if(hook!=null)hook.run();
        SessionModel.process=new SessionModel.ModelProcess();
        if(SessionModel.scenario==2)throw SessionModel.exact;
        return SessionModel.process;
    }
}
