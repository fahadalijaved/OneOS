"""Default OFF host-only Context observer. Root coordinates every phone action.

Default is an offline plan. --preflight and --run currently report unconditional
HOLD: no termination owner or live transport is selected. Prospective templates
retain fixed metadata/approval/permit checks for root's later source review.
No service, setting, guest switch, native VM gate or recovery operation exists.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/host-context-probe-controller'
ADB = ROOT.parent / 'out/toolchain/android-sdk/platform-tools/adb.exe'
ADB_SHA = 'b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f'
HELP = 'out/host-context-preflight/20261106T010201032041Z-2e3f31b8b71f464d8210fa5c884b68bf/help-and-environment.json'
UID_EVIDENCE = 'out/host-context-preflight/20261106T010908955487Z-b89dd74b2e4a4bcfaba91b7cdd52b6d8/uid1000-correct-order.json'
JAR = ROOT / 'out/samsung-context-probe/20261105T191533125222Z-5c0551305cc340c6a912916babe057b3/samsung-context-probe.jar'
JAR_SHA = 'fbce6bff35fe889d3b354f1e3017c19b4960b9468b3a35a9c336d70ddfc6b806'
SOURCE = ROOT / 'compat/android/com/appleexploit/oneos/security/probe/SamsungContextProbe.java'
SOURCE_SHA = '58e53f216ef472064e9e8d347dd5b733fdba00f1295ce55c6e75aeba488148e8'
REMOTE_DIR = '/data/local/tmp/oneos-host-context-probe-20261106-fbce6bff'
REMOTE_JAR = REMOTE_DIR + '/samsung-context-probe.jar'
MAIN = 'com.appleexploit.oneos.security.probe.SamsungContextProbe'
PORT = 5038
DEADLINE = 30
GRACE = 2
MAX_OUTPUT = 65536
PROFILE_NAME = 'ordinary-oneui-ksu-uid1000-context-diagnostic-v1'
# Root rejected numeric PID-check/kill. No owner, override flag or live selection.
TERMINATION_OWNER = None
LIVE_EXECUTION_SELECTED = False
ENV_KEYS = ('PATH', 'ANDROID_ROOT', 'ANDROID_DATA', 'ANDROID_I18N_ROOT', 'ANDROID_TZDATA_ROOT',
            'BOOTCLASSPATH', 'DEX2OATBOOTCLASSPATH', 'SYSTEMSERVERCLASSPATH', 'STANDALONE_SYSTEMSERVER_JARS')
CODE = {
    '/system/framework/framework.jar': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
    '/system/framework/services.jar': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
    '/system/bin/app_process64': '08891284f79ebd9411d7ebd2e267bd2c083e8d5a02f2f192629fb126fabfeec8',
    '/system/lib64/libandroid_runtime.so': 'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d',
    '/apex/com.android.art/lib64/libart.so': '4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa',
}
PROPS = {'ro.product.model': 'SM-S948U1', 'ro.build.version.sdk': '37',
         'ro.build.display.id': 'CP2A.260605.016.S948U1UES4BZIG',
         'ro.build.fingerprint': 'samsung/m3quew/m3q:17/CP2A.260605.016/S948U1UES4BZIG_OYM4BZIG:user/release-keys'}
STAT_KEYS = ('Uid', 'Gid', 'Groups', 'CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb', 'NoNewPrivs')
BOOL_KEYS = {'activityThreadCurrentMatches', 'mainLooperCurrentMatches', 'contextPresent', 'applicationPresent',
             'contextApplicationMatches', 'resourcesPresent', 'resourcesMatchSystem', 'contextClassLoaderPresent',
             'applicationClassLoaderPresent'}
PINS = {'out/host-context-preflight/20261106T010201032041Z-2e3f31b8b71f464d8210fa5c884b68bf/help-and-environment.json': '42ee8c3826caf9c69150af07c62348cdaf5f33173a8ed300db0d8f107d47b82a', 'out/host-context-preflight/20261106T010908955487Z-b89dd74b2e4a4bcfaba91b7cdd52b6d8/uid1000-correct-order.json': 'f644015970262a2faefd57c68a8314df1b301c77719b724f175f0bb9899f566b', 'inventory/samsung-context-probe.json': '0773ca344ba04180ad90530f9ef68ef9d020262194effa785f375f4a50cca1a4'}  # Literal saved evidence identities.

class Refusal(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Refusal(reason)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def numeric(value):
    value = str(value)
    require(bool(re.fullmatch(r'[1-9][0-9]{0,6}', value)), 'bounded-numeric-selector')
    return value

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')

def durable_save(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temp.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)

def parse_stat(value, pid):
    # comm may contain spaces and parentheses. Fields start after its FINAL ).
    end = value.rfind(') ')
    require(end >= 3 and value.startswith(str(pid) + ' ('), 'stat-pid-or-comm')
    fields = value[end + 2:].split()
    require(len(fields) >= 20 and re.fullmatch('[A-Za-z]', fields[0]) is not None
            and fields[1].isdigit() and fields[19].isdigit(), 'stat-field-shape')
    return {'pid': int(pid), 'ppid': int(fields[1]), 'starttime': int(fields[19]), 'state': fields[0]}

def verified_inputs():
    for name, pin in PINS.items():
        require(sha(ROOT / name) == pin, 'saved-input-drift')
    require(sha(ADB) == ADB_SHA and sha(JAR) == JAR_SHA and JAR.stat().st_size == 4588
            and sha(SOURCE) == SOURCE_SHA, 'artifact-or-tool-drift')
    env = json.loads((ROOT / HELP).read_text())['selectedSystemServerEnvironment']
    require(set(env) == set(ENV_KEYS), 'source-environment-key-set')
    for key, value in env.items():
        require(isinstance(value, str) and 0 < len(value) <= 8192
                and re.fullmatch(r'[A-Za-z0-9_./:+-]+', value) is not None, 'source-environment-value')
    require(len(env['BOOTCLASSPATH'].split(':')) == 61, 'source-bcp-count')
    return env

def plan():
    env = verified_inputs()
    return {'schema': 'host-context-probe-controller-plan/v1', 'sourceSha256': sha(__file__),
            'artifactSha256': JAR_SHA, 'artifactBytes': 4588, 'remoteDirectory': REMOTE_DIR,
            'remoteJar': REMOTE_JAR, 'directoryOwnerMode': '0:1000:750', 'jarOwnerMode': '0:1000:444',
            'environment': dict(env, CLASSPATH=REMOTE_JAR), 'probeArgv': ['/system/bin/app_process64', '/system/bin', MAIN, '--host-context-probe'],
            'ksuArgvPrefix': ['/system/bin/su', '-g', '1000', '-G', '1000', '1000', '-c'],
            'requiredCodeHashes': CODE, 'optionalVoldNotRead': True, 'deadlineSeconds': DEADLINE,
            'killGraceSeconds': GRACE, 'maxOutputBytes': MAX_OUTPUT, 'maxProbeRecordBytes': 2048,
            'defaultOffline': True, 'runExecuted': False, 'authorityReady': False,
            'diagnosticProfile': PROFILE_NAME, 'equivalentToSystemServer': False,
            'terminationOwnerSelected': False, 'liveExecutionSelected': False,
            'requiredApprovalFields': ['schema', 'controllerSha256', 'planSha256', 'explicitUserApprovalReference',
                                       'ordinaryOneUiConfirmed', 'transportId', 'hostPid', 'preflightReceipt',
                                       'preflightReceiptSha256', 'allowExactStagingLaunchCleanup'],
            'terminationLimit': 'Numeric PID-check/kill rejected. No termination owner is selected; every live transport/preflight/run path is unconditionally held. No accept-risk Boolean or CLI override exists.'}

def plan_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def shell_quote(value):
    return shlex.quote(str(value))

def facts_script(pid, root_view=False, jar=False):
    p = str(pid) if pid != '$$' else '$$'
    prefix = '/proc/' + p + '/root' if root_view else ''
    lines = ['set -eu', 'p=' + p, "printf 'PID\\t%s\\n' \"$p\"",
             "printf 'STAT\\t'; cat /proc/$p/stat", "printf 'BOOT\\t'; cat /proc/sys/kernel/random/boot_id",
             "printf 'DOMAIN\\t'; tr -d '\\000' < /proc/$p/attr/current; printf '\\n'",
             "printf 'MNT\\t'; readlink /proc/$p/ns/mnt",
             "printf 'PIDNS\\t'; readlink /proc/$p/ns/pid",
             "printf 'USERNS\\t'; readlink /proc/$p/ns/user",
             "awk '/^(Uid|Gid|Groups|CapInh|CapPrm|CapEff|CapBnd|CapAmb|NoNewPrivs):/ {printf \"STATUS\\t%s\\n\",$0}' /proc/$p/status"]
    for path in CODE:
        lines.append("printf 'HASH\\t%s\\t' " + shell_quote(path) + '; sha256sum ' + shell_quote(prefix + path) + " | awk '{print $1}'")
    for key in PROPS:
        lines.append("printf 'PROP\\t%s\\t' " + shell_quote(key) + '; getprop ' + shell_quote(key))
    lines.append("tr '\\000' '\\n' < /proc/$p/environ | while IFS='=' read -r k v; do case \"$k\" in "
                 + '|'.join(ENV_KEYS) + ") printf 'ENV\\t%s\\t%s\\n' \"$k\" \"$v\";; esac; done")
    if jar:
        lines += ["printf 'JARHASH\\t'; sha256sum " + shell_quote(REMOTE_JAR) + " | awk '{print $1}'",
                  "printf 'JARMETA\\t'; stat -c '%u:%g:%a:%s' " + shell_quote(REMOTE_JAR),
                  "printf 'DIRMETA\\t'; stat -c '%u:%g:%a' " + shell_quote(REMOTE_DIR),
                  '[ ! -L ' + shell_quote(REMOTE_DIR) + ' ] && [ ! -L ' + shell_quote(REMOTE_JAR) + ' ]']
    lines += ["printf 'FACTS_END\\n'"]
    return '\n'.join(lines)

def parse_facts(lines, expected_env, jar=False):
    require(lines and lines[-1] == 'FACTS_END' and lines.count('FACTS_END') == 1, 'facts-frame-end')
    scalar, status, hashes, env, props = {}, {}, {}, {}, {}
    for line in lines:
        parts = line.split('\t')
        if parts == ['FACTS_END']:
            continue
        key = parts[0]
        if key in ('HASH', 'ENV', 'PROP'):
            require(len(parts) == 3, 'fact-triple-shape')
            target = {'HASH': hashes, 'ENV': env, 'PROP': props}[key]
            require(parts[1] not in target, 'duplicate-fact')
            target[parts[1]] = parts[2]
        elif key == 'STATUS':
            require(len(parts) >= 2, 'status-shape')
            name, sep, value = '\t'.join(parts[1:]).partition(':')
            require(sep and name in STAT_KEYS and name not in status, 'status-key')
            status[name] = value.strip()
        else:
            require(key in ('PID', 'STAT', 'BOOT', 'DOMAIN', 'MNT', 'PIDNS', 'USERNS', 'JARHASH', 'JARMETA', 'DIRMETA')
                    and len(parts) == 2 and key not in scalar, 'scalar-fact-shape')
            scalar[key] = parts[1]
    expected_scalar = {'PID', 'STAT', 'BOOT', 'DOMAIN', 'MNT', 'PIDNS', 'USERNS'}
    if jar:
        expected_scalar |= {'JARHASH', 'JARMETA', 'DIRMETA'}
    require(set(scalar) == expected_scalar and set(status) == set(STAT_KEYS), 'incomplete-facts')
    pid = int(numeric(scalar['PID'])); identity = parse_stat(scalar.pop('STAT'), pid)
    require(re.fullmatch(r'[0-9a-f-]{36}', scalar['BOOT']) is not None
            and re.fullmatch(r'mnt:\[[1-9][0-9]*\]', scalar['MNT']) is not None
            and re.fullmatch(r'pid:\[[1-9][0-9]*\]', scalar['PIDNS']) is not None
            and re.fullmatch(r'user:\[[1-9][0-9]*\]', scalar['USERNS']) is not None
            and re.fullmatch(r'u:r:[A-Za-z0-9_]+:s0', scalar['DOMAIN']) is not None, 'fact-value-shape')
    for key in ('Uid', 'Gid'):
        values = status[key].split()
        require(len(values) == 4 and all(re.fullmatch(r'[0-9]{1,10}', v) for v in values), 'all-four-credential-shape')
    groups = status['Groups'].split()
    require(len(groups) <= 128 and len(set(groups)) == len(groups)
            and all(re.fullmatch(r'[0-9]{1,10}', v) for v in groups), 'supplementary-group-shape')
    for key in ('CapInh', 'CapPrm', 'CapEff', 'CapAmb'):
        require(re.fullmatch(r'[0-9a-f]{16}', status[key]) is not None, 'capability-shape')
    require(re.fullmatch(r'[0-9a-f]{16}', status['CapBnd']) is not None and status['NoNewPrivs'] in ('0', '1'), 'cap-bound-or-nnp')
    require(hashes == CODE and props == PROPS and env == expected_env, 'required-code-build-or-environment-view')
    if jar:
        require(scalar['JARHASH'] == JAR_SHA and scalar['JARMETA'] == '0:1000:444:4588'
                and scalar['DIRMETA'] == '0:1000:750', 'jar-public-metadata-schema')
    return {'identity': identity, 'boot': scalar['BOOT'], 'domain': scalar['DOMAIN'], 'mountNamespace': scalar['MNT'],
            'pidNamespace': scalar['PIDNS'], 'userNamespace': scalar['USERNS'],
            'credentials': status, 'hashes': hashes, 'environment': env, 'properties': props,
            'jarHash': scalar.get('JARHASH'), 'jarMeta': scalar.get('JARMETA'), 'directoryMeta': scalar.get('DIRMETA')}

class Wire:
    """Capped concurrent stdout/stderr; unknown content is never written to disk."""
    def __init__(self, argv, timeout=DEADLINE):
        self.end = time.monotonic() + timeout
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.events = queue.Queue(); self.total = 0; self.lock = threading.Lock()
        self.unknown = 0; self.stderr_bytes = 0; self.stream_error = None
        self.partial_stdout_bytes = 0; self.stdout_ended = False
        self.threads = [threading.Thread(target=self._read, args=(pipe, channel), daemon=True)
                        for pipe, channel in [(self.process.stdout, 'out'), (self.process.stderr, 'err')]]
        for thread in self.threads:
            thread.start()

    def _read(self, pipe, channel):
        pending = bytearray()
        try:
            while True:
                block = pipe.read(1)
                if not block:
                    break
                with self.lock:
                    self.total += len(block)
                    if self.total > MAX_OUTPUT:
                        self.stream_error = 'stream-cap'
                        self.events.put(('error', 'stream-cap')); return
                    if channel == 'err':
                        self.stderr_bytes += len(block); continue
                    pending.extend(block); self.partial_stdout_bytes = len(pending)
                    if len(pending) > 8192:
                        self.stream_error = 'line-cap'
                        self.events.put(('error', 'line-cap')); return
                    if block == b'\n':
                        self.events.put(('line', bytes(pending).rstrip(b'\r\n')))
                        pending.clear(); self.partial_stdout_bytes = 0
            if pending:
                with self.lock:
                    self.stream_error = 'unterminated-output'
                self.events.put(('error', 'unterminated-output'))
        finally:
            pipe.close()
            with self.lock:
                if channel == 'out': self.stdout_ended = True
                self.events.put(('eof', channel))

    def event(self):
        remaining = self.end - time.monotonic()
        require(remaining > 0, 'deadline')
        try:
            kind, value = self.events.get(timeout=remaining)
        except queue.Empty:
            raise Refusal('deadline')
        if kind == 'error':
            raise Refusal(value)
        if kind == 'line':
            try:
                return kind, value.decode('ascii', 'strict')
            except UnicodeError:
                with self.lock:
                    self.stream_error = 'unapproved-output'
                self.unknown += len(value); raise Refusal('unapproved-output')
        return kind, value

    def check_before_permit(self):
        with self.lock:
            require(self.stderr_bytes == 0 and self.stream_error is None and self.total <= MAX_OUTPUT
                    and self.partial_stdout_bytes == 0 and not self.stdout_ended,
                    'known-pre-permit-stream-failure')
            # This run child must be waiting on stdin after READY. Already-read
            # additional stdout/EOF/error cannot be silently skipped at admission.
            with self.events.mutex:
                require(not self.events.queue, 'unexpected-pending-pre-permit-output')

    def finish(self):
        require(time.monotonic() < self.end, 'deadline')
        try:
            rc = self.process.wait(timeout=max(.01, self.end - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise Refusal('deadline')
        for thread in self.threads:
            thread.join(timeout=1)
        require(not any(t.is_alive() for t in self.threads) and self.stderr_bytes == 0, 'stderr-or-incomplete-pipe')
        return rc

    def send(self, data=b'', close=False):
        done = threading.Event(); errors = []
        def writer():
            try:
                if data:
                    self.process.stdin.write(data); self.process.stdin.flush()
                if close:
                    self.process.stdin.close()
            except (OSError, ValueError) as failure:
                errors.append(type(failure).__name__)
            finally:
                done.set()
        threading.Thread(target=writer, daemon=True).start()
        if not done.wait(max(0, self.end - time.monotonic())):
            self.stop_pc()  # Never claim this canceled a permit already in transit.
            raise Refusal('input-deadline')
        require(not errors, 'input-pipe-failure')

    def stop_pc(self):
        # This stops only local adb. It does NOT certify remote termination.
        if self.process.poll() is None:
            self.process.kill()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass

class Adb:
    def __init__(self, transport):
        require(LIVE_EXECUTION_SELECTED and TERMINATION_OWNER is not None, 'live-hold-unselected-termination-owner')
        self.transport = numeric(transport)

    def wire(self, script, timeout=DEADLINE):
        require(LIVE_EXECUTION_SELECTED and TERMINATION_OWNER is not None, 'live-hold-unselected-termination-owner')
        require(sha(ADB) == ADB_SHA, 'adb-drift')
        with socket.create_connection(('127.0.0.1', PORT), timeout=2):
            pass
        # Existing-server check is not an atomic no-autostart guarantee.
        return Wire([str(ADB), '-P', str(PORT), '-t', self.transport, 'exec-out', '/system/bin/sh', '-c', shell_quote(script)], timeout)

    def query(self, script, timeout=15):
        wire = self.wire(script + '\nprintf "COMMAND_END\\n"', timeout)
        lines = []; ended = False; eofs = set()
        try:
            while len(eofs) != 2:
                kind, value = wire.event()
                if kind == 'eof':
                    eofs.add(value); continue
                if value == 'COMMAND_END':
                    require(not ended, 'duplicate-command-end'); ended = True
                else:
                    require(not ended, 'output-after-command-end'); lines.append(value)
            require(ended and wire.finish() == 0, 'query-status')
            return lines
        finally:
            wire.stop_pc()

def target_facts(adb, host_pid, expected_env):
    # getprop and named-file reads must use the actual chosen view as well.
    pid = numeric(host_pid)
    script = '/system/bin/toybox nsenter -t ' + pid + ' -m /system/bin/sh -c ' + shell_quote(facts_script(pid))
    rows = adb.query(script)
    facts = parse_facts(rows, expected_env)
    require(facts['identity']['pid'] == int(host_pid) and facts['environment'] == expected_env
            and facts['credentials']['Uid'].split() == ['1000'] * 4, 'current-source-environment')
    return facts

def same_identity(a, b):
    return a['identity']['pid'] == b['identity']['pid'] and a['identity']['starttime'] == b['identity']['starttime'] and a['boot'] == b['boot']

def child_script(env, permit, run):
    script = facts_script('$$', jar=run) + '\nprintf "READY\\n"\n'
    if run:
        script += 'IFS= read -r permit\n[ "$permit" = ' + shell_quote(permit) + ' ] || exit 23\n'
        script += 'exec /system/bin/app_process64 /system/bin ' + MAIN + ' --host-context-probe\n'
    else:
        script += 'exit 0\n'
    assignments = [key + '=' + value for key, value in env.items()]
    if run:
        assignments.append('CLASSPATH=' + REMOTE_JAR)
    inner = 'exec /system/bin/env -i ' + ' '.join(shell_quote(x) for x in assignments) + ' /system/bin/sh -c ' + shell_quote(script)
    # Proven numeric-user BEFORE -c. No -M/-Z/-p/UID-drop guess.
    return '/system/bin/su -g 1000 -G 1000 1000 -c ' + shell_quote(inner)

def child_shape(child):
    require(all(child['credentials'][key].split() == ['1000'] * 4 for key in ('Uid', 'Gid'))
            and child['credentials']['Groups'].split() == ['1000']
            and all(int(child['credentials'][key], 16) == 0 for key in ('CapInh', 'CapPrm', 'CapEff', 'CapAmb')), 'child-credentials')
    require(child['domain'] == 'u:r:ksu:s0', 'child-domain')

def validate_child(child, target, env, run, approved=None, owner_ns=None):
    child_shape(child)
    require(child['identity']['pid'] not in (1, target['identity']['pid'], target['identity']['ppid'])
            and child['boot'] == target['boot'] and child['mountNamespace'] == target['mountNamespace']
            and child['pidNamespace'] == target['pidNamespace'] and child['userNamespace'] == target['userNamespace']
            and owner_ns == {'pid': child['pidNamespace'], 'user': child['userNamespace']}, 'child-host-view-or-protected-pid')
    require(child['domain'] == 'u:r:ksu:s0' and child['environment'] == env, 'child-domain-or-source-environment')
    if run:
        require(child['jarHash'] == JAR_SHA and child['jarMeta'] == '0:1000:444:4588'
                and child['directoryMeta'] == '0:1000:750', 'staged-jar-identity-or-modes')
        require(approved is not None and approved['childDomain'] == child['domain']
                and approved['childMountNamespace'] == child['mountNamespace'], 'approved-child-profile')

def parse_probe(line, child):
    require(len(line.encode()) <= 2048, 'probe-line-bound')
    try:
        def unique(pairs):
            value = {}
            for key, item in pairs:
                require(key not in value, 'duplicate-probe-field')
                value[key] = item
            return value
        value = json.loads(line, object_pairs_hook=unique)
    except (ValueError, TypeError):
        raise Refusal('unapproved-native-output')
    require(isinstance(value, dict) and value.get('schema') == 'samsung-context-probe/v1'
            and value.get('hostOnly') is True and value.get('authorityReady') is False, 'probe-schema')
    if value.get('status') == 'CONTEXT_OBSERVED_ONLY':
        expected = {'schema', 'status', 'hostOnly', 'authorityReady', 'sdk', 'model', 'display', 'fingerprint', 'pid', 'uid'} | BOOL_KEYS
        require(set(value) == expected and type(value['sdk']) is int and value['sdk'] == 37
                and type(value['pid']) is int and value['pid'] == child['identity']['pid']
                and type(value['uid']) is int and value['uid'] == 1000
                and value['model'] == PROPS['ro.product.model'] and value['display'] == PROPS['ro.build.display.id']
                and value['fingerprint'] == PROPS['ro.build.fingerprint']
                and all(type(value[k]) is bool for k in BOOL_KEYS)
                and value['contextPresent'] and value['applicationPresent'], 'probe-public-fields')
    else:
        require(set(value) == {'schema', 'status', 'hostOnly', 'authorityReady', 'phase', 'failureKind'}
                and value['status'] == 'REFUSED_OR_FAILED'
                and value['phase'] in ('argument', 'recorded-host-profile', 'fresh-process', 'prepare-main-looper', 'system-main', 'context-observation')
                and value['failureKind'] in ('reflection', 'guard-or-runtime'), 'probe-failure-fields')
    return value

def child_absent(adb, child):
    pid = numeric(child['identity']['pid'])
    lines = adb.query('[ ! -e /proc/' + pid + ' ] && printf "OWN_CHILD_ABSENT\\n"')
    return lines == ['OWN_CHILD_ABSENT']

def issue_permit(wire, record, checkpoint, permit):
    """Prospective protocol helper; real transport remains unselected/held."""
    require(record.get('childAdmittedForPermit') is True and record.get('cleanupHold') is True
            and not record.get('launchPermitAttempted'), 'permit-state-order')
    require(re.fullmatch(r'RUN_[0-9a-f]{32}', permit) is not None, 'permit-token-shape')
    require(time.monotonic() < wire.end, 'deadline-before-permit')
    wire.check_before_permit()
    record['launchPermitAttempted'] = True
    checkpoint()  # admitted identity + possible send survive a PC failure
    wire.send((permit + '\n').encode('ascii'))
    record['launchPermitWriteCompleted'] = True
    checkpoint()

def approval(path, options, current_plan):
    require(path is not None, 'separate-explicit-approval-required')
    path = path.resolve(); require(path.is_relative_to(OUT.resolve()), 'approval-under-own-out-only')
    value = json.loads(path.read_text())
    require(set(value) == set(current_plan['requiredApprovalFields']) and value['schema'] == 'host-context-probe-approval/v1'
            and value['controllerSha256'] == sha(__file__) and value['planSha256'] == plan_hash(current_plan)
            and value['ordinaryOneUiConfirmed'] is True and value['allowExactStagingLaunchCleanup'] is True
            and value['transportId'] == options.transport and value['hostPid'] == options.host_pid
            and isinstance(value['explicitUserApprovalReference'], str) and 1 <= len(value['explicitUserApprovalReference']) <= 500, 'approval-fields')
    rp = (ROOT / value['preflightReceipt']).resolve()
    require(rp.is_relative_to(OUT.resolve()) and sha(rp) == value['preflightReceiptSha256'], 'approved-preflight-receipt')
    prior = json.loads(rp.read_text())
    require(prior['status'] == 'PREFLIGHT_ONLY_COMPLETE' and prior['cleanupHold'] is False
            and prior['controllerSha256'] == sha(__file__), 'approved-preflight-result')
    return value, {'childDomain': prior['child']['domain'], 'childMountNamespace': prior['child']['mountNamespace'],
                   'targetBefore': prior['targetBefore']}

def stage(adb, host_pid, record, checkpoint):
    # No reuse/overwrite: mkdir is exclusive, and a later failure retains HOLD.
    q = shell_quote; prefix = '/proc/' + numeric(host_pid) + '/root'
    script = 'set -eu\n[ ! -e ' + q(prefix + REMOTE_DIR) + ' ] && [ ! -L ' + q(prefix + REMOTE_DIR) + ' ]\n'
    script += 'mkdir -m 700 ' + q(prefix + REMOTE_DIR) + '\nprintf "DIRECTORY_CREATED\\n"'
    record['stagingProgress'] = 'exclusive-mkdir-attempted'
    checkpoint()
    require(adb.query(script) == ['DIRECTORY_CREATED'], 'exclusive-directory-refusal')
    record['stagingProgress'] = 'exclusive-directory-confirmed'
    checkpoint()
    # Binary is passed as bytes on stdin, never a shell-built byte string.
    record['stagingProgress'] = 'binary-stream-attempted'
    checkpoint()
    wire = adb.wire('set -eu\numask 077\ncat > ' + q(prefix + REMOTE_JAR) + '\nprintf "JAR_STAGED\\n"')
    try:
        wire.send(JAR.read_bytes(), close=True)
        lines = []; eofs = set()
        while len(eofs) != 2:
            kind, value = wire.event()
            if kind == 'eof': eofs.add(value)
            else: lines.append(value)
        require(lines == ['JAR_STAGED'] and wire.finish() == 0, 'binary-stage-status')
    finally:
        wire.stop_pc()
    script = 'set -eu\nchown 0:1000 ' + q(prefix + REMOTE_DIR) + ' ' + q(prefix + REMOTE_JAR) + '\n'
    script += 'chmod 444 ' + q(prefix + REMOTE_JAR) + '\nchmod 750 ' + q(prefix + REMOTE_DIR) + '\n'
    script += 'printf "STAGED_HASH\\t"; sha256sum ' + q(prefix + REMOTE_JAR) + " | awk '{print $1}'"
    record['stagingProgress'] = 'owner-mode-and-hash-attempted'
    checkpoint()
    require(adb.query(script) == ['STAGED_HASH\t' + JAR_SHA], 'staged-root-hash')
    record['stagingProgress'] = 'complete'
    checkpoint()

def cleanup(adb, host_pid):
    # Called only after positive own-process absence and stable target checks.
    prefix = '/proc/' + numeric(host_pid) + '/root'
    script = 'set -eu\n[ ! -L ' + shell_quote(prefix + REMOTE_DIR) + ' ]\n'
    script += '[ "$(sha256sum ' + shell_quote(prefix + REMOTE_JAR) + " | awk '{print $1}')\" = " + shell_quote(JAR_SHA) + ' ]\n'
    script += 'rm ' + shell_quote(prefix + REMOTE_JAR) + '\nrmdir ' + shell_quote(prefix + REMOTE_DIR) + '\nprintf "EXACT_STAGE_REMOVED\\n"'
    require(adb.query(script) == ['EXACT_STAGE_REMOVED'], 'exact-cleanup-refusal')

def operate(options, run):
    require(LIVE_EXECUTION_SELECTED and TERMINATION_OWNER is not None, 'live-hold-unselected-termination-owner')
    current_plan = plan(); env = verified_inputs(); approved = None; approval_value = None
    if run:
        approval_value, approved = approval(options.approval_file, options, current_plan)
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / 'UNRESOLVED.json'
    # Never silently retry after an uncertain prior launch/preflight or PC crash.
    with lock.open('x') as f:
        json.dump({'status': 'ACTIVE_OR_UNRESOLVED', 'controllerSha256': sha(__file__)}, f)
    work = OUT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex)
    work.mkdir()
    record = {'schema': 'host-context-probe-controller-receipt/v1', 'controllerSha256': sha(__file__),
              'mode': 'run' if run else 'preflight', 'status': 'HOLD', 'cleanupHold': True,
              'diagnosticProfile': PROFILE_NAME, 'equivalentToSystemServer': False,
              'launchPermitAttempted': False, 'launchPermitWriteCompleted': False,
              'contextProbeRecordReceived': False, 'jarStaged': False, 'authorityReady': False,
              'postExecDomainObserved': False, 'postExecNativeOrLoadedCodeAttested': False,
              'unknownOutputBytes': 0, 'stderrBytes': 0, 'terminationIsAtomic': False,
              'transportId': options.transport, 'hostPid': options.host_pid}
    record['work'] = work.relative_to(ROOT).as_posix()
    def checkpoint():
        durable_save(work / 'checkpoint.json', record)
        durable_save(lock, {'status': 'ACTIVE_OR_HOLD_NO_REPEAT', 'work': record['work'],
                            'controllerSha256': record['controllerSha256'],
                            'checkpoint': (work / 'checkpoint.json').relative_to(ROOT).as_posix(),
                            'checkpointSha256': sha(work / 'checkpoint.json')})
    checkpoint()  # Saved before any phone operation, not only before mutation.
    adb = Adb(options.transport); child = None; owned = None; wire = None; target = None; staged = False
    try:
        # Confirm root transport separately; no domain/namespace is inferred from0.
        require(adb.query('id -u') == ['0'], 'root-transport-required')
        owner_rows = adb.query("printf 'PIDNS\\t'; readlink /proc/$$/ns/pid\nprintf 'USERNS\\t'; readlink /proc/$$/ns/user")
        require(len(owner_rows) == 2 and all(len(row.split('\t')) == 2 for row in owner_rows)
                and owner_rows[0].split('\t')[0] == 'PIDNS' and owner_rows[1].split('\t')[0] == 'USERNS', 'root-owner-namespace-shape')
        owner_ns = {'pid': owner_rows[0].split('\t')[1], 'user': owner_rows[1].split('\t')[1]}
        require(re.fullmatch(r'pid:\[[1-9][0-9]*\]', owner_ns['pid']) is not None
                and re.fullmatch(r'user:\[[1-9][0-9]*\]', owner_ns['user']) is not None, 'root-owner-namespace-values')
        record['signalOwnerNamespaces'] = owner_ns
        target = target_facts(adb, options.host_pid, env); record['targetBefore'] = target
        if run:
            require(same_identity(target, approved['targetBefore'])
                    and all(target[key] == approved['targetBefore'][key] for key in
                            ('mountNamespace', 'pidNamespace', 'userNamespace')), 'approved-target-drift')
            staged = True  # Conservative even when a write's acknowledgement is lost.
            stage(adb, options.host_pid, record, checkpoint); record['jarStaged'] = True; checkpoint()
            require(same_identity(target, target_facts(adb, options.host_pid, env)), 'target-drift-after-stage')
        permit = 'RUN_' + uuid.uuid4().hex
        script = '/system/bin/toybox nsenter -t ' + numeric(options.host_pid) + ' -m ' + child_script(env, permit, run)
        script += '\nrc=$?\nprintf "SUPERVISOR_EXIT\\t%s\\n" "$rc"\nexit "$rc"'
        wire = adb.wire(script); facts = []; ready = False; result = None; remote_exit = None; eofs = set()
        while len(eofs) != 2:
            kind, value = wire.event()
            if kind == 'eof': eofs.add(value); continue
            if not ready:
                if value == 'READY':
                    try:
                        candidate = parse_facts(facts, env, jar=run)
                        child_shape(candidate)
                    except Refusal:
                        wire.unknown += sum(len(row) for row in facts)
                        raise
                    child = candidate; record['child'] = child
                    fresh = target_facts(adb, options.host_pid, env)
                    require(same_identity(target, fresh) and target['mountNamespace'] == fresh['mountNamespace'], 'target-drift-at-permit')
                    validate_child(child, fresh, env, run, approved, owner_ns)
                    owned = child; ready = True; record['childAdmittedForPermit'] = True
                    checkpoint()
                    if run:
                        issue_permit(wire, record, checkpoint, permit)
                else:
                    require(not value.startswith('SUPERVISOR_EXIT'), 'child-failed-before-ready')
                    facts.append(value)
            elif value.startswith('SUPERVISOR_EXIT\t'):
                require(remote_exit is None and re.fullmatch(r'SUPERVISOR_EXIT\t[0-9]{1,3}', value) is not None, 'remote-exit-shape')
                remote_exit = int(value.split('\t')[1]); require(remote_exit <= 255, 'remote-exit-range')
            elif run and value.startswith('{'):
                require(result is None and remote_exit is None, 'duplicate-or-late-probe-record')
                result = parse_probe(value, child)
                record['contextProbeRecordReceived'] = True
            else:
                wire.unknown += len(value); raise Refusal('unapproved-output')
        local_exit = wire.finish()
        require(ready and remote_exit is not None, 'missing-ready-or-exit')
        record.update(localAdbExit=local_exit, wrapperReportedExit=remote_exit, probe=result)
        require(child_absent(adb, child), 'own-child-exit-unconfirmed')
        final = target_facts(adb, options.host_pid, env)
        require(same_identity(target, final) and target['mountNamespace'] == final['mountNamespace'], 'host-drift-after-child')
        record['targetAfter'] = final
        if run:
            require(result is not None, 'missing-authored-probe-record')
            cleanup(adb, options.host_pid); staged = False
            record['status'] = 'CONTEXT_OBSERVED_ONLY' if result['status'] == 'CONTEXT_OBSERVED_ONLY' and remote_exit == 0 and local_exit == 0 else 'PROBE_REFUSED_OR_FAILED'
        else:
            require(remote_exit == 0 and local_exit == 0, 'preflight-exit')
            record['status'] = 'PREFLIGHT_ONLY_COMPLETE'
        record['cleanupHold'] = False
    except (Refusal, OSError, ValueError, KeyError) as failure:
        # Persist only a fixed exception class/reason enum, never raw native text.
        record['failureKind'] = type(failure).__name__
        record['failureReason'] = str(failure) if isinstance(failure, Refusal) else 'local-or-protocol-failure'
        if wire is not None and wire.process.stdin and not wire.process.stdin.closed:
            try:
                wire.send(close=True)  # pre-permit EOF is a refusal, not a launch.
            except (OSError, Refusal):
                pass
        if owned is not None:
            try:
                record['ownChildAbsentAfterFailure'] = child_absent(adb, owned)
            except (Refusal, OSError, ValueError):
                record['ownChildAbsentAfterFailure'] = False
        # Even a confirmed termination does not silently complete staging recovery.
        # Keep HOLD for root review, retained arena/cache effects and exact cleanup.
    finally:
        if wire is not None:
            record['unknownOutputBytes'] = wire.unknown
            record['stderrBytes'] = wire.stderr_bytes
            wire.stop_pc()
        record['stageCleanupPending'] = staged
        path = work / 'receipt.json'; save(path, record)
        if record['cleanupHold']:
            save(lock, {'status': 'HOLD_NO_REPEAT', 'receipt': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
        else:
            lock.unlink()  # PC-only own marker; all historical receipts remain.
    print(json.dumps({'status': record['status'], 'receipt': path.relative_to(ROOT).as_posix(),
                      'cleanupHold': record['cleanupHold'], 'authorityReady': False}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--preflight', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--transport', type=int)
    parser.add_argument('--host-pid', type=int)
    parser.add_argument('--approval-file', type=Path)
    args = parser.parse_args()
    if not args.preflight and not args.run:
        value = plan(); print(json.dumps({'plan': value, 'planSha256': plan_hash(value)}, indent=2)); return
    require(args.transport is not None and args.host_pid is not None, 'explicit-current-selectors-required')
    numeric(args.transport); numeric(args.host_pid)
    if not LIVE_EXECUTION_SELECTED or TERMINATION_OWNER is None:
        print(json.dumps({'status': 'HOLD_UNSELECTED_TERMINATION_OWNER', 'requestedMode': 'run' if args.run else 'preflight',
                          'diagnosticProfile': PROFILE_NAME, 'phoneCalls': False, 'authorityReady': False}))
        return 2
    operate(args, args.run)

if __name__ == '__main__':
    sys.exit(main() or 0)
