"""Decode one saved mixed native Stop capture without granting device credit."""

import errno
import hashlib
import json
import re

from file_stage_stop_carrier_capture import decode_stop_carrier_capture


_MAX_BYTES = 128 * 1024
_MAX_LINE_BYTES = 16 * 1024
_I32 = (1 << 31) - 1
_I64 = (1 << 63) - 1
_U32 = (1 << 32) - 1
_U64 = (1 << 64) - 1
_RELATIVE_PATH = re.compile(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+')
_BOOT_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
_SELINUX = re.compile(r'[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+:s[0-9][s0-9c,.:\-]{0,80}')
_IDENTITY_SCHEMA = 'oneos-file-stage-stop-identity/v2'
_PROCESS_SCHEMA = 'oneos-file-stage-stop-process/v2'
_ROLES = ('controller', 'child')
_DEVICE = ('deviceMajor', 'deviceMinor')
_IDS = ('uid', 'euid', 'fsuid', 'gid', 'egid', 'fsgid')
_POLL_COUNTS = ('pollBeforeCount', 'pollAfterCount')
_POLL_REVENTS = ('pollBeforeRevents', 'pollAfterRevents')
_POLLIN = 1
_POLLHUP = 16


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _record(value, fields, label):
    _require(type(value) is dict and value.keys() == set(fields), f'Invalid {label} fields')
    return value


def _integer(value, lower, upper, label):
    _require(type(value) is int and lower <= value <= upper, f'Invalid {label}')
    return value


def _unique_object(items):
    row = dict(items)
    _require(len(row) == len(items), 'Duplicate native session JSON key')
    return row


def _reject_constant(value):
    raise ValueError(f'Invalid native session JSON constant: {value}')


def _line_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except RecursionError as exc:
        raise ValueError('Native session JSON nesting exceeds bounds') from exc


def _lines(raw, path, expected_count):
    _require(type(path) is str and len(path) <= 512 and _RELATIVE_PATH.fullmatch(path) is not None
             and not {'.', '..'}.intersection(path.split('/')), 'Invalid saved session path')
    _require(type(raw) is bytes and 0 < len(raw) <= _MAX_BYTES and raw.isascii() and b'\0' not in raw
             and b'\r' not in raw and raw.endswith(b'\n'), 'Invalid native session framing')
    lines = raw[:-1].split(b'\n')
    _require(len(lines) == expected_count and all(0 < len(line) <= _MAX_LINE_BYTES for line in lines),
             'Unexpected native session line count or size')
    return lines


def _references(raw, path):
    digest = hashlib.sha256(raw).hexdigest()

    def at(index):
        return {'savedRelativePath': path, 'sha256': digest, 'recordLocator': f'line:{index + 1}'}

    return at


def _carrier(lines, indexes, path, reference):
    """Validate original carrier lines and replace projected references with session references."""
    opened, before, after, closed = indexes
    projected = b''.join(lines[index] + b'\n' for index in indexes)
    capture = decode_stop_carrier_capture(projected, saved_relative_path=path)
    for name, index in (('before', before), ('after', after)):
        capture[name]['rawRef'] = reference(index)
        capture[name]['measurement']['rawRef'] = reference(index)
    capture['continuity']['rawRef'] = reference(opened)
    capture['closed']['rawRef'] = reference(closed)
    capture['physicalRelease']['rawRef'] = reference(after)
    return capture


def _elapsed(value):
    return _integer(value, 0, _I64, 'native elapsed milliseconds')


def _pid(value):
    return _integer(value, 1, _I32, 'native PID')


def _device(row):
    for key in _DEVICE:
        _integer(row[key], 0, _U32, key)


def _namespace(value, label):
    row = _record(value, (*_DEVICE, 'inode'), label)
    _device(row)
    _integer(row['inode'], 1, _U64, f'{label} inode')


def _identity(raw, phase, reference):
    row = _record(_line_json(raw), ('schema', 'phase', 'elapsedMs', 'bootId', 'mountNamespace', 'timeNamespace',
                                   'procRoot', 'reader'), 'native identity')
    _require(row['schema'] == _IDENTITY_SCHEMA and row['phase'] == phase, 'Unexpected identity version or phase')
    boot_id = row['bootId']
    _require(type(boot_id) is str and _BOOT_ID.fullmatch(boot_id) is not None
             and boot_id != '00000000-0000-0000-0000-000000000000', 'Invalid native boot ID')
    _elapsed(row['elapsedMs'])
    _namespace(row['mountNamespace'], 'native mount namespace')
    _namespace(row['timeNamespace'], 'native time namespace')
    proc = _record(row['procRoot'], ('mountId', *_DEVICE, 'inode'), 'native proc root')
    _device(proc)
    _integer(proc['mountId'], 1, _U64, 'proc mount ID')
    _integer(proc['inode'], 1, 1, 'proc root inode')
    reader = _record(row['reader'], ('pid', 'startTicks', *_IDS, 'groups', 'selinuxContext'), 'native reader identity')
    _pid(reader['pid'])
    _integer(reader['startTicks'], 1, _U64, 'reader start ticks')
    for key in _IDS:
        _integer(reader[key], 0, _U32, f'reader {key}')
    groups = reader['groups']
    _require(type(groups) is list and len(groups) <= 128, 'Invalid native supplementary group list')
    group_ids = {_integer(value, 0, _U32, 'reader supplementary group') for value in groups}
    domain = reader['selinuxContext']
    _require(len(group_ids) == len(groups) and type(domain) is str and len(domain) <= 192
             and _SELINUX.fullmatch(domain) is not None, 'Invalid native reader groups or SELinux context')
    return row | {'rawRef': reference}


def _process(raw, phase, role, reference, prior=None):
    row = _record(_line_json(raw), ('schema', 'phase', 'role', 'pid', 'startTicks', 'errno',
                                   'lookupStartedElapsedMs', 'sampleElapsedMs', 'pidfd', *_POLL_COUNTS,
                                   *_POLL_REVENTS), 'native process')
    _require((row['schema'], row['phase'], row['role']) == (_PROCESS_SCHEMA, phase, role),
             'Unexpected process version, phase or role')
    pid = _pid(row['pid'])
    started = _elapsed(row['lookupStartedElapsedMs'])
    sampled = _elapsed(row['sampleElapsedMs'])
    _require(started <= sampled, 'Native process lookup time regressed')
    pidfd = _integer(row['pidfd'], 3, _I32, 'native pidfd')
    count = 0 if prior is None else 1
    for key in _POLL_COUNTS:
        _integer(row[key], count, count, key)
    allowed = (0,) if prior is None else (_POLLIN, _POLLIN | _POLLHUP)
    for key in _POLL_REVENTS:
        _require(type(row[key]) is int and row[key] in allowed, f'Invalid native {key}')
    sample = {key: row[key] for key in ('pidfd', *_POLL_COUNTS, *_POLL_REVENTS)}
    sample.update(lookupStartedElapsedMs=started, sampleElapsedMs=sampled, rawRef=reference)
    if prior is None:
        _integer(row['errno'], 0, 0, 'native live lookup errno')
        ticks = _integer(row['startTicks'], 1, _U64, 'native process start ticks')
        return sample | {'birth': {'pid': pid, 'startTicks': ticks, 'pidNamespace': None}}
    _require(pid == prior['birth']['pid'] and pidfd == prior['pidfd'], 'Native probe PID or pidfd differs from prior birth')
    _integer(row['startTicks'], 0, 0, 'absent process start ticks')
    _integer(row['errno'], errno.ENOENT, errno.ENOENT, 'native direct absence errno')
    return sample | {'pid': pid, 'lookup': 'proc_pid_nofollow', 'errno': row['errno'], 'priorBirthRef': prior['rawRef']}


def _process_pair(lines, indexes, phase, reference, prior=None):
    return {role: _process(lines[index], phase, role, reference(index), None if prior is None else prior[role])
            for role, index in zip(_ROLES, indexes)}


def _process_times(pair):
    return tuple(pair[role][key] for role in _ROLES for key in ('lookupStartedElapsedMs', 'sampleElapsedMs'))


def _check_order(carrier, identity, pre, post_start, post_end):
    before = carrier['before']
    after = carrier['after']
    opened = [event['elapsedMs'] for event in carrier['continuity']['events']]
    close_elapsed = carrier['closed']['elapsedMs']
    pre_times, start_times, end_times = map(_process_times, (pre, post_start, post_end))
    clock = (identity['before']['elapsedMs'], *opened, before['startElapsedMs'], before['endElapsedMs'],
             *pre_times, *start_times, after['startElapsedMs'], after['endElapsedMs'], *end_times,
             identity['after']['elapsedMs'], close_elapsed)
    _require(all(_elapsed(a) <= _elapsed(b) for a, b in zip(clock, clock[1:]))
             and pre_times[-1] < start_times[0] and start_times[-1] < end_times[1],
             'Native process and carrier records do not form ordered Stop windows')


def decode_stop_session_capture(raw, *, saved_relative_path):
    """Return native identity, process, and carrier observations with original line references.

    The output supplies sampled values only. Capture status and EOF, actual process
    and mount visibility, attempt ownership, and UI bounds belong to the caller.
    """
    lines = _lines(raw, saved_relative_path, 12)
    reference = _references(raw, saved_relative_path)
    identity = {'before': _identity(lines[0], 'pre', reference(0)),
                'after': _identity(lines[10], 'post', reference(10))}
    _require(all(identity['before'][key] == identity['after'][key]
                 for key in ('bootId', 'mountNamespace', 'timeNamespace', 'procRoot', 'reader')),
             'Native reader identity changed')
    carrier = _carrier(lines, (1, 2, 7, 11), saved_relative_path, reference)
    owner = identity['before']['reader']['pid']
    _require(carrier['ownerPid'] == owner, 'Native carrier and process reader PIDs differ')
    pre = _process_pair(lines, (3, 4), 'pre', reference)
    _require(len({owner, *(pre[role]['birth']['pid'] for role in _ROLES)}) == 3, 'Native process roles alias a PID')
    fds = [event['fd'] for event in carrier['continuity']['events']]
    _require(len({*fds, *(pre[role]['pidfd'] for role in _ROLES)}) == 4, 'Native process and carrier descriptor cells alias')
    start = _process_pair(lines, (5, 6), 'post-start', reference, pre)
    end = _process_pair(lines, (8, 9), 'post-end', reference, pre)
    _check_order(carrier, identity, pre, start, end)
    return {
        'carrier': carrier,
        'identity': identity,
        'processes': {
            'preStop': {'elapsedMs': pre['child']['sampleElapsedMs'], **pre},
            'postStart': {'elapsedMs': start['controller']['lookupStartedElapsedMs'], 'probes': start},
            'postEnd': {'elapsedMs': identity['after']['elapsedMs'], 'probes': end},
        },
    }
