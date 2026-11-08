"""Derive the matched, unselected file-stage tester readiness sources."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).absolute().parents[4]
BASE = "out/file-stage-prepare-app-build-review/r-4935c4ad"
OUTPUT = ROOT / "out/file-stage-tester-ui-review/readiness"

INPUTS = {
    "app/PrepareActivity.java": ("src/PrepareActivity.java",
        "f8384acbc5c41201ed747af61897411e81998e92fb80de78f1617d84d54e2e17"),
    "host/PreparedRetainedHostNativeBindingV2.java": ("inputs/22-PreparedRetainedHostNativeBindingV2.java",
        "35ae3a2e3ed50017ac0528dff7a170a0cd84814bb3e2fdb400be7dd8b2b10d8d"),
    "shared/RetainedViewAppProtocol.java": ("src/RetainedViewAppProtocol.java",
        "18f157d6e4642c7a5b094ca7cc9feabfa16af2e02ba66e013b5f0748f788597f"),
}

ACTIVITY_READY = """        private boolean awaitReadyOnWorker(IBinder binder) {
            long until = SystemClock.elapsedRealtime() + PREPARE_READY_MILLIS;
            while (dispatch.get() == OPEN && SystemClock.elapsedRealtime() < until) {
                if (attempt == null) {
                    try { attempt = RetainedRootHostServiceV2.claimView(binder); }
                    catch (RuntimeException refused) { return false; }
                }
                if (attempt != null && readStatus(attempt) == RetainedViewAppProtocol.STATUS_READY_TO_PREPARE) {
                    return SystemClock.elapsedRealtime() < until;
                }
                long remaining = until - SystemClock.elapsedRealtime();
                if (remaining <= 0 || dispatch.get() != OPEN) break;
                try { Thread.sleep(Math.min(remaining, READY_POLL_MILLIS)); }
                catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    return false;
                }
            }
            return false;
        }

        private void prepareOnWorker(IBinder binder) {
            if (!awaitReadyOnWorker(binder) || !dispatch.compareAndSet(OPEN, COMMITTED)) {
"""

HOST_READY = """    private boolean readinessCurrentLocked(AppViewReadiness observation) {
        return appViewReadiness == observation && appView == null && !viewCreditIssued && !privateViewClosing
                && appViewPeerLocked() && appViewLiveLocked() && offer == observation.offer
                && nativeControl == observation.control;
    }

    private int appViewReadinessStatus(int uid, int pid) {
        final AppViewReadiness observation;
        final boolean submit;
        synchronized (lock) {
            if (!appViewCallerLocked(uid, pid) || appView != null || viewCreditIssued || privateViewClosing
                    || retired || failure != null || unbindAttempted) {
                return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
            }
            if (!appViewLiveLocked() || nativeControl == null) return RetainedViewAppProtocol.STATUS_PENDING;
            submit = appViewReadiness == null;
            if (submit) appViewReadiness = new AppViewReadiness(offer, nativeControl);
            observation = appViewReadiness;
        }
        if (submit) {
            boolean accepted = false;
            try { accepted = handler.post(observation); }
            catch (RuntimeException unavailable) { }
            finally {
                synchronized (lock) {
                    observation.postAccepted = accepted;
                    observation.postReturned = true;
                }
            }
            return RetainedViewAppProtocol.STATUS_PENDING;
        }
        boolean committed = observation.control.committed();
        synchronized (lock) {
            if (!committed || !appViewCallerLocked(uid, pid) || !readinessCurrentLocked(observation)
                    || (observation.postReturned && !observation.postAccepted)) {
                return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
            }
            if (!observation.postReturned || !observation.checked) return RetainedViewAppProtocol.STATUS_PENDING;
            return observation.available ? RetainedViewAppProtocol.STATUS_READY_TO_PREPARE
                    : RetainedViewAppProtocol.STATUS_UNAVAILABLE;
        }
    }

    private final class AppViewReadiness implements Runnable {
        final Offer offer;
        final RetainedHostNativeControlV2 control;
        boolean postReturned, postAccepted, started, checked, available;

        AppViewReadiness(Offer offer, RetainedHostNativeControlV2 control) {
            this.offer = offer;
            this.control = control;
        }

        @Override public void run() {
            if (Thread.currentThread() != mainThread || Looper.getMainLooper() != main
                    || main.getThread() != mainThread) return;
            synchronized (lock) {
                if (started || !readinessCurrentLocked(this) || (postReturned && !postAccepted)) return;
                started = true;
            }
            boolean observed = false;
            try {
                observed = source.privateViewRequestAvailableForControl() && control.committed();
            } catch (Throwable unavailable) {
                // This read-only observation supplies no close or mutation credit.
            } finally {
                synchronized (lock) {
                    available = observed && readinessCurrentLocked(this);
                    checked = true;
                }
            }
        }
    }

"""

EDITS = {
    "app/PrepareActivity.java": (
        ("import android.os.Looper;\n", "import android.os.Looper;\nimport android.os.SystemClock;\n"),
        ("        private static final long BIND_WAIT_MILLIS = 10_000;\n",
         "        private static final long BIND_WAIT_MILLIS = 10_000;\n"
         "        private static final long PREPARE_READY_MILLIS = 12_000;\n"
         "        private static final long READY_POLL_MILLIS = 200;\n"),
        ("""        private void prepareOnWorker(IBinder binder) {
            if (dispatch.get() == OPEN) {
                try { attempt = RetainedRootHostServiceV2.claimView(binder); }
                catch (RuntimeException refused) { attempt = null; }
            }
            if (attempt == null || !dispatch.compareAndSet(OPEN, COMMITTED)) {
""", ACTIVITY_READY),
        ("""                        final int sample = readStatus(attempt);
                        workerTerminal = workerTerminal || terminalStatus(sample);
""", """                        int received = readStatus(attempt);
                        final int sample = received == RetainedViewAppProtocol.STATUS_READY_TO_PREPARE
                                ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : received;
                        workerTerminal = workerTerminal || terminalStatus(sample);
"""),
        ("""            StringBuilder text = new StringBuilder(label(observed));
""", """            StringBuilder text = new StringBuilder(dispatch.get() == OPEN && !prepareReturned
                    ? "Waiting for the host. Prepare has not been sent." : label(observed));
"""),
    ),
    "host/PreparedRetainedHostNativeBindingV2.java": (
        ("    private AppView appView;\n", "    private AppView appView;\n    private AppViewReadiness appViewReadiness;\n"),
        ("""    private int appViewStatus(int uid, int pid) {
        AppView occurrence;
        synchronized (lock) {
            occurrence = appView;
            if (occurrence == null || !appViewCallerLocked(uid, pid) || !appViewRetainedLocked(occurrence)) {
                return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
            }
            if (occurrence.stoppedBeforeDispatch) return RetainedViewAppProtocol.STATUS_STOPPED_BEFORE_DISPATCH;
            if (!occurrence.prepareStarted) {
                return occurrence.prepareUnavailable || !appViewLiveLocked()
                        ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : RetainedViewAppProtocol.STATUS_PENDING;
            }
        }
""", HOST_READY + """    private int appViewStatus(int uid, int pid) {
        AppView occurrence;
        synchronized (lock) {
            if (!appViewCallerLocked(uid, pid)) return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
            occurrence = appView;
            if (occurrence != null) {
                if (!appViewRetainedLocked(occurrence)) return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
                if (occurrence.stoppedBeforeDispatch) return RetainedViewAppProtocol.STATUS_STOPPED_BEFORE_DISPATCH;
                if (!occurrence.prepareStarted) {
                    return occurrence.prepareUnavailable || !appViewLiveLocked()
                            ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : RetainedViewAppProtocol.STATUS_PENDING;
                }
            }
        }
        if (occurrence == null) return appViewReadinessStatus(uid, pid);
"""),
    ),
    "shared/RetainedViewAppProtocol.java": (
        ("    public static final int STATUS_UNAVAILABLE = 9;\n",
         "    public static final int STATUS_UNAVAILABLE = 9;\n"
         "    /** Pre-Prepare observation for this exact app/host attempt, with no mutation credit. */\n"
         "    public static final int STATUS_READY_TO_PREPARE = 10;\n"),
        ("value >= STATUS_PENDING && value <= STATUS_UNAVAILABLE",
         "value >= STATUS_PENDING && value <= STATUS_READY_TO_PREPARE"),
    ),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_exact(data, old, new, newline):
    old = old.replace("\n", newline).encode("ascii")
    new = new.replace("\n", newline).encode("ascii")
    if data.count(old) != 1:
        raise ValueError("Exact readiness edit anchor differs")
    return data.replace(old, new, 1)


def derive():
    result = {}
    for relative, (held, pin) in INPUTS.items():
        path = BASE + "/" + held
        before = (ROOT / path).read_bytes()
        if sha(before) != pin:
            raise ValueError("Held signed source differs " + path)
        newline = "\r\n" if relative.startswith("host/") else "\n"
        after = before
        for old, new in EDITS[relative]:
            after = replace_exact(after, old, new, newline)
        inverse = after
        for old, new in reversed(EDITS[relative]):
            inverse = replace_exact(inverse, new, old, newline)
        if inverse != before:
            raise ValueError("Readiness source inverse differs " + path)
        result[relative] = (path, before, after)
    return result


def main():
    files = derive()
    OUTPUT.mkdir(parents=False, exist_ok=False)
    records, patch = {}, []
    for relative, (path, before, after) in files.items():
        destination = OUTPUT / relative
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(after)
        records[relative] = {"before": path, "beforeSha256": sha(before), "afterSha256": sha(after)}
        patch.extend(difflib.unified_diff(before.decode("utf-8").splitlines(keepends=True),
                     after.decode("utf-8").splitlines(keepends=True), "a/" + relative, "b/" + relative))
    diff = "".join(patch).encode("utf-8")
    (OUTPUT / "readiness.patch").write_bytes(diff)
    receipt = {"status": "MATCHED_READINESS_SOURCES_ONLY", "files": records, "patchSha256": sha(diff),
               "wholeSourceInversePassed": True, "selected": False, "compiledOrSigned": False}
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
