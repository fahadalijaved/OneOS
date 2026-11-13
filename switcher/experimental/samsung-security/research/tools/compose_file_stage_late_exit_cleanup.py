"""Stage late process-exit cleanup for the held Prepare and Stop worker."""

import argparse
import hashlib
import json
from uuid import uuid4

from run_guest_tree_install_transport import ROOT, load_io, pinned


NAME = 'RetainedHostNativeControlV2.java'
BASE = 'out/file-stage-readiness-build/r-98658bf067'
SOURCE = (BASE + '/host/src/' + NAME,
          '52482a9358f32ee51dd50d7a38d8a91f5b7cdb042bcb48ea6518723677e5671f')
OUT = ROOT / 'out/file-stage-late-exit-source'

ORIGINAL = b'''        long until = deadline();
        Thread actual;
        synchronized (lock) { actual = exitThread; }
        if (actual != null) {
            try { actual.join(remaining(until)); if (actual.isAlive()) okay = false; }
            catch (Throwable problem) { failed(problem); okay = false; }
        } else if (pidfdValidated) {
            // A failed observer start may already have an owned stack. Never
            // replace it or close its live descriptor based on a timeout.
            okay = false;
        }
        if (pidfd != null && (!pidfdValidated || (pidfdExited && exitFinished))) okay &= closePidfd();
'''

SUCCESSOR = b'''        long until = deadline();
        Thread actual;
        boolean retainedTerminal;
        synchronized (lock) {
            actual = exitThread;
            retainedTerminal = pidfdValidated && lastViewState != null && lastViewState.state == 6;
        }
        boolean observedExit = false;
        if (actual != null) {
            try {
                // This worker still owns final cleanup. A caller's observation
                // deadline does not release the validated descriptor.
                if (retainedTerminal) actual.join();
                else actual.join(remaining(until));
                boolean observerEnded = !actual.isAlive();
                synchronized (lock) {
                    observedExit = observerEnded && pidfdExited && exitFinished;
                }
                if (!observerEnded) okay = false;
            } catch (Throwable problem) {
                failed(problem);
                okay = false;
            }
        } else if (pidfdValidated) {
            // A failed observer start may already have an owned stack. Never
            // replace it or close its live descriptor based on a timeout.
            okay = false;
        }
        if (pidfd != null && (!pidfdValidated || observedExit)) okay &= closePidfd();
'''


def keep_cleanup_owner(source):
    original, successor = ORIGINAL, SUCCESSOR
    if b'\r\n' in source:
        original, successor = (text.replace(b'\n', b'\r\n') for text in (original, successor))
    if source.count(original) != 1 or successor in source:
        raise ValueError('Expected the exact original settlement block')
    staged = source.replace(original, successor, 1)
    if staged.count(successor) != 1 or staged.replace(successor, original, 1) != source:
        raise ValueError('Late exit settlement lacks the exact whole-source inverse')
    return staged


def compose():
    io = load_io()
    raw = pinned(io, *SOURCE, 65536)
    staged = keep_cleanup_owner(raw)
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    run.mkdir()
    target = run / NAME
    with target.open('xb') as stream:
        stream.write(staged)
    result = {
        'schema': 'oneos-file-stage-late-exit-source/v1',
        'status': 'STAGED_FILE_STAGE_LATE_EXIT_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'baseSource': {'path': SOURCE[0], 'sha256': SOURCE[1], 'bytes': len(raw)},
        'source': {'path': target.relative_to(ROOT).as_posix(), 'bytes': len(staged),
                   'sha256': hashlib.sha256(staged).hexdigest()},
        'wholeSourceInversePassed': True,
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
