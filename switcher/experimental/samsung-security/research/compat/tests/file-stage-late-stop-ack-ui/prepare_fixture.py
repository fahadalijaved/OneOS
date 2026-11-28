"""Stage an exact Activity Operation with an authored Stop-acknowledgment model."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'out/late-stop-ack-ui-worker'
PRIOR = ROOT / 'out/file-stage-tester-ui-review'
TEMPLATE = 'e1ce3a847f1515d8b1391d0ba23444cf5fa9003af63cdeca9c88965aab15b659'
HOST = 'c36e0b7aa7ef1af391d41054d8be7080cfb4c4e9e37acb53543ea09cbbaae82b'
PROTOCOL = 'cc59e6f39856c1c7093adebfe93312b99d3bbf41b2b1f068a8638e1a8dbc93c7'
ORIGINAL_ACTIVITY = 'd9e4c23210dc28fc621c89cbbe3d49030e274a902c6ae82118b276ac823cefeb'
ORIGINAL_HARNESS = 'd15648e82f9286751a1e30237cfe1c297610ac39df17a8fce3df397a5063fec0'
OPERATION = b'    private static final class Operation implements ServiceConnection {\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_path(path, allow_missing_leaf=False):
    require(path.is_absolute() and path == Path(os.path.normpath(path)) and path.is_relative_to(ROOT),
            'Expected literal repo path')
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if part == path and allow_missing_leaf:
                return None
            raise
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                'Fixture path alias refused')
    return info


def read(path, expected=None):
    require(stat.S_ISREG(check_path(path).st_mode), 'Expected regular fixture input')
    with path.open('rb') as source:
        raw = source.read(65537)
    require(0 < len(raw) <= 65536 and (expected is None or digest(raw) == expected), 'Fixture input pin differs')
    return raw


def operation(raw):
    require(raw.count(OPERATION) == 1 and raw.endswith(b'\n    }\n}\n'), 'Exact final Operation declaration required')
    return raw[raw.index(OPERATION):-3]


def replace(raw, before, after):
    before, after = before.encode('ascii'), after.encode('ascii')
    require(raw.count(before) == 1, 'One exact fixture template anchor required')
    return raw.replace(before, after, 1)


def overlay(template, cases):
    revised = replace(template, '    private static long elapsed;\n', '''    private static boolean loseStop, lateStopAck, onWorker;
    private static int statusReads, lastAckStatusRead;
    private static long elapsed;
''')
    revised = replace(revised, '        void unbindService(ServiceConnection c) { unbinds++; }', '''        Runnable onUnbind;
        void unbindService(ServiceConnection c) {
            unbinds++;
            if (onUnbind != null) onUnbind.run();
        }''')
    revised = replace(revised, '        int status() { return host.status(10021, 234); }', '''        int status() { statusReads++; return host.status(10021, 234); }
        boolean stopAcknowledged() {
            check(onWorker && statusReads > lastAckStatusRead, "Stop ack is sampled on worker after status");
            lastAckStatusRead = statusReads;
            return lateStopAck;
        }''')
    revised = replace(revised, '        int stop() { stops++; return RetainedViewAppProtocol.QUEUED; }', '''        int stop() {
            stops++;
            if (loseStop) throw new IllegalStateException("Modeled lost Stop reply after request");
            return RetainedViewAppProtocol.QUEUED;
        }''')
    revised = replace(revised, '        acknowledged = withAck; losePrepare = false;', '''        acknowledged = withAck; losePrepare = false;
        loseStop = lateStopAck = onWorker = false;
        statusReads = lastAckStatusRead = 0;''')
    revised = replace(revised, '        while (!workerQueue.isEmpty()) workerQueue.remove().run();', '''        onWorker = true;
        try { while (!workerQueue.isEmpty()) workerQueue.remove().run(); }
        finally { onWorker = false; }''')
    main = b'    public static void main(String[] args) throws Exception {\n'
    require(revised.count(main) == 1 and cases.endswith(b'\n'), 'Expected exact fixture main boundary')
    revised = revised.replace(main, cases + b'\n' + main, 1)
    return replace(revised, '        System.out.println("9 readiness cases passed");', '''        lateAckAtLocalTerminal(); lateAckAtCleanup(); cleanupWithoutAck(); ackWithoutRequestedStop();
        System.out.println("13 readiness and late Stop acknowledgment cases passed");''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activity', type=Path, required=True)
    parser.add_argument('--activity-sha256', required=True)
    args = parser.parse_args()
    source = ROOT / args.activity
    require(source.is_relative_to(ROOT / 'out'), 'Expected staged Activity under repo out')
    actual = operation(read(source, args.activity_sha256))
    template = read(PRIOR / 'AppHarness.template', TEMPLATE)
    old = operation(read(PRIOR / 'readiness/app/PrepareActivity.java', ORIGINAL_ACTIVITY))
    require(digest(template + old + b'\n}\n') == ORIGINAL_HARNESS, 'Prior fixture extraction differs')
    cases = read(HERE / 'Cases.java.inc')
    host = read(PRIOR / 'model/HostHarness.java', HOST)
    protocol = read(PRIOR / 'model/RetainedViewAppProtocol.java', PROTOCOL)
    staged = {'AppHarness.java': overlay(template, cases) + actual + b'\n}\n',
              'HostHarness.java': host, 'RetainedViewAppProtocol.java': protocol}
    require(operation(staged['AppHarness.java']) == actual, 'Staged Operation differs from exact input')

    output_root = check_path(BASE, allow_missing_leaf=True)
    require(output_root is None or stat.S_ISDIR(output_root.st_mode), 'Expected fixture output directory')
    BASE.mkdir(exist_ok=True)
    run = BASE / ('r-' + uuid.uuid4().hex[:10])
    run.mkdir()
    for name, raw in staged.items():
        with (run / name).open('xb') as output:
            output.write(raw)
        require((run / name).read_bytes() == raw, 'Staged fixture changed')
    receipt = {'status': 'STAGED_EXACT_OPERATION_AND_AUTHORED_FIXTURES_ONLY',
               'activity': source.relative_to(ROOT).as_posix(), 'activitySha256': args.activity_sha256,
               'operationSha256': digest(actual), 'casesSha256': digest(cases),
               'fixturePins': {name: digest(raw) for name, raw in staged.items()}}
    with (run / 'source.json').open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(receipt, indent=2) + '\n')
    print(run.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
