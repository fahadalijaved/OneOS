"""Static route-B data-view plan over frozen installed scripts/native evidence.

Never executes a shell script, ELF, OEM class, mount or device command.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/guest-installd-data-view'
RAW = ROOT / 'firmware/guest-installd-data-view'
ASSETS = ROOT / 'firmware/installed-oneos-code-profile/static/assets'
STAGE = '/data/local/tmp/oneos'
PINS = {
    'inventory/retained-installd-routing.json': 'effb6cef11e13ee4c42f626f110e746ecbdace812f52f3af9eaaf00deeb0f62a',
    'inventory/retained-guest-user-lifecycle.json': '731ac8031bf051c283d1cbb7ec23425d69d90c7a12b1895a547e9a64a5421040',
    'inventory/retained-installd-native-owner.json': '14d15d212d09deffd0decd0a2c0657af79e15dedadaa7251322bfaa0da2f9f47',
    'firmware/retained-installd-native-owner/static/selected-native.json': '073ce4abb6ed496693e57a529b7a6e7c9d24d8785df7f20135db5ea79a02f776',
    'out/installed-oneos-code-profile/static/appdata-bridge-source.json': '07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
    'inventory/installed-oneos-code-profile.json': 'e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a',
}
SCRIPT_PINS = {
    'bridges.sh': 'afe5e27673b8bf0b259de5c8ded4cd4960f57a2ee0e7ca01a45dc4696c415a1b',
    'guest_prepare.sh': '000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70',
    'guest_start.sh': '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446',
    'oneos_switch.sh': 'e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150',
    'return_to_oneui.sh': '04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    checks, selected_lines = [], []
    def check(label, condition):
        assert condition, label
        checks.append(label)
    for path, pin in PINS.items():
        check('frozen input ' + path, sha(ROOT / path) == pin)
    scripts = {}
    for name, pin in SCRIPT_PINS.items():
        check('installed asset ' + name, sha(ASSETS / name) == pin)
        scripts[name] = (ASSETS / name).read_text().splitlines()
    def line(name, number, text, label):
        actual = scripts[name][number - 1]
        check(label, text in actual)
        selected_lines.append({'asset': name, 'line': number, 'text': actual})
    specs = [
        ('oneos_switch.sh', 79, 'nsenter -t 1 -m', 'switch reenters init mount namespace'),
        ('oneos_switch.sh', 1087, 'guest_prepare.sh', 'prepare precedes guest namespace launch'),
        ('oneos_switch.sh', 1418, 'unshare -m', 'guest mount namespace fork is after prepare'),
        ('guest_prepare.sh', 7, '/proc/1/ns/mnt', 'unchanged prepare requires init mount namespace'),
        ('guest_prepare.sh', 9, 'exit 4', 'non-init namespace explicitly refused'),
        ('guest_prepare.sh', 21, 'p="$STAGE/data"', 'existing mounts under staged data refused'),
        ('guest_prepare.sh', 24, 'exit 4', 'staged mount conflict terminates'),
        ('guest_prepare.sh', 58, '[ -L "$STAGE/data" ]', 'staged root symlink refused'),
        ('guest_prepare.sh', 63, '[ -L "$_p" ]', 'each selected staged component symlink checked'),
        ('guest_prepare.sh', 71, 'no_symlink', 'all14 bridge destinations checked'),
        ('guest_prepare.sh', 276, 'losetup -r', 'image attaches read-only'),
        ('guest_prepare.sh', 305, '--make-rslave "$ROOTFS/sys"', 'sys inherited slave view'),
        ('guest_prepare.sh', 316, '--rbind /dev', 'guest rootfs receives device tree'),
        ('guest_prepare.sh', 317, '--make-rprivate', 'guest dev made recursively private'),
        ('guest_prepare.sh', 1209, '--rbind /mnt', 'guest initially receives entire host mnt tree'),
        ('guest_prepare.sh', 1213, '--make-rslave', 'inherited mnt initially slave; errors ignored'),
        ('guest_prepare.sh', 2068, 'dalvik-cache/arm64', 'staged cache prepared'),
        ('guest_prepare.sh', 2475, 'misc/user/0', 'staged misc/user0 prepared'),
        ('guest_prepare.sh', 2485, 'media/0', 'staged media source prepared'),
        ('guest_prepare.sh', 2500, 'user_de/0/$pkg', 'guest package DE scaffolding writer'),
        ('guest_prepare.sh', 2503, 'user/0/$pkg', 'guest package CE scaffolding writer'),
        ('guest_prepare.sh', 2508, 'resource-cache', 'staged resource cache prepared'),
        ('guest_prepare.sh', 2548, 'rm -rf', 'profile cleanup is an actual extra writer'),
        ('guest_prepare.sh', 2914, 'misc/profiles/cur/0', 'staged current/reference profiles prepared'),
        ('guest_prepare.sh', 3244, 'mount --bind "$STAGE/data/$s" "/data/$h"', 'actual14 global host overbind producer'),
        ('guest_prepare.sh', 3252, 'stat -c %d:%i', 'current global bridge identity check'),
        ('guest_prepare.sh', 3256, 'exit 3', 'unbridged existing path refuses guest launch'),
        ('guest_prepare.sh', 3260, 'mount --bind "$STAGE/data" "$ROOTFS/data"', 'whole staged data also supplied to guest root'),
        ('guest_prepare.sh', 3266, '--make-private', 'data mount privacy precedes child mounts'),
        ('guest_prepare.sh', 3267, 'mount --bind /data/adb', 'host adb tree is an explicit distinct child source'),
        ('guest_prepare.sh', 3268, 'mount --bind /data/apex', 'host apex data is an explicit distinct child source'),
        ('guest_prepare.sh', 3451, '/data/user/0/$pkg', 'guest fix helper uses actual user data paths'),
        ('guest_prepare.sh', 3459, '/data/misc/profiles/cur/0/$pkg', 'guest fix helper writes profile trees'),
        ('guest_prepare.sh', 3571, '/data/user_de/0/$pkg', 'periodic guest helper writes CE and DE data'),
        ('guest_prepare.sh', 3591, '/data/media/0/Android', 'periodic guest helper writes media'),
        ('guest_prepare.sh', 3604, '/data/system/packages.list', 'helper consumes guest package metadata'),
        ('guest_prepare.sh', 3700, 'ensure_app_storage.sh', 'periodic writer remains live beyond startup'),
        ('guest_prepare.sh', 4305, '--make-rprivate "$ROOTFS"', 'final root privacy command ignores failure'),
        ('guest_start.sh', 12, 'cd /data/local/tmp/oneos/rootfs', 'pivot resolves stage path before root replacement'),
        ('guest_start.sh', 13, '--make-rprivate /', 'guest root privacy is attempted before pivot'),
        ('guest_start.sh', 14, 'pivot_root . postinstall', 'root changes by original pivot producer'),
        ('guest_start.sh', 44, 'umount -l /postinstall', 'old host-root detach attempted'),
        ('guest_start.sh', 47, 'exit 1', 'remaining postinstall mounts refuse launch'),
        ('guest_start.sh', 57, 'pass_through|installer|androidwritable|runtime|user', 'storage cleanup has a finite subtree selector'),
        ('guest_start.sh', 63, 'exit 1', 'remaining selected host storage mounts refuse launch'),
        ('guest_start.sh', 71, '--make-shared /mnt', 'guest storage creates new mnt peer group after private root'),
        ('guest_start.sh', 77, '/data/user/0 /data/data', 'user0 legacy alias receiver'),
        ('guest_start.sh', 78, 'tmpfs /data_mirror', 'guest mirror root is new tmpfs attempt'),
        ('guest_start.sh', 81, '/data/user_de/0 /data_mirror/data_de/null/0', 'DE mirror receives staged user0'),
        ('guest_start.sh', 82, '/data/user/0 /data_mirror/data_ce/null/0', 'CE mirror receives staged user0'),
        ('guest_start.sh', 84, '/data/misc/profiles/cur', 'current profile mirror receiver'),
        ('guest_start.sh', 85, '/data/misc/profiles/ref', 'reference profile mirror receiver'),
        ('guest_start.sh', 93, '/data/media/0 /storage/emulated/0', 'guest shared-storage receiver'),
        ('guest_start.sh', 97, '/data/media/0 /mnt/user/0/emulated', 'guest mnt user media receiver'),
        ('guest_start.sh', 1129, '/data/resource-cache/', 'guest native idmap output path selected'),
        ('guest_start.sh', 1134, '/system/bin/idmap2 create', 'actual noninstalld native command consumes resource output path'),
        ('guest_start.sh', 1147, 'app_storage_loop.sh', 'extra guest data writer spawned asynchronously'),
        ('guest_start.sh', 1197, '/system/bin/idmap2d', 'actual guest idmap daemon is launched'),
    ]
    for spec in specs:
        line(*spec)
    bridge = json.loads((ROOT / 'out/installed-oneos-code-profile/static/appdata-bridge-source.json').read_text())
    pairs = re.search(r'^BRIDGES="([^"]+)"$', '\n'.join(scripts['bridges.sh']), re.M).group(1).split()
    check('exact14 bridge pairs equal frozen producer ledger', len(pairs) == 14 and
          [{'host': '/data/' + p.split(':')[0], 'staged': STAGE + '/data/' + p.split(':')[1]} for p in pairs] == bridge['bridgePairs'])
    check('layout state is outside all14 redirect roots', not any(p.split(':')[0] == 'misc/installd' for p in pairs))
    check('mnt expand absent from finite host-storage cleanup selector', 'expand' not in scripts['guest_start.sh'][56])
    native = json.loads((ROOT / 'firmware/retained-installd-native-owner/static/selected-native.json').read_text())
    instructions = {x['pc']: x for f in native['functions'] for x in f['instructions']}
    for pc, literal in [(0x743c0, 'ANDROID_DATA'), (0x743d4, 'ANDROID_ROOT'),
                        (0x8ac84, '%smisc/installd/layout_version'), (0x8ad84, '%s/keychain/cacerts-added'),
                        (0x8adb4, '%s/keychain/cacerts-removed'), (0x8adc8, '/data/user')]:
        check('reused native exact literal@' + hex(pc), instructions[pc]['literal'] == literal)
    consumers = {
        'app': ['prepare2910-2912 direct mkdir/owner/mode writer; all guest processes receive rootfs/data3260'],
        'app-staging': ['prepare2910-2912 direct mkdir/owner/mode writer; whole guest data view3260'],
        'user': ['prepare2503-2505 package scaffolding; helpers3451/3571; guest CE mirror start82'],
        'user_de': ['prepare2500-2502 package scaffolding; helpers3451/3571; guest DE mirror start81'],
        'dalvik-cache': ['prepare2068/2910 direct directory writer; guest whole-data receiver3260; artd role only source-comment evidence here'],
        'misc/profiles': ['prepare2548 deletes profiles; helper3459-3464 creates profiles; guest mirror start84-85'],
        'data': ['guest bind start77 aliases staged user0; native legacy CE path is separate selected native evidence'],
        'media': ['prepare2485; helper3591/3612 writes media; start88-97 writes and supplies guest storage views'],
        'misc/user': ['prepare2475 creates user0; native ensure_config_user_dirs reaches real fs_prepare_dir'],
        'misc_ce/0/sdksandbox': ['generic bridge mkdir3242; whole guest data receiver3260; no separate concrete reader pinned here'],
        'misc_de/0/sdksandbox': ['generic bridge mkdir3242; whole guest data receiver3260; no separate concrete reader pinned here'],
        'misc_ce/0/rollback': ['generic bridge mkdir3242; whole guest data receiver3260; no separate concrete reader pinned here'],
        'misc_de/0/rollback': ['generic bridge mkdir3242; whole guest data receiver3260; no separate concrete reader pinned here'],
        'resource-cache': ['prepare2508-2510 direct writer; actual guest idmap2 invocation start1129-1137; guest idmap2d launch1197'],
    }
    matrix = [{**p, 'futureGuestInstalldPath': p['host'], 'futureObject': p['staged'],
               'sourceConsumers': consumers[p['host'][6:]], 'provenInstalldExclusive': False,
               'physicalObjectAdmission': 'UNOBSERVED; source path only'} for p in bridge['bridgePairs']]
    root_map = [
        {'path': '/data', 'candidateObject': STAGE + '/data', 'owner': 'existing staged guest root; frozen package/code profile is not directory identity', 'status': 'SOURCE_PATH_KNOWN_ACTUAL_ADMISSION_OPEN'},
        {'path': '/data/data', 'candidateObject': STAGE + '/data/user/0', 'owner': 'guest legacy user0 alias; require actual same subject/serial', 'status': 'USER0_SOURCE_ONLY'},
        {'path': '/data/user and /data/user_de', 'candidateObject': STAGE + '/data/user and user_de', 'owner': 'guest app data; original Samsung registry/physical CE authority remains separate', 'status': 'USER0_SCAFFOLD_ONLY_OTHER_USERS_OPEN'},
        {'path': '/data/misc/installd/layout_version', 'candidateObject': STAGE + '/data/misc/installd/layout_version', 'owner': 'new guest daemon layout/migration writer before publication', 'status': 'NO_PACKAGED_SPECIFIC_PREPARATION_OR_VALIDATED_STATE'},
        {'path': '/data/misc/user/<user>', 'candidateObject': STAGE + '/data/misc/user/<user>', 'owner': 'new guest daemon native ensure_config_user_dirs; only user0 script scaffold', 'status': 'NATIVE_FIRST_EFFECT_REQUIRES_ADMISSION'},
        {'path': '/data/misc/keychain/cacerts-* and migration destinations under misc/user', 'candidateObject': STAGE + '/data/misc/<same-relative-native-path>', 'owner': 'native conditional legacy migration; no host CA tree import/read proposed', 'status': 'FORMAT_AND_BASE_MUST_RESOLVE_PRIVATE_DATA_BEFORE_MAIN'},
        {'path': '/mnt/expand/<uuid>', 'candidateObject': None, 'owner': 'actual adopted-volume/UUID/mount/FBE owner not supplied by staged path list', 'status': 'UNBOUND_HOST_MNT_INHERITANCE_NOT_PRIVATE_GUEST_MAPPING'},
        {'path': '/data_mirror/data_ce/null/0 and data_de/null/0', 'candidateObject': STAGE + '/data/user/0 and user_de/0 through private mirror mounts', 'owner': 'guest app/zygote isolation receivers; original script ignores mount errors', 'status': 'USER0_ATTEMPT_ONLY_NOT_NATIVE_TRYMOUNT_ACK'},
        {'path': '/data_mirror/misc_ce and misc_de', 'candidateObject': STAGE + '/data/misc_ce and misc_de through new native mirror setup', 'owner': 'new guest daemon tryMountDataMirror and actual user/volume subject', 'status': 'NOT_PREPARED_BY_ORIGINAL_START_MIRROR_BLOCK'},
        {'path': '/data_mirror/cur_profiles and ref_profiles', 'candidateObject': STAGE + '/data/misc/profiles/cur and ref', 'owner': 'guest mirror receiver; other native profile owner unclosed', 'status': 'SOURCE_MOUNT_ATTEMPT_NO_DRAIN_OR_EXCLUSIVITY'},
        {'path': '/data/adb and /data/apex', 'candidateObject': 'host child sources via prepare3267-3288, intended read-only; not new guest-owned metadata', 'owner': 'original host root-manager/APEX owners; native clone original runtime binding must be selected separately', 'status': 'EXPLICIT_SHARED_CHILDREN_NOT_BLANKET_DATA_ISOLATION'},
        {'path': 'caller-selected absolute paths, including SDP database paths', 'candidateObject': None, 'owner': 'genuine caller/subject/routing; aliases do not rewrite caller strings', 'status': 'UNBOUND_OUTSIDE_FIXED_ROOT_SET'},
    ]
    RAW.mkdir(parents=True, exist_ok=True)
    selected = RAW / 'selected-script-lines.json'
    selected.write_text(json.dumps({'schema': 'guest-installd-data-view-script-slice/v1', 'assets': SCRIPT_PINS, 'lines': selected_lines}, indent=2) + '\n')
    result = {'schema': 'guest-installd-data-view/v1', 'status': 'NO_CLOSED_PRIVATE_VIEW_LAUNCH_PREFIX',
              'selected': False, 'scriptsExecuted': False, 'nativeExecuted': False, 'oemExecuted': False, 'phoneActions': [],
              'inputs': PINS, 'assetPins': SCRIPT_PINS, 'selectedRaw': {'path': str(selected.relative_to(ROOT)), 'sha256': sha(selected)},
              'checkCount': len(checks), 'checks': checks, 'bridgeMatrix': matrix, 'nativeRootMap': root_map,
              'provenInstalldExclusiveTreeCount': 0,
              'firstUnboundOwner': 'Source-owned private-view preparation/control before the unchanged prepare global-bind region: no admitted namespace/held-stage-object/source-composition producer exists, and unchanged prepare explicitly refuses non-init execution.',
              'decisiveLaterGap': 'Non-null UUID native paths select /mnt/expand, inherited from host mnt and not removed by the guest selector; no actual guest volume object/owner is supplied.',
              'launcherEmissionAuthorized': False, 'runtimeReady': False,
              'limits': ['Static source plan; no stage app data, keys, CA files or credential state opened.',
                         'No kernel/API/native implementation executed or independent native decoding repeated.',
                         'No exclusive installd-only consumer inferred from bridge names or comments.',
                         'Directory FDs would retain an object, not snapshot its mutable contents/labels or establish policy/physical freshness.',
                         'Mount namespace isolation does not establish independent kernel quota/backing metadata/UID or CE/key authority.'],
              'toolSha256': sha(Path(__file__))}
    WORK.mkdir(parents=True, exist_ok=True)
    (ROOT / 'inventory/guest-installd-data-view.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'bridgePairs': len(matrix), 'nativeRootEntries': len(root_map), 'scriptLines': len(selected_lines)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true', required=True)
    parser.parse_args()
    audit()
