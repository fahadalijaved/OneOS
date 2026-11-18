"""Derive the unselected host callback for versioned Stop status evidence."""

from build_tree_retained_controller import edit, require, sha
from compose_file_stage_stop_role_host import BINDING, derive as derive_stop_role


ROLE_BINDING_SHA256 = 'e1c8490233e42ef8d01b3426cae326469dcecc68f006b24f5bdb164389367aab'

_IMPORT = 'import com.fahadali.oneos.core.root.RetainedHostControlProtocol;\n'
_CALLBACK = '''        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {
'''
_TRANSACTION = '''            if (code == RetainedStopStatus.TRANSACTION) {
                require(flags == 0 && reply != null, "Synchronous Stop status callback required");
                int uid = Binder.getCallingUid();
                int pid = Binder.getCallingPid();
                data.enforceInterface(RetainedHostControlProtocol.CALLBACK);
                require(data.readInt() == RetainedHostControlProtocol.VERSION, "Callback version differs");
                require(data.readInt() == RetainedStopStatus.VERSION, "Stop status version differs");
                data.enforceNoDataAvail();
                RetainedStopStatus status = appStopStatus(uid, pid);
                reply.writeNoException();
                status.write(reply);
                return true;
            }
'''
_APP_VIEW = '    private static final class AppView {\n'
_STATUS = '''    private RetainedStopStatus appStopStatus(int uid, int pid) {
        AppView occurrence;
        synchronized (lock) {
            if (!appViewCallerLocked(uid, pid)) {
                return RetainedStopStatus.withoutRole(RetainedViewAppProtocol.STATUS_UNAVAILABLE);
            }
            occurrence = appView;
            if (occurrence != null) {
                if (!appViewRetainedLocked(occurrence)) {
                    return RetainedStopStatus.withoutRole(RetainedViewAppProtocol.STATUS_UNAVAILABLE);
                }
                if (occurrence.stoppedBeforeDispatch) {
                    return RetainedStopStatus.withoutRole(RetainedViewAppProtocol.STATUS_STOPPED_BEFORE_DISPATCH);
                }
                if (!occurrence.prepareStarted) {
                    int status = occurrence.prepareUnavailable || !appViewLiveLocked()
                            ? RetainedViewAppProtocol.STATUS_UNAVAILABLE : RetainedViewAppProtocol.STATUS_PENDING;
                    return RetainedStopStatus.withoutRole(status);
                }
            }
        }
        if (occurrence == null) return RetainedStopStatus.withoutRole(appViewReadinessStatus(uid, pid));
        // Sample the retained control outside the host lock, then recheck its app peer.
        RetainedStopStatus status = occurrence.control.appStopStatus(pid, android.os.Process.myPid());
        synchronized (lock) {
            if (!appViewCallerLocked(uid, pid) || !appViewRetainedLocked(occurrence)) {
                return RetainedStopStatus.withoutRole(RetainedViewAppProtocol.STATUS_UNAVAILABLE);
            }
            return status;
        }
    }

'''
_EDITS = (
    (_IMPORT, _IMPORT + 'import com.fahadali.oneos.core.root.RetainedStopStatus;\n'),
    (_CALLBACK, _CALLBACK + _TRANSACTION),
    (_APP_VIEW, _STATUS + _APP_VIEW),
)


def derive(controller_sha256, controller_bytes):
    """Return only the binding overlay on the exact role-aware host source."""
    original = derive_stop_role(controller_sha256, controller_bytes)[BINDING]
    require(sha(original) == ROLE_BINDING_SHA256, 'Unexpected Stop role host binding')
    return {BINDING: edit(original, _EDITS)}
