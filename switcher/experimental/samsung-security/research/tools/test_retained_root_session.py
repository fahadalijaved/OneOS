"""Run closed root-session models with unchanged SDK controller and only fake Spawn.

Compiles authored Android-public-API/Spawn fixtures only; never su, C, Android/OEM or JNI implementations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'out/retained-root-session-tests'
FIXTURES = ROOT / 'compat/tests/retained_root_session_model'
SUPPORT = ROOT / 'tools/test_guest_policy_init.py'
SUPPORT_SHA = 'd0be8dd63d2eef588e36c5d0008930301414f4b509c9d6a5b2ab597d2eaad121'
PACKAGE = 'com/fahadali/oneos/core/root/'
SPAWN = PACKAGE + 'RetainedRootSessionSpawn.class'
JAVA_SOURCES = {'compat/android/' + PACKAGE + name + '.java' for name in
                ('RetainedRootSession','RetainedRootSessionSpawn','RetainedRootProtocol','RetainedRootCommand')}



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
    support = {'__name__': 'root_session_test_support', '__file__': str(SUPPORT)}
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
    require(fixture['schema'] == 'retained-root-session-authored-models/v1', 'Fixture schema differs')
    selected = fixture['actualSelectedSdk']
    require(isinstance(selected, dict), 'Actual compiled SDK selection required before use')
    sdk_receipt = sdk_receipt.resolve(strict=True)
    sdk_receipt.relative_to(ROOT / 'out')
    sdk = json.loads(capture(sdk_receipt, selected['receiptSha256']))
    require(sdk['status'] == 'PASS_NATIVE_STATIC_AND_PUBLIC_SDK_COMPILE_ONLY'
            and sdk['classPins'] == selected['allClassPins']
            and sdk['modelClassPins'] == selected['modelClassPins'], 'Actual SDK cohort differs')
    program = sdk['modelClassPins']
    require(set(sdk['classPins']) - set(program) == {SPAWN}
            and sdk['modelExcludedRealSpawn'] == SPAWN
            and all(sdk['classPins'][n] == h for n,h in program.items())
            and sdk['compilerOnlyProjections'] == [] and not sdk['d8Executed'],
            'Exclude only the actual package-private Spawn definition')
    sdk_run = (ROOT / relative(sdk['run'])).resolve(strict=True)
    sdk_run.relative_to(ROOT / 'out')
    model_classes = (ROOT / relative(sdk['modelClassDirectory'])).resolve(strict=True)
    model_classes.relative_to(ROOT / 'out')
    require(sdk_receipt.parent == sdk_run, 'Actual SDK receipt location differs')
    require(class_map(sdk_run / 'classes') == sdk['classPins']
            and class_map(model_classes) == program, 'Actual SDK program bytes changed')
    for path in [Path(__file__), *tools.values()]:
        capture(path)
    require(set(selected['productionSources']) == JAVA_SOURCES, 'Exact four source-owned Java components required')
    for name, expected in selected['productionSources'].items():
        require(sdk['sourcePins'].get(name) == expected, 'Compiled source binding differs')
        capture(ROOT / relative(name), expected)
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
    require(len(destinations) == 15 and {path.resolve() for path in FIXTURES.rglob('*.java')}
            == {path for rows in sources.values() for _, path in rows}, 'Exact authored source closure required')
    for folder, records in ((sdk_run / 'classes', sdk['classPins']), (model_classes, program)):
        for name, expected in records.items():
            capture(folder / relative(name), expected)

    def boundary():
        for path, record in pins.items():
            require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                    'Original input changed: ' + str(path))
        require(class_map(sdk_run / 'classes') == sdk['classPins'] and class_map(model_classes) == program, 'Original SDK/model closure changed')

    boundary()
    output(BASE).mkdir(exist_ok=True)
    run = output(BASE / ('r-' + uuid.uuid4().hex[:8]))
    run.mkdir()
    print(json.dumps({'run': run.relative_to(ROOT).as_posix(), 'productionRecompiled': False}), flush=True)
    result = {'schema': 'retained-root-session-authored-tests/v1', 'status': 'FAILED',
              'commands': {}, 'productionRecompiled': False, 'classfileShaping': False,
              'privateControllerStateInspected': False, 'realSpawnExecuted': False, 'nativeHelperExecuted': False, 'androidNativeOrPhoneActions': False,
              'sdkReceipt': {'path': sdk_receipt.relative_to(ROOT).as_posix(), **pins[sdk_receipt]}}
    try:
        for folder in ('inputs', 'src', 'program', 'framework', 'driver', 'tmp', 'runtime-home',
                       'empty-native', 'empty-classpath', 'fixture-data'):
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
        for name, expected in program.items():
            target = output(run / 'program' / relative(name))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(captured[(model_classes / name).resolve(strict=True)])
        env = {key: value for key, value in os.environ.items() if key.upper() not in support['STRIP']}
        env.update(TMP=str(run / 'tmp'), TEMP=str(run / 'tmp'), TMPDIR=str(run / 'tmp'),
                   HOME=str(run / 'runtime-home'), USERPROFILE=str(run / 'runtime-home'))
        jvm = ['-Xmx256m', '-Djava.io.tmpdir=' + str(run / 'tmp'),
               '-Duser.home=' + str(run / 'runtime-home'), '-Djava.library.path=' + str(run / 'empty-native')]
        javac = [tools['javac'], *['-J' + value for value in jvm], '-proc:none', '-implicit:none',
                 '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-sourcepath', '']

        def copies():
            boundary()
            require(class_map(run / 'program') == program, 'Copied SDK bytes changed')
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
        require(all(actual.values()) and set(actual['framework']) & set(sdk['classPins']) == {SPAWN},
                'Only the authored Spawn boundary may replace a production definition')
        metadata = {role: {name: links((run / role / name).read_bytes()) for name in rows}
                    for role, rows in actual.items()}
        require(all(record['name'] + '.class' == name for rows in metadata.values() for name, record in rows.items()),
                'Compiled fixture internal name differs')
        copies()
        result['commands']['models'] = command(
            [tools['java'], *jvm, '-Xint', '-cp', run / 'driver', 'model.RootSessionModelTest',
             run / 'program', run / 'framework', run / 'fixture-data', ROOT], run, env, 'models', tools)
        lines = (run / 'models.stdout').read_text(encoding='utf-8').splitlines()
        require(len(lines) == 26 and lines[:-1] == ['MODEL_CASE ' + str(n) for n in range(25)],
                'Exact bounded case order required')
        tests = json.loads(lines[-1])
        require(tests == {'pass': True, 'modeledOnly': True, 'cases': 25, 'checks': tests.get('checks'),
                          'privateControllerStateInspected': False, 'nativeOrSuExecuted': False}
                and type(tests['checks']) is int and tests['checks'] > 0, 'Authored result schema differs')
        copies()
        require({role: class_map(run / role) for role in sources} == actual, 'Fixture classes changed after run')
        require(not list((run / 'fixture-data').iterdir()), 'Fixture data cleanup incomplete')
        result.update(status='PASS_AUTHORED_ROOT_SESSION_JVM_MODELS_ONLY', tests=tests,
                      programClassPinsBeforeAfter=program, originalSdkClassPinsBeforeAfter=sdk['classPins'], excludedRealSpawn=SPAWN, fixtureClassPinsBeforeAfter=actual,
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
