"""Stage the exact original guest SystemServer Runnable entry observation."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from run_guest_tree_install_transport import ROOT, load_io, pinned


PACKAGE = 'com/android/internal/os'
HELPER = 'PreparedGuestSystemServerFork.java'
PERMIT = 'GuestForkCapturePermit.java'
BASE = 'compat/boot/' + PACKAGE + '/'
PINS = {
    HELPER: '201dd20fac8c11ea6643a82b3c464f8ae282300731ef120fab03612f3344babc',
    PERMIT: 'a3bb4f98267964d7bc480d08374741516cf48c3116e891f3175fa9e2a5f7b761',
}
OUT = ROOT / 'out/guest-system-server-runnable-source'
ANCHOR = b'    private static void observeZeroChild() throws java.io.IOException {'

RUN_ENTRY = b'''    /** Observes the exact original run entry and preserves the original call. */
    static void invokeOriginalSystemServerRunnable(Runnable actual) {
        ChildRecord owned = observeRunnableEntry(actual);
        try {
            actual.run();
        } finally {
            if (owned != null) {
                owned.runActive = false;
                failChildSafely(owned);
            }
        }
    }

    private static ChildRecord observeRunnableEntry(Runnable actual) {
        ChildRecord record = child;
        if (record == null || record.off) return null;
        try {
            require(!record.failed && Thread.currentThread() == record.sourceThread
                    && record.linked && !record.runEntryClaimed && actual == record.runnable
                    && record.selfPidfd != null && record.selfPidfd.valid());
            // Reserve before any external currentness observation can reenter.
            record.runEntryClaimed = true;
            requireBootCohort(record);
            requireCurrent(record);
            record.runActive = true;
            return record;
        } catch (Throwable observationFailure) {
            failChildSafely(record);
            return null;
        }
    }

'''

OLD_CURRENT = b'''        require(child == record && !record.failed
                && Thread.currentThread() == record.sourceThread
                && Process.myPid() == record.selfPid);
'''
NEW_CURRENT = b'''        require(child == record && !record.failed && Thread.currentThread() == record.sourceThread);
        int observedPid = Process.myPid();
        require(child == record && !record.failed && observedPid == record.selfPid);
'''
OLD_FAIL = b'''    private static void failChildSafely() {
        try {
            ChildRecord record = child;
'''
NEW_FAIL = b'''    private static void failChildSafely() {
        failChildSafely(child);
    }

    private static void failChildSafely(ChildRecord record) {
        try {
'''


def add_run_entry(source):
    edits = (
        (ANCHOR, RUN_ENTRY + ANCHOR),
        (OLD_CURRENT, NEW_CURRENT),
        (OLD_FAIL, NEW_FAIL),
        (b'            if (Thread.currentThread() != record.sourceThread) return;',
         b'            if (Thread.currentThread() != record.sourceThread || record.runActive) return;'),
        (b'        boolean linked;\n',
         b'        boolean linked;\n        boolean runEntryClaimed;\n        boolean runActive;\n'),
    )
    if b'\r\n' in source:
        edits = tuple((before.replace(b'\n', b'\r\n'), after.replace(b'\n', b'\r\n'))
                      for before, after in edits)
    staged = source
    for before, after in edits:
        if staged.count(before) != 1 or after in staged:
            raise ValueError('Expected the exact guest startup source anchor')
        staged = staged.replace(before, after, 1)
    inverse = staged
    for before, after in reversed(edits):
        if inverse.count(after) != 1:
            raise ValueError('Runnable entry lacks an exact inverse anchor')
        inverse = inverse.replace(after, before, 1)
    if inverse != source:
        raise ValueError('Runnable entry lacks the whole-source inverse')
    return staged


def compose():
    io = load_io()
    originals = {name: pinned(io, BASE + name, pin, 16384) for name, pin in PINS.items()}
    sources = {HELPER: add_run_entry(originals[HELPER]), PERMIT: originals[PERMIT]}
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    target = run / Path(PACKAGE)
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
        'schema': 'oneos-guest-system-server-runnable-source/v1',
        'status': 'STAGED_GUEST_SYSTEM_SERVER_RUNNABLE_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'wholeSourceInversePassed': True, 'outputs': outputs,
        'originalSources': {BASE + name: pin for name, pin in PINS.items()},
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
