"""Stage exact worker-exit and main final-callback observations for the guest PIN request."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from compose_guest_pin_source_occurrence import COMPLETION, OCCURRENCE, PACKAGE, REQUEST
from run_guest_tree_install_transport import ROOT, load_io, pinned


BASE = ('out/guest-pin-progress-queue-source/r-a9d154be/receipt.json',
        'be080732f4ce285e6091f155464c1e6f5d1cfb3df3a815e5e740b86356c443e5')
OUT = ROOT / 'out/guest-pin-final-delivery-source'

RECEIPTS = b'''    enum WorkerExitKind { NORMAL_RETURN, CAUGHT_REMOTE_FAILURE }

    enum TerminalState { ENTERED, RETURNED, THREW }

    private static final class WorkerExit {
        private final WorkerExitKind kind;
        private final VerifyCredentialResponse response;
        private boolean settled;

        private WorkerExit(WorkerExitKind kind, VerifyCredentialResponse response) {
            this.kind = kind;
            this.response = response;
        }
    }

    /** Original callback observations only; cleanup and policy remain with the source. */
    static final class TerminalDelivery {
        final WorkerExitKind workerExitKind;
        final PinCheckCompletion.FinalKind resultKind;
        final int originalTimeout;
        final boolean originalDuplicate;
        private final Slot slot;
        private TerminalState state = TerminalState.ENTERED;

        private TerminalDelivery(Slot slot, WorkerExitKind workerExitKind,
                PinCheckCompletion.FinalKind resultKind, int originalTimeout, boolean originalDuplicate) {
            this.slot = slot;
            this.workerExitKind = workerExitKind;
            this.resultKind = resultKind;
            this.originalTimeout = originalTimeout;
            this.originalDuplicate = originalDuplicate;
        }

        boolean finish(Throwable failure) {
            if (Looper.myLooper() != slot.main) return false;
            synchronized (slot.lock) {
                if (state != TerminalState.ENTERED) return false;
                state = failure == null ? TerminalState.RETURNED : TerminalState.THREW;
                return true;
            }
        }

        TerminalState state() {
            synchronized (slot.lock) {
                return state;
            }
        }
    }

'''

OLD_RETURN = b'''        PinCheckCompletion active;
        IInterface originalReceiver;
        synchronized (slot.lock) {
            if (!workerCurrentLocked(actualTask)) return null;
            active = completion;
            originalReceiver = receiver;
        }
        // Original framework predicates can run arbitrary code. Retire and recheck off them.
        Runnable ticket = active.recordFinal(task, originalReceiver, response);
        synchronized (slot.lock) {
            return workerCurrentLocked(actualTask) ? preparePostLocked(ticket) : null;
        }
    }
'''
NEW_RETURN = b'''        PinCheckCompletion active;
        IInterface originalReceiver;
        WorkerExit exit;
        synchronized (slot.lock) {
            if (!workerOwnsLocked(actualTask)) return null;
            exit = rememberWorkerExitLocked(WorkerExitKind.NORMAL_RETURN, response);
            if (exit == null) return null;
            if (!currentLocked()) {
                exit.settled = true;
                return null;
            }
            active = completion;
            originalReceiver = receiver;
        }
        Runnable ticket;
        try {
            ticket = active.recordFinal(task, originalReceiver, response);
        } finally {
            synchronized (slot.lock) {
                exit.settled = true;
            }
        }
        synchronized (slot.lock) {
            return workerCurrentLocked(actualTask) ? preparePostLocked(ticket) : null;
        }
    }

    /** Records the catch-return contour and its unmodified, possibly nonnull carried result. */
    void observeCaughtOriginalRemoteFailure(AsyncTask<?, ?, ?> actualTask,
            VerifyCredentialResponse carriedResponse, RemoteException failure) {
        synchronized (slot.lock) {
            if (!workerOwnsLocked(actualTask) || failure == null) return;
            WorkerExit exit = rememberWorkerExitLocked(WorkerExitKind.CAUGHT_REMOTE_FAILURE, carriedResponse);
            if (exit == null) return;
            completion.recordFailure(task, receiver, failure);
            exit.settled = true;
            retireUnpostedProgressLocked();
        }
    }

    private WorkerExit rememberWorkerExitLocked(WorkerExitKind kind, VerifyCredentialResponse response) {
        if (workerExit != null) {
            if (workerExit.kind != kind || workerExit.response != response) {
                workerExitConflict = true;
                retireUnpostedProgressLocked();
            }
            return null;
        }
        workerExit = new WorkerExit(kind, response);
        return workerExit;
    }

    /** Compares the actual final callback operands before the original invocation. */
    TerminalDelivery beginOriginalFinalDelivery(AsyncTask<?, ?, ?> actualTask, Object actualHigherCallback,
            VerifyCredentialResponse actualResponse, int originalTimeout, boolean originalDuplicate) {
        if (Looper.myLooper() != slot.main || actualTask != task || actualHigherCallback != higherCallback) return null;
        synchronized (slot.lock) {
            if (workerExit == null || workerExitConflict) return null;
            if (workerExit.response != actualResponse) {
                workerExitConflict = true;
                retireUnpostedProgressLocked();
                return null;
            }
            if (!workerExit.settled || terminalDelivery != null) return null;
            PinCheckCompletion.FinalKind kind = completion.finalKind();
            if (workerExit.kind == WorkerExitKind.CAUGHT_REMOTE_FAILURE
                    && kind == PinCheckCompletion.FinalKind.PENDING) {
                kind = PinCheckCompletion.FinalKind.UNAVAILABLE_FAILURE;
            }
            terminalDelivery = new TerminalDelivery(slot, workerExit.kind, kind, originalTimeout, originalDuplicate);
            return terminalDelivery;
        }
    }
'''


def bind_final_delivery(source):
    slot = b'    /** One slot on the original checker, independent of mCheckCredentialTask. */\n'
    replacements = (
        (b'import android.os.Looper;\n', b'import android.os.Looper;\nimport android.os.RemoteException;\n'),
        (slot, RECEIPTS + slot),
        (b'    private ProgressPost progressPost;\n',
         b'    private ProgressPost progressPost;\n'
         b'    private WorkerExit workerExit;\n'
         b'    private boolean workerExitConflict;\n'
         b'    private TerminalDelivery terminalDelivery;\n'),
        (OLD_RETURN, NEW_RETURN),
        (b'            if (completion == null) return PinCheckCompletion.FinalKind.PENDING;\n'
         b'            return completion.finalKind();',
         b'            if (workerExitConflict) return PinCheckCompletion.FinalKind.CONFLICT;\n'
         b'            if (completion == null) return PinCheckCompletion.FinalKind.PENDING;\n'
         b'            return completion.finalKind();'),
        (b'        return completion.finalKind() == PinCheckCompletion.FinalKind.ORIGINAL_MATCH;',
         b'        return !workerExitConflict && workerExit != null && workerExit.kind == WorkerExitKind.NORMAL_RETURN\n'
         b'                && completion.finalKind() == PinCheckCompletion.FinalKind.ORIGINAL_MATCH;'),
        (b'        return currentLocked() && actualTask == task && Thread.currentThread() == worker;\n    }',
         b'        return currentLocked() && workerOwnsLocked(actualTask);\n    }\n\n'
         b'    private boolean workerOwnsLocked(AsyncTask<?, ?, ?> actualTask) {\n'
         b'        return actualTask == task && Thread.currentThread() == worker;\n    }'),
    )
    if b'\r\n' in source:
        replacements = tuple((old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n'))
                             for old, new in replacements)
    updated = source
    for old, new in replacements:
        if updated.count(old) != 1 or new in updated:
            raise ValueError('Exact held request final-delivery anchor changed')
        updated = updated.replace(old, new, 1)
    inverse = updated
    for old, new in reversed(replacements):
        if inverse.count(new) != 1:
            raise ValueError('Staged final delivery lacks the exact inverse')
        inverse = inverse.replace(new, old, 1)
    if inverse != source:
        raise ValueError('Staged final delivery lacks the whole-source inverse')
    return updated


def compose():
    io = load_io()
    base = json.loads(pinned(io, *BASE, 16384), object_pairs_hook=io['unique_object'])
    if (base['status'] != 'STAGED_DONOR_PIN_PROGRESS_QUEUE_SOURCE_ONLY'
            or base['selected'] is not False or base['deviceEligible'] is not False
            or base['targetExecuted'] is not False or base['wholeSourceInversePassed'] is not True
            or base['package'] != PACKAGE or set(base['outputs']) != {REQUEST, COMPLETION, OCCURRENCE}):
        raise ValueError('Expected the held progress queue source cohort')
    sources = {name: pinned(io, row['path'], row['sha256'], 32768)
               for name, row in base['outputs'].items()}
    sources[REQUEST] = bind_final_delivery(sources[REQUEST])
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    target = run / Path(*PACKAGE.split('.'))
    run.mkdir()
    target.mkdir(parents=True)
    outputs = {}
    for name, raw in sources.items():
        path = target / name
        with path.open('xb') as stream:
            stream.write(raw)
        outputs[name] = {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest()}
    result = {
        'schema': 'oneos-guest-pin-final-delivery-source/v1',
        'status': 'STAGED_DONOR_PIN_FINAL_DELIVERY_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'package': PACKAGE, 'outputs': outputs, 'wholeSourceInversePassed': True,
        'baseReceipt': {'path': BASE[0], 'sha256': BASE[1]},
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
