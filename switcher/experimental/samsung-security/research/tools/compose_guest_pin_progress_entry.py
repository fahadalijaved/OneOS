"""Derive the unselected PIN request source with an exact progress entry claim."""

import argparse
import hashlib
import json
from uuid import uuid4

from run_guest_tree_install_transport import ROOT, load_io, pinned


TRANSPORT = 'compat/android/com/appleexploit/oneos/security/transport/'
REQUEST = TRANSPORT + 'GuestPinCheckRequest.java'
COMPLETION = TRANSPORT + 'PinCheckCompletion.java'
REQUEST_SHA = 'a5fb4e6f6ae6af6aa923865021070eaba9e79e088fa55fd9df2f78b196fc1b61'
COMPLETION_SHA = '338d8900998c7d008df2462ab89c671842fa83b4e1fbb192892ab8a2a5be0726'
OUT = ROOT / 'out/guest-pin-progress-entry-source'
ANCHOR = b'    /** The original cancellation, replacement or source loss retires this request. */'
SLOT_ANCHOR = b'        GuestPinCheckRequest adoptBeforeExecute(Object actualChecker, Object controller,'
LIFECYCLE = b'''        /** Retires the current request at the original synchronous pause or new-entry cut.
         * Delayed task-specific callbacks use retireFromOriginalSource instead.
         */
        boolean retireAtOriginalLifecycleEntry(Object actualChecker, Object actualController,
                View actualView, Object actualMonitor) {
            if (Looper.myLooper() != main || actualChecker != checker) return false;
            synchronized (lock) {
                GuestPinCheckRequest request = current;
                if (request == null || request.retired || request.controller != actualController
                        || request.view != actualView || request.monitor != actualMonitor) return false;
                request.retireLocked();
                return true;
            }
        }

'''
ENTRY = b'''    /** Claims the exact held progress ticket at its original main-thread entry.
     * The selected source still owns posting, retirement, and the real policy checks.
     */
    boolean claimOriginalProgressAtEntry(Object actualController, View actualView,
            Object actualMonitor, int actualGuestUser, AsyncTask<?, ?, ?> actualTask,
            Object actualHigherCallback, IInterface actualReceiver, Handler actualHandler,
            Runnable originalTicket) {
        if (Looper.myLooper() != slot.main || actualController != controller || actualView != view
                || actualMonitor != monitor || actualGuestUser != guestUser || actualTask != task
                || actualHigherCallback != higherCallback || originalTicket == null) return false;
        synchronized (slot.lock) {
            if (!entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;
        }
        if (!view.isAttachedToWindow()) return false;
        synchronized (slot.lock) {
            // The last cell-locked MATCH read commits the claim with the slot still held.
            if (!entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;
            pendingOriginalTicket = null;
            return true;
        }
    }

    private boolean entryCurrentLocked(IInterface actualReceiver, Handler actualHandler,
            Runnable originalTicket) {
        return currentLocked() && pendingOriginalTicket == originalTicket && actualReceiver == receiver
                && actualHandler == handler && completion.finalKind() == PinCheckCompletion.FinalKind.ORIGINAL_MATCH;
    }

'''


def compose(with_lifecycle=False):
    io = load_io()
    request = pinned(io, REQUEST, REQUEST_SHA, 16384)
    pinned(io, COMPLETION, COMPLETION_SHA, 16384)
    additions = [(ANCHOR, ENTRY)]
    if with_lifecycle:
        additions.append((SLOT_ANCHOR, LIFECYCLE))
    if b'\r\n' in request:
        additions = [(anchor, text.replace(b'\n', b'\r\n')) for anchor, text in additions]
    staged = request
    for anchor, addition in additions:
        if staged.count(anchor) != 1 or addition in staged:
            raise ValueError('Exact original request entry anchor changed')
        staged = staged.replace(anchor, addition + anchor, 1)
    original = staged
    for anchor, addition in reversed(additions):
        combined = addition + anchor
        if original.count(combined) != 1:
            raise ValueError('Staged request entry does not have the exact inverse')
        original = original.replace(combined, anchor, 1)
    if original != request:
        raise ValueError('Staged request does not have the exact inverse')
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    run.mkdir()
    source = run / 'GuestPinCheckRequest.java'
    with source.open('xb') as stream:
        stream.write(staged)
    status = 'STAGED_PIN_REQUEST_LIFECYCLE_SOURCE_ONLY' if with_lifecycle else 'STAGED_ORIGINAL_PROGRESS_ENTRY_SOURCE_ONLY'
    result = {'status': status, 'selected': False, 'deviceEligible': False,
              'originalSources': {REQUEST: REQUEST_SHA, COMPLETION: COMPLETION_SHA},
              'source': {'path': source.relative_to(ROOT).as_posix(), 'bytes': len(staged),
                         'sha256': hashlib.sha256(staged).hexdigest()}, 'wholeSourceInversePassed': True}
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--with-lifecycle-retirement', action='store_true')
    print(json.dumps(compose(cli.parse_args().with_lifecycle_retirement), indent=2))
