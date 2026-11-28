"""Run authored PIN scheduling-cell models against separately compiled cell bytes.

Compiles fixtures only; no Android/OEM implementation, callbacks, DPM or native work executes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'out/pin-check-completion-tests'
FIXTURES = ROOT / 'compat/tests/pin_check_completion_model'
SUPPORT = ROOT / 'tools/test_guest_policy_init.py'
SUPPORT_SHA = 'd0be8dd63d2eef588e36c5d0008930301414f4b509c9d6a5b2ab597d2eaad121'
SOURCE_PINS = {
    'compat/android/com/appleexploit/oneos/security/transport/PinCheckCompletion.java': '338d8900998c7d008df2462ab89c671842fa83b4e1fbb192892ab8a2a5be0726',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(value):
    require(isinstance(value, str) and value, 'Relative string path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in value,
            'Contained relative path required')
    return path


def build(java_home, sdk_receipt):
    captured, pins = {}, {}

    def capture(path, expected=None, size=None):
        path = path.resolve(strict=True)
        require(path.is_file(), 'Regular input required')
        if path not in captured:
            data = path.read_bytes()
            require(len(data) <= 32 * 1024 * 1024, 'Bounded input required')
            captured[path] = data
            pins[path] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        require(expected is None or pins[path]['sha256'] == expected, 'Input hash differs: ' + str(path))
        require(size is None or pins[path]['bytes'] == size, 'Input size differs: ' + str(path))
        return captured[path]

    # Execute the first retained reviewed bytes, never reread a moving definition.
    support = {'__name__': 'completion_test_support', '__file__': str(SUPPORT)}
    exec(compile(capture(SUPPORT, SUPPORT_SHA), str(SUPPORT), 'exec'), support)
    output, save, command = support['output'], support['save'], support['command']
    class_map, links = support['class_map'], support['links']
    command.__globals__['BASE'] = BASE
    java_home = java_home.resolve(strict=True)
    suffix = '.exe' if os.name == 'nt' else ''
    tools = {name: (java_home / 'bin' / (name + suffix)).resolve(strict=True)
             for name in ('java', 'javac')}
    require(all(path.is_file() and path.parent == java_home / 'bin' for path in tools.values()),
            'Canonical existing JDK required')
    manifest = FIXTURES / 'manifest.json'
    fixture = json.loads(capture(manifest))
    require(fixture['schema'] == 'pin-check-completion-authored-models/v1', 'Fixture schema differs')
    selected = fixture['actualSelectedSdk']
    require(isinstance(selected, dict), 'Actual compiled SDK selection required before use')
    sdk_receipt = sdk_receipt.resolve(strict=True)
    sdk_receipt.relative_to(ROOT / 'out')
    sdk = json.loads(capture(sdk_receipt, selected['receiptSha256']))
    require(sdk['status'] == 'PASS_PIN_CHECK_COMPLETION_SDK_D8_ONLY'
            and sdk['classPins'] == selected['classPins'], 'Selected actual SDK map differs')
    sdk_run = (ROOT / relative(sdk['run'])).resolve(strict=True)
    sdk_run.relative_to(ROOT / 'out')
    require(sdk_receipt.parent == sdk_run and len(sdk['classPins']) == 3, 'Exact actual program location/closure required')
    require(class_map(sdk_run / 'classes') == sdk['classPins'], 'Actual SDK class bytes changed')
    for path in [Path(__file__), *tools.values()]:
        capture(path)
    for name, expected in SOURCE_PINS.items():
        capture(ROOT / name, expected)
    sources = {role: [] for role in ('framework', 'driver')}
    destinations = set()
    for item in fixture['sources']:
        role = item['role']
        require(role in sources, 'Unexpected source role')
        name = relative(item['relative'])
        require(name.suffix == '.java', 'Only fixture Java sources allowed')
        path = (FIXTURES / role / name).resolve(strict=True)
        path.relative_to(FIXTURES.resolve(strict=True))
        require((role, str(name)) not in destinations, 'Duplicate fixture destination')
        destinations.add((role, str(name)))
        capture(path, item['sha256'], item['bytes'])
        sources[role].append((name, path))
    require(len(destinations) == 5 and {path.resolve() for path in FIXTURES.rglob('*.java')}
            == {path for rows in sources.values() for _, path in rows}, 'Exact authored source closure required')
    for name, expected in sdk['classPins'].items():
        capture(sdk_run / 'classes' / relative(name), expected)

    def boundary():
        for path, record in pins.items():
            require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                    'Original input changed: ' + str(path))
        require(class_map(sdk_run / 'classes') == sdk['classPins'], 'Original SDK closure changed')

    boundary()
    output(BASE).mkdir(exist_ok=True)
    run = output(BASE / ('r-' + uuid.uuid4().hex[:8]))
    run.mkdir()
    print(json.dumps({'run': run.relative_to(ROOT).as_posix(), 'productionRecompiled': False}), flush=True)
    result = {'schema': 'pin-check-completion-authored-tests/v1', 'status': 'FAILED',
              'commands': {}, 'productionRecompiled': False, 'classfileShaping': False,
              'privateCellStateInspected': False, 'androidNativeOrPhoneActions': False,
              'sdkReceipt': {'path': sdk_receipt.relative_to(ROOT).as_posix(), **pins[sdk_receipt]}}
    try:
        for folder in ('inputs', 'src', 'program', 'framework', 'driver', 'tmp', 'runtime-home',
                       'empty-native', 'empty-classpath'):
            output(run / folder).mkdir()
        snapshots, staged = {}, {role: [] for role in sources}
        for index, (path, record) in enumerate(sorted(pins.items(), key=lambda row: str(row[0]))):
            target = run / 'inputs' / ('%03d-' % index + path.name)
            target.write_bytes(captured[path])
            snapshots[str(path)] = {'path': target.relative_to(ROOT).as_posix(), **record}
        for role, rows in sources.items():
            for name, source in rows:
                target = output(run / 'src' / role / name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(captured[source])
                staged[role].append(target)
        for name, expected in sdk['classPins'].items():
            target = output(run / 'program' / relative(name))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(captured[(sdk_run / 'classes' / name).resolve(strict=True)])
        env = {key: value for key, value in os.environ.items() if key.upper() not in support['STRIP']}
        env.update(TMP=str(run / 'tmp'), TEMP=str(run / 'tmp'), TMPDIR=str(run / 'tmp'),
                   HOME=str(run / 'runtime-home'), USERPROFILE=str(run / 'runtime-home'))
        jvm = ['-Xmx256m', '-Djava.io.tmpdir=' + str(run / 'tmp'),
               '-Duser.home=' + str(run / 'runtime-home'), '-Djava.library.path=' + str(run / 'empty-native')]
        javac = [tools['javac'], *['-J' + value for value in jvm], '-proc:none', '-implicit:none',
                 '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-sourcepath', '']

        def copies():
            boundary()
            require(class_map(run / 'program') == sdk['classPins'], 'Copied SDK bytes changed')
            for record in snapshots.values():
                require(sha(ROOT / record['path']) == record['sha256'], 'Retained input changed')
            for role, rows in sources.items():
                for (_, original), target in zip(rows, staged[role]):
                    require(sha(target) == pins[original]['sha256'], 'Staged fixture changed')

        for role in ('framework', 'driver'):
            copies()
            cp = run / ('program' if role == 'framework' else 'empty-classpath')
            result['commands']['compile-' + role] = command(
                [*javac, '-classpath', cp, '-d', run / role, *staged[role]], run, env, 'compile-' + role, tools)
        actual = {role: class_map(run / role) for role in sources}
        require(all(actual.values()) and not (set(actual['framework']) & set(sdk['classPins'])),
                'Nonempty modeled output must not replace helper definitions')
        metadata = {role: {name: links((run / role / name).read_bytes()) for name in rows}
                    for role, rows in actual.items()}
        require(all(record['name'] + '.class' == name for rows in metadata.values() for name, record in rows.items()),
                'Compiled fixture internal name differs')
        copies()
        result['commands']['models'] = command(
            [tools['java'], *jvm, '-Xint', '-cp', run / 'driver', 'model.CompletionModelTest',
             run / 'program', run / 'framework'], run, env, 'models', tools)
        lines = (run / 'models.stdout').read_text(encoding='utf-8').splitlines()
        require(len(lines) == 17 and lines[:-1] == ['MODEL_CASE ' + str(n) for n in range(16)],
                'Exact bounded case order required')
        tests = json.loads(lines[-1])
        require(tests == {'pass': True, 'modeledOnly': True, 'cases': 16, 'checks': tests.get('checks'),
                          'privateCellStateInspected': False, 'runnableInvocations': 0}
                and type(tests['checks']) is int and tests['checks'] > 0, 'Authored result schema differs')
        copies()
        require({role: class_map(run / role) for role in sources} == actual, 'Fixture classes changed after run')
        result.update(status='PASS_AUTHORED_PIN_CHECK_COMPLETION_JVM_MODELS_ONLY', tests=tests,
                      programClassPinsBeforeAfter=sdk['classPins'], fixtureClassPinsBeforeAfter=actual,
                      fixtureClassMetadata=metadata, inputSnapshots=snapshots,
                      stagedSourcePins={path.relative_to(ROOT).as_posix(): sha(path)
                                        for paths in staged.values() for path in paths})
    except BaseException as failure:
        result.update(failureType=type(failure).__name__, failureMessage=str(failure)[:2048])
        raise
    finally:
        save(run / 'receipt.json', result)
        print(json.dumps({'status': result['status'], 'receipt': (run / 'receipt.json').relative_to(ROOT).as_posix(),
                          'receiptSha256': sha(run / 'receipt.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--sdk-receipt', type=Path, required=True)
    args = parser.parse_args()
    build(args.java_home, args.sdk_receipt)
