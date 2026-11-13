package android.os;

import java.util.Objects;
import java.util.concurrent.Executor;

/** Authored JVM model of the original start boundary. */
public abstract class AsyncTask<Params, Progress, Result> {
    @FunctionalInterface
    public interface StartAction {
        AsyncTask<?, ?, ?> start(AsyncTask<?, ?, ?> task, Executor executor,
                Object[] args) throws Throwable;
    }

    private StartAction startAction;

    public final void setStartAction(StartAction action) {
        startAction = Objects.requireNonNull(action);
    }

    @SafeVarargs
    @SuppressWarnings("unchecked")
    public final AsyncTask<Params, Progress, Result> executeOnExecutor(Executor executor, Params... args) {
        if (startAction == null) throw new IllegalStateException("No authored start action");
        try {
            return (AsyncTask<Params, Progress, Result>) startAction.start(this, executor, args);
        } catch (Throwable failure) {
            throw AsyncTask.<RuntimeException>exact(failure);
        }
    }

    @SuppressWarnings("unchecked")
    private static <T extends Throwable> T exact(Throwable failure) throws T {
        throw (T) failure;
    }
}
