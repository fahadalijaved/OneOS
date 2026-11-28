"""Render read-only Stop evidence on the existing file-stage tester screen."""

from build_tree_retained_controller import edit
from run_guest_tree_install_transport import load_io, pinned


NAME = 'PrepareActivity.java'
SOURCE = ('out/file-stage-confirmation-lifecycle-build/r-ff4de804/app/src/' + NAME,
          '40f96f111b5521813b9d9302d59cf29ee01eecd6ae893e3c05ad71c3eb60fe28')

REFRESH = """                        int received = readStatus(attempt);
                        final int sample = received == RetainedViewAppProtocol.STATUS_READY_TO_PREPARE
                                ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : received;
                        workerTerminal = workerTerminal || terminalStatus(sample);
                        final boolean acknowledged = attempt.stopAcknowledged();
                        main.post(new Runnable() {
                            @Override public void run() {
                                if (stopRequested && acknowledged) stopReply = RetainedViewAppProtocol.QUEUED;
                                refreshing = false;
                                observe(sample);
                            }
                        });"""

TYPED_REFRESH = """                        final ViewAttempt source = attempt;
                        final StopSample typed = readStopStatus(source);
                        int received = typed == null ? readStatus(source) : typed.status.status;
                        final int sample = received == RetainedViewAppProtocol.STATUS_READY_TO_PREPARE
                                ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : received;
                        workerTerminal = workerTerminal || terminalStatus(sample);
                        final boolean acknowledged = source.stopAcknowledged();
                        main.post(new Runnable() {
                            @Override public void run() {
                                if (stopRequested && acknowledged) stopReply = RetainedViewAppProtocol.QUEUED;
                                refreshing = false;
                                recordStopSample(source, typed);
                                observe(sample);
                            }
                        });"""

CAPTURE = """        private static StopSample readStopStatus(ViewAttempt source) {
            try { return source.stopStatus(); }
            catch (RuntimeException unavailable) { return null; }
        }

        private void recordStopSample(ViewAttempt source, StopSample sample) {
            latestRoleAvailable = false;
            if (current != this || source == null || source != preparedAttempt
                    || terminal() || connectionLost || releaseWanted || captureInvalid
                    || sample == null || sample.status.role == null) return;
            if (partialEvidence != null && !partialEvidence.status.role.equals(sample.status.role)) {
                captureInvalid = true;
                return;
            }
            int status = sample.status.status;
            if (!stopRequested && status == RetainedViewAppProtocol.STATUS_PARTIAL
                    && prepareReply != null && prepareReply == RetainedViewAppProtocol.QUEUED) {
                if (partialEvidence == null) partialEvidence = sample;
                latestRoleAvailable = true;
            } else if (stopRequested && status == RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED
                    && partialEvidence != null && stopReply != null && stopReply == RetainedViewAppProtocol.QUEUED
                    && stopRequestedElapsedMs >= partialEvidence.completedElapsedMs
                    && sample.startedElapsedMs >= stopRequestedElapsedMs) {
                terminalEvidence = sample;
            }
        }

        String stopCaptureText() {
            if (captureInvalid || connectionLost || partialEvidence == null) return "";
            boolean complete = terminalEvidence != null
                    && observed == RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
            if (!complete && (stopRequested || !latestRoleAvailable || unavailableSample
                    || observed != RetainedViewAppProtocol.STATUS_PARTIAL)) return "";
            RetainedStopStatus.Role role = partialEvidence.status.role;
            return "ONEOS_STOP_ROLE_V1 " + (complete ? "terminal" : "partial")
                    + " " + role.prepareSequence + " " + role.appPid + " " + role.systemServerPid
                    + " " + role.controllerPid + " " + role.controllerStartTicks
                    + " " + role.childPid + " " + role.childStartTicks
                    + " " + Long.toUnsignedString(role.childMountNamespaceInode)
                    + " " + partialEvidence.startedElapsedMs + " " + partialEvidence.completedElapsedMs
                    + " " + (complete ? stopRequestedElapsedMs : 0)
                    + " " + (complete ? terminalEvidence.startedElapsedMs : 0)
                    + " " + (complete ? terminalEvidence.completedElapsedMs : 0);
        }

"""


def derive():
    raw = pinned(load_io(), *SOURCE, 64 * 1024)
    return {NAME: edit(raw, (
        ('import com.fahadali.oneos.core.root.RetainedRootHostServiceV2.ViewAttempt;\n',
         'import com.fahadali.oneos.core.root.RetainedRootHostServiceV2.StopSample;\n'
         'import com.fahadali.oneos.core.root.RetainedRootHostServiceV2.ViewAttempt;\n'
         'import com.fahadali.oneos.core.root.RetainedStopStatus;\n'),
        ('    private TextView status;\n', '    private TextView status, stopCapture;\n'),
        ('        content.addView(status);\n', '        content.addView(status);\n'
         '        stopCapture = new TextView(this);\n'
         '        stopCapture.setVisibility(View.GONE);\n'
         '        content.addView(stopCapture);\n'),
        ('        if (operation != null) status.setText(operation.message());\n',
         '        String evidence = operation == null ? "" : operation.stopCaptureText();\n'
         '        stopCapture.setText(evidence);\n'
         '        stopCapture.setVisibility(evidence.isEmpty() ? View.GONE : View.VISIBLE);\n'
         '        if (operation != null) status.setText(operation.message());\n'),
        ('        private Integer prepareReply, stopReply;\n', '        private Integer prepareReply, stopReply;\n'
         '        private ViewAttempt preparedAttempt;\n'
         '        private StopSample partialEvidence, terminalEvidence;\n'
         '        private boolean latestRoleAvailable, captureInvalid;\n'
         '        private long stopRequestedElapsedMs;\n'),
        ('            if (!canStop()) return;\n            stopRequested = true;\n',
         '            if (!canStop()) return;\n'
         '            stopRequestedElapsedMs = SystemClock.elapsedRealtime();\n'
         '            stopRequested = true;\n'),
        ('            final int reply = mutation(attempt, false);\n'
         '            main.post(new Runnable() {\n'
         '                @Override public void run() {\n'
         '                    prepareReply = reply;\n',
         '            final ViewAttempt source = attempt;\n'
         '            final int reply = mutation(source, false);\n'
         '            main.post(new Runnable() {\n'
         '                @Override public void run() {\n'
         '                    preparedAttempt = source;\n'
         '                    prepareReply = reply;\n'),
        (REFRESH, TYPED_REFRESH),
        ('        private void observe(int sample) {\n', CAPTURE + '        private void observe(int sample) {\n'),
    ))}
