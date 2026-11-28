"""Stage startup exit cleanup on the exact late-exit worker."""

import argparse
import hashlib
import json
from uuid import uuid4

from run_guest_tree_install_transport import ROOT, load_io, pinned


NAME = 'RetainedHostNativeControlV2.java'
BASE = ('out/file-stage-late-exit-source/r-4b0fa0d1/receipt.json',
        'f6761d23a03d0dd2f0a3c2e99594c16ee173f8961cc3dec2ae57624d7995640c')
OUT = ROOT / 'out/file-stage-early-exit-source'

OLD_POLL = b'''    private void alive() throws Throwable {
        StructPollfd actual = new StructPollfd(); actual.fd = pidfd.getFileDescriptor(); actual.events = (short) OsConstants.POLLIN;
        int count = Os.poll(new StructPollfd[] {actual}, 0);
        require(count == 0 && actual.revents == 0, "Native process is not observed live");
    }
'''
NEW_POLL = b'''    private void alive() throws Throwable { alive(false); }

    private void alive(boolean initialProbe) throws Throwable {
        StructPollfd actual = new StructPollfd(); actual.fd = pidfd.getFileDescriptor(); actual.events = (short) OsConstants.POLLIN;
        int count = Os.poll(new StructPollfd[] {actual}, 0);
        if (initialProbe && count == 1 && (actual.revents & OsConstants.POLLIN) != 0
                && (actual.revents & (OsConstants.POLLERR | OsConstants.POLLNVAL)) == 0) {
            synchronized (lock) {
                if (pidfdValidated && exitThread == null && !exitStartAttempted) {
                    preObserverExitFd = actual.fd;
                }
            }
        }
        require(count == 0 && actual.revents == 0, "Native process is not observed live");
    }
'''


def keep_initial_exit_evidence(raw):
    edits = (
        (b'    private FileDescriptor procRead, procCloseUncertain, pidfdClosing;\n',
         b'    private FileDescriptor procRead, procCloseUncertain, pidfdClosing;\n'
         b'    private FileDescriptor preObserverExitFd;\n'),
        (b'            pidfdValidated = true;\n            alive();',
         b'            pidfdValidated = true;\n            alive(true);'),
        (OLD_POLL, NEW_POLL),
        (b'        boolean retainedTerminal;\n        synchronized (lock) {\n            actual = exitThread;\n'
         b'            retainedTerminal = pidfdValidated && lastViewState != null && lastViewState.state == 6;\n'
         b'        }\n        boolean observedExit = false;',
         b'        boolean retainedTerminal, observedExit;\n        synchronized (lock) {\n'
         b'            actual = exitThread;\n'
         b'            // Pre-birth exit permits only local descriptor disposal.\n'
         b'            observedExit = preObserverExitFd != null && actual == null && !exitStartAttempted;\n'
         b'            retainedTerminal = pidfdValidated && lastViewState != null && lastViewState.state == 6;\n'
         b'        }'),
        (b'            pidfdClosing = pidfd.getFileDescriptor(); pidfdCloseAttempted = true;',
         b'            pidfdClosing = pidfd.getFileDescriptor();\n'
         b'            require(preObserverExitFd == null || preObserverExitFd == pidfdClosing,\n'
         b'                    "Initial exit descriptor changed");\n'
         b'            pidfdCloseAttempted = true;'),
    )
    if b'\r\n' in raw:
        edits = tuple((old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n')) for old, new in edits)
    staged = raw
    for old, new in edits:
        if staged.count(old) != 1 or new in staged:
            raise ValueError('Expected the exact early-exit source anchor')
        staged = staged.replace(old, new, 1)
    restored = staged
    for old, new in reversed(edits):
        if restored.count(new) != 1:
            raise ValueError('Early-exit staging lacks an exact inverse anchor')
        restored = restored.replace(new, old, 1)
    if restored != raw:
        raise ValueError('Early-exit staging lacks the exact whole-source inverse')
    return staged


def compose():
    io = load_io()
    base = json.loads(pinned(io, *BASE, 16384), object_pairs_hook=io['unique_object'])
    if (base['status'] != 'STAGED_FILE_STAGE_LATE_EXIT_SOURCE_ONLY'
            or base['selected'] is not False or base['deviceEligible'] is not False):
        raise ValueError('Expected the held late-exit worker')
    source = base['source']
    original = pinned(io, source['path'], source['sha256'], 65536)
    if len(original) != source['bytes']:
        raise ValueError('Expected the exact late-exit source extent')
    staged = keep_initial_exit_evidence(original)
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    run.mkdir()
    target = run / NAME
    with target.open('xb') as stream:
        stream.write(staged)
    result = {
        'schema': 'oneos-file-stage-early-exit-source/v1',
        'status': 'STAGED_FILE_STAGE_EARLY_EXIT_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'baseSource': source,
        'baseReceipt': {'path': BASE[0], 'sha256': BASE[1]},
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
