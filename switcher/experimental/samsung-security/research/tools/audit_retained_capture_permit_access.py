"""Verify saved permit source and root-acquired metadata, without a device read.

This is not a compiled SELinux policy reader or an access-check implementation.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OBS = 'out/retained-capture-permit-preflight/20261106T040831455570Z-ecc1ece9e4954c8390ed44eb0abe4cbc/observation.json'
OBS_SHA = 'ba8a463e484ec7528391387f06c4b4af407bbfae2dc8a442d553bf6616a88e1f'
SOURCE = 'probe/retained-capture/src/com/appleexploit/oneos/security/probe/retained/PermitFile.java'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    check('literal readonly metadata pin', sha(ROOT / OBS) == OBS_SHA)
    obs = json.loads((ROOT / OBS).read_text())
    check('root report no phone modification, permit creation or restart',
          not obs['phoneModified'] and not obs['permitCreated'] and not obs['restartAttempted'])
    results = obs['results']
    for key in ['systemServerDomain', 'systemServerIds', 'existingPermitParents', 'dedicatedPermitAbsence', 'existingContextNoSecret']:
        check('read metadata ' + key, results[key]['status'] == 'READ')
    check('observed global Enforcing', results['existingContextNoSecret']['text'].strip() == 'Enforcing')
    check('observed original system_server domain', results['systemServerDomain']['text'].rstrip('\0') == 'u:r:system_server:s0')
    ids = results['systemServerIds']['text'].splitlines()
    check('observed real/effective/saved/filesystem UID1000', ids[0].split() == ['Uid:', '1000', '1000', '1000', '1000'])
    check('observed real/effective/saved/filesystem GID1000', ids[1].split() == ['Gid:', '1000', '1000', '1000', '1000'])
    parents = results['existingPermitParents']['text'].splitlines()
    check('observed tmp parent shell_data_file', any('u:object_r:shell_data_file:s0' in x and x.endswith('/data/local/tmp') for x in parents))
    check('observed system parent system_data_file', any('u:object_r:system_data_file:s0' in x and x.endswith('/data/system') for x in parents))
    absent = results['dedicatedPermitAbsence']['text'].splitlines()
    check('both dedicated objects absent', absent == ['ABSENT:/data/local/tmp/oneos-samsung-security-capture', 'ABSENT:/data/local/tmp/oneos-samsung-security-capture/request-v1'])
    source = (ROOT / SOURCE).read_text().splitlines()
    for line, text in [(12, '"/data/local/tmp/oneos-samsung-security-capture"'),
                       (25, 'Os.open(DIRECTORY, OsConstants.O_RDONLY'),
                       (30, 'Os.open(REQUEST, OsConstants.O_RDONLY'),
                       (38, 'Os.read(request'), (50, 'Os.lstat(REQUEST)'),
                       (58, 'catch (Throwable ignored) { valid = false; }'),
                       (67, '!= 0750'), (68, 'stat.st_uid != 0 || stat.st_gid != 1000'),
                       (72, '!= 0440'), (73, 'stat.st_nlink != 1')]:
        check('fixed permit source line' + str(line), text in source[line - 1])
    result = {
        'schema': 'retained-capture-permit-access/v1', 'status': 'DAC_COMPATIBLE_SELINUX_READ_ACCESS_UNKNOWN_TARGET_ABSENT',
        'inputs': {OBS: OBS_SHA, SOURCE: sha(ROOT / SOURCE)},
        'checkCount': len(checks), 'checks': checks,
        'observed': {'pid': obs['systemServerPid'], 'domain': 'u:r:system_server:s0', 'fsuid': 1000, 'fsgid': 1000,
                     'globalSelinux': 'Enforcing', 'tmpParentType': 'shell_data_file', 'systemParentType': 'system_data_file',
                     'dedicatedDirectoryExists': False, 'requestExists': False},
        'sourceAccessSet': {'parentDirectories': ['search', 'getattr as needed'],
                            'dedicatedDirectory': ['getattr', 'open', 'read for O_RDONLY directory'],
                            'requestFile': ['getattr', 'open', 'read'],
                            'limits': 'Required access categories, not a decoded complete kernel permission/check trace.'},
        'dacAssessment': 'Given reported fsuid/fsgid1000, proposed root:1000 dir0750 and file0440 permit group traversal/read; observed parent modes permit traversal. No existing target inode/ACL is admitted.',
        'selinuxAssessment': 'UNKNOWN: no actual target labels or access attempt, and no applicable unpacked Samsung policy/file_contexts or named compiled policy reader located in bounded existing-file searches.',
        'searchedScopes': ['../firmware/samsung and nested firmware filenames via rg --files; compressed mounted-OS archive was not extracted',
                           'tools, ../tools and ../out/toolchain filenames for sesearch/seinfo/checkpolicy/secilc/sepolicy-analyze/libsepol; selected authored sources for policydb/avtab reader references'],
        'excludedEvidence': 'ColorOS donor plat_file_contexts/plat_sepolicy.cil are a different OS; their labels/rules cannot establish Samsung effective policy.',
        'alternative': {'path': '/data/system/oneos-samsung-security-capture',
                        'status': 'CONDITIONAL_ONLY_NO_CHANGE_APPROVED',
                        'basis': 'Observed parent system_data_file and UID/GID1000; more aligned with system service state than shell_data_file.',
                        'missing': 'Applicable Samsung file_contexts/type-transition/effective allow evidence and actual future object labels; changing parent does not auto-attest access.',
                        'sourceChangeRequired': True},
        'minimalRemainingEvidence': ['Applicable effective Samsung system_server→actual directory/file type allow/constraints evidence (including parent search and directory O_RDONLY open/read).',
                                     'If an independently approved permit is later created, readonly exact object labels/modes/owner/inode metadata; current absence is not denial.',
                                     'Only if an already-authorized attempt occurred, bounded matching AVC evidence can establish that particular denial; absence of AVC does not prove access.'],
        'policyChanged': False, 'pathChanged': False, 'phoneActions': [], 'oemExecuted': False,
        'readProbeExecuted': False, 'toolSha256': sha(Path(__file__))}
    out = ROOT / 'inventory/retained-capture-permit-access.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'inventory': str(out.relative_to(ROOT)), 'checks': len(checks), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true', required=True)
    parser.parse_args()
    audit()
