"""Read bounded nonsecret profile facts through an EXISTING local ADB server.

Default: list transports only. --collect is a separately coordinated read.
Uses pinned adb on port5038 after an existing-server precheck; never explicitly
starts/resets a server. The precheck is not an atomic no-autostart guarantee.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import threading
import uuid

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
ADB = PARENT/'out/toolchain/android-sdk/platform-tools/adb.exe'
PORT = 5038
STAGE = '/data/local/tmp/oneos/rootfs'
PROPS = ('ro.product.model', 'ro.product.device', 'ro.product.manufacturer',
         'ro.build.version.sdk', 'ro.build.version.release', 'ro.build.version.security_patch',
         'ro.build.id', 'ro.build.display.id', 'ro.build.version.incremental', 'ro.build.fingerprint')
FILES = ('/system/framework/services.jar', '/system/framework/framework.jar',
         '/system/framework/oplus-services.jar', '/system/bin/vold', '/system/build.prop')
RUNTIME_FILES = FILES[:-1]
HASH_PATHS = FILES + tuple(STAGE+p for p in FILES)
SOURCE = 'firmware/reference/OneOS/2a5f41043b4a69399cae058bad213cdef7408e88/switcher/assets/'
SOURCE_PINS = {'guest_start.sh': '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446',
               'guest_prepare.sh': 'dee533911fd2c5bcf5e15696210c48413893983bdf8362d8626eb94562879936',
               'oneos_switch.sh': 'c2a8604667aeefd1721623bffab571955a755009cb490d0c4dfb36caf38dfece'}
PROPERTY_SOURCE = 'firmware/security-profile/guest_props-2a5f41043b4a69399cae058bad213cdef7408e88.sh'
PROPERTY_SHA = 'f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a'


class ProfileError(ValueError):
    pass


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def bounded_command(command, limit, timeout=20):
    """Bound actual child output while running, including simultaneous stderr."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    chunks = [bytearray(), bytearray()]
    lock = threading.Lock()
    oversized = threading.Event()
    def drain(pipe, index):
        while True:
            block = pipe.read(4096)
            if not block:
                break
            with lock:
                if len(chunks[0])+len(chunks[1])+len(block) > limit:
                    oversized.set()
                    process.kill()
                    break
                chunks[index].extend(block)
        pipe.close()
    workers = [threading.Thread(target=drain, args=(pipe, i), daemon=True)
               for i, pipe in enumerate((process.stdout, process.stderr))]
    for worker in workers:
        worker.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise ProfileError('ADB command timed out')
    finally:
        for worker in workers:
            worker.join(timeout=2)
    if any(worker.is_alive() for worker in workers):
        raise ProfileError('Output readers failed to finish')
    if oversized.is_set():
        raise ProfileError('ADB output exceeds bound')
    if process.returncode != 0:
        raise ProfileError('ADB/remote command failed, exit '+str(process.returncode))
    if chunks[1]:
        raise ProfileError('ADB/remote stderr present; result unresolved')
    return bytes(chunks[0])


def adb(arguments, limit):
    # Refuse a missing existing server. A race can still permit the adb client
    # to perform its normal startup if that server exits after this check.
    with socket.create_connection(('127.0.0.1', PORT), timeout=2):
        pass
    return bounded_command([str(ADB), '-P', str(PORT), *arguments], limit)


def parse_devices(data):
    if len(data) > 65535:
        raise ProfileError('Device list exceeds bound')
    text = data.decode('utf-8', 'strict')
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2 or not re.fullmatch(r'[A-Za-z0-9_.:\[\]-]{1,160}', parts[0]):
            raise ProfileError('Malformed transport row')
        if any(r['serial'] == parts[0] for r in rows):
            raise ProfileError('Duplicate transport serial')
        rows.append({'serial': parts[0], 'state': parts[1], 'details': parts[2:]})
        if len(rows) > 64:
            raise ProfileError('Too many transports')
    return rows


def devices():
    data = adb(['devices', '-l'], 65535)
    lines = data.decode('utf-8', 'strict').splitlines()
    if not lines or lines[0] != 'List of devices attached':
        raise ProfileError('Missing adb device-list header')
    return parse_devices('\n'.join(lines[1:]).encode())


def select_device(rows, serial=None):
    selected = [r for r in rows if r['serial'] == serial] if serial else rows
    if len(selected) != 1 or selected[0]['state'] != 'device':
        raise ProfileError('Require exactly one already trusted transport, or one explicit connected serial; offline/unauthorized/ambiguous rejected')
    return selected[0]['serial']


def parse_pids(text):
    parts = text.strip().split()
    if not 1 <= len(parts) <= 2 or len(set(parts)) != len(parts) or any(not re.fullmatch(r'[1-9][0-9]{0,6}', p) for p in parts):
        raise ProfileError('Require one or two distinct numeric system_server PIDs')
    return sorted(parts, key=int)


def parse_pid_stat(text, pid):
    prefix = pid+' (system_server) '
    if not text.startswith(prefix):
        raise ProfileError('PID process identity differs')
    fields = text[len(prefix):].split()
    if len(fields) < 20 or not fields[19].isdigit():
        raise ProfileError('Invalid process starttime')
    return {'pid': pid, 'starttimeTicks': fields[19]}


def hash_command(path):
    proc = re.fullmatch(r'/proc/([1-9][0-9]{0,6})/root(/system/(?:framework/(?:services|framework|oplus-services)\.jar|bin/vold))', path)
    if path not in HASH_PATHS and not proc:
        raise ProfileError('Path outside source-verified hash allowlist')
    # Refuse aliases to unreviewed/private paths. Only bounded regular bytes;
    # no raw file contents leave the phone. No shell input derives from serial.
    accepted = HASH_PATHS if proc else (path,)
    pattern = '|'.join("'"+p+"'" for p in accepted)
    return (f"p='{path}'; r=$(readlink -f \"$p\") || exit 21; "
            f'case "$r" in {pattern}) ;; *) exit 22;; esac; '
            '[ -f "$p" ] && [ ! -L "$p" ] || exit 22; '
            'n=$(stat -c %s "$p") || exit 23; '
            'case "$n" in ""|*[!0-9]*) exit 24;; esac; '
            '[ "$n" -gt 0 ] && [ "$n" -le 134217728 ] || exit 25; '
            'sha256sum "$p"')


def queries():
    q = {key: ('getprop '+key, 1024, 'property') for key in PROPS}
    q.update({path: (hash_command(path), 1024, 'file-hash') for path in HASH_PATHS})
    q['shell-mount-namespace'] = ('readlink /proc/self/ns/mnt', 128, 'namespace')
    q['init-mount-namespace'] = ('readlink /proc/1/ns/mnt', 128, 'namespace')
    q['shell-mountinfo'] = ('cat /proc/self/mountinfo', 512*1024, 'mountinfo')
    q['system-server-pids'] = ('pidof system_server', 64, 'pids')
    return q


def remote(serial, key, pid=None):
    q = queries()
    if pid is not None:
        if parse_pids(pid) != [pid]:
            raise ProfileError('One exact numeric PID required')
        q['pid-namespace'] = (f'readlink /proc/{pid}/ns/mnt', 128, 'namespace')
        q['pid-identity'] = (f'cat /proc/{pid}/stat', 4096, 'pid-stat')
        for path in RUNTIME_FILES:
            full = f'/proc/{pid}/root'+path
            q[full] = (hash_command(full), 1024, 'file-hash')
    if key not in q:
        raise ProfileError('Unknown query')
    command, bound, kind = q[key]
    text = adb(['-s', serial, 'shell', '-T', command], bound).decode('utf-8', 'strict')
    value = text.strip()
    if kind == 'property':
        if not value or len(value) > 512 or any(ord(c) < 32 or ord(c) > 126 for c in value):
            raise ProfileError('Missing/invalid property')
    elif kind == 'file-hash':
        match = re.fullmatch(r'([0-9a-f]{64})  '+re.escape(key), value)
        if not match:
            raise ProfileError('Invalid exact-path hash result')
        value = match[1]
    elif kind == 'namespace':
        if not re.fullmatch(r'mnt:\[[0-9]+\]', value):
            raise ProfileError('Invalid namespace identity')
    elif kind == 'pids':
        value = parse_pids(value)
    elif kind == 'pid-stat':
        value = parse_pid_stat(value, pid)
    elif kind == 'mountinfo':
        rows = []
        for line in text.splitlines():
            before, sep, after = line.partition(' - ')
            left, right = before.split(), after.split()
            if not sep or len(left) < 6 or len(right) < 3 or not re.fullmatch(r'[0-9]+:[0-9]+', left[2]):
                raise ProfileError('Invalid mountinfo record')
            # Return only OS-role mount facts, never unrelated path names/options.
            if left[4] in ('/', '/system', '/system_ext', '/product', '/vendor', '/data', '/metadata', STAGE):
                rows.append({'device': left[2], 'root': left[3], 'mountpoint': left[4], 'filesystem': right[0], 'source': right[1]})
        if not rows:
            raise ProfileError('No selected mount facts')
        value = rows
    return value


def validate_profile(properties):
    if properties.get('ro.product.model') != 'SM-S948U1' or properties.get('ro.build.version.sdk') != '37':
        raise ProfileError('Active property view does not match the scoped S26/API37 profile')
    expected = 'CP2A.260605.016.S948U1UES4BZIG'
    if properties.get('ro.build.display.id') != expected:
        raise ProfileError('Active build display ID does not match GOAL baseline; no identity inferred')
    if not properties.get('ro.build.fingerprint') or '/' not in properties['ro.build.fingerprint']:
        raise ProfileError('Missing/invalid fingerprint')


def assess_profile(properties, inspection=False):
    """Inspection records the same strict decision; it never turns it into admission."""
    try:
        validate_profile(properties)
    except ProfileError as error:
        if not inspection:
            raise
        return {'recordedPropertySubsetMatches': False, 'profileAdmitted': False,
                'classification': 'inspection-only mismatch or unresolved; not supported-profile evidence',
                'reason': str(error)}
    return {'recordedPropertySubsetMatches': True, 'profileAdmitted': False,
            'classification': 'matching property subset only; complete profile and authority admission unresolved'}


def request_mode(collect=False, serial=None, inspection_serial=None):
    if inspection_serial is not None:
        if collect or serial is not None or not re.fullmatch(r'[A-Za-z0-9_.:\[\]-]{1,160}', inspection_serial):
            raise ProfileError('Inspection requires its own one explicit already-connected serial')
        return 'inspection-only', inspection_serial
    if serial is not None and not collect:
        raise ProfileError('--serial requires --collect; inspection uses --inspect-serial')
    return ('collect' if collect else 'list-only'), serial


def source_pins():
    pins = {}
    for name, expected in SOURCE_PINS.items():
        path = PARENT/(SOURCE+name)
        if digest(path) != expected:
            raise ProfileError('Pinned source changed: '+name)
        pins['../'+SOURCE+name] = expected
    pins['../out/toolchain/android-sdk/platform-tools/adb.exe'] = digest(ADB)
    if digest(ROOT/PROPERTY_SOURCE) != PROPERTY_SHA:
        raise ProfileError('Exact2a property-policy source moved')
    pins[PROPERTY_SOURCE] = PROPERTY_SHA
    return pins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--collect', action='store_true', help='Root-coordinated read requiring recorded property subset; default lists only')
    mode_group.add_argument('--inspect-serial', help='Root-coordinated observation only for this explicit trusted serial; mismatches never admitted')
    parser.add_argument('--serial', help='An already connected trusted transport; never connects/pairs it')
    args = parser.parse_args()
    mode, requested_serial = request_mode(args.collect, args.serial, args.inspect_serial)
    pins = source_pins()
    report = {'schema': 'security-profile-observation/v1', 'port': PORT, 'mode': mode,
              'sourcePins': pins, 'toolSha256': digest(Path(__file__)), 'facts': {}, 'unresolved': {},
              'runtimeSecurityAcceptance': False, 'deviceMutation': False, 'explicitServerStartOrReset': False,
              'serverPrecheckLimit': 'Not atomic: normal adb startup can occur if existing server exits after precheck',
              'stagePathsClassification': 'source defaults; not proof of a live guest or actual loaded bytes',
              'propertyPolicyEvidence': 'Exact2a switch1138 invokes guest-property import. Exact2a helper101-109 records nonempty host keys;147 skips them during generic import. No explicit model/API/display-ID override found in this helper. Missing/empty host keys can be imported; source is not installed/live-state evidence.'}
    try:
        report['devices'] = devices()
        if mode != 'list-only':
            serial = select_device(report['devices'], requested_serial)
            report['selectedSerial'] = serial
            for key in PROPS:
                try:
                    report['facts'][key] = remote(serial, key)
                except (OSError, ValueError) as error:
                    report['unresolved'][key] = str(error)
            assessment = assess_profile(report['facts'], inspection=mode == 'inspection-only')
            report['profileAssessment'] = assessment
            if not assessment['recordedPropertySubsetMatches']:
                report['unresolved']['profileAdmission'] = assessment['reason']
            for key in queries():
                if key in PROPS:
                    continue
                try:
                    report['facts'][key] = remote(serial, key)
                except (OSError, ValueError) as error:
                    report['unresolved'][key] = str(error)
            report['runtimeProcesses'] = []
            for pid in report['facts'].get('system-server-pids', []):
                entry = {'pid': pid, 'facts': {}, 'unresolved': {}}
                try:
                    identity = remote(serial, 'pid-identity', pid)
                    namespace = remote(serial, 'pid-namespace', pid)
                    for path in RUNTIME_FILES:
                        full = f'/proc/{pid}/root'+path
                        try:
                            entry['facts'][full] = remote(serial, full, pid)
                        except (OSError, ValueError) as error:
                            entry['unresolved'][full] = str(error)
                    if identity != remote(serial, 'pid-identity', pid) or namespace != remote(serial, 'pid-namespace', pid):
                        raise ProfileError('PID identity or namespace moved; file observations invalid')
                    entry.update(identity=identity, mountNamespace=namespace)
                except (OSError, ValueError) as error:
                    entry['unresolved']['identity'] = str(error)
                    entry['facts'] = {}
                report['runtimeProcesses'].append(entry)
                if entry['unresolved']:
                    report['unresolved']['pid-'+pid] = entry['unresolved']
            if 'system-server-pids' in report['facts'] and remote(serial, 'system-server-pids') != report['facts']['system-server-pids']:
                raise ProfileError('system_server PID set moved during collection')
            # Detect observed transport/property drift without claiming atomicity.
            if select_device(devices(), serial) != serial:
                raise ProfileError('Selected transport changed')
            for key in ('ro.product.model', 'ro.build.version.sdk', 'ro.build.display.id', 'ro.build.fingerprint'):
                if key not in report['facts']:
                    continue  # Original failed observation stays unresolved in inspection mode.
                if remote(serial, key) != report['facts'][key]:
                    raise ProfileError('Property view moved during collection')
            report['profileStatus'] = ('inspection-only; no profile admission' if mode == 'inspection-only'
                                       else 'observed-matching-properties; authority/installed-stack/profile acceptance unresolved')
        report['status'] = 'observed' if not report['unresolved'] else 'partial-unresolved'
    except (OSError, ValueError) as error:
        report['status'] = 'unresolved'
        report['unresolved']['collection'] = str(error)
    if source_pins() != pins:
        raise ProfileError('Source pins moved during observation')
    output = ROOT/'out/security-profile'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
    if not output.resolve().is_relative_to(ROOT.resolve()):
        raise ProfileError('Output ancestor resolves outside nested project')
    output.mkdir(parents=True, exist_ok=False)
    path = output/'profile.json'
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'report': str(path.relative_to(ROOT)), 'status': report['status'], 'devices': report.get('devices', []), 'mode': report['mode']}))
    return 0 if report['status'] == 'observed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
