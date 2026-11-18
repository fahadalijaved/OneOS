"""Run both exact SDK-compiled Activity cohorts with authored JDK fixtures."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'out/file-stage-activity-lifecycle-model'
BUILDS = {
    'baseline': ('out/file-stage-late-stop-ack-build/r-6c7d607f',
                 '4cc7b353a02d933e887beeaa029a7c5a1564ebf0caa2caace0bc3ce8e270fc4e',
                 'PASS_UNSELECTED_FILE_STAGE_LATE_STOP_ACK_APP_SDK37_DEX_ONLY'),
    'successor': ('out/file-stage-activity-lifecycle-build/r-ccef04ee',
                  '55af5c0047cf3acf79ea3ff62433dbb91bb408b96f9fd714fc184592314b11d6',
                  'PASS_UNSELECTED_FILE_STAGE_ACTIVITY_LIFECYCLE_APP_SDK37_DEX_ONLY'),
}
ACTIVITY = 'com/fahadali/oneos/viewprep/filetree/PrepareActivity'
PROTOCOL = 'com/fahadali/oneos/core/root/RetainedViewAppProtocol.class'
ENTRY = 'com.fahadali.oneos.viewprep.filetree.ActivityLifecycleFixture'
REUSED = ('Binder.java', 'IBinder.java', 'IInterface.java', 'Looper.java', 'Parcel.java',
          'RemoteException.java', 'SystemClock.java')
CASES = {'overlap': 'OVERLAP_A_LOST', 'render-both': 'OVERLAP_RENDER_STALE',
         'dialog-prepare': 'DIALOG_LIFECYCLE_STALE', 'dialog-stop': 'DIALOG_LIFECYCLE_STALE',
         'dialog-create': 'DIALOG_CREATE_OWNER_LOST', 'recreate': None}
STRIP = {'CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'JDK_JAVAC_OPTIONS'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, pin=None):
    with path.open('rb') as stream:
        raw = stream.read(1_048_577)
    require(0 < len(raw) <= 1_048_576 and (pin is None or digest(raw) == pin), 'Input pin differs: ' + path.name)
    return raw


def actual_program():
    programs, jdk = {}, None
    for cohort, (directory, receipt_pin, status) in BUILDS.items():
        receipt = json.loads(read(ROOT / directory / 'receipt.json', receipt_pin))
        require(receipt['status'] == status and receipt['run'] == directory
                and all(receipt[key] is False for key in ('selected', 'deviceEligible', 'signed', 'androidOrOemExecuted')),
                'Expected reviewed offline SDK receipt')
        roles = {name: pin for name, pin in receipt['classPins'].items() if name == PROTOCOL
                 or name == ACTIVITY + '.class' or name.startswith(ACTIVITY + '$') and name.endswith('.class')}
        require(ACTIVITY + '.class' in roles and len(roles) == 12 and PROTOCOL in roles,
                'Exact Activity and protocol class closure required')
        programs[cohort] = {name: read(ROOT / directory / 'classes' / name, pin) for name, pin in roles.items()}
        tools = {name: receipt['tools'][name] for name in ('java', 'javac')}
        require(jdk is None or jdk == tools, 'Expected same existing JDK for both cohorts')
        jdk = tools
    require(programs['baseline'].keys() == programs['successor'].keys()
            and programs['baseline'][PROTOCOL] == programs['successor'][PROTOCOL], 'Class roles or protocol changed')
    return programs, jdk


def write(run, name, raw):
    path = run / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'Fixture staging differs')
    return path


def check_tools(rows):
    for row in rows.values():
        require(len(read(Path(row['path']), row['sha256'])) == row['bytes'], 'Existing JDK bytes changed')


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    programs, tools = actual_program()
    check_tools(tools)
    sources = {p.relative_to(HERE).as_posix(): read(p) for p in sorted(HERE.rglob('*.java'))}
    require(len(sources) == 23 and not any(name.endswith('/PrepareActivity.java') for name in sources),
            'Expected authored fixture source closure')
    for name in REUSED:
        leaf = 'android/os/' + name
        require(leaf not in sources, 'Duplicate fixture source')
        sources[leaf] = read(HERE.parent / 'file-stage-late-stop-ack' / leaf)

    require(BASE.resolve() == BASE, 'Expected canonical run root')
    BASE.mkdir(exist_ok=True)
    run = BASE / ('r-' + uuid.uuid4().hex[:10])
    run.mkdir()
    for leaf in ('models', 'home', 'tmp', 'empty-native', 'empty-source'):
        (run / leaf).mkdir()
    staged = {write(run, 'src/' + name, raw): raw for name, raw in sources.items()}
    for cohort, members in programs.items():
        for name, raw in members.items():
            staged[write(run, cohort + '/' + name, raw)] = raw

    env = {key: val for key, val in os.environ.items() if key.upper() not in STRIP}
    env.update(TMP=str(run / 'tmp'), TEMP=str(run / 'tmp'), TMPDIR=str(run / 'tmp'))
    jvm = ['-Duser.home=' + str(run / 'home'), '-Djava.io.tmpdir=' + str(run / 'tmp'),
           '-Djava.library.path=' + str(run / 'empty-native')]
    result = {'status': 'FAILED', 'builds': BUILDS, 'tools': tools, 'commands': {},
              'fixtureSources': {name: digest(raw) for name, raw in sources.items()},
              'programClasses': {side: {name: digest(raw) for name, raw in members.items()}
                                 for side, members in programs.items()}}

    def invoke(label, argv):
        check_tools(tools)
        command = [str(item) for item in argv]
        child = subprocess.run(command, cwd=run, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
        for channel, raw in (('stdout', child.stdout), ('stderr', child.stderr)):
            write(run, label + '.' + channel, raw)
        result['commands'][label] = {'argv': command, 'exitCode': child.returncode,
                                     'stdoutSha256': digest(child.stdout), 'stderrSha256': digest(child.stderr)}
        return child

    try:
        compile_ = invoke('compile-models', [tools['javac']['path'], *('-J' + opt for opt in jvm), '-proc:none',
            '-implicit:none', '--release', '8', '-sourcepath', run / 'empty-source', '-classpath', run / 'baseline',
            '-d', run / 'models', *(path for path in staged if path.suffix == '.java')])
        require(compile_.returncode == 0, 'Authored fixture compile failed')
        model_classes = {path.relative_to(run / 'models').as_posix(): digest(path.read_bytes())
                         for path in (run / 'models').rglob('*.class')}
        require(model_classes and not model_classes.keys() & programs['baseline'].keys()
                and not model_classes.keys() & programs['successor'].keys(), 'Fixture shadows actual production class')
        result['modelClasses'] = model_classes
        for cohort in BUILDS:
            cp = os.pathsep.join(str(run / leaf) for leaf in (cohort, 'models'))
            for case, failure in CASES.items():
                child = invoke(cohort + '-' + case,
                               [tools['java']['path'], *jvm, '-Xint', '-cp', cp, ENTRY, case])
                expected = f'FILE_STAGE_ACTIVITY_LIFECYCLE {case} PASS'.encode('ascii')
                if cohort == 'baseline' and failure is not None:
                    require(child.returncode == 1 and not child.stdout and failure.encode('ascii') in child.stderr,
                            'Wrong baseline refusal: ' + case)
                else:
                    require(child.returncode == 0 and child.stdout.splitlines() == [expected] and not child.stderr,
                            'Unexpected fixture result: ' + cohort + '-' + case)
        require(all(path.read_bytes() == raw for path, raw in staged.items()), 'Staged fixture/program bytes changed')
        check_tools(tools)
        result['status'] = 'PASS_ACTUAL_SDK_ACTIVITY_LIFECYCLE_WITH_AUTHORED_MODELS_ONLY'
    finally:
        raw = (json.dumps(result, indent=2) + '\n').encode('utf-8')
        receipt = write(run, 'receipt.json', raw)
        print(result['status'], receipt.relative_to(ROOT).as_posix(), digest(raw))


if __name__ == '__main__':
    main()
