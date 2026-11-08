"""Derive the typed Stop status relay on the exact confirmation lifecycle service."""

from prepare_retained_writer_app import apply
from run_guest_tree_install_transport import load_io, pinned


BASE = 'out/file-stage-confirmation-lifecycle-build/r-ff4de804/app/src/'
NAME = 'RetainedRootHostServiceV2.java'
SOURCE_BYTES = 20881
SOURCE_SHA256 = '7e1b35790f832863686603de0f764a5b1947c8cba78fb1574d8c47c8e0ccc92e'

ATTEMPT = b'    /** One app-local handle. Call off the UI thread. A queued reply is only a receipt. */\n'
SAMPLE = b'''    /** One timely, typed status response from the existing app-local relay. */
    public static final class StopSample {
        public final RetainedStopStatus status;
        public final long startedElapsedMs, completedElapsedMs;

        private StopSample(RetainedStopStatus status, long started, long completed) {
            this.status = status;
            this.startedElapsedMs = started;
            this.completedElapsedMs = completed;
        }
    }

'''

OLD_CALL = b'''        int callView(int code) {
            boolean status = code == RetainedViewAppProtocol.APP_VIEW_STATUS;
            boolean stop = code == RetainedViewAppProtocol.APP_VIEW_STOP;
            int unavailable = status ? RetainedViewAppProtocol.STATUS_UNAVAILABLE
                    : RetainedViewAppProtocol.UNAVAILABLE;
            int unknown = status ? RetainedViewAppProtocol.STATUS_UNAVAILABLE
                    : RetainedViewAppProtocol.UNCERTAIN;
            if (Looper.myLooper() == Looper.getMainLooper()
                    || (!stop && Thread.currentThread().isInterrupted())) {
                return unavailable;
            }
            ViewCall call = new ViewCall(code, SystemClock.elapsedRealtime() + VIEW_WAIT_MILLIS);
            boolean startWorker;
            synchronized (lock) {
                if (!viewCurrentLocked()) return unavailable;
                if (stop) {
                    if (!viewPrepareIssued || viewStopIssued) return unavailable;
                    viewStopIssued = true;
                    // Retain the only STOP even if PREPARE/STATUS is blocked in Binder.
                    viewStop = call;
                } else {
                    if (viewWorkerFailed || viewCall != null || viewStop != null) return unavailable;
                    if (code == RetainedViewAppProtocol.APP_VIEW_PREPARE) {
                        if (viewPrepareIssued) return unavailable;
                        viewPrepareIssued = true;
                    }
                    viewCall = call;
                }
                startWorker = !viewWorkerClaimed;
                viewWorkerClaimed = true;
                lock.notifyAll();
            }
            if (startWorker) startViewWorker();
            try {
                synchronized (lock) {
                    while (!call.completed && viewCurrentLocked() && !viewWorkerFailed) {
                        long remaining = call.deadline - SystemClock.elapsedRealtime();
                        if (remaining <= 0) break;
                        lock.wait(remaining);
                    }
                    if (call.completed && viewCurrentLocked()) return call.result;
                    if (!stop) call.abandoned = true;
                }
            } catch (InterruptedException interrupted) {
                if (!stop) synchronized (lock) { call.abandoned = true; }
                Thread.currentThread().interrupt();
            }
            return unknown;
        }
'''

NEW_CALL = b'''        int callView(int code) {
            boolean status = code == RetainedViewAppProtocol.APP_VIEW_STATUS;
            ViewCall call = submitView(code, null);
            if (call == null) return status ? RetainedViewAppProtocol.STATUS_UNAVAILABLE
                    : RetainedViewAppProtocol.UNAVAILABLE;
            if (awaitView(call)) return call.result;
            return status ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : RetainedViewAppProtocol.UNCERTAIN;
        }

        StopSample stopStatus(ViewAttempt attempt) {
            ViewCall call = submitView(RetainedStopStatus.TRANSACTION, attempt);
            return call != null && awaitView(call) ? call.stopSample : null;
        }

        private ViewCall submitView(int code, ViewAttempt attempt) {
            boolean stop = code == RetainedViewAppProtocol.APP_VIEW_STOP;
            if (Looper.myLooper() == Looper.getMainLooper()
                    || (!stop && Thread.currentThread().isInterrupted())) return null;
            long now = SystemClock.elapsedRealtime();
            if (attempt != null && (now < 0 || now > Long.MAX_VALUE - VIEW_WAIT_MILLIS)) return null;
            ViewCall call = new ViewCall(code, now + VIEW_WAIT_MILLIS, attempt);
            boolean startWorker;
            synchronized (lock) {
                if (!viewCurrentLocked() || (attempt != null && viewAttempt != attempt)) return null;
                if (stop) {
                    if (!viewPrepareIssued || viewStopIssued) return null;
                    viewStopIssued = true;
                    // Retain the only STOP even if PREPARE/STATUS is blocked in Binder.
                    viewStop = call;
                } else {
                    if (viewWorkerFailed || viewCall != null || viewStop != null) return null;
                    if (code == RetainedViewAppProtocol.APP_VIEW_PREPARE) {
                        if (viewPrepareIssued) return null;
                        viewPrepareIssued = true;
                    }
                    viewCall = call;
                }
                startWorker = !viewWorkerClaimed;
                viewWorkerClaimed = true;
                lock.notifyAll();
            }
            if (startWorker) startViewWorker();
            return call;
        }

        private boolean awaitView(ViewCall call) {
            boolean stop = call.code == RetainedViewAppProtocol.APP_VIEW_STOP;
            try {
                synchronized (lock) {
                    while (!call.completed && viewCurrentLocked() && !viewWorkerFailed) {
                        long remaining = call.deadline - SystemClock.elapsedRealtime();
                        if (remaining <= 0) break;
                        lock.wait(remaining);
                    }
                    if (call.completed && viewCurrentLocked() && (call.attempt == null ||
                            (viewAttempt == call.attempt && !call.abandoned
                                    && SystemClock.elapsedRealtime() < call.deadline))) return true;
                    if (!stop) call.abandoned = true;
                }
            } catch (InterruptedException interrupted) {
                if (!stop) synchronized (lock) { call.abandoned = true; }
                Thread.currentThread().interrupt();
            }
            return false;
        }
'''

OLD_REPLY = b'''                        int value = reply.readInt();
                        reply.enforceNoDataAvail();
                        if (!(status ? RetainedViewAppProtocol.isStatus(value)
                                : RetainedViewAppProtocol.isMutationReply(value))) {
                            throw new IllegalStateException("V2 view relay reply differs");
                        }
                        result = value;
'''

NEW_REPLY = b'''                        if (typed) {
                            RetainedStopStatus observed = RetainedStopStatus.read(reply);
                            long completed = SystemClock.elapsedRealtime();
                            if (observed != null && completed >= started && completed < call.deadline
                                    && (observed.role == null || observed.role.appPid == android.os.Process.myPid())
                                    && callback.isBinderAlive()) sample = new StopSample(observed, started, completed);
                        } else {
                            int value = reply.readInt();
                            reply.enforceNoDataAvail();
                            if (!(status ? RetainedViewAppProtocol.isStatus(value)
                                    : RetainedViewAppProtocol.isMutationReply(value))) {
                                throw new IllegalStateException("V2 view relay reply differs");
                            }
                            result = value;
                        }
'''

EDITS = (
    (ATTEMPT, SAMPLE + ATTEMPT, 1),
    (b'        public int status() { return owner.callView(RetainedViewAppProtocol.APP_VIEW_STATUS); }\n',
     b'        public int status() { return owner.callView(RetainedViewAppProtocol.APP_VIEW_STATUS); }\n'
     b'        public StopSample stopStatus() { return owner.stopStatus(this); }\n', 1),
    (b'''            final long deadline;
            boolean abandoned, completed;
            int result;

            ViewCall(int code, long deadline) { this.code = code; this.deadline = deadline; }
''',
     b'''            final long deadline;
            final ViewAttempt attempt;
            boolean abandoned, completed;
            int result;
            StopSample stopSample;

            ViewCall(int code, long deadline, ViewAttempt attempt) {
                this.code = code;
                this.deadline = deadline;
                this.attempt = attempt;
            }
''', 1),
    (OLD_CALL, NEW_CALL, 1),
    (b'''                    int result = transactView(call);
                    synchronized (lock) {
                        call.result = result;
                        call.completed = true;
                        if (call == viewStop) {
                            viewStopAcknowledged = result == RetainedViewAppProtocol.QUEUED
''',
     b'''                    transactView(call);
                    synchronized (lock) {
                        if (call.stopSample != null && (viewCall != call || viewAttempt != call.attempt
                                || call.abandoned || !viewCurrentLocked()
                                || SystemClock.elapsedRealtime() >= call.deadline)) call.stopSample = null;
                        call.completed = true;
                        if (call == viewStop) {
                            viewStopAcknowledged = call.result == RetainedViewAppProtocol.QUEUED
''', 1),
    (b'        private int transactView(ViewCall call) {\n',
     b'        private void transactView(ViewCall call) {\n'
     b'            boolean typed = call.attempt != null;\n', 1),
    (b'            int result = stop ? unknown : unavailable;\n',
     b'            int result = stop ? unknown : unavailable;\n'
     b'            StopSample sample = null;\n', 1),
    (b'''                    data.writeInt(RetainedHostControlProtocol.VERSION);
                    boolean send;
''',
     b'''                    data.writeInt(RetainedHostControlProtocol.VERSION);
                    if (typed) data.writeInt(RetainedStopStatus.VERSION);
                    boolean send;
''', 1),
    (b'''                        send = viewCurrentLocked() && (stop || (!call.abandoned
                                && SystemClock.elapsedRealtime() < call.deadline));
                    }
                    if (send) {
''',
     b'''                        send = viewCurrentLocked() && (stop || (!call.abandoned
                                && (!typed || (viewCall == call && viewAttempt == call.attempt))
                                && SystemClock.elapsedRealtime() < call.deadline));
                    }
                    if (send) {
                        long started = typed ? SystemClock.elapsedRealtime() : 0;
                        if (typed && (started < 0 || started >= call.deadline)) {
                            throw new IllegalStateException("Typed Stop status wait expired");
                        }
''', 1),
    (OLD_REPLY, NEW_REPLY, 1),
    (b'''            } catch (Throwable problem) {
                result = unknown;
            } finally {
                try {
                    try { if (reply != null) reply.recycle(); }
                    finally { if (data != null) data.recycle(); }
                } catch (Throwable problem) { result = unknown; }
            }
            return result;
''',
     b'''            } catch (Throwable problem) {
                result = unknown;
                sample = null;
            } finally {
                try {
                    try { if (reply != null) reply.recycle(); }
                    finally { if (data != null) data.recycle(); }
                } catch (Throwable problem) {
                    result = unknown;
                    sample = null;
                }
            }
            // Provisional until runView publishes completion under the attempt lock.
            call.result = result;
            call.stopSample = sample;
''', 1),
)


def derive():
    """Return the held service overlay after exact source and whole inverse checks."""
    original = pinned(load_io(), BASE + NAME, SOURCE_SHA256, SOURCE_BYTES)
    if len(original) != SOURCE_BYTES:
        raise ValueError('Unexpected confirmation lifecycle service size')
    staged = apply(original, EDITS)
    inverse = [(new, old, count) for old, new, count in reversed(EDITS)]
    if apply(staged, inverse, allow_existing=True) != original:
        raise ValueError('Stop status relay source lacks an exact inverse')
    return {NAME: staged}
