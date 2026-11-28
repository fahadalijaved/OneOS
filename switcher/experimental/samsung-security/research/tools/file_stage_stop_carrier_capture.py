"""Decode the retained carrier observer's saved native frames without I/O.

The decoded windows contain no boot, namespace, reader, or attempt identity.
Those fields must come from independently admitted observations.
"""

import errno
import hashlib
import json
import re


_U64 = (1 << 64) - 1
_U32 = (1 << 32) - 1
_I32 = (1 << 31) - 1
_S64_MIN = -(1 << 63)
_S64_MAX = (1 << 63) - 1
_MAX_CAPTURE_BYTES = 64 * 1024
_MAX_LINE_BYTES = 8190
_STAGE_PATH = '/data/local/tmp/oneos-viewprep'
_CARRIER_PATH = _STAGE_PATH + '/guest.erofs'
_READER_SCHEMA = 'oneos-file-stage-stop-reader/v1'
_WINDOW_SCHEMA = 'oneos-file-stage-stop-window/v1'
_MOUNT = ('mountId', 'deviceMajor', 'deviceMinor')
_NODE = (*_MOUNT, 'inode', 'typeAndMode', 'uid', 'gid')
_SAMPLES = ('namedBefore', 'heldBefore', 'namedAfter', 'heldAfter')
_OBJECT = ('path', 'fd', 'statusFlags', *_SAMPLES)
_MEASUREMENT = ('operation', 'fd', 'elapsedMs', 'status', 'algorithm', 'digestBytes', 'digestHex')
_BACKING_NODES = ('data', 'stage', 'backing', 'dev', 'guard')
_BACKING_MARKERS = ('writerErrno', 'legacyErrno', 'viewErrno')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _record(value, fields, label):
    _require(type(value) is dict and value.keys() == set(fields), f'Invalid {label} fields')
    return value


def _integer(value, lower, upper, label):
    _require(type(value) is int and lower <= value <= upper, f'Invalid {label}')
    return value


def _elapsed(value):
    return _integer(value, 0, _U64, 'elapsed milliseconds')


def _mount(row):
    return (_integer(row['mountId'], 1, _U64, 'mount ID'),
            _integer(row['deviceMajor'], 0, _U32, 'device major'),
            _integer(row['deviceMinor'], 0, _U32, 'device minor'))


def _node(value):
    row = _record(value, _NODE, 'native statx node')
    _mount(row)
    _integer(row['inode'], 1, _U64, 'node inode')
    _integer(row['typeAndMode'], 0, 0xffff, 'node mode')
    _integer(row['uid'], 0, _U32, 'node uid')
    _integer(row['gid'], 0, _U32, 'node gid')
    return row


def _carrier_node(value):
    row = _record(value, ('node', 'links', 'sizeBytes', 'mtimeSec', 'mtimeNsec', 'ctimeSec', 'ctimeNsec'),
                  'native carrier statx node')
    node = _node(row['node'])
    _integer(row['links'], 1, 1, 'carrier link count')
    _integer(row['sizeBytes'], 1, _U64, 'carrier size')
    for kind in ('mtime', 'ctime'):
        _integer(row[kind + 'Sec'], _S64_MIN, _S64_MAX, kind + ' seconds')
        _integer(row[kind + 'Nsec'], 0, 999_999_999, kind + ' nanoseconds')
    return node


def _objects(value, opened, mount, *, carrier):
    row = _record(value, _OBJECT, 'native named and held samples')
    path = _CARRIER_PATH if carrier else _STAGE_PATH
    _require(row['path'] == path, 'Unexpected native object path')
    _integer(row['fd'], opened['fd'], opened['fd'], 'native held descriptor')
    flags = _integer(row['statusFlags'], 0, _I32, 'native F_GETFL result')
    _require(flags & (0o10000000 | 0o3) == 0, 'Native descriptor is not read-only')
    first = row['namedBefore']
    for key in _SAMPLES:
        sample = row[key]
        node = _carrier_node(sample) if carrier else _node(sample)
        mode = 0o100600 if carrier else 0o40700
        _require(sample == first and _mount(node) == mount
                 and (node['typeAndMode'], node['uid'], node['gid']) == (mode, 0, 0),
                 'Native named or held object differs from its expected identity')
    return row | {'openSequence': opened['sequence']}


def _measurement(value, opened, start, end, reference):
    row = _record(value, _MEASUREMENT, 'native fs-verity measurement')
    _integer(row['fd'], opened['fd'], opened['fd'], 'native fs-verity descriptor')
    _integer(row['elapsedMs'], start, end, 'native fs-verity elapsed time')
    for key, expected in (('status', 0), ('algorithm', 1), ('digestBytes', 32)):
        _integer(row[key], expected, expected, 'native fs-verity ' + key)
    digest = row['digestHex']
    _require(row['operation'] == 'FS_IOC_MEASURE_VERITY' and type(digest) is str
             and re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'Invalid native fs-verity result')
    return row | {'openSequence': opened['sequence'], 'rawRef': reference.copy()}


def _backing(value, data, stage):
    row = _record(value, (*_BACKING_NODES, *_BACKING_MARKERS), 'physical release sample')
    for key in _BACKING_NODES:
        _node(row[key])
    for key in _BACKING_MARKERS:
        _integer(row[key], errno.ENOENT, errno.ENOENT, 'direct reservation lookup errno')
    _require(row['data'] == data and row['stage'] == stage, 'Release sample differs from held data or stage')
    backing, dev, guard = (row[key] for key in ('backing', 'dev', 'guard'))
    _require(_mount(backing) == _mount(data) and _mount(dev) == _mount(guard)
             and _mount(dev) != _mount(data) and len({data['inode'], stage['inode'], backing['inode']}) == 3
             and dev['inode'] != guard['inode']
             and (backing['typeAndMode'], backing['uid'], backing['gid']) == (0o40700, 0, 0)
             and (dev['typeAndMode'], dev['uid'], dev['gid']) == (0o40755, 0, 0)
             and (guard['typeAndMode'], guard['uid'], guard['gid']) == (0o40700, 0, 0),
             'Backing or guard is outside its physical directory profile')
    return row


def _window(value, phase, opened, reference):
    row = _record(value, ('schema', 'window', 'startElapsedMs', 'endElapsedMs', 'dataMount', 'dataHeld',
                          'stage', 'carrier', 'measurement', 'backing'), 'native descriptor window')
    _require(row['schema'] == _WINDOW_SCHEMA and row['window'] == phase, 'Unexpected native window version or order')
    start, end = (_elapsed(row[key]) for key in ('startElapsedMs', 'endElapsedMs'))
    _require(start <= end, 'Native window time regressed')
    data = _record(row['dataMount'], ('mountPoint', 'filesystemType', *_MOUNT), 'native data mount')
    _require(data['mountPoint'] == '/data' and data['filesystemType'] == 'f2fs',
             'Expected native host /data mount')
    mount = _mount(data)
    held_data = _node(row['dataHeld'])
    _require(_mount(held_data) == mount
             and (held_data['typeAndMode'], held_data['uid'], held_data['gid']) == (0o40771, 1000, 1000),
             'Held data differs from the native /data profile')
    stage = _objects(row['stage'], opened[0], mount, carrier=False)
    carrier = _objects(row['carrier'], opened[1], mount, carrier=True)
    _require(len({held_data['inode'], stage['namedBefore']['inode'], carrier['namedBefore']['node']['inode']}) == 3,
             'Native data, stage or carrier inode alias')
    measure = _measurement(row['measurement'], opened[1], start, end, reference)
    if phase == 'pre':
        _require(row['backing'] is None, 'Unexpected pre-Stop release sample')
    else:
        _backing(row['backing'], held_data, stage['namedBefore'])
    return {'startElapsedMs': start, 'endElapsedMs': end, 'dataMount': data, 'stage': stage, 'carrier': carrier,
            'measurement': measure, 'rawRef': reference.copy()}


def _unique_object(items):
    row = dict(items)
    _require(len(row) == len(items), 'Duplicate native JSON key')
    return row


def _reject_constant(value):
    raise ValueError(f'Invalid native JSON constant: {value}')


def _reader(value, event, fields):
    row = _record(value, ('schema', 'event', 'ownerPid', 'stageFd', 'carrierFd', *fields), 'native reader frame')
    _require(row['schema'] == _READER_SCHEMA and row['event'] == event, 'Unexpected native reader version or order')
    return (_integer(row['ownerPid'], 1, _I32, 'native reader PID'),
            _integer(row['stageFd'], 3, _I32, 'native stage descriptor'),
            _integer(row['carrierFd'], 3, _I32, 'native carrier descriptor'))


def decode_stop_carrier_capture(raw, *, saved_relative_path):
    """Return normalized windows and references into the original native capture.

    The caller supplies saved bytes and must independently establish their capture
    status and EOF. The two open sequences encode the order in the opener frame.
    """
    _require(type(saved_relative_path) is str and len(saved_relative_path) <= 512
             and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', saved_relative_path) is not None
             and not {'.', '..'}.intersection(saved_relative_path.split('/')), 'Invalid saved capture path')
    _require(type(raw) is bytes and 0 < len(raw) <= _MAX_CAPTURE_BYTES and raw.isascii()
             and b'\0' not in raw and b'\r' not in raw and raw.endswith(b'\n'), 'Invalid native capture framing')
    lines = raw[:-1].split(b'\n')
    _require(len(lines) == 4 and all(0 < len(line) <= _MAX_LINE_BYTES for line in lines),
             'Expected exactly four bounded native capture lines')
    try:
        opener, pre, post, closer = (json.loads(line, object_pairs_hook=_unique_object,
                                               parse_constant=_reject_constant) for line in lines)
    except RecursionError as exc:
        raise ValueError('Native capture JSON nesting exceeds bounds') from exc

    identity = _reader(opener, 'opened', ('stageOpenedElapsedMs', 'carrierOpenedElapsedMs'))
    _require(_reader(closer, 'closed', ('elapsedMs',)) == identity, 'Native reader or descriptor number changed')
    owner, stage_fd, carrier_fd = identity
    stage_open, carrier_open = (_elapsed(opener[key]) for key in ('stageOpenedElapsedMs', 'carrierOpenedElapsedMs'))
    closed = _elapsed(closer['elapsedMs'])
    _require(stage_fd != carrier_fd and stage_open <= carrier_open, 'Native descriptor opens alias or are out of order')
    events = [
        {'operation': 'open', 'role': 'stage', 'fd': stage_fd, 'sequence': 1, 'elapsedMs': stage_open},
        {'operation': 'open', 'role': 'carrier', 'fd': carrier_fd, 'sequence': 2, 'elapsedMs': carrier_open},
    ]
    digest = hashlib.sha256(raw).hexdigest()

    def ref(line):
        return {'savedRelativePath': saved_relative_path, 'sha256': digest, 'recordLocator': f'line:{line}'}

    before = _window(pre, 'pre', events, ref(2))
    after = _window(post, 'post', events, ref(3))
    _require(carrier_open <= before['startElapsedMs'] <= before['endElapsedMs']
             < after['startElapsedMs'] <= after['endElapsedMs'] <= closed, 'Native carrier windows overlap or regress')
    _require(pre['dataHeld'] == post['dataHeld'] and before['dataMount'] == after['dataMount']
             and all(before[role] == after[role] for role in ('stage', 'carrier'))
             and before['measurement']['digestHex'] == after['measurement']['digestHex'],
             'Native windows do not retain the same physical data, stage and carrier')
    return {
        'ownerPid': owner,
        'before': before,
        'after': after,
        'continuity': {'events': events, 'throughElapsedMs': after['endElapsedMs'], 'rawRef': ref(1)},
        'closed': {'ownerPid': owner, 'stageFd': stage_fd, 'carrierFd': carrier_fd, 'elapsedMs': closed, 'rawRef': ref(4)},
        'physicalRelease': {'sample': post['backing'], 'rawRef': ref(3)},
        'rawWindows': {'before': pre, 'after': post},
    }
