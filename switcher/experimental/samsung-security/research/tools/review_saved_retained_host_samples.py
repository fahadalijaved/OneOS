"""Corroborate the three historical Samsung process roles using saved records only."""

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = (
    'out/authority-topology-capture/20261106T002206999443Z-27a74a3267004ce7999b2012f9d53938/observation.json',
    342752, '29dc8279dfd7d61f91257856d89d18775c6c49c0195bae23256001650a83af1b',
)
PARENT_SAMPLE = (
    'out/retained-parent-readonly-preflight/20261106T043716560466Z-9d3000e929354e3b9293c070abc2ae3d/observation.json',
    2562, '6cd6c6307fdf58b1d1a0b0d7b703be8a2b7113aba1816ac967ab7959ba03f443',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_pinned(pin):
    name, length, digest = pin
    path = ROOT / name
    require(path.resolve(strict=True) == path, 'Saved sample path was redirected')
    with path.open('rb') as stream:
        raw = stream.read(length + 1)
    require(len(raw) == length and hashlib.sha256(raw).hexdigest() == digest,
            'Saved sample bytes differ from the pin')
    return json.loads(raw)


def observed(result):
    require(result['status'] == 'observed', 'Required process observation is unresolved')
    return result['value']


def identity(row, parent_key, ticks):
    pid, parent, comm = row['pid'], row[parent_key], row['comm']
    require(type(pid) is int and type(parent) is int and 0 < pid <= 2**31 - 1
            and 0 < parent <= 2**31 - 1 and type(comm) is str and bool(comm)
            and type(ticks) is int and 0 < ticks <= 2**64 - 1, 'Malformed process identity')
    return pid, parent, comm, ticks


def compare(topology, point):
    require(topology['schema'] == 'authority-topology-observation/v1'
            and point['schema'] == 'retained-parent-readonly-observation/v1', 'Unexpected sample schema')
    boot = observed(topology['facts']['bootBefore'])
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot)
            and int(boot.replace('-', ''), 16)
            and boot == observed(topology['facts']['bootAfter']), 'Earlier boot endpoints disagree')
    primary, native_next = point['parents']
    require((primary['domain'], native_next['domain']) == ('u:r:zygote:s0', 'u:r:zygote_next:s0'),
            'Parent domains do not match the recorded roles')

    births = []
    for group, name, later, uid in (
        ('system_server', 'system_server', point['systemServer'], 1000),
        ('zygote', 'zygote64', primary['identity'], 0),
        ('zygote', 'zygote_next', native_next['identity'], 0),
    ):
        require(re.fullmatch(r'[1-9][0-9]{0,19}', later['starttimeTicks']), 'Malformed later start ticks')
        birth = identity(later, 'parentPid', int(later['starttimeTicks']))
        pid, parent, _, _ = birth
        require(observed(topology['roles'][group]['candidateLookups'][name]) == [pid]
                and observed(topology['roleLookupsAfter'][group][name]) == [pid], 'Role lookup differs')
        process = topology['processes'][str(pid)]
        for boundary in ('statBefore', 'statAfter'):
            row = observed(process[boundary])
            require(identity(row, 'ppid', row['starttimeTicks']) == birth, 'Process sample differs')
        status = observed(process['status'])
        require((status['Pid'], status['Tgid'], status['PPid']) == (pid, pid, parent)
                and status['Uid'] == status['Gid'] == [uid] * 4, 'Process role credentials or parent differ')
        births.append(birth)

    server, primary_birth, next_birth = births
    require(len({row[0] for row in births}) == 3 and server[1] == primary_birth[0]
            and primary_birth[1] == next_birth[1] == 1 and primary_birth[3] <= server[3]
            and point['reportedPrimaryZygotePid'] == primary_birth[0]
            and point['reportedNextZygotePid'] == next_birth[0], 'Samsung process family differs')
    return {
        'status': 'HISTORICAL_ROLE_SAMPLES_AGREE',
        'matchedRoles': ['system_server', 'primary_zygote', 'zygote_next'],
        'crossCaptureBootJoinVerified': False,
        'sameSessionReturnVerified': False,
        'deviceAcceptance': False,
    }


def main():
    try:
        result = compare(read_pinned(TOPOLOGY), read_pinned(PARENT_SAMPLE))
    except (KeyError, OSError, TypeError, ValueError) as failure:
        print(json.dumps({'status': 'SAVED_ROLE_COMPARISON_HELD', 'reason': type(failure).__name__,
                          'deviceAcceptance': False}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
