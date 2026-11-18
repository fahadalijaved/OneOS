package android.os;

/** Thread-local Java identity model for the selected decoded entry. */
public class Binder {
    private static final class CallingState {
        int pid = Process.myPid();
        int uid = Process.myUid();
        int clears;
        int restores;
        boolean failNextGetter;
    }

    private static final ThreadLocal<CallingState> CALLING =
            ThreadLocal.withInitial(CallingState::new);

    public static void set(int pid, int uid) {
        CallingState state = CALLING.get();
        state.pid = pid;
        state.uid = uid;
    }

    public static void fail() { CALLING.get().failNextGetter = true; }
    public static int peekCallingPid() { return CALLING.get().pid; }
    public static int peekCallingUid() { return CALLING.get().uid; }
    public static int clearCalls() { return CALLING.get().clears; }
    public static int restoreCalls() { return CALLING.get().restores; }

    public static int getCallingPid() {
        CallingState state = CALLING.get();
        checkGetter(state);
        return state.pid;
    }

    public static int getCallingUid() {
        CallingState state = CALLING.get();
        checkGetter(state);
        return state.uid;
    }

    private static void checkGetter(CallingState state) {
        if (state.failNextGetter) {
            state.failNextGetter = false;
            throw new IllegalStateException("Modeled Binder identity getter failure");
        }
    }

    public static long clearCallingIdentity() {
        CallingState state = CALLING.get();
        long prior = ((long) state.uid << 32) | (state.pid & 0xffffffffL);
        state.clears++;
        set(Process.myPid(), Process.myUid());
        return prior;
    }

    public static void restoreCallingIdentity(long prior) {
        CALLING.get().restores++;
        set((int) prior, (int) (prior >>> 32));
    }
}
