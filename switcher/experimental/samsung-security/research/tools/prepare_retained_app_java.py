"""Place six authored sources in a local full-flavor candidate; never build or run."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CLONE = ROOT / 'firmware/oneos-pr/OneOS'
SOURCE = ROOT / 'compat/android/com/fahadali/oneos/core/root'
TARGET = CLONE / 'app-android/app/src/full/java/com/fahadali/oneos/core/root'
NAMES = ('RetainedRootSession', 'RetainedRootSessionSpawn', 'RetainedRootCommand',
         'RetainedRootProtocol', 'ClosedRootLinkProtocol', 'RetainedRootHostService')
BASE = '93c6da8053e3494b8732bc359b2095319ff93b6a'
OLD = b'                RetainedRootSession.Attempt returned = RetainedRootSession.begin(sha256, bytes);'
NEW = (b'                com.fahadali.oneos.session.RetainedControllerSetup.ensureInstalled(service, sha256, bytes);\n'
       b'                if (!mayContinue()) { notifyHost(null); return; }\n' + OLD)
CALL_GUARD = b'        if (Binder.getCallingUid() != 1000) throw new SecurityException("System caller required");'
SDK_GUARD = (CALL_GUARD + b'\n        if (android.os.Build.VERSION.SDK_INT != 37) {\n'
             b'            throw new IllegalStateException("Retained controller profile unavailable");\n'
             b'        }')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CLONE).decode().strip() == BASE
    source = {name: (SOURCE/(name+'.java')).read_bytes() for name in NAMES}
    service = source['RetainedRootHostService']
    assert sha(service) == '6a11fd931157368e68de80771fcb6669f280399c96129f42b82a11d23af3d9ea'
    assert service.count(OLD) == 1 and NEW not in service and service.count(CALL_GUARD) == 1
    derived = dict(source)
    derived['RetainedRootHostService'] = service.replace(OLD, NEW).replace(CALL_GUARD, SDK_GUARD)
    assert derived['RetainedRootHostService'].replace(NEW, OLD).replace(SDK_GUARD, CALL_GUARD) == service
    TARGET.resolve().relative_to(CLONE.resolve())
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, data in derived.items():
        path = TARGET/(name+'.java')
        # Refuse overwriting other implementation work, including partial copies.
        if path.exists():
            assert path.is_file() and not path.is_symlink()
            previous = path.read_bytes()
            if name == 'RetainedRootHostService' and sha(previous) == '52846a4751544e2bb30b4b5f7d31ddab7ac8bf9985d2d95f6ff7acda9f437fd9':
                history = ROOT/'out/full-app-integration/service-52846-before-sdkguard.java'
                history.parent.mkdir(parents=True, exist_ok=True)
                if history.exists():
                    assert history.read_bytes() == previous
                else:
                    history.write_bytes(previous)
                path.write_bytes(data)
            else:
                assert previous == data
        else:
            with path.open('xb') as out:
                out.write(data)
    assert all((SOURCE/(name+'.java')).read_bytes() == data for name, data in source.items())
    assert all((TARGET/(name+'.java')).read_bytes() == data for name, data in derived.items())
    result = {'status': 'SOURCE_PLACEMENT_ONLY', 'baseCommit': BASE,
              'canonicalSourcesUnchanged': True, 'fullOnly': True,
              'serviceChange': 'SDK37 guard before newer Parcel APIs; actual pinned installer before begin and local retirement fence',
              'exactServiceInverse': True, 'sources': {
                  name: {'canonicalSha256': sha(source[name]), 'candidateSha256': sha(derived[name]),
                         'candidate': (TARGET/(name+'.java')).relative_to(ROOT).as_posix()}
                  for name in NAMES},
              'buildOrAndroidOrNativeOrPhoneExecution': False}
    out = ROOT/'out/full-app-integration'
    out.mkdir(exist_ok=True)
    (out/'java-placement.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'files': len(derived), 'actualServiceSha256': sha(derived['RetainedRootHostService'])}))

if __name__ == '__main__':
    main()
