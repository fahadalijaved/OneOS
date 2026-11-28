"""Stage the scoped caller observation without selecting a guest call site."""

from run_guest_tree_install_transport import load_io, pinned


SOURCE = 'compat/guest-pin-delivery/com/android/server/locksettings/GuestPinCallerFrame.java'
SOURCE_SHA = 'a0615398b85f48ff1246423d6e71b47a993c638b961848e30af4e86015e767b6'
FRAME_ANCHOR = b'    private static final class Frame {\n'
OBSERVATION = b'''    /** Only the original permission-success edge may run this synchronous observation. */
    static void observeAfterPermission(LockSettingsService actualService,
            LockscreenCredential parcelPin, int requestedUser,
            ICheckCredentialProgressCallback originalCallback, int expectedPid, int expectedUid,
            Consumer<PreClearObservation> observer) {
        Frame frame = null;
        PreClearObservation opened = null;
        try {
            frame = CURRENT.get();
            if (observer == null || !matchesFrame(frame, actualService, parcelPin, requestedUser,
                    originalCallback, expectedPid, expectedUid) || frame.preClearAttempted) return;
            frame.preClearAttempted = true;
            if (!matchesIncomingIdentity(actualService, parcelPin, requestedUser, originalCallback,
                    expectedPid, expectedUid)) return;
            opened = new PreClearObservation();
            frame.preClearObservation = opened;
            observer.accept(opened);
        } catch (Throwable observationFailure) {
            if (frame != null) frame.unavailable = true;
        } finally {
            if (opened != null && frame.preClearObservation == opened) frame.preClearObservation = null;
        }
    }

    /** Identity of this observation scope only. It carries no credential or caller fields. */
    static final class PreClearObservation {
        private PreClearObservation() { }

        boolean isCurrent() {
            try {
                Frame frame = CURRENT.get();
                return frame != null && frame.preClearObservation == this
                        && matchesIncomingIdentity(frame.service, frame.pin, frame.user, frame.callback,
                                frame.callerPid, frame.callerUid)
                        && frame.preClearObservation == this;
            } catch (Throwable unavailable) {
                return false;
            }
        }
    }

    private static boolean matchesFrame(Frame frame, LockSettingsService actualService,
            LockscreenCredential parcelPin, int requestedUser,
            ICheckCredentialProgressCallback originalCallback, int expectedPid, int expectedUid) {
        return frame != null && !frame.unavailable && frame.callerPid > 0
                && frame.service == actualService && frame.pin == parcelPin
                && frame.callback == originalCallback && frame.user == requestedUser
                && frame.callerPid == expectedPid && frame.callerUid == expectedUid;
    }

'''
EDITS = (
    (b'import com.android.internal.widget.VerifyCredentialResponse;\n',
     b'import com.android.internal.widget.VerifyCredentialResponse;\nimport java.util.function.Consumer;\n'),
    (b'                owned.unavailable = true;\n                owned.service = null;\n',
     b'                owned.unavailable = true;\n                owned.preClearObservation = null;\n'
     b'                owned.service = null;\n'),
    (b'''            if (frame == null || frame.unavailable || frame.callerPid <= 0
                    || frame.service != actualService || frame.pin != parcelPin
                    || frame.callback != originalCallback || frame.user != requestedUser
                    || frame.callerPid != expectedPid || frame.callerUid != expectedUid) {
''',
     b'''            if (!matchesFrame(frame, actualService, parcelPin, requestedUser, originalCallback,
                    expectedPid, expectedUid)) {
'''),
    (FRAME_ANCHOR, OBSERVATION + FRAME_ANCHOR),
    (b'        boolean unavailable;\n',
     b'        boolean unavailable;\n        boolean preClearAttempted;\n'
     b'        PreClearObservation preClearObservation;\n'),
)


def derive():
    original = pinned(load_io(), SOURCE, SOURCE_SHA, 16 * 1024)
    successor = original
    for before, after in EDITS:
        if successor.count(before) != 1 or after in successor:
            raise ValueError('Pre-clear observation source anchor differs')
        successor = successor.replace(before, after, 1)
    inverse = successor
    for before, after in reversed(EDITS):
        if inverse.count(after) != 1:
            raise ValueError('Pre-clear observation source inverse differs')
        inverse = inverse.replace(after, before, 1)
    if inverse != original:
        raise ValueError('Pre-clear observation source inverse failed')
    return successor
