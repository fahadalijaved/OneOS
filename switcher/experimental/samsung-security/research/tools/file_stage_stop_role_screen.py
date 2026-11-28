"""Decode the two exact tester Stop diagnostic rows as local evidence only."""

import re


_UINT32_MAX = 2**32 - 1
_PID_MAX = 2**31 - 1
_JAVA_LONG_MAX = 2**63 - 1
_UINT64_MAX = 2**64 - 1
_VIEW_WAIT_MS = 2000
_FIELDS = (
    'prepareSequence', 'appPid', 'systemServerPid', 'controllerPid', 'controllerStartTicks',
    'childPid', 'childStartTicks', 'childMountNamespaceInode', 'partialStartedElapsedMs',
    'partialCompletedElapsedMs', 'stopRequestedElapsedMs', 'terminalStartedElapsedMs',
    'terminalCompletedElapsedMs',
)
_ROW = re.compile(rb'ONEOS_STOP_ROLE_V1 (partial|terminal)' + rb' (0|[1-9][0-9]{0,19})' * len(_FIELDS))


def _decode_row(raw, phase):
    match = _ROW.fullmatch(raw)
    if match is None or match[1] != phase:
        raise ValueError('Unexpected Stop diagnostic phase or field encoding')
    return tuple(map(int, match.groups()[1:]))


def decode_stop_role_screen(raw: bytes) -> dict[str, int]:
    """Return the fields of one Partial then terminal pair, each ending in LF.

    The caller establishes screenshot custody, process births, and the tester's
    clock relationship to other observers. These text rows confer no authority.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 640 or not raw.isascii() or raw.count(b'\n') != 2:
        raise ValueError('Expected two bounded ASCII Stop diagnostic rows')
    partial_raw, terminal_raw, remainder = raw.split(b'\n')
    if remainder:
        raise ValueError('Unexpected data after Stop diagnostic rows')
    partial = _decode_row(partial_raw, b'partial')
    terminal = _decode_row(terminal_raw, b'terminal')
    if partial[-3:] != (0, 0, 0) or partial[:-3] != terminal[:-3]:
        raise ValueError('Stop diagnostic role or retained Partial bounds changed')

    record = dict(zip(_FIELDS, terminal))
    pids = tuple(record[key] for key in ('appPid', 'systemServerPid', 'controllerPid', 'childPid'))
    if (not 2 <= record['prepareSequence'] <= _UINT32_MAX or len(set(pids)) != len(pids)
            or any(not 1 <= pid <= _PID_MAX for pid in pids)
            or not 1 <= record['controllerStartTicks'] <= _JAVA_LONG_MAX
            or not 1 <= record['childStartTicks'] <= _JAVA_LONG_MAX
            or not 1 <= record['childMountNamespaceInode'] <= _UINT64_MAX):
        raise ValueError('Stop diagnostic role fields are outside the codec bounds')

    start, end, stop, terminal_start, terminal_end = terminal[-5:]
    if (not 0 <= start <= end <= stop <= terminal_start <= terminal_end <= _JAVA_LONG_MAX
            or end - start >= _VIEW_WAIT_MS or terminal_end - terminal_start >= _VIEW_WAIT_MS):
        raise ValueError('Stop diagnostic elapsed times are outside the relay bounds')
    return record
