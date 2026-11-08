"""Run authored bootstrap fixtures against unchanged, reviewed SDK class files.

Requires the separately built SDK receipt; compiles only checked-in JDK fixtures.
No Android/OEM implementation or JNI, DEX, APK or device is executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'out/retained-pin-bootstrap-tests'
FIXTURES = ROOT / 'compat/tests/retained_pin_bootstrap_model'
SUPPORT = ROOT / 'tools/test_guest_policy_init.py'
SUPPORT_SHA = 'd0be8dd63d2eef588e36c5d0008930301414f4b509c9d6a5b2ab597d2eaad121'
SOURCE_PINS = {
    'compat/host-module/com/appleexploit/oneos/security/authority/RetainedPinHostModule.java': '0544fd310a96c9b9a83ee1f8aa9d5faf97b23aab34bc8eeaee0c2e6d19aa0b9d',
    'compat/host-module/com/appleexploit/oneos/security/authority/HostBootstrapPermit.java': 'f0ad63b4b85c718123679efebd47fd375f59de80eeca835016b5d3faf9e3cbbd',
    'compat/android/com/appleexploit/oneos/security/authority/PreparedRetainedPinBinding.java': 'f7f006d2d9db467d46abb1a14f94bcabd63f5e63f6218b1eef43d926729a35ed',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(value):
    require(isinstance(value, str), 'String path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in value,
            'Contained relative path required')
    return path


def build(java_home, sdk_receipt):
    captured, input_pins = {}, {}

    def capture(path, expected_hash=None, expected_size=None):
        path = path.resolve(strict=True)
        require(path.is_file(), 'Regular input required')
        if path not in captured:
            data = path.read_bytes()
            require(len(data) <= 32 * 1024 * 1024, 'Bounded input required')
            captured[path] = data
            input_pins[path] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        record = input_pins[path]
        require(expected_hash is None or record['sha256'] == expected_hash, 'Captured input hash differs: ' + str(path))
        require(expected_size is None or record['bytes'] == expected_size, 'Captured input size differs: ' + str(path))
        return captured[path]

    support_bytes = capture(SUPPORT, SUPPORT_SHA)
    support = {'__name__': 'bootstrap_test_support', '__file__': str(SUPPORT)}
    exec(compile(support_bytes, str(SUPPORT), 'exec'), support)
    output, save = support['output'], support['save']
    class_map, command, links = support['class_map'], support['command'], support['links']
    # Same repository containment and process ownership; only the new output root differs.
    command.__globals__['BASE'] = BASE
    java_home = java_home.resolve(strict=True)
    suffix = '.exe' if os.name == 'nt' else ''
    tools = {name: (java_home / 'bin' / (name + suffix)).resolve(strict=True)
             for name in ('java', 'javac')}
    require(all(path.is_file() and path.parent == java_home / 'bin'
                for path in tools.values()), 'Existing canonical JDK required')
    sdk_receipt = sdk_receipt.resolve(strict=True)
    sdk_receipt.relative_to(ROOT / 'out')
    manifest = FIXTURES / 'manifest.json'
    fixture = json.loads(capture(manifest))
    require(fixture['schema'] == 'retained-pin-bootstrap-authored-model-fixtures/v1',
            'Authored bootstrap fixture schema required')
    selected = fixture['actualSelectedSdk']
    sdk = json.loads(capture(sdk_receipt, selected['receiptSha256']))
    require(sdk['status'] == 'PASS_CAPTURE_ONLY_BOOTSTRAP_SDK_D8'
            and sdk['classPins'] == selected['programClassPins']
            and sdk['dependencyPins'] == selected['dependencyClassPins'], 'SDK class maps differ')
    require(len(sdk['classPins']) == 9 and len(sdk['dependencyPins']) == 11,
            'Actual nine program and eleven dependency definitions required')
    sdk_run = (ROOT / relative(sdk['run'])).resolve(strict=True)
    sdk_run.relative_to(ROOT / 'out')
    require(sdk_receipt.parent == sdk_run, 'Receipt and actual SDK output must agree')
    require(class_map(sdk_run / 'classes') == sdk['classPins']
            and class_map(sdk_run / 'deps') == sdk['dependencyPins'], 'Original SDK bytes changed')
    sources = {role: [] for role in ('framework', 'service', 'driver')}
    for path in (Path(__file__), SUPPORT, manifest, sdk_receipt, *tools.values()):
        capture(path)
    for name, expected in SOURCE_PINS.items():
        capture(ROOT / name, expected)
    destinations = set()
    for item in fixture['sources']:
        role = item['role']
        require(role in sources, 'Unknown fixture role')
        name = relative(item['relative'])
        require(name.suffix == '.java', 'Only authored Java sources required')
        source = (FIXTURES / relative(item['path'])).resolve(strict=True)
        source.relative_to(FIXTURES.resolve(strict=True))
        require(source == (FIXTURES / role / name).resolve(strict=True)
                and item['repoPath'] == source.relative_to(ROOT).as_posix(), 'Fixture placement differs')
        require((role, str(name)) not in destinations, 'Duplicate fixture destination')
        destinations.add((role, str(name)))
        capture(source, item['sha256'], item['bytes'])
        sources[role].append((name, source))
    require(len(destinations) == 69 and set(FIXTURES.rglob('*.java'))
            == {path for role in sources.values() for _, path in role}, 'Exact authored source closure required')
    for folder, pins in (('classes', sdk['classPins']), ('deps', sdk['dependencyPins'])):
        for name, expected in pins.items():
            capture(sdk_run / folder / relative(name), expected)

    def boundary():
        for path, expected in input_pins.items():
            require(path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'],
                    'Input changed: ' + str(path))
        require(class_map(sdk_run / 'classes') == sdk['classPins']
                and class_map(sdk_run / 'deps') == sdk['dependencyPins'], 'Original SDK closure changed')

    boundary()
    output(BASE).mkdir(exist_ok=True)
    run = output(BASE / ('r-' + uuid.uuid4().hex[:8]))
    run.mkdir()
    print(json.dumps({'run': run.relative_to(ROOT).as_posix(), 'productionRecompiled': False}), flush=True)
    result = {'schema': 'retained-pin-bootstrap-public-jdk-tests/v1', 'status': 'FAILED',
              'commands': {}, 'productionRecompiled': False, 'classfileShaping': False,
              'sdkImplementationRuntime': False, 'phoneActions': [],
              'sdkReceipt': {'path': sdk_receipt.relative_to(ROOT).as_posix(),
                             'sha256': input_pins[sdk_receipt]['sha256']}}
    try:
        for folder in ('src', 'program', 'deps', 'framework', 'service', 'driver',
                       'inputs', 'tmp', 'runtime-home', 'empty-native', 'empty-classpath', 'permit-data'):
            output(run / folder).mkdir()
        snapshots = {}
        for index, (path, expected) in enumerate(sorted(input_pins.items(), key=lambda pair: str(pair[0]))):
            target = run / 'inputs' / ('%03d-' % index + path.name)
            target.write_bytes(captured[path])
            require(sha(target) == expected['sha256'], 'Input snapshot changed')
            snapshots[str(path)] = {'path': target.relative_to(ROOT).as_posix(), **expected}
        staged = {}
        for role, items in sources.items():
            staged[role] = []
            for name, source in items:
                target = output(run / 'src' / role / name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(captured[source])
                staged[role].append(target)
        for source_folder, target_folder, pins in (('classes', 'program', sdk['classPins']),
                                                   ('deps', 'deps', sdk['dependencyPins'])):
            for name, expected in pins.items():
                target = output(run / target_folder / relative(name))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(captured[(sdk_run / source_folder / name).resolve(strict=True)])
                require(sha(target) == expected, 'SDK copy changed')
        env = {key: value for key, value in os.environ.items() if key.upper() not in support['STRIP']}
        env.update(TMP=str(run / 'tmp'), TEMP=str(run / 'tmp'), TMPDIR=str(run / 'tmp'),
                   HOME=str(run / 'runtime-home'), USERPROFILE=str(run / 'runtime-home'))
        jvm = ['-Xmx512m', '-Djava.io.tmpdir=' + str(run / 'tmp'),
               '-Duser.home=' + str(run / 'runtime-home'),
               '-Djava.library.path=' + str(run / 'empty-native')]
        javac = [tools['javac'], *['-J' + value for value in jvm], '-proc:none', '-implicit:none',
                 '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-sourcepath', '']

        def check_copies():
            boundary()
            require(class_map(run / 'program') == sdk['classPins']
                    and class_map(run / 'deps') == sdk['dependencyPins'], 'Runtime SDK bytes changed')
            for path, record in snapshots.items():
                require(sha(ROOT / record['path']) == record['sha256'], 'Saved snapshot changed: ' + path)
            for role, items in sources.items():
                for (name, source), target in zip(items, staged[role]):
                    require(sha(target) == input_pins[source]['sha256'], 'Staged fixture changed')

        for role in ('framework', 'service', 'driver'):
            check_copies()
            cp = run / ('framework' if role == 'service' else 'empty-classpath')
            result['commands']['compile-' + role] = command(
                [*javac, '-classpath', cp, '-d', run / role, *staged[role]], run, env, 'compile-' + role, tools)
        actual = {role: class_map(run / role) for role in sources}
        require(all(actual.values()), 'Every fixture role must produce classes')
        metadata = {role: {name: links((run / role / name).read_bytes()) for name in pins}
                    for role, pins in actual.items()}
        for role, records in metadata.items():
            require(all(record['name'] + '.class' == name for name, record in records.items()),
                    'Fixture internal class name mismatch')
            require(not any(name.startswith('com/appleexploit/oneos/security/') for name in records),
                    'Fixture must not replace a production helper')
        check_copies()
        result['commands']['models'] = command(
            [tools['java'], *jvm, '-Xint', '-cp', run / 'driver', fixture['runtimeMain'],
             run / 'program', run / 'deps', run / 'framework', run / 'service', run / 'permit-data', ROOT],
            run, env, 'models', tools)
        lines = (run / 'models.stdout').read_text(encoding='utf-8').splitlines()
        require(len(lines) == len(fixture['cases']) + 1
                and lines[:-1] == ['MODEL_CASE ' + name for name in fixture['cases']], 'Exact modeled case order required')
        tests = json.loads(lines[-1])
        require(tests == {'pass': True, 'modeledOnly': True, 'cases': fixture['expectedCases'],
                          'checks': tests.get('checks'), 'privateSdkStateInspected': False, 'verificationCalls': 0}
                and type(tests['checks']) is int and tests['checks'] > 0, 'Exact authored result shape required')
        check_copies()
        require({role: class_map(run / role) for role in sources} == actual, 'Fixture bytes changed after JVM')
        result.update(status='PASS_AUTHORED_BOOTSTRAP_JVM_TESTS_ONLY', tests=tests,
                      programClassPinsBeforeAfter=sdk['classPins'], dependencyPinsBeforeAfter=sdk['dependencyPins'],
                      fixtureClassPinsBeforeAfter=actual, fixtureClassMetadata=metadata, snapshots=snapshots,
                      stagedSources={role: [path.relative_to(ROOT).as_posix() for path in paths]
                                     for role, paths in staged.items()})
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
