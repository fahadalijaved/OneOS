"""Offline native-supervisor v1 integration. No live transport is selectable.

Only root may compose a later owner/transport/staging proposal. This module has
no ADB, subprocess, socket, numeric signal, transfer or live-execution code.
"""
import argparse
import copy
import functools
import hashlib
import json
from pathlib import Path
import re
import runpy
import stat
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'tools/host_context_probe_controller.py'
BASE_SHA = 'ff1119745e8251e62a7fba7cc8b5a22d47ec327b1810299b271a51e5293ed6e6'
LIVE_EXECUTION_SELECTED = False
PROFILE_NAME = 'ordinary-oneui-root-supervised-uid1000-context-diagnostic-v1'
DIRECTORY = '/data/local/tmp/oneos-host-context-probe-20261106-fbce6bff'
SUPERVISOR = DIRECTORY + '/host_probe_supervisor'
JAR = DIRECTORY + '/samsung-context-probe.jar'
CLI = '--host-context-supervisor-v1'
ROLES = ('framework', 'services', 'app_process', 'runtime', 'art', 'jar')
WIRE_MAX = 262144
LINE_MAX = 8192
RAW_MAX = 65536
FAIL_REASONS = {'ARGUMENTS', 'ROOT_OR_PROFILE', 'CLOCK', 'CLOCK_LOST', 'SIGNALS', 'DESCRIPTORS', 'FORK', 'CHILD_SETUP', 'NONCE_UNAVAILABLE'}
HOLD_REASONS = {'OWNERSHIP_LOST', 'NONTERMINAL_WAIT', 'UNREAPED', 'UNREAPED_CLOCK_LOST'}
# Filled only from the author's actual frozen source/build/profile receipt.
# Pending values are a refusal, never a caller-configurable artifact fallback.
NATIVE_PINS = {}
NATIVE_ARTIFACT = None
NATIVE_PROFILE_SHA256 = None
NATIVE_DESCRIPTOR_MASKS = None
_base = None

class Refusal(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Refusal(reason)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def base():
    global _base
    need(sha(BASE) == BASE_SHA, 'frozen-validator-source-drift')
    if _base is None:
        _base = runpy.run_path(str(BASE))
    need(_base['LIVE_EXECUTION_SELECTED'] is False and _base['TERMINATION_OWNER'] is None,
         'frozen-validator-live-state')
    return _base

def native_inputs():
    need(bool(NATIVE_PINS) and isinstance(NATIVE_ARTIFACT, dict)
         and isinstance(NATIVE_PROFILE_SHA256, str), 'native-build-pins-pending')
    for name, expected in NATIVE_PINS.items():
        need(sha(ROOT / name) == expected, 'native-source-build-drift')
    need(set(NATIVE_ARTIFACT) == {'path', 'sha256', 'bytes'}, 'native-artifact-schema')
    artifact = ROOT / NATIVE_ARTIFACT['path']
    need(artifact.stat().st_size == NATIVE_ARTIFACT['bytes'] and sha(artifact) == NATIVE_ARTIFACT['sha256'], 'native-artifact-drift')
    need(re.fullmatch(r'[0-9a-f]{64}', NATIVE_PROFILE_SHA256) is not None, 'native-profile-pin')
    base()['verified_inputs']()
    return dict(NATIVE_ARTIFACT)

def integer(value, lo=0, hi=(1 << 64) - 1):
    need(type(value) is int and lo <= value <= hi, 'integer-shape')
    return value

def decimal(value):
    need(isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is not None
         and int(value) <= (1 << 64) - 1, 'decimal-string-shape')
    return value

def exact(value, keys):
    need(isinstance(value, dict) and set(value) == set(keys), 'exact-object-schema')

def boolean(value):
    need(type(value) is bool, 'boolean-shape')

def unique(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate-json-field')
        value[key] = item
    return value

SCHEMAS = {
    'READY': {'nonce', 'pid', 'ppid', 'uid', 'gid', 'groups', 'pdeathsig', 'domain', 'ns', 'profile_sha256',
              'deadline_boottime_ms', 'remaining_ms', 'fds'},
    'OUTPUT': {'stream', 'seq', 'hex'}, 'PERMIT_ATTEMPTED': {'pid'}, 'EXEC_ATTEMPTED': {'pid'},
    'EXEC_ERROR': {'pid', 'errno'}, 'EXEC_PIPE_CLOSED': {'pid', 'ambiguous'},
    'SIGNAL': {'pid', 'signal', 'rc', 'errno'}, 'HOLD': {'pid', 'reason', 'owned_unreaped'},
    'REAPED': {'pid', 'kind', 'status', 'permit_attempted', 'exec_attempt_observed', 'stdout_complete', 'stderr_complete', 'cancelled'},
    'FAIL': {'reason', 'errno'},
}

def parse_event(line):
    need(isinstance(line, bytes) and line.endswith(b'\n') and len(line) <= LINE_MAX
         and b'\r' not in line and b'\n' not in line[:-1], 'native-frame-boundary')
    try:
        value = json.loads(line[:-1].decode('ascii'), object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal('native-json-frame')
    need(isinstance(value, dict) and type(value.get('v')) is int and value['v'] == 1
         and isinstance(value.get('event'), str) and value['event'] in SCHEMAS, 'native-version-or-event')
    event = value['event']; exact(value, SCHEMAS[event] | {'v', 'event'})
    if 'pid' in value: integer(value['pid'], 2, 4194304)
    if 'errno' in value: integer(value['errno'], 0, 4095)
    if event == 'READY':
        integer(value['ppid'], 2, 4194304)
        need(value['pid'] != value['ppid'], 'native-child-parent-distinct')
        for key in ('uid', 'gid'):
            need(isinstance(value[key], list) and len(value[key]) == 4
                 and all(type(n) is int and n == 1000 for n in value[key]), 'native-four-credentials')
        need(value['groups'] == [1000] and all(type(n) is int for n in value['groups'])
             and type(value['pdeathsig']) is int and value['pdeathsig'] == 9, 'native-groups-or-pdeathsig')
        need(isinstance(value['nonce'], str) and re.fullmatch(r'[0-9a-f]{32}', value['nonce']) is not None,
             'native-nonce-shape')
        need(isinstance(value['domain'], str) and re.fullmatch(r'u:r:[A-Za-z0-9_]+:s0', value['domain']) is not None,
             'native-domain-shape')
        exact(value['ns'], {'mnt', 'pid', 'user'})
        for key in ('mnt', 'pid', 'user'):
            need(isinstance(value['ns'][key], str) and re.fullmatch(key + r':\[[1-9][0-9]*\]', value['ns'][key]) is not None,
                 'native-namespace-shape')
        need(isinstance(value['profile_sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', value['profile_sha256']) is not None,
             'native-profile-shape')
        integer(value['deadline_boottime_ms'], 1); integer(value['remaining_ms'], 1, 30000)
        need(value['deadline_boottime_ms'] >= value['remaining_ms'], 'native-ready-clock-consistency')
        need(isinstance(value['fds'], list) and len(value['fds']) == 6, 'native-fd-count')
        seen = set()
        for role, fd in zip(ROLES, value['fds']):
            exact(fd, {'role', 'fd', 'dev', 'ino', 'size', 'mode'})
            need(fd['role'] == role, 'native-fd-role-order')
            integer(fd['fd'], 3, 1048576); need(fd['fd'] not in seen, 'native-fd-alias'); seen.add(fd['fd'])
            for key in ('dev', 'ino', 'size'): decimal(fd[key])
            integer(fd['mode'], 0, (1 << 32) - 1); need(stat.S_ISREG(fd['mode']), 'native-fd-not-regular')
    elif event == 'OUTPUT':
        need(value['stream'] in ('stdout', 'stderr'), 'native-output-stream')
        integer(value['seq'], 1)
        need(isinstance(value['hex'], str) and re.fullmatch(r'(?:[0-9a-f]{2}){1,256}', value['hex']) is not None,
             'native-output-hex')
    elif event == 'EXEC_PIPE_CLOSED':
        need(value['ambiguous'] is True, 'exec-pipe-is-ambiguous')
    elif event == 'SIGNAL':
        need(type(value['signal']) is int and value['signal'] in (15, 9)
             and type(value['rc']) is int and value['rc'] in (0, -1)
             and ((value['rc'] == 0 and value['errno'] == 0) or (value['rc'] == -1 and value['errno'] > 0)), 'native-signal-shape')
    elif event == 'HOLD':
        need(isinstance(value['reason'], str) and value['reason'] in HOLD_REASONS, 'native-hold-reason'); boolean(value['owned_unreaped'])
    elif event == 'FAIL':
        need(isinstance(value['reason'], str) and value['reason'] in FAIL_REASONS, 'native-fail-reason')
    elif event == 'REAPED':
        need(value['kind'] in ('exit', 'signal'), 'native-wait-kind')
        integer(value['status'], 0 if value['kind'] == 'exit' else 1, 255 if value['kind'] == 'exit' else 64)
        for key in ('permit_attempted', 'exec_attempt_observed', 'stdout_complete', 'stderr_complete', 'cancelled'):
            boolean(value[key])
        need(not value['exec_attempt_observed'] or value['permit_attempted'], 'native-wait-exec-without-permit')
    return value

def validate_ready_observation(ready, observation, expected_native_sha, expected_env, descriptor_masks):
    """Pure predicate over independently acquired root facts, NOT their issuer.

    Root still owes genuine transport/observer/native-parent/channel admission.
    A caller-created dictionary and a matching hash are not that admission.
    Descriptor masks must come from the source-compiled native ABI receipt.
    """
    need(isinstance(expected_native_sha, str) and re.fullmatch(r'[0-9a-f]{64}', expected_native_sha) is not None,
         'expected-native-artifact-shape')
    exact(observation, {'profile_sha256', 'boot_id', 'boottime_ms', 'supervisor', 'child', 'fd_objects', 'host_env', 'host_props'})
    need(observation['profile_sha256'] == ready['profile_sha256'], 'observed-profile-mismatch')
    need(isinstance(observation['boot_id'], str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', observation['boot_id']) is not None,
         'observed-boot-shape')
    now = integer(observation['boottime_ms'])
    need(ready['deadline_boottime_ms'] - ready['remaining_ms'] <= now < ready['deadline_boottime_ms'],
         'observed-native-deadline')
    parent, child = observation['supervisor'], observation['child']
    exact(parent, {'pid', 'starttime', 'uid', 'domain', 'ns', 'exe_sha256'})
    integer(parent['pid'], 2, 4194304); integer(parent['starttime'], 1)
    need(isinstance(parent['uid'], list) and len(parent['uid']) == 4
         and all(type(n) is int and n == 0 for n in parent['uid'])
         and parent['pid'] == ready['ppid'] and parent['exe_sha256'] == expected_native_sha, 'observed-root-parent')
    exact(child, {'pid', 'ppid', 'starttime', 'uid', 'gid', 'groups', 'domain', 'ns', 'caps', 'no_new_privs'})
    integer(child['pid'], 2, 4194304); integer(child['ppid'], 2, 4194304)
    integer(child['starttime'], 1)
    for key in ('uid', 'gid'):
        need(isinstance(child[key], list) and len(child[key]) == 4
             and all(type(n) is int and n == 1000 for n in child[key]), 'observed-four-credential-types')
    need(isinstance(child['groups'], list) and child['groups'] == [1000]
         and all(type(n) is int for n in child['groups']), 'observed-group-types')
    for key in ('pid', 'ppid', 'uid', 'gid', 'groups', 'domain', 'ns'):
        need(child[key] == ready[key], 'observed-child-fact-mismatch')
    need(child['pid'] not in (1, parent['pid']), 'observed-child-parent-distinct')
    exact(child['caps'], {'Inh', 'Prm', 'Eff', 'Bnd', 'Amb'})
    for key, value in child['caps'].items():
        need(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{16}', value) is not None, 'observed-cap-shape')
        if key != 'Bnd': need(int(value, 16) == 0, 'observed-child-capability')
    need(type(child['no_new_privs']) is int and child['no_new_privs'] in (0, 1), 'observed-nnp-shape')
    need(parent['ns'] == ready['ns'] and parent['domain'] == child['domain'] == 'u:r:ksu:s0', 'observed-diagnostic-domain-or-view')
    need(observation['host_env'] == expected_env and observation['host_props'] == base()['PROPS'], 'observed-original-host-env-or-build')
    exact(descriptor_masks, {'O_ACCMODE', 'O_RDONLY', 'O_CLOEXEC'})
    for value in descriptor_masks.values(): integer(value, 0, (1 << 32) - 1)
    need(descriptor_masks['O_CLOEXEC'] != 0 and descriptor_masks['O_ACCMODE'] != 0, 'descriptor-mask-profile')
    need(isinstance(observation['fd_objects'], list) and len(observation['fd_objects']) == 6, 'observed-fd-count')
    expected_hashes = list(base()['CODE'].values()) + [base()['JAR_SHA']]
    for emitted, actual, expected_hash in zip(ready['fds'], observation['fd_objects'], expected_hashes):
        exact(actual, {'role', 'fd', 'dev', 'ino', 'size', 'mode', 'sha256', 'fdinfo_flags'})
        integer(actual['fd'], 3, 1048576); integer(actual['mode'], 0, (1 << 32) - 1)
        for key in ('dev', 'ino', 'size'): decimal(actual[key])
        for key in ('role', 'fd', 'dev', 'ino', 'size', 'mode'):
            need(actual[key] == emitted[key], 'observed-held-fd-object-mismatch')
        need(actual['sha256'] == expected_hash, 'observed-held-fd-hash')
        flags = actual['fdinfo_flags']
        need(isinstance(flags, str) and re.fullmatch(r'[0-7]{1,12}', flags) is not None, 'observed-fdinfo-flags')
        bits = int(flags, 8)
        need(bits & descriptor_masks['O_ACCMODE'] == descriptor_masks['O_RDONLY']
             and bits & descriptor_masks['O_CLOEXEC'] != 0, 'observed-descriptor-access-or-cloexec')
    return {'childPid': child['pid'], 'childStarttime': child['starttime'], 'supervisorPid': parent['pid'],
            'supervisorStarttime': parent['starttime'], 'bootId': observation['boot_id'], 'namespaces': dict(ready['ns']),
            'heldFdObjectsMatched': True, 'loadedCodeAttested': False, 'postExecDomainAttested': False}

def serialized_mutation(method):
    """One actor thread; external checkpoint callbacks cannot mutate/reenter."""
    @functools.wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            if threading.get_ident() != self._thread:
                self.failures.add('foreign-session-thread'); self._revision += 1
                raise Refusal('foreign-session-thread')
            if self._checkpoint_active:
                self.failures.add('checkpoint-reentry'); self._revision += 1
                raise Refusal('checkpoint-reentry')
            self._revision += 1
            try:
                return method(self, *args, **kwargs)
            except Refusal:
                self.failures.add('session-operation-refused')
                raise
    return call

def serialized_snapshot(method):
    @functools.wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            need(threading.get_ident() == self._thread, 'foreign-session-snapshot-thread')
            return method(self, *args, **kwargs)
    return call

class ProtocolSession:
    """Offline control/state helper, not a runtime owner or authority lease.

    Artifact/channel/process authenticity and actual root observations remain
    externally owned. No metadata dictionary enables live execution here.
    """
    def __init__(self, profile_sha256):
        need(isinstance(profile_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', profile_sha256) is not None, 'session-profile-shape')
        self.profile = profile_sha256; self.ready = None; self.pid = None
        self.wire_bytes = 0; self.raw_bytes = 0; self.stdout_bytes = 0; self.stderr_bytes = 0; self.seq = 0
        self.unapproved_stdout = 0; self.buffer = bytearray(); self.probe = None
        self.failures = set(); self.admitted = False; self.permit_attempted = False; self.permit_written = False
        self.cancel_attempted = False; self.native_permit = False; self.native_exec = False
        self.reaped = None; self.ownership_lost = False; self.events_seen = []
        self.native_partial = bytearray(); self.observation = None
        self.channel_eof = False; self.transport_stderr_bytes = 0
        self._lock = threading.RLock(); self._thread = threading.get_ident()
        self._revision = 0; self._checkpoint_active = False

    @serialized_mutation
    def feed_bytes(self, data):
        try:
            need(not self.channel_eof, 'native-data-after-eof')
            need(isinstance(data, bytes), 'native-bytes-type')
            need(self.wire_bytes + len(self.native_partial) + self.transport_stderr_bytes + len(data) <= WIRE_MAX, 'native-wire-cap')
            self.native_partial.extend(data)
            while b'\n' in self.native_partial:
                end = self.native_partial.index(10) + 1
                line = bytes(self.native_partial[:end]); del self.native_partial[:end]
                self.feed_line(line)
            need(len(self.native_partial) < LINE_MAX, 'partial-native-line-cap')
        except Refusal as failure:
            self.failures.add(str(failure)); raise

    @serialized_mutation
    def note_transport_stderr(self, data):
        need(isinstance(data, bytes), 'transport-stderr-type')
        self.transport_stderr_bytes += len(data)
        if data: self.failures.add('unframed-supervisor-stderr')
        if self.transport_stderr_bytes + self.wire_bytes + len(self.native_partial) > WIRE_MAX:
            self.failures.add('native-wire-cap'); raise Refusal('native-wire-cap')

    @serialized_mutation
    def finish_input(self):
        need(not self.channel_eof, 'duplicate-native-eof')
        self.channel_eof = True
        if self.native_partial: self.failures.add('incomplete-native-frame')
        if self.buffer:
            self.unapproved_stdout += len(self.buffer); self.buffer.clear()
            self.failures.add('unapproved-partial-child-stdout')
        if self.reaped is None: self.failures.add('missing-native-reaped')

    @serialized_mutation
    def admit_ready(self, observation):
        # Intentionally unconditional, including after real artifact pins exist.
        # A plain dict is not the unimplemented genuine root-observer issuer.
        raise Refusal('root-observer-issuer-unimplemented')

    @serialized_mutation
    def _model_admit_after_predicate(self, details):
        """Explicit AUTHORED MODEL transition; never selected root admission."""
        need(self.ready is not None and not self.admitted and not self.failures
             and not self.raw_bytes and not self.native_partial, 'ready-observation-state')
        need(isinstance(details, dict) and details.get('modelOnly') is True, 'authored-model-details-required')
        self.observation = copy.deepcopy(details); self.admitted = True

    @serialized_mutation
    def feed_line(self, line):
        try:
            need(isinstance(line, bytes), 'native-bytes-type')
            self.wire_bytes += len(line)
            need(not self.channel_eof, 'native-data-after-eof')
            need(self.wire_bytes + self.transport_stderr_bytes <= WIRE_MAX, 'native-wire-cap')
            event = parse_event(line); self._event(event)
        except Refusal as failure:
            self.failures.add(str(failure))
            raise

    def _pid(self, event):
        if 'pid' in event:
            if self.pid is None: self.pid = event['pid']
            need(self.pid == event['pid'], 'native-child-pid-changed')

    def _event(self, event):
        name = event['event']; need(self.reaped is None, 'event-after-terminal-reap')
        self._pid(event); self.events_seen.append(name)
        if name == 'READY':
            need(self.ready is None and not self.permit_attempted and not self.cancel_attempted,
                 'duplicate-or-late-ready')
            need(event['profile_sha256'] == self.profile, 'native-profile-mismatch')
            self.ready = event
        elif name == 'OUTPUT':
            need(event['seq'] == self.seq + 1, 'native-output-sequence'); self.seq = event['seq']
            data = bytes.fromhex(event['hex']); self.raw_bytes += len(data)
            need(self.raw_bytes <= RAW_MAX, 'native-child-output-cap')
            if not self.permit_attempted:
                self.failures.add('pre-permit-child-output')
            if event['stream'] == 'stderr':
                self.stderr_bytes += len(data); self.failures.add('child-stderr-observed')
            else:
                self.stdout_bytes += len(data); self._stdout(data)
        elif name == 'PERMIT_ATTEMPTED':
            need(not self.native_permit, 'duplicate-native-permit')
            if not self.permit_attempted or self.ready is None:
                self.failures.add('unexpected-native-permit')
            self.native_permit = True
        elif name == 'EXEC_ATTEMPTED':
            need(not self.native_exec, 'duplicate-native-exec-attempt')
            if not self.native_permit: self.failures.add('unexpected-native-exec-attempt')
            self.native_exec = True
        elif name == 'EXEC_ERROR':
            need(self.native_exec, 'exec-error-without-attempt'); self.failures.add('native-exec-error')
        elif name == 'EXEC_PIPE_CLOSED':
            pass  # Also legal before READY/exec. Never an exec-success signal.
        elif name in ('SIGNAL', 'FAIL', 'HOLD'):
            self.failures.add('native-' + name.lower())
            if name == 'HOLD' and event['reason'] == 'OWNERSHIP_LOST': self.ownership_lost = True
        elif name == 'REAPED':
            if self.ownership_lost: self.failures.add('terminal-after-lost-ownership')
            if event['permit_attempted'] != self.native_permit or event['exec_attempt_observed'] != self.native_exec:
                self.failures.add('terminal-history-mismatch')
            if self.ready is None:
                if event['permit_attempted'] or event['exec_attempt_observed']: self.failures.add('no-ready-terminal-exec')
            self.reaped = {key: event[key] for key in SCHEMAS['REAPED']}

    def _stdout(self, data):
        # Only bounded authored JSON is retained; unapproved bytes/hex are not.
        for byte in data:
            self.buffer.append(byte)
            if len(self.buffer) > 2049:
                self.unapproved_stdout += len(self.buffer); self.buffer.clear()
                self.failures.add('child-stdout-line-cap'); continue
            if byte == 10:
                line = bytes(self.buffer[:-1]); self.buffer.clear()
                try:
                    need(self.probe is None and self.ready is not None, 'duplicate-or-early-probe')
                    text = line.decode('ascii')
                    self.probe = base()['parse_probe'](text, {'identity': {'pid': self.pid}})
                except (ValueError, UnicodeError, RecursionError):
                    self.unapproved_stdout += len(line) + 1; self.failures.add('unapproved-child-stdout')

    def _checkpoint(self, checkpoint):
        before = self._revision; snapshot = self.summary(); self._checkpoint_active = True
        self._lock.release()  # Never hold the actor lock across external work.
        try:
            checkpoint(snapshot)
        except BaseException:
            with self._lock: self.failures.add('checkpoint-failed')
            raise
        finally:
            self._lock.acquire()
            self._checkpoint_active = False
        need(self._revision == before, 'checkpoint-reentry-state-change')

    @serialized_mutation
    def prepare_permit(self, checkpoint):
        raise Refusal('root-observer-issuer-unimplemented')

    @serialized_mutation
    def _model_prepare_permit(self, checkpoint):
        """AUTHORED MODEL control bytes; not callable live issuer admission."""
        need(self.admitted and self.ready is not None and not self.failures and not self.buffer and not self.native_partial
             and self.raw_bytes == 0 and not self.permit_attempted and not self.cancel_attempted and self.reaped is None,
             'permit-state-not-admitted')
        self.permit_attempted = True
        self._checkpoint(checkpoint)  # Durable caller checkpoint BEFORE possible send.
        need(self.admitted and not self.failures and not self.buffer and not self.native_partial
             and not self.cancel_attempted and self.reaped is None and not self.channel_eof, 'permit-post-checkpoint-drift')
        return ('PERMIT ' + self.ready['nonce'] + '\n').encode('ascii')

    @serialized_mutation
    def note_permit_written(self):
        raise Refusal('root-observer-transport-unimplemented')

    @serialized_mutation
    def _model_note_permit_written(self):
        need(self.permit_attempted and not self.permit_written, 'permit-write-state')
        self.permit_written = True

    @serialized_mutation
    def prepare_cancel(self, checkpoint):
        raise Refusal('root-observer-transport-unimplemented')

    @serialized_mutation
    def _model_prepare_cancel(self, checkpoint):
        need(not self.cancel_attempted and self.reaped is None, 'cancel-state')
        self.cancel_attempted = True; self.failures.add('local-cancel-attempted')
        self._checkpoint(checkpoint)
        need(self.reaped is None and not self.channel_eof, 'cancel-post-checkpoint-drift')
        return b'CANCEL\n'

    @serialized_snapshot
    def summary(self):
        terminal = self.reaped is not None
        observed = bool(not self.cancel_attempted and self.channel_eof and terminal and self.probe and self.probe['status'] == 'CONTEXT_OBSERVED_ONLY'
                        and not self.failures and not self.buffer and not self.native_partial and self.stderr_bytes == 0
                        and self.reaped['kind'] == 'exit' and self.reaped['status'] == 0
                        and self.reaped['stdout_complete'] and self.reaped['stderr_complete']
                        and not self.reaped['cancelled'] and self.native_permit and self.native_exec)
        return copy.deepcopy({'profile': PROFILE_NAME, 'authorityReady': False, 'liveExecutionSelected': False,
                'rootObserverIssuerImplemented': False, 'reapRecordAuthenticated': False,
                'authoredModelAdmission': bool(self.observation and self.observation.get('modelOnly') is True),
                'nativeReaped': terminal, 'reap': self.reaped, 'contextObservedOnly': observed,
                'permitSendAttempted': self.permit_attempted, 'permitWriteCompleted': self.permit_written,
                'cancelSendAttempted': self.cancel_attempted, 'nativePermitAttempted': self.native_permit,
                'nativeExecAttempted': self.native_exec, 'wireBytes': self.wire_bytes, 'rawChildBytes': self.raw_bytes,
                'nativeChannelEof': self.channel_eof, 'transportStderrBytes': self.transport_stderr_bytes,
                'stdoutBytes': self.stdout_bytes, 'stderrBytes': self.stderr_bytes,
                'unapprovedStdoutBytes': self.unapproved_stdout, 'partialStdoutBytes': len(self.buffer),
                'partialNativeFrameBytes': len(self.native_partial), 'readyObservation': self.observation,
                'failureReasons': sorted(self.failures), 'probe': self.probe,
                'cleanupHold': not self.channel_eof or not terminal or bool(self.buffer) or bool(self.native_partial) or bool(self.failures)
                               or not self.reaped['stdout_complete'] or not self.reaped['stderr_complete'],
                'stageCleanupAuthorized': False, 'noncePersisted': False, 'rawOutputPersisted': False})

def plan():
    try:
        artifact = native_inputs(); status = 'OFFLINE_NATIVE_CONTRACT_PINNED'
    except Refusal as failure:
        artifact = None; status = str(failure)
    return {'status': status, 'protocol': 1, 'liveExecutionSelected': False,
            'profile': PROFILE_NAME, 'supervisorPath': SUPERVISOR, 'supervisorArgv': [SUPERVISOR, CLI],
            'supervisorRunsAsRoot': True, 'childUidGid': 1000, 'numericSuChildLauncher': False,
            'artifact': artifact, 'nativeProfileSha256': NATIVE_PROFILE_SHA256,
            'control': ['PERMIT <32-lowercase-hex>\\n', 'CANCEL\\n'], 'pcNumericSignals': False,
            'futureRootRequirements': ['actual native parent/source/profile/channel admission',
                                       'fresh same-child proc4/caps/namespace and held FD-object hashes',
                                       'complete buffered-output/stream state before permit',
                                       'explicit user approval and root-composed staging/transport/cleanup review'],
            'authorityReady': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.run:
        print(json.dumps({'status': 'HOLD_ROOT_COMPOSITION_UNSELECTED', 'liveExecutionSelected': False, 'phoneCalls': 0}))
        return 2
    print(json.dumps(plan(), indent=2))

if __name__ == '__main__':
    sys.exit(main() or 0)
