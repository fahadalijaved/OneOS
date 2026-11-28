"""Compare normalized post-Stop process records against the exact prior births."""

import errno
import re


_ROLES = ('controller', 'child')
_INT64_MAX = 2**63 - 1
_UINT32_MAX = 2**32 - 1
_UINT64_MAX = 2**64 - 1
_SHA256 = re.compile(r'[0-9a-f]{64}')
_BOOT_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
_FINGERPRINT = re.compile(r'[a-zA-Z0-9_.:/-]{1,256}')
_RECORD_LOCATOR = re.compile(r'(?:line:[1-9][0-9]{0,9}|record:[a-zA-Z0-9_.-]{1,96})')
_RELATIVE_PATH = re.compile(r'[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)+')
_SELINUX = re.compile(r'[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+:s[0-9][s0-9c,.:\-]{0,80}')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _row(value, fields, label):
    _require(type(value) is dict and value.keys() == fields, f'Invalid {label} record')


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum, f'Invalid {label}')
    return value


def _matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def _raw_ref(value):
    _row(value, {'savedRelativePath', 'sha256', 'recordLocator'}, 'raw evidence reference')
    path, digest, locator = value['savedRelativePath'], value['sha256'], value['recordLocator']
    _require(type(path) is str and len(path) <= 512 and _matches(_RELATIVE_PATH, path)
             and not {'.', '..'}.intersection(path.split('/'))
             and _matches(_SHA256, digest) and _matches(_RECORD_LOCATOR, locator),
             'Invalid raw evidence path, digest or record locator')
    return digest, locator


def _device(value):
    return (_integer(value['deviceMajor'], 0, _UINT32_MAX, 'device major'),
            _integer(value['deviceMinor'], 0, _UINT32_MAX, 'device minor'))


def _namespace(value):
    _row(value, {'deviceMajor', 'deviceMinor', 'inode'}, 'namespace')
    _device(value)
    _integer(value['inode'], 1, _UINT64_MAX, 'namespace inode')
    return value.copy()


def _pid(value):
    return _integer(value, 1, 2**31 - 1, 'numeric PID')


def _birth(value, *, global_pid_view):
    _row(value, {'pid', 'startTicks', 'pidNamespace'}, 'process birth')
    _pid(value['pid'])
    _integer(value['startTicks'], 0, _UINT64_MAX, 'process start ticks')
    if global_pid_view:
        _require(value['pidNamespace'] is None, 'Global PID view cannot supply a PID namespace inode')
        return value.copy()
    return value | {'pidNamespace': _namespace(value['pidNamespace'])}


def _reader(value, *, global_pid_view):
    ids = {'uid', 'euid', 'fsuid', 'gid', 'egid', 'fsgid'}
    _row(value, ids | {'birth', 'groups', 'selinuxContext'}, 'proc reader')
    for key in ids:
        _integer(value[key], 0, _UINT32_MAX, f'proc reader {key}')
    groups = value['groups']
    _require(type(groups) is list and len(groups) <= 128, 'Invalid supplementary group list')
    group_ids = tuple(sorted(_integer(group, 0, _UINT32_MAX, 'supplementary group') for group in groups))
    _require(len(set(group_ids)) == len(group_ids) and type(value['selinuxContext']) is str
             and len(value['selinuxContext']) <= 192 and _matches(_SELINUX, value['selinuxContext']),
             'Invalid proc reader groups or SELinux context')
    return value | {'birth': _birth(value['birth'], global_pid_view=global_pid_view), 'groups': group_ids}


def _pid_view(value):
    if type(value) is dict and value.get('mode') == 'global-no-config-pid-ns':
        _row(value, {'mode', 'configRawRef'}, 'global PID view')
        _raw_ref(value['configRawRef'])
        return value | {'configRawRef': value['configRawRef'].copy()}, True
    return _namespace(value), False


def _proc_view(value):
    fields = {'mountId', 'deviceMajor', 'deviceMinor', 'rootInode', 'filesystemType', 'pidNamespace',
              'hidePid', 'bypassGid'}
    _row(value, fields | {'mountRawRef', 'visibilityRawRef'}, 'proc view')
    _require(value['filesystemType'] == 'proc', 'Lookup view is not procfs')
    _raw_ref(value['mountRawRef'])
    _raw_ref(value['visibilityRawRef'])
    _integer(value['hidePid'], 0, 2, 'proc hidepid mode')
    if value['bypassGid'] is not None:
        _integer(value['bypassGid'], 0, _UINT32_MAX, 'proc bypass gid')
    _integer(value['mountId'], 1, _UINT64_MAX, 'proc mount ID')
    _device(value)
    _integer(value['rootInode'], 1, _UINT64_MAX, 'proc root inode')
    pid_namespace, global_pid_view = _pid_view(value['pidNamespace'])
    return {key: value[key] for key in fields} | {'pidNamespace': pid_namespace}, global_pid_view


def _context(value):
    _row(value, {'bootId', 'buildFingerprint', 'hostMountNamespace', 'appBirth', 'systemServerBirth', 'procView', 'reader'},
         'process context')
    _require(_matches(_BOOT_ID, value['bootId']) and _matches(_FINGERPRINT, value['buildFingerprint']),
             'Invalid boot ID or build fingerprint')
    proc_view, global_pid_view = _proc_view(value['procView'])
    reader = _reader(value['reader'], global_pid_view=global_pid_view)
    bypass = proc_view['bypassGid']
    _require(proc_view['hidePid'] == 0 or bypass == reader['fsgid'] or bypass in reader['groups'],
             'Proc lookup can be masked for this reader')
    return value | {'hostMountNamespace': _namespace(value['hostMountNamespace']),
                    'appBirth': _birth(value['appBirth'], global_pid_view=global_pid_view),
                    'systemServerBirth': _birth(value['systemServerBirth'], global_pid_view=global_pid_view),
                    'procView': proc_view, 'reader': reader}, global_pid_view


def _time(value):
    return _integer(value, 0, _INT64_MAX, 'elapsedRealtime milliseconds')


def _post_boundary(value, context, births, used_refs):
    _row(value, {'elapsedMs', 'context', 'rawRef', 'probes'}, 'post-Stop boundary')
    _require(_context(value['context'])[0] == context, 'Process context differs from pre-Stop')
    _distinct_ref(value['rawRef'], used_refs)
    probes = value['probes']
    _row(probes, set(_ROLES), 'post-Stop process probes')
    times = []
    for role in _ROLES:
        probe = probes[role]
        _row(probe, {'pid', 'priorBirthRef', 'sampleElapsedMs', 'lookup', 'errno', 'rawRef'}, 'direct PID probe')
        _raw_ref(probe['priorBirthRef'])
        _require(_pid(probe['pid']) == births[role][0] and probe['priorBirthRef'] == births[role][1],
                 f'Probe does not name the prior {role} birth')
        _require(probe['lookup'] == 'proc_pid_nofollow' and type(probe['errno']) is int
                 and probe['errno'] == errno.ENOENT, f'Direct absence of {role} is unconfirmed')
        _distinct_ref(probe['rawRef'], used_refs)
        times.append(_time(probe['sampleElapsedMs']))
    return _time(value['elapsedMs']), times


def _distinct_ref(value, used_refs):
    identity = _raw_ref(value)
    _require(identity not in used_refs, 'Raw evidence record was reused')
    used_refs.add(identity)


def verify_stop_processes(evidence, *, attempt, terminal_elapsed_ms) -> dict:
    """Compare one accepted occurrence's normalized process evidence.

    The caller verifies the original record bytes and locators and supplies the
    UI terminal time bound from the same elapsedRealtime clock. This comparison
    establishes the record relationship only.
    """
    _row(evidence, {'attempt', 'preStop', 'postStart', 'postEnd'}, 'post-Stop process evidence')
    _require(_matches(_SHA256, attempt) and evidence['attempt'] == attempt, 'Stop attempt differs')
    terminal = _time(terminal_elapsed_ms)
    baseline = evidence['preStop']
    _row(baseline, {'elapsedMs', 'context', 'rawRef', *_ROLES}, 'pre-Stop process baseline')
    _require(_time(baseline['elapsedMs']) < terminal, 'Process baseline does not precede the UI terminal')
    context, global_pid_view = _context(baseline['context'])
    used_refs = {_raw_ref(baseline['rawRef'])}
    births = {}
    for role in _ROLES:
        row = baseline[role]
        _row(row, {'birth', 'rawRef'}, f'pre-Stop {role} birth')
        _distinct_ref(row['rawRef'], used_refs)
        births[role] = (_birth(row['birth'], global_pid_view=global_pid_view)['pid'], row['rawRef'])
    pids = (context['appBirth']['pid'], context['systemServerBirth']['pid'], context['reader']['birth']['pid'],
            *(birth[0] for birth in births.values()))
    _require(len(set(pids)) == len(pids), 'Process roles alias a numeric PID')

    start, start_samples = _post_boundary(evidence['postStart'], context, births, used_refs)
    end, end_samples = _post_boundary(evidence['postEnd'], context, births, used_refs)
    _require(terminal < start <= min(start_samples) <= max(start_samples) < min(end_samples)
             <= max(end_samples) <= end, 'Post-Stop probes fall outside their ordered time bracket')
    return {'bootId': context['bootId'], 'hostMountNamespace': context['hostMountNamespace'],
            'postStartElapsedMs': start, 'postEndElapsedMs': end}
