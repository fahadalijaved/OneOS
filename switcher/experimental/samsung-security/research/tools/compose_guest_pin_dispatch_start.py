"""Stage original PIN task start custody on the disabled lifecycle baseline."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from run_guest_tree_install_transport import ROOT, load_io, pinned


BASE = ('out/guest-pin-systemui-lifecycle-relocated-source/r-0f5e5016/receipt.json',
        'db8f76995be5f0f48bf427e1f68f167b1208937e785a823a1dca3a48bc1ea6a7')
OUT = ROOT / 'out/guest-pin-dispatch-start-source'
PACKAGE = 'com.oplus.keyguard.security'
REQUEST = 'GuestPinCheckRequest.java'
COMPLETION = 'PinCheckCompletion.java'

EXECUTE_ADOPTED = b'''        /**
         * Starts the original task once after the actual source owner adopts it.
         * A throwing start leaves the exact task in custody because dispatch
         * may already have progressed beyond the original executor call.
         */
        @SuppressWarnings("unchecked")
        AsyncTask<?, ?, ?> executeAdopted(GuestPinCheckRequest request,
                AsyncTask<?, ?, ?> actualTask, Executor executor, Object[] args) throws Throwable {
            require(Looper.myLooper() == main);
            synchronized (lock) {
                require(request != null && request.slot == this && request.task == actualTask
                        && request.currentLocked() && starting == null && !request.startClaimed);
                request.startClaimed = true;
                starting = request;
            }

            AsyncTask<?, ?, ?> result;
            try {
                result = ((AsyncTask<Object, ?, ?>) actualTask).executeOnExecutor(executor, args);
            } catch (Throwable originalFailure) {
                try {
                    synchronized (lock) {
                        // Keep starting reserved until real settlement can be proved.
                        request.retireLocked();
                    }
                } finally {
                    throw originalFailure;
                }
            }
            synchronized (lock) {
                starting = null;
            }
            return result;
        }

'''


def add_start(source):
    changes = (
        (b'import com.android.internal.widget.VerifyCredentialResponse;\n',
         b'import com.android.internal.widget.VerifyCredentialResponse;\nimport java.util.concurrent.Executor;\n'),
        (b'        private GuestPinCheckRequest current;\n',
         b'        private GuestPinCheckRequest current;\n        private GuestPinCheckRequest starting;\n'),
        (b'            synchronized (lock) {\n                if (current != null) {',
         b'            synchronized (lock) {\n                require(starting == null);\n'
         b'                if (current != null) {'),
        (b'        GuestPinCheckRequest adoptBeforeExecute(',
         EXECUTE_ADOPTED + b'        GuestPinCheckRequest adoptBeforeExecute('),
        (b'    private boolean retired;\n', b'    private boolean retired;\n    private boolean startClaimed;\n'),
    )
    if b'\r\n' in source:
        changes = tuple((old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n')) for old, new in changes)
    updated = source
    for old, new in changes:
        if updated.count(old) != 1 or new in updated:
            raise ValueError('Exact original start anchor changed')
        updated = updated.replace(old, new, 1)
    inverse = updated
    for old, new in reversed(changes):
        if inverse.count(new) != 1:
            raise ValueError('Staged start lacks the exact inverse')
        inverse = inverse.replace(new, old, 1)
    if inverse != source:
        raise ValueError('Staged start lacks the whole-source inverse')
    return updated


def compose():
    io = load_io()
    base = json.loads(pinned(io, *BASE, 16384), object_pairs_hook=io['unique_object'])
    if (base['status'] != 'STAGED_DONOR_PIN_LIFECYCLE_RELOCATION_SOURCE_ONLY'
            or base['selected'] is not False or base['deviceEligible'] is not False
            or base['package'] != PACKAGE or set(base['outputs']) != {REQUEST, COMPLETION}):
        raise ValueError('Expected the held disabled lifecycle source pair')
    originals = {name: pinned(io, row['path'], row['sha256'], 16384)
                 for name, row in base['outputs'].items()}
    sources = {REQUEST: add_start(originals[REQUEST]), COMPLETION: originals[COMPLETION]}
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
        'schema': 'oneos-guest-pin-dispatch-start-source/v1',
        'status': 'STAGED_DONOR_PIN_DISPATCH_START_SOURCE_ONLY',
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
