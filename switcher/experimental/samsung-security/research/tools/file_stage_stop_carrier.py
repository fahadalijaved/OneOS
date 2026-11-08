"""Compare decoded before/after Stop carrier evidence without opening any files.

The caller binds raw references to the complete relevant descriptor lifecycle
and sampled kernel records, and admits the attempt and publication receipt.
The comparison cannot authenticate claims supplied in place of those records.
"""

import json
import re

from check_file_stage_device_preflight import STAGE, require
from run_guest_tree_install_transport import selected_source_receipt


_SOURCE = json.loads(selected_source_receipt())
_CARRIER_BYTES = _SOURCE['imageBytes']
_VERITY_DIGEST = _SOURCE['fsVerityDigest']
_U64 = 2**64 - 1
_U32 = 2**32 - 1
_I32 = 2**31 - 1
_O_PATH_OR_ACCESS_MODE = 0o10000000 | 0o3
_MOUNT = ('mountId', 'deviceMajor', 'deviceMinor')
_NAMESPACE = ('deviceMajor', 'deviceMinor', 'inode')
_SAMPLES = ('namedBefore', 'heldBefore', 'namedAfter', 'heldAfter')
_WINDOW = ('bootId', 'hostMountNamespace', 'ownerBirth', 'startElapsedMs', 'endElapsedMs',
           'dataMount', 'stage', 'carrier', 'measurement', 'rawRef')
_PUBLICATION = (*_MOUNT, 'inode', 'bytes', 'mtimeSec', 'mtimeNs', 'ctimeSec', 'ctimeNs')


def _record(value, fields, label):
    require(type(value) is dict and value.keys() == set(fields), f'Invalid {label} fields')
    return value


def _integer(value, lower, upper, label):
    require(type(value) is int and lower <= value <= upper, f'Invalid {label}')
    return value


def _elapsed(value):
    return _integer(value, 0, _U64, 'elapsed milliseconds')


def _raw_ref(value):
    row = _record(value, ('savedRelativePath', 'sha256', 'recordLocator'), 'raw reference')
    path, digest, locator = (row[key] for key in ('savedRelativePath', 'sha256', 'recordLocator'))
    require(type(path) is str and len(path) <= 512 and re.fullmatch(r'[A-Za-z0-9_./-]+', path)
            and not set(path.split('/')) & {'', '.', '..'} and type(digest) is str
            and re.fullmatch(r'[0-9a-f]{64}', digest) and type(locator) is str
            and re.fullmatch(r'(?:line:[1-9][0-9]{0,19}|record:[A-Za-z0-9_.-]{1,96})', locator),
            'Invalid raw reference')


def _device(row):
    return tuple(_integer(row[key], 0, _U32, key) for key in _MOUNT[1:])


def _mount(row):
    return _integer(row['mountId'], 1, _U64, 'mount ID'), *_device(row)


def _namespace(value):
    row = _record(value, _NAMESPACE, 'namespace')
    _device(row)
    _integer(row['inode'], 1, _U64, 'namespace inode')


def _owner_birth(value, *, global_pid_view):
    row = _record(value, ('pid', 'startTicks', 'pidNamespace'), 'descriptor owner birth')
    _integer(row['pid'], 1, _I32, 'descriptor owner PID')
    _integer(row['startTicks'], 1, _U64, 'descriptor owner start ticks')
    if global_pid_view:
        require(row['pidNamespace'] is None, 'Global PID view cannot supply a PID namespace inode')
    else:
        _namespace(row['pidNamespace'])


def _node(value, mount, mode):
    row = _record(value, (*_MOUNT, 'inode', 'typeAndMode', 'uid', 'gid'), 'statx node')
    require(_mount(row) == mount, 'Node is outside the physical /data mount')
    _integer(row['inode'], 1, _U64, 'node inode')
    for key, expected in (('typeAndMode', mode), ('uid', 0), ('gid', 0)):
        _integer(row[key], expected, expected, key)


def _carrier_node(value, mount):
    row = _record(value, ('node', 'links', 'sizeBytes', 'mtimeSec', 'mtimeNsec', 'ctimeSec', 'ctimeNsec'),
                  'carrier statx node')
    _node(row['node'], mount, 0o100600)
    _integer(row['links'], 1, 1, 'carrier link count')
    _integer(row['sizeBytes'], _CARRIER_BYTES, _CARRIER_BYTES, 'carrier size')
    for kind in ('mtime', 'ctime'):
        _integer(row[kind + 'Sec'], -(2**63), 2**63 - 1, kind + ' seconds')
        _integer(row[kind + 'Nsec'], 0, 999_999_999, kind + ' nanoseconds')


def _same_holder(row, opened):
    _integer(row['fd'], opened['fd'], opened['fd'], 'held descriptor')
    _integer(row['openSequence'], opened['sequence'], opened['sequence'], 'descriptor open generation')


def _object_samples(value, path, mount, opened, *, carrier=False):
    row = _record(value, ('path', 'fd', 'openSequence', 'statusFlags', *_SAMPLES), 'named and held samples')
    require(type(row['path']) is str and row['path'] == path, 'Unexpected named object path')
    _same_holder(row, opened)
    flags = _integer(row['statusFlags'], 0, _I32, 'held F_GETFL result')
    require(flags & _O_PATH_OR_ACCESS_MODE == 0, 'Descriptor is not read-only and usable for measurement')
    first = row[_SAMPLES[0]]
    for key in _SAMPLES:
        if carrier:
            _carrier_node(row[key], mount)
        else:
            _node(row[key], mount, 0o40700)
        require(row[key] == first, 'Named or held object changed across the measurement')
    return first


def _open_events(value, *, global_pid_view):
    row = _record(value, ('ownerBirth', 'throughElapsedMs', 'events', 'rawRef'), 'descriptor continuity')
    _owner_birth(row['ownerBirth'], global_pid_view=global_pid_view)
    _raw_ref(row['rawRef'])
    events = row['events']
    require(type(events) is list and len(events) == 2, 'Expected only the two retained opens and no replacement')
    for event, role in zip(events, ('stage', 'carrier')):
        _record(event, ('operation', 'role', 'fd', 'sequence', 'elapsedMs'), 'descriptor open event')
        require(event['operation'] == 'open' and event['role'] == role, 'Unexpected descriptor lifecycle event')
        _integer(event['fd'], 3, _I32, 'descriptor number')
        _integer(event['sequence'], 1, _U64, 'descriptor open generation')
        _elapsed(event['elapsedMs'])
    stage, carrier = events
    require(stage['fd'] != carrier['fd'] and stage['sequence'] < carrier['sequence']
            and stage['elapsedMs'] <= carrier['elapsedMs'], 'Descriptor opens alias or are out of order')
    return stage, carrier


def _measurement(value, opened, start, end):
    row = _record(value, ('operation', 'fd', 'openSequence', 'elapsedMs', 'status', 'algorithm',
                          'digestBytes', 'digestHex', 'rawRef'), 'fs-verity measurement')
    _same_holder(row, opened)
    require(start <= _elapsed(row['elapsedMs']) <= end and row['operation'] == 'FS_IOC_MEASURE_VERITY',
            'Missing in-window kernel fs-verity measurement')
    for key, expected in (('status', 0), ('algorithm', 1), ('digestBytes', 32)):
        _integer(row[key], expected, expected, 'fs-verity ' + key)
    require(type(row['digestHex']) is str and row['digestHex'] == _VERITY_DIGEST, 'Unexpected kernel verity digest')
    _raw_ref(row['rawRef'])


def _window(row, context, continuity, opened, start, end, *, global_pid_view):
    _namespace(row['hostMountNamespace'])
    _owner_birth(row['ownerBirth'], global_pid_view=global_pid_view)
    require(type(row['bootId']) is str and row['bootId'] == context['bootId']
            and row['hostMountNamespace'] == context['hostMountNamespace']
            and row['ownerBirth'] == continuity['ownerBirth'], 'Measurement boot, namespace or descriptor owner changed')
    data_mount = _record(row['dataMount'], ('mountPoint', 'filesystemType', *_MOUNT), 'data mount')
    require(data_mount['mountPoint'] == '/data' and data_mount['filesystemType'] == 'f2fs',
            'Expected the physical host F2FS /data mount')
    mount = _mount(data_mount)
    stage = _object_samples(row['stage'], STAGE, mount, opened[0])
    carrier = _object_samples(row['carrier'], STAGE + '/guest.erofs', mount, opened[1], carrier=True)
    require(stage['inode'] != carrier['node']['inode'], 'Stage and carrier inode alias')
    _measurement(row['measurement'], opened[1], start, end)
    _raw_ref(row['rawRef'])
    return stage, carrier


def verify_stop_carrier(evidence, *, attempt, context):
    """Raise ValueError unless the two kernel windows join the admitted publication."""
    row = _record(evidence, ('attempt', 'before', 'after', 'continuity', 'publication'), 'carrier evidence')
    require(type(row['attempt']) is type(attempt) and row['attempt'] == attempt, 'Carrier attempt differs')
    require(type(context) is dict and {'bootId', 'hostMountNamespace', 'postStartElapsedMs', 'postEndElapsedMs'}
            <= context.keys(), 'Missing admitted process context')
    boot = context['bootId']
    require(type(boot) is str and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot),
            'Invalid admitted boot ID')
    _namespace(context['hostMountNamespace'])
    global_pid_view = context.get('globalPidView') is True
    opened = _open_events(row['continuity'], global_pid_view=global_pid_view)
    before = _record(row['before'], _WINDOW, 'pre-Stop window')
    after = _record(row['after'], _WINDOW, 'post-Stop window')
    pre_start, pre_end = (_elapsed(before[key]) for key in ('startElapsedMs', 'endElapsedMs'))
    post_start, post_end = (_elapsed(after[key]) for key in ('startElapsedMs', 'endElapsedMs'))
    lower, upper = (_elapsed(context[key]) for key in ('postStartElapsedMs', 'postEndElapsedMs'))
    through = _elapsed(row['continuity']['throughElapsedMs'])
    require(opened[1]['elapsedMs'] <= pre_start <= pre_end < lower <= post_start <= post_end <= through <= upper,
            'Descriptor lifetime or carrier windows fall outside the admitted Stop interval')
    pre = _window(before, context, row['continuity'], opened, pre_start, pre_end, global_pid_view=global_pid_view)
    post = _window(after, context, row['continuity'], opened, post_start, post_end, global_pid_view=global_pid_view)
    require(pre == post and before['rawRef'] != after['rawRef']
            and before['measurement']['rawRef'] != after['measurement']['rawRef'],
            'Before and after carrier observations are not distinct samples of the same objects')
    carrier = pre[1]
    publication = _record(row['publication'], _PUBLICATION, 'V2 carrier publication')
    identity = {key: carrier['node'][key] for key in (*_MOUNT, 'inode')}
    identity.update(bytes=carrier['sizeBytes'], mtimeSec=carrier['mtimeSec'], mtimeNs=carrier['mtimeNsec'],
                    ctimeSec=carrier['ctimeSec'], ctimeNs=carrier['ctimeNsec'])
    require(all(type(value) is int for value in publication.values()) and publication == identity,
            'Measured carrier differs from the admitted V2 publication')
