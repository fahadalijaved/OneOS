"""Project code 85's declared payloads and captured host fallback as a scenario."""

from hashlib import sha256
from io import BytesIO
import json
import os
import re
import stat
import tarfile
from zipfile import ZipFile

from audit_samsung_boot_classpath_cohort import MANIFEST_SHA, TAR, fragment, manifest
from check_guest_classpath_selection import ENUM, ROOT, identity, plain, read_held, require
from review_guest_classpath_factory import FRAGMENTS, JAR, file_row, member
from review_guest_classpath_frontier import expected_exports, pinned, scenarios


APK = ('firmware/installed-oneos-current/r-7b4bd2c2/base.apk', 42820359,
       'af557d9be156b2c6781be6a57958af4e9b0a9734afbf2c2ba210bce8bd247ed0')
FACTORY_PATH = 'out/guest-classpath-factory/r-5bb77c65/receipt.json'
FACTORY_SHA = '5961617a5a70b3d71d6fceed30a95748a2bbc1cc5f2b3cbd15dca2dddb4716c2'
BINDING = ('out/live-stage1-stock-stage-binding/r-ab3223b1/receipt.json', 860,
           '5a30b7e5674a138dd4607e170b68dde19820c4ec2fae817c06fee10bcf1ed7c3')
OVERRIDES = {
    '/system/framework/framework.jar': 'framework_patched.jar',
    '/system/framework/telephony-common.jar': 'telephony-common_patched.jar',
    '/system/framework/services.jar': 'services_patched.jar',
    '/system/framework/oplus-services.jar': 'oplus-services_patched.jar',
}


def sums(raw):
    output = {}
    for line in raw.decode('ascii').splitlines():
        digest, name = line.split('  ')
        require(re.fullmatch(r'[0-9a-f]{64}', digest) and re.fullmatch(r'[A-Za-z0-9._+-]+', name)
                and name not in output, 'Exact unique stage checksum row')
        output[name] = digest
    return output


def read_selection(binding, factory):
    with ZipFile(BytesIO(pinned(*APK))) as archive:
        scripts = sums(member(archive, 'assets/oneos/sets/scripts.sha256', 4096))
        packages = sums(member(archive, 'assets/oneos/sets/x9u-in-sultra.sha256', 4096))
        prepare_sha = scripts['guest_prepare.sh']
        prepare = member(archive, 'assets/oneos/files/' + prepare_sha, 512 * 1024)
        require(sha256(prepare).hexdigest() == prepare_sha, 'Exact packaged prepare script')
    require(len(scripts) == 19 and len(packages) == 30 and not scripts.keys() & packages.keys(),
            'Disjoint code85 script and package sets')
    stage = scripts | packages
    combined = ''.join(f'{stage[name]}  {name}\n' for name in sorted(stage)).encode('ascii')
    require(binding['installedVersionCode'] == 85 and len(stage) == binding['exactManifestRows']
            and sha256(combined).hexdigest() == binding['stageManifestSha256'], 'Saved stage digest does not match APK')

    text = prepare.decode('utf-8')
    targets = dict(re.findall(r'^mount_payload "([a-z0-9]+)" "([a-z0-9.]+)"$', text, re.M))
    required_edges = ('for a in /apex/*; do', '*samsung*)', 'mount --bind "$a" "$ROOTFS/apex/$base"',
                      'mount_payload "sdkext" "com.android.sdkext"')
    require(all(edge in text for edge in required_edges) and 'clean_apex_info_list.xml' not in packages,
            'Expected mixed fallback source path')
    declared = {}
    for path, digest in packages.items():
        if not path.endswith('_payload.img'):
            continue
        target = targets[path.removesuffix('_payload.img')]
        matches = [name for name, row in factory['modules'].items() if row['payload']['sha256'] == digest]
        require(matches == [target] and target not in declared, 'Selected payload lacks exact matching factory origin')
        declared[target] = {'stageName': path, **factory['modules'][target]['payload']}
    require(len(declared) == 16 and 'com.android.tethering' not in declared, 'Expected declared direct payload set')

    replacements = {}
    for logical, stage_name in OVERRIDES.items():
        require(f'"$STAGE/{stage_name}" "$ROOTFS{logical}"' in text, f'JAR bind changed: {logical}')
        factory_jar = factory['jars'][logical]
        observed = binding['stagedJarHashes'].get(stage_name)
        digest = packages[stage_name]
        require(digest != factory_jar['sha256'] and (observed is None or observed['sha256'] == digest),
                'Unexpected staged JAR digest profile')
        replacements[logical] = {'stageName': stage_name, 'sha256': digest, 'factorySha256': factory_jar['sha256'],
                                 'savedStageHashObserved': observed is not None, 'origin': 'declared-stage-jar-bind'}
    return declared, replacements, file_row('guest_prepare.sh', prepare)


def host_members(index, paths, limit):
    wanted = set(paths)
    if not wanted:
        return
    first = TAR.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and first.st_size == 20434769920,
            'Saved Samsung archive extent or type changed')
    with TAR.open('rb') as file:
        opened = os.fstat(file.fileno())
        require(identity(opened) == identity(first), 'Samsung archive identity on open')
        with tarfile.open(fileobj=file, mode='r:') as archive:
            for item in archive:
                path = item.name.removeprefix('./')
                if path not in wanted:
                    continue
                row = index[path]
                require(item.isfile() and row['kind'] == 'file' and 0 < item.size == row['size'] <= limit,
                        'Indexed host member extent or type changed')
                stream = archive.extractfile(item)
                require(stream is not None, 'Missing held host member')
                with stream:
                    raw = stream.read(item.size + 1)
                require(len(raw) == item.size and sha256(raw).hexdigest() == row['sha256'], 'Indexed host member bytes changed')
                wanted.remove(path)
                yield path, raw
                if not wanted:
                    break
        finished = os.fstat(file.fileno())
        require(identity(finished) == identity(opened) and finished.st_ctime_ns == opened.st_ctime_ns,
                'Samsung archive changed during read')
    last = TAR.lstat()
    require(plain(last) and identity(last) == identity(first) and last.st_ctime_ns == first.st_ctime_ns,
            'Samsung archive name changed')
    require(not wanted, 'Missing indexed host members')


def host_fragments(index, aliases):
    wanted = {f'apex/{alias}/{relative}': keys for alias in aliases for relative, keys in FRAGMENTS.items()
              if f'apex/{alias}/{relative}' in index}
    output = []
    for path, raw in host_members(index, wanted, 8192):
        keys = wanted[path]
        groups = {key: [] for key in keys}
        for entry in fragment(raw):
            group = next((key for key in keys if ENUM[key] == entry['classpathRaw']), None)
            jar = entry['path']
            require(group is not None and JAR.fullmatch(jar) and not {'.', '..'}.intersection(jar.split('/')),
                    'Unsupported host classpath entry')
            groups[group].append(entry)
        output.append({**file_row('/' + path, raw), 'orderedGroups': groups, 'origin': 'captured-host-apex'})
    return output


def derive():
    raw = read_held(ROOT / FACTORY_PATH, 512 * 1024)
    require(sha256(raw).hexdigest() == FACTORY_SHA, 'Exact factory classpath receipt')
    factory = json.loads(raw)
    binding = json.loads(pinned(*BINDING))
    declared, replacements, prepare = read_selection(binding, factory)
    index = manifest()
    captured_aliases = {path.split('/')[1] for path, row in index.items() if path.startswith('apex/')
                        and path.count('/') == 1 and row['kind'] == 'directory' and '@' not in path}
    skipped = {name for name in captured_aliases if 'samsung' in name}
    host_aliases = captured_aliases - skipped - declared.keys()
    fragments = [row for row in factory['fragments'] if row['path'].startswith('/system/')
                 or row['path'].split('/')[2] in declared]
    fragments.extend(host_fragments(index, host_aliases))

    jars, host_jar_paths = {}, set()
    for row in fragments:
        for group in row['orderedGroups'].values():
            for entry in group:
                jar = entry['path']
                if jar in jars or jar[1:] in host_jar_paths:
                    continue
                if jar in replacements:
                    jars[jar] = replacements[jar]
                else:
                    if jar.startswith('/apex/'):
                        name = jar.split('/')[2]
                        if name in host_aliases:
                            host_jar_paths.add(jar[1:])
                            continue
                        require(name in declared, 'JAR belongs to an unselected APEX')
                    jars[jar] = {**factory['jars'][jar], 'origin': 'factory-donor'}
    for path, _ in host_members(index, host_jar_paths, 64 * 1024 * 1024):
        info = index[path]
        jars['/' + path] = {'origin': 'captured-host-apex', 'bytes': info['size'], 'sha256': info['sha256']}

    sdk = 37
    result = scenarios(fragments, jars, sdk)
    return {'status': 'CODE85_CONDITIONAL_MIXED_CLASSPATH_SCENARIO_ONLY', 'apk': {'path': APK[0], 'sha256': APK[2]},
            'bindingSha256': BINDING[2], 'factoryReceiptSha256': FACTORY_SHA, 'hostIndexSha256': MANIFEST_SHA,
            'prepare': prepare, 'stageManifestSha256': binding['stageManifestSha256'], 'declaredApexPayloads': declared,
            'capturedFallbackAliases': sorted(host_aliases), 'scriptExcludedHostAliases': sorted(skipped),
            'unstagedFactoryModules': sorted(factory['modules'].keys() - declared.keys()), 'classpathJarBinds': replacements,
            'fragments': fragments, 'jars': jars, 'releaseScenario': result,
            'exportFixture': file_row('modeled-code85-sdk37', expected_exports(result)),
            'selectedMountsObserved': False, 'runtimeAdmitted': False, 'deviceAction': False}


if __name__ == '__main__':
    print(json.dumps(derive(), indent=2))
