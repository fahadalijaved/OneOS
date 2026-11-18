"""Export the fixed local candidate delta; no commit, remote operation or build."""
from pathlib import Path
import hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
CLONE = ROOT/'firmware/oneos-pr/OneOS'
BASE = '93c6da8053e3494b8732bc359b2095319ff93b6a'
PACKAGE = 'app-android/app/src/full/java/com/fahadali/oneos/core/root/'
FILES = [
    '.gitattributes', 'app-android/app/build.gradle.kts',
    'app-android/app/src/full/AndroidManifest.xml',
    'app-android/app/src/full/assets/root/oneos_root.sh',
    'app-android/app/src/full/kotlin/com/fahadali/oneos/session/RootVerbs.kt',
    'app-android/app/src/full/kotlin/com/fahadali/oneos/session/RetainedControllerSetup.kt',
    'app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootScript.kt',
    'app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootShell.kt',
    'scripts/build-retained-root-session.py',
    'switcher/native/retained_root_session.c',
    'switcher/native/retained_root_session_protocol.h',
] + [PACKAGE+n+'.java' for n in ('RetainedRootSession', 'RetainedRootSessionSpawn',
     'RetainedRootProtocol', 'RetainedRootCommand', 'ClosedRootLinkProtocol', 'RetainedRootHostService')]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=CLONE)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert len(FILES) == len(set(FILES)) == 17
    before = {name: (CLONE/name).read_bytes() for name in FILES}
    assert b'\r' not in before['app-android/app/src/full/assets/root/oneos_root.sh']
    # Staging these exact reviewed source paths does not commit or publish them.
    subprocess.run(['git', 'add', '--', *FILES], cwd=CLONE, check=True)
    staged = git('diff', '--cached', '--name-only', '-z').decode().split('\0')
    assert set(filter(None, staged)) == set(FILES), 'Unexpected staged candidate path'
    records = {}
    for name in FILES:
        committed = git('show', ':'+name)
        # Git text normalization is recorded rather than confused with new code.
        assert committed == before[name] or committed == before[name].replace(b'\r\n', b'\n')
        if name.startswith('switcher/native/'):
            assert committed == before[name], 'Native recipe requires exact source bytes in Git'
        records[name] = {'workingSha256': digest(before[name]), 'gitBlobSha256': digest(committed),
                         'bytes': len(committed), 'eolNormalizationOnly': committed != before[name]}
    patch = git('diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--unified=3')
    assert 0 < len(patch) < 512*1024
    assert all((CLONE/name).read_bytes() == data for name, data in before.items())
    out = ROOT/'compat/app-integration/oneos-retained-controller.patch'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(patch)
    record = {'schema': 'oneos-retained-controller-candidate/v1',
              'status': 'REVIEWED_LOCAL_SOURCE_DELTA_NOT_PUBLISHED', 'baseCommit': BASE,
              'patch': out.relative_to(ROOT).as_posix(), 'patchSha256': digest(patch),
              'patchBytes': len(patch), 'files': records,
              'nativeBinaryIncluded': False, 'phoneOrRemoteOperation': False,
              'fullGradleOrApkAcceptance': False}
    (ROOT/'inventory/retained-app-candidate.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'status': record['status'], 'files': len(FILES), 'patchSha256': digest(patch), 'patchBytes': len(patch)}))

if __name__ == '__main__':
    main()
