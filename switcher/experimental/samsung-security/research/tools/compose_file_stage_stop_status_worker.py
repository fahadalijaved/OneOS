"""Derive the unselected Stop status join on the retained native worker."""

from build_tree_retained_controller import edit
from compose_file_stage_stop_role_host import CONTROL, derive as derive_role_host


STOP_STATUS = '''    /** Same scalar status with optional evidence from this worker's original Prepare. */
    RetainedStopStatus appStopStatus(int appPid, int systemServerPid) {
        ViewCommand preparation;
        PrepareRole role;
        ViewState original, latest;
        long controllerTicks;
        Throwable recordedFailure;
        boolean closing, finished, exited, cleaned;
        synchronized (lock) {
            preparation = viewPreparation;
            role = preparation == null ? null : preparation.stopRole;
            original = preparation == null ? null : preparation.response;
            controllerTicks = preparation == null ? 0 : preparation.controllerStartTicks;
            latest = lastViewState;
            recordedFailure = failure;
            closing = closeRequested;
            finished = workerFinished;
            exited = pidfdExited;
            cleaned = cleanupSucceeded;
        }
        // In particular, appViewStatus checks worker termination outside lock.
        int status = appViewStatus();
        if (role == null || controllerTicks <= 0 || original == null || original.state != 1
                || !original.observed || original.namespaceInodeBits == 0 || !stopRoleStatus(status)
                || appPid <= 0 || systemServerPid <= 0 || appPid == systemServerPid
                || appPid == offeredPid || systemServerPid == offeredPid
                || appPid == role.child.childPid || systemServerPid == role.child.childPid) {
            return RetainedStopStatus.withoutRole(status);
        }
        synchronized (lock) {
            if (!samePrepareRole(preparation, original, role) || preparation.controllerStartTicks != controllerTicks
                    || lastViewState != latest || failure != recordedFailure || closeRequested != closing
                    || workerFinished != finished || pidfdExited != exited || cleanupSucceeded != cleaned) {
                return RetainedStopStatus.withoutRole(status);
            }
        }
        return RetainedStopStatus.withRole(status, new RetainedStopStatus.Role(role.sequence, offeredPid,
                controllerTicks, role.child.childPid, role.child.childStartTicks, original.namespaceInodeBits,
                appPid, systemServerPid));
    }

    private static boolean stopRoleStatus(int status) {
        return status == RetainedViewAppProtocol.STATUS_PARTIAL || status == RetainedViewAppProtocol.STATUS_CLOSING
                || status == RetainedViewAppProtocol.STATUS_CLEANUP_UNCONFIRMED
                || status == RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL
                || status == RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
    }

'''

CONTROLLER_BIRTH = '''    // Called by the sole worker after publishing the original view status.
    private void captureStopControllerBirth(ViewCommand preparation, ViewState observation,
            PrepareRole role, long until) throws Throwable {
        synchronized (lock) {
            if (!samePrepareRole(preparation, observation, role) || !pidfdValidated
                    || closeRequested || failure != null || pidfdExited) return;
        }
        final long ticks;
        try {
            remaining(until);
            alive();
            ticks = RetainedStopControllerBirth.read(offeredPid);
            alive();
            remaining(until);
        } catch (Throwable unavailable) {
            if (unavailable instanceof IOException || unavailable instanceof ErrnoException
                    || unavailable instanceof IllegalStateException || unavailable instanceof IllegalArgumentException
                    || unavailable instanceof SecurityException) return;
            throw unavailable;
        }
        synchronized (lock) {
            if (ticks > 0 && samePrepareRole(preparation, observation, role) && !closeRequested
                    && failure == null && !pidfdExited) preparation.controllerStartTicks = ticks;
        }
    }

    /** Requires the existing worker lock. */
    private boolean samePrepareRole(ViewCommand preparation, ViewState observation, PrepareRole role) {
        return viewPreparation == preparation && preparation.response == observation && preparation.stopRole == role;
    }

'''


def derive(controller_sha256, controller_bytes):
    """Return only the worker derived from the exact Prepare role source."""
    original = derive_role_host(controller_sha256, controller_bytes)[CONTROL]
    return {CONTROL: edit(original, (
        ('import android.system.Os;\n', 'import android.system.ErrnoException;\nimport android.system.Os;\n'),
        ('import com.fahadali.oneos.core.root.RetainedViewAppProtocol;\n',
         'import com.fahadali.oneos.core.root.RetainedStopStatus;\n'
         'import com.fahadali.oneos.core.root.RetainedViewAppProtocol;\n'),
        ('    void requestClose() {\n', STOP_STATUS + '    void requestClose() {\n'),
        ('                owner.nativeProgress(this);\n'
         '                if (observed.state == 5 || observed.state == 6) return;\n',
         '                owner.nativeProgress(this);\n'
         '                if (role != null) captureStopControllerBirth(view, observed, role, until);\n'
         '                if (observed.state == 5 || observed.state == 6) return;\n'),
        ('    // Called only after the exact response header and tail are validated.\n',
         CONTROLLER_BIRTH + '    // Called only after the exact response header and tail are validated.\n'),
        ('        PrepareRole stopRole;\n',
         '        PrepareRole stopRole;\n'
         '        long controllerStartTicks; // Set once by the sole Prepare reply worker.\n'),
    ))}
