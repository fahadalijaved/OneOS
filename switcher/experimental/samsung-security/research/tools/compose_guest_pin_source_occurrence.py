"""Stage exact source-occurrence checks on the retained PIN request pair."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from compose_guest_pin_dispatch_start import COMPLETION, PACKAGE, REQUEST
from compose_guest_pin_systemui_lifecycle import relocate
from run_guest_tree_install_transport import ROOT, load_io, pinned


BASE = ('out/guest-pin-dispatch-start-source/r-9a205b18/receipt.json',
        '99776b585193c5045a10eec6813dd274f4324d4b94b2f7f72460e854fc96090a')
OUT = ROOT / 'out/guest-pin-source-occurrence-source'
OCCURRENCE = 'GuestPinSourceOccurrence.java'
AUTHORED = ROOT / 'compat/android/com/appleexploit/oneos/security/transport' / OCCURRENCE

OLD_ADOPT = b'''            require(controller != null && view != null && monitor != null && guestUser >= 0
                    && hasSourceShape(task, TASK) && higherCallback != null);
            GuestPinCheckRequest request = new GuestPinCheckRequest(this, controller, view,
                    monitor, guestUser, task, higherCallback);
            synchronized (lock) {
                require(starting == null);
                if (current != null) {
                    require(current.task != task);
                    current.retireLocked();
                }
                current = request;
            }
            return request;
'''
NEW_ADOPT = b'''            require(occurrence != null && occurrence.belongsTo(actualChecker, controller, view, monitor, guestUser)
                    && hasSourceShape(task, TASK) && higherCallback != null);
            GuestPinCheckRequest previous;
            boolean previousRetired;
            synchronized (lock) {
                require(!adopting && starting == null && occurrence.isLive());
                previous = current;
                require(previous == null || previous.task != task);
                previousRetired = previous != null && previous.retired;
                adopting = true;
            }
            try {
                require(occurrence.matchesNow());
                GuestPinCheckRequest request = new GuestPinCheckRequest(this, controller, view,
                        monitor, guestUser, task, higherCallback, occurrence);
                synchronized (lock) {
                    synchronized (occurrence.publicationLock()) {
                        require(occurrence.isLive() && current == previous
                                && (previous == null || previous.retired == previousRetired));
                        if (previous != null) previous.retireLocked();
                        current = request;
                    }
                }
                return request;
            } finally {
                synchronized (lock) {
                    adopting = false;
                }
            }
'''

OLD_OBSERVE = b'''        synchronized (slot.lock) {
            if (!entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;
        }
        if (!view.isAttachedToWindow()) return false;
'''
NEW_OBSERVE = b'''        synchronized (slot.lock) {
            if (slot.adopting || checkingProgress
                    || !entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;
            checkingProgress = true;
        }
        boolean matches = false;
        try {
            matches = occurrence.matchesNow();
        } catch (RuntimeException failure) {
            return false;
        } finally {
            synchronized (slot.lock) {
                checkingProgress = false;
                if (!matches && ownsRequestLocked()) retireLocked();
            }
        }
        if (!matches) return false;
'''


def bind_occurrence(source):
    replacements = (
        (b'        private GuestPinCheckRequest starting;\n',
         b'        private GuestPinCheckRequest starting;\n        private boolean adopting;\n'),
        (b'                require(request != null && request.slot == this && request.task == actualTask\n'
         b'                        && request.currentLocked() && starting == null && !request.startClaimed);\n'
         b'                request.startClaimed = true;\n                starting = request;',
         b'                require(request != null && request.slot == this && request.task == actualTask);\n'
         b'                synchronized (request.occurrence.publicationLock()) {\n'
         b'                    require(request.currentLocked() && starting == null && !adopting\n'
         b'                            && !request.startClaimed);\n'
         b'                    request.startClaimed = true;\n                    starting = request;\n                }'),
        (b'                Object higherCallback) {\n            require(Looper.myLooper()',
         b'                Object higherCallback, GuestPinSourceOccurrence occurrence) {\n'
         b'            require(Looper.myLooper()'),
        (OLD_ADOPT, NEW_ADOPT),
        (b'    private final Object higherCallback;\n',
         b'    private final Object higherCallback;\n    private final GuestPinSourceOccurrence occurrence;\n'),
        (b'    private boolean startClaimed;\n',
         b'    private boolean startClaimed;\n    private boolean checkingProgress;\n'),
        (b'            int guestUser, AsyncTask<?, ?, ?> task, Object higherCallback) {',
         b'            int guestUser, AsyncTask<?, ?, ?> task, Object higherCallback,\n'
         b'            GuestPinSourceOccurrence occurrence) {'),
        (b'        this.higherCallback = higherCallback;\n',
         b'        this.higherCallback = higherCallback;\n        this.occurrence = occurrence;\n'),
        (OLD_OBSERVE, NEW_OBSERVE),
        (b'            // The last cell-locked MATCH read commits the claim with the slot still held.\n'
         b'            if (!entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;\n'
         b'            pendingOriginalTicket = null;\n            return true;',
         b'            synchronized (occurrence.publicationLock()) {\n'
         b'                // Order the final MATCH and ticket claim with off-main source retirement.\n'
         b'                if (!entryCurrentLocked(actualReceiver, actualHandler, originalTicket)) return false;\n'
         b'                pendingOriginalTicket = null;\n                return true;\n            }'),
        (b'if (actualTask == task && currentLocked()) retireLocked();',
         b'if (actualTask == task && ownsRequestLocked()) retireLocked();'),
        (b'    private boolean currentLocked() {\n        return slot.current == this && !retired;\n    }',
         b'    private boolean ownsRequestLocked() {\n        return slot.current == this && !retired;\n    }\n\n'
         b'    private boolean currentLocked() {\n        return ownsRequestLocked() && occurrence.isLive();\n    }'),
    )
    if b'\r\n' in source:
        replacements = tuple((old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n')) for old, new in replacements)
    updated = source
    for old, new in replacements:
        if updated.count(old) != 1 or new in updated:
            raise ValueError('Exact held request occurrence anchor changed')
        updated = updated.replace(old, new, 1)
    inverse = updated
    for old, new in reversed(replacements):
        if inverse.count(new) != 1:
            raise ValueError('Staged occurrence lacks the exact inverse')
        inverse = inverse.replace(new, old, 1)
    if inverse != source:
        raise ValueError('Staged occurrence lacks the whole-source inverse')
    return updated


def compose():
    io = load_io()
    base = json.loads(pinned(io, *BASE, 16384), object_pairs_hook=io['unique_object'])
    if (base['status'] != 'STAGED_DONOR_PIN_DISPATCH_START_SOURCE_ONLY'
            or base['selected'] is not False or base['deviceEligible'] is not False
            or base['package'] != PACKAGE or set(base['outputs']) != {REQUEST, COMPLETION}):
        raise ValueError('Expected the held dispatch start source pair')
    originals = {name: pinned(io, row['path'], row['sha256'], 16384)
                 for name, row in base['outputs'].items()}
    with io['checked_input'](AUTHORED, max_size=16384) as stream:
        authored = stream.read(16385)
    if not 0 < len(authored) <= 16384:
        raise ValueError('Expected bounded authored occurrence source')
    sources = {REQUEST: bind_occurrence(originals[REQUEST]), COMPLETION: originals[COMPLETION],
               OCCURRENCE: relocate(authored)}
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
        'schema': 'oneos-guest-pin-source-occurrence-source/v1',
        'status': 'STAGED_DONOR_PIN_SOURCE_OCCURRENCE_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'package': PACKAGE, 'outputs': outputs, 'wholeSourceInversePassed': True,
        'authoredOccurrence': {'path': AUTHORED.relative_to(ROOT).as_posix(),
                               'sha256': hashlib.sha256(authored).hexdigest()},
        'baseReceipt': {'path': BASE[0], 'sha256': BASE[1]},
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
