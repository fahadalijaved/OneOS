"""Recheck the exact saved guest AMS fingerprint caller cut, offline and read-only."""

import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

sys.dont_write_bytecode = True

from run_guest_tree_install_transport import ROOT, load_io, pinned, sha


INVENTORY = ('inventory/retained-fingerprint-caller-ingress.json',
             'f8694f29b663b4694fc4d169175f8b3fb39c4ca55ae2102a7cf9f120d55ce621')
ARCHIVE = 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/services_patched.jar'
ARCHIVE_BYTES = 44699364
ARCHIVE_SHA = 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'
PHYSICAL_SHA = 'bcc9cb821ffc6a37b3838ca2391253652a0d40245a4b75b8b35eccd17779ca20'
AMS = 'Lcom/android/server/am/ActivityManagerService;'
PID_MAP = 'Lcom/android/server/am/ActivityManagerService$PidMap;'
RECORD = 'Lcom/android/server/am/ProcessRecord;'
THREAD = 'Landroid/app/IApplicationThread;'
BINDER = 'Landroid/os/Binder;'
START_UID = RECORD + '->getStartUid()I'
START_SEQ = RECORD + '->getStartSeq()J'
GET_THREAD = RECORD + '->getThread()' + THREAD
PID_LOOKUP = PID_MAP + '->get(I)' + RECORD
WAIT = 'Lcom/android/server/am/ActivityManagerConstants;->mEnableWaitForFinishAttachApplication:Z'
MONITOR = AMS + '->mGlobalLock:Lcom/android/server/am/ActivityManagerGlobalLock;'
RESET = AMS + '->resetPriorityAfterProcLockedSection()V'
TRACE = AMS + '->traceAfterProcUnlock()V'
HANDLE_DIED = AMS + '->handleAppDiedLocked(' + RECORD + 'IZZZ)V'
THREAD_BINDER = THREAD + '->asBinder()Landroid/os/IBinder;'
ATTACH = 'attachApplication(' + THREAD + 'J)V'
LOCKED = 'attachApplicationLocked(' + THREAD + 'IIJ)V'
OUTER = 'finishAttachApplication(JJ)V'
INNER = 'finishAttachApplicationInner(JII)V'
DEATH = 'appDiedLocked(' + RECORD + 'I' + THREAD + 'ZLjava/lang/String;)V'
GROUPS = {'guestAttach': {ATTACH, LOCKED}, 'guestFinishAttachAndDeath': {INNER, OUTER, DEATH}}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_pin(io, spec, maximum):
    require(type(spec['bytes']) is int and 0 < spec['bytes'] <= maximum, 'Static source record exceeds bound')
    data = pinned(io, spec['path'], spec['sha256'], spec['bytes'])
    require(len(data) == spec['bytes'], 'Static source record size differs')
    return data


def archive_proof(io):
    path = ROOT / ARCHIVE
    with io['checked_input'](path, size=ARCHIVE_BYTES) as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == ARCHIVE_SHA, 'Held guest archive differs')
        stream.seek(0)
        with ZipFile(stream) as archive:
            rows = [item for item in archive.infolist() if item.filename == 'classes.dex']
            require(len(rows) == 1 and rows[0].file_size == 12186672, 'Held physical DEX extent differs')
            with archive.open(rows[0]) as member:
                require(hashlib.file_digest(member, 'sha256').hexdigest() == PHYSICAL_SHA, 'Held physical DEX differs')


def read_bodies(io, inventory):
    bodies, proofs, sources = {}, {}, {}
    for role, signatures in GROUPS.items():
        evidence = inventory['boundedStaticReads'][role]
        receipt = json.loads(read_pin(io, evidence['receipt'], 256 * 1024), object_pairs_hook=io['unique_object'])
        require(receipt['schema'] == 'static-security-reader/v1' and type(receipt['readerExitCode']) is int
                and receipt['readerExitCode'] == 0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] is True
                and receipt['oemCodeExecuted'] is False and receipt['androidExecuted'] is False
                and Path(receipt['archive']) == ROOT / ARCHIVE and receipt['archiveSha256'] == evidence['archiveSha256'] == ARCHIVE_SHA
                and receipt['selectedMethodProofs'] == evidence['methods'], 'Saved reader receipt differs: ' + role)
        raw_pin = evidence['raw']
        require((receipt['raw'], receipt['rawBytes'], receipt['rawSha256']) ==
                (raw_pin['path'], raw_pin['bytes'], raw_pin['sha256']), 'Saved reader raw link differs: ' + role)
        raw = read_pin(io, raw_pin, 512 * 1024)
        require(raw.endswith(b'\n'), 'Incomplete static body framing')
        summary = {item['signature']: item for item in evidence['methods']}
        require(summary.keys() == signatures and len(summary) == len(evidence['methods']), 'Unexpected method receipt scope')
        seen = set()
        records = []
        for line_number, line in enumerate(raw.splitlines(), 1):
            item = json.loads(line, object_pairs_hook=io['unique_object'])
            records.append(item)
            if item['record'] != 'method':
                continue
            body = item['body']
            signature = body['signature']
            require(signature in signatures and signature not in seen, 'Unexpected or duplicate raw method')
            seen.add(signature)
            _, marker, normalized = line.partition(b',"body":')
            proof = summary[signature]
            require(marker and normalized.endswith(b'}}') and sha(normalized[:-1]) == item['normalizedBodySha256']
                    == proof['normalizedBodySha256'] and item['physicalDex'] == proof['physicalDex'] == 'classes.dex'
                    and item['logicalHeaderOffset'] == proof['logicalHeaderOffset'] == 0
                    and body['owner'] == proof['owner'] == AMS and body['accessFlags'] == proof['accessFlags']
                    and body['hasCode'] is proof['hasCode'] is True and len(body['instructions']) == proof['instructionCount']
                    and len(body['catches']) == proof['tryHandlerCount'], 'Exact normalized body differs: ' + signature)
            bodies[signature] = body
            proofs[signature] = {**proof, 'rawLine': line_number, 'raw': raw_pin}
        physical = [row for row in records if row['record'] == 'dex' and row['physicalDex'] == 'classes.dex']
        require(seen == signatures and len(physical) == 1 and physical[0]['physicalDexSha256'] == PHYSICAL_SHA
                and physical[0]['logicalHeaderOffset'] == 0 and physical[0]['version'] == '039'
                and records[-1]['record'] == 'summary' and records[-1]['selectedMethods'] == len(signatures),
                'Static body stream scope differs: ' + role)
        sources[role] = {'receipt': evidence['receipt'], 'raw': raw_pin}
    return bodies, proofs, sources


def normal_graph(body):
    instructions = {}
    cursor = 0
    for row in body['instructions']:
        require(row['pc'] == cursor and type(row['codeUnits']) is int and row['codeUnits'] > 0,
                'Invalid instruction extent')
        instructions[cursor] = row
        cursor += row['codeUnits']
    graph = {pc: set() for pc in instructions}
    for pc, row in instructions.items():
        opcode = row['opcode']
        require('SWITCH' not in opcode and 'PAYLOAD' not in opcode, 'Unexpected branch-payload form')
        if 'targetPc' in row:
            require(opcode.startswith(('IF_', 'GOTO')) and row['targetPc'] in instructions, 'Unexpected branch target')
            graph[pc].add(row['targetPc'])
        if not opcode.startswith(('GOTO', 'RETURN', 'THROW')):
            successor = pc + row['codeUnits']
            require(successor in instructions, 'Unexpected instruction fallthrough')
            graph[pc].add(successor)
    boundaries = instructions.keys() | {cursor}
    for row in body['catches']:
        require(row['startPc'] in instructions and row['handlerPc'] in instructions
                and row['startPc'] + row['codeUnits'] in boundaries, 'Unexpected catch boundaries')
    return instructions, graph


def reverse(graph):
    parents = {pc: set() for pc in graph}
    for pc, successors in graph.items():
        for successor in successors:
            parents[successor].add(pc)
    return parents


def reachable(graph, start, blocked=None):
    seen, pending = set(), [start]
    while pending:
        pc = pending.pop()
        if pc != blocked and pc not in seen:
            seen.add(pc)
            pending.extend(graph[pc] - seen)
    return seen


def returns(instructions):
    return [pc for pc, row in instructions.items() if row['opcode'].startswith('RETURN')]


def check_sites(index, rows):
    for pc, opcode, fields in rows:
        actual = index.get(pc, {})
        require(actual.get('opcode') == opcode and all(actual.get(key) == value for key, value in fields.items()),
                f'Exact source instruction differs at PC {pc}')
    return [index[pc] for pc, _, _ in rows]


def site(pc, opcode, regs=None, ref=None, *, target=None, span=None, literal=None):
    fields = {}
    for key, value in (('registers', regs), ('reference', ref), ('targetPc', target), ('literal', literal)):
        if value is not None:
            fields[key] = value
    if span is not None:
        fields.update(registerStart=span[0], registerCount=span[1])
    return pc, opcode, fields


def writes_register(row, register):
    return (row.get('registers', [None])[:1] == [register]
            and not row['opcode'].startswith(('IF_', 'INVOKE_', 'MONITOR_', 'RETURN', 'THROW', 'IPUT', 'SPUT', 'APUT')))


def verify_cut(bodies):
    graphs = {signature: normal_graph(body) for signature, body in bodies.items()}
    inner, inner_graph = graphs[INNER]
    outer, outer_graph = graphs[OUTER]
    attach, _ = graphs[ATTACH]
    locked, _ = graphs[LOCKED]
    death, death_graph = graphs[DEATH]
    checks = {}
    checks['nativeFinishSender'] = check_sites(outer, [
        site(0, 'INVOKE_STATIC', [], BINDER + '->getCallingPid()I'), site(3, 'MOVE_RESULT', [1]),
        site(4, 'INVOKE_STATIC', [], BINDER + '->getCallingUid()I'), site(7, 'MOVE_RESULT', [7]),
        site(10, 'IGET_BOOLEAN', [0, 0], WAIT), site(12, 'IF_NEZ', [0], target=54),
        site(53, 'RETURN_VOID'), site(56, 'IF_NE', [1, 0], target=63),
        site(58, 'CONST_16', [0], literal=1000), site(60, 'IF_NE', [7, 0], target=63), site(62, 'RETURN_VOID'),
        site(63, 'INVOKE_STATIC', [], BINDER + '->clearCallingIdentity()J'), site(66, 'MOVE_RESULT_WIDE', [8]),
        site(67, 'INVOKE_DIRECT', [10, 11, 12, 7, 1], AMS + '->' + INNER),
        site(70, 'INVOKE_STATIC', [8, 9], BINDER + '->restoreCallingIdentity(J)V'),
        site(93, 'RETURN_VOID'), site(94, 'MOVE_EXCEPTION', [0]),
        site(97, 'INVOKE_STATIC', [8, 9], BINDER + '->restoreCallingIdentity(J)V'), site(100, 'THROW', [13]),
    ])
    require(bodies[OUTER]['registerCount'] == 15 and returns(outer) == [53, 62, 93]
            and outer_graph[67] == {70} and reverse(outer_graph)[70] == {67}
            and bodies[OUTER]['catches'] == [{'startPc': 67, 'codeUnits': 3, 'exceptionType': None, 'handlerPc': 94}],
            'Original finish attach return/identity contour differs')
    checks['innerGeneration'] = check_sites(inner, [
        site(0, 'MOVE_OBJECT_FROM16', [1, 38]), site(2, 'MOVE_FROM16', [7, 41]), site(4, 'MOVE_FROM16', [3, 42]),
        site(10, 'IGET_OBJECT', [2, 1], AMS + '->mPidsSelfLocked:' + PID_MAP), site(12, 'MONITOR_ENTER', [2]),
        site(15, 'INVOKE_VIRTUAL', [0, 3], PID_LOOKUP), site(18, 'MOVE_RESULT_OBJECT', [0]),
        site(19, 'MOVE_OBJECT', [4, 0]), site(20, 'MONITOR_EXIT', [2]), site(22, 'IF_EQZ', [4], target=862),
        site(24, 'INVOKE_VIRTUAL', [4], START_UID), site(27, 'MOVE_RESULT', [0]), site(28, 'IF_NE', [0, 7], target=862),
        site(30, 'INVOKE_VIRTUAL', [4], START_SEQ), site(33, 'MOVE_RESULT_WIDE', [10]),
        site(34, 'CMP_LONG', [0, 10, 39]), site(36, 'IF_NEZ', [0], target=862),
        site(147, 'IGET_OBJECT', [10, 1], MONITOR), site(155, 'MONITOR_ENTER', [10]),
        site(161, 'CONST_4', [5], literal=0),
        site(162, 'INVOKE_VIRTUAL', [0, 4, 5], 'Lcom/android/server/am/psc/ProcessStateController;->setPendingFinishAttach(Lcom/android/server/am/psc/ProcessRecordInternal;Z)V'),
        site(165, 'IGET_OBJECT', [0, 4], RECORD + '->processName:Ljava/lang/String;'),
        site(167, 'MOVE_OBJECT', [11, 0]),
    ])
    checks['ordinaryFinishAndRefusals'] = check_sites(inner, [
        site(438, 'IF_EQZ', [0], target=483),
        site(444, 'INVOKE_VIRTUAL', [4, 2, 5, 6], RECORD + '->killLocked(Ljava/lang/String;IZ)V'),
        site(451, 'INVOKE_VIRTUAL_RANGE', ref=HANDLE_DIED, span=(1, 6)),
        site(454, 'MONITOR_EXIT', [10]), site(458, 'INVOKE_STATIC', [], TRACE), site(461, 'RETURN_VOID'),
        site(483, 'MOVE_OBJECT', [2, 4]), site(580, 'MOVE_OBJECT_FROM16', [16, 11]),
        site(694, 'MOVE_OBJECT_FROM16', [16, 11]), site(778, 'MOVE_OBJECT', [3, 10]),
        site(779, 'MOVE_OBJECT_FROM16', [4, 16]), site(781, 'MOVE_FROM16', [10, 42]),
        site(793, 'MONITOR_EXIT', [3]), site(794, 'INVOKE_STATIC', [], RESET),
        site(797, 'INVOKE_STATIC', [], TRACE), site(800, 'RETURN_VOID'),
        site(852, 'MONITOR_EXIT', [3]), site(859, 'THROW', [0]), site(862, 'MOVE', [10, 3]),
        site(940, 'MONITOR_ENTER', [1]),
        site(949, 'INVOKE_VIRTUAL', [8, 0, 2, 6], RECORD + '->killLocked(Ljava/lang/String;IZ)V'),
        site(952, 'MONITOR_EXIT', [1]), site(956, 'INVOKE_STATIC', [], TRACE), site(959, 'RETURN_VOID'),
        site(968, 'THROW', [0]), site(974, 'THROW', [0]),
    ])
    predecessors = reverse(inner_graph)
    require(bodies[INNER]['registerCount'] == 43 and returns(inner) == [461, 800, 959]
            and all(predecessors[pc] == {prior} for prior, pc in ((793, 794), (794, 797), (797, 800)))
            and not any(c['handlerPc'] in {793, 794, 797, 800} or c['startPc'] <= 797 < c['startPc'] + c['codeUnits']
                        for c in bodies[INNER]['catches'])
            and all(800 not in reachable(inner_graph, 0, blocked=pc) for pc in (19, 22, 28, 36, 155, 438, 483)),
            'Ordinary post-monitor completion edge is ambiguous')
    for start, end, register in ((19, 483, 4), (483, 800, 2)):
        normal = reachable(inner_graph, start) & reachable(predecessors, end)
        # Refuse any lower-register destination too, so a wide write cannot clobber the record word.
        require(end in normal and not any(writes_register(inner[pc], word) for pc in normal - {start}
                                          for word in (register - 1, register)),
                'Record register changes on an ordinary completion path')

    checks['initialAttachNotIssuance'] = check_sites(attach, [
        site(12, 'IGET_OBJECT', [10, 13], MONITOR), site(20, 'MONITOR_ENTER', [10]),
        site(24, 'INVOKE_STATIC', [], BINDER + '->getCallingPid()I'), site(27, 'MOVE_RESULT', [3]),
        site(28, 'INVOKE_STATIC', [], BINDER + '->getCallingUid()I'), site(31, 'MOVE_RESULT', [4]),
        site(32, 'INVOKE_STATIC', [], BINDER + '->clearCallingIdentity()J'),
        site(87, 'INVOKE_DIRECT_RANGE', ref=AMS + '->' + LOCKED, span=(1, 6)),
        site(90, 'INVOKE_STATIC', [11, 12], BINDER + '->restoreCallingIdentity(J)V'), site(93, 'MONITOR_EXIT', [10]),
    ])
    checks['lockedAttachAndReplacement'] = check_sites(locked, [
        site(25, 'INVOKE_VIRTUAL', [0, 3], PID_LOOKUP), site(32, 'INVOKE_VIRTUAL', [0], START_UID),
        site(36, 'IF_NE', [2, 10], target=51), site(38, 'INVOKE_VIRTUAL', [0], START_SEQ),
        site(42, 'CMP_LONG', [2, 4, 11]), site(44, 'IF_EQZ', [2], target=47),
        site(317, 'INVOKE_VIRTUAL', [2], GET_THREAD), site(320, 'MOVE_RESULT_OBJECT', [0]),
        site(321, 'IF_EQZ', [0], target=336), site(327, 'INVOKE_VIRTUAL_RANGE', ref=HANDLE_DIED, span=(1, 6)),
        site(412, 'INVOKE_DIRECT', [0, 1, 3, 2, 9], 'Lcom/android/server/am/ActivityManagerService$AppDeathRecipient;-><init>(' + AMS + RECORD + 'I' + THREAD + ')V'),
        site(415, 'INVOKE_INTERFACE', [9], THREAD_BINDER),
        site(419, 'INVOKE_INTERFACE', [6, 0, 5], 'Landroid/os/IBinder;->linkToDeath(Landroid/os/IBinder$DeathRecipient;I)V'),
        site(422, 'INVOKE_VIRTUAL', [3, 0], RECORD + '->setDeathRecipient(Landroid/os/IBinder$DeathRecipient;)V'),
        site(1597, 'INVOKE_INTERFACE_RANGE', span=(1, 34)),
        site(1730, 'INVOKE_VIRTUAL', [2, 0, 7], RECORD + '->makeActive(Lcom/android/server/am/ApplicationThreadDeferred;Lcom/android/server/am/ProcessStatsService;)V'),
        site(1751, 'CONST_4', [3], literal=1),
        site(1752, 'INVOKE_VIRTUAL', [0, 2, 3], 'Lcom/android/server/am/psc/ProcessStateController;->setPendingFinishAttach(Lcom/android/server/am/psc/ProcessRecordInternal;Z)V'),
        site(1901, 'IGET_BOOLEAN', [0, 0], WAIT), site(1903, 'IF_NEZ', [0], target=1915),
        site(1905, 'MOVE_FROM16', [5, 66]), site(1907, 'MOVE_FROM16', [7, 67]), site(1909, 'MOVE_WIDE_FROM16', [3, 68]),
        site(1911, 'INVOKE_DIRECT', [14, 3, 4, 7, 5], AMS + '->' + INNER), site(1914, 'GOTO', target=1921),
        site(2294, 'INVOKE_VIRTUAL', [2], RECORD + '->unlinkDeathRecipient()V'),
        site(2301, 'INVOKE_VIRTUAL', [2, 3, 6, 1], RECORD + '->killLocked(Ljava/lang/String;IZ)V'),
        site(2310, 'INVOKE_VIRTUAL_RANGE', ref=HANDLE_DIED, span=(1, 6)),
    ])
    require(locked[1597]['reference'].startswith(THREAD + '->bindApplication('), 'Original bindApplication target differs')
    callers = [(signature, pc) for signature, (rows, _) in graphs.items() for pc, row in rows.items()
               if row.get('reference') == AMS + '->' + INNER]
    require(set(callers) == {(OUTER, 67), (LOCKED, 1911)}, 'Inner callsites differ in the audited bodies')

    checks['deathIdentityAndRetirement'] = check_sites(death, [
        site(0, 'MOVE_FROM16', [1, 16]), site(4, 'IGET_OBJECT', [3, 14], AMS + '->mPidsSelfLocked:' + PID_MAP),
        site(6, 'MONITOR_ENTER', [3]), site(9, 'INVOKE_VIRTUAL', [0, 1], PID_LOOKUP),
        site(12, 'MOVE_RESULT_OBJECT', [0]), site(13, 'MOVE_OBJECT', [8, 0]), site(14, 'MONITOR_EXIT', [3]),
        site(15, 'IF_EQ', [8, 15], target=175), site(17, 'IF_EQZ', [18], target=130),
        site(19, 'IF_EQZ', [8], target=67), site(29, 'IF_EQZ', [0], target=32), site(66, 'GOTO', target=175),
        site(69, 'INVOKE_VIRTUAL', [0, 15, 1], 'Lcom/android/server/am/ProcessList;->handleDyingAppDeathLocked(' + RECORD + 'I)Z'),
        site(129, 'RETURN_VOID'), site(174, 'RETURN_VOID'),
        site(313, 'INVOKE_VIRTUAL', [15], RECORD + '->getPid()I'), site(316, 'MOVE_RESULT', [5]),
        site(317, 'IF_NE', [5, 1], target=336), site(319, 'INVOKE_VIRTUAL', [15], GET_THREAD),
        site(322, 'MOVE_RESULT_OBJECT', [5]), site(324, 'IF_EQZ', [5], target=336),
        site(326, 'INVOKE_INTERFACE', [6], THREAD_BINDER), site(329, 'MOVE_RESULT_OBJECT', [5]),
        site(330, 'INVOKE_INTERFACE_RANGE', ref=THREAD_BINDER, span=(17, 1)), site(333, 'MOVE_RESULT_OBJECT', [11]),
        site(334, 'IF_EQ', [5, 11], target=363), site(342, 'IF_EQZ', [5], target=363),
        site(348, 'INVOKE_INTERFACE', [5], THREAD_BINDER), site(351, 'MOVE_RESULT_OBJECT', [5]),
        site(352, 'INVOKE_INTERFACE_RANGE', ref=THREAD_BINDER, span=(17, 1)), site(355, 'MOVE_RESULT_OBJECT', [6]),
        site(356, 'IF_NE', [5, 6], target=359), site(358, 'GOTO', target=363),
        site(638, 'INVOKE_VIRTUAL_RANGE', ref=HANDLE_DIED, span=(1, 6)), site(779, 'RETURN_VOID'),
    ])
    death_parents = reverse(death_graph)
    require(death_parents[175] == {15, 66} and death_parents[363] == {334, 342, 358}
            and returns(death) == [129, 174, 779], 'Original death/reuse convergence differs')
    return checks


def audit():
    io = load_io()
    inventory = json.loads(pinned(io, *INVENTORY, 32 * 1024), object_pairs_hook=io['unique_object'])
    require(inventory['schema'] == 'retained-fingerprint-caller-ingress/v1'
            and inventory['status'] == 'CLOSED_NO_LIVE_SETTINGS_BINDER_CALLER_GENERATION', 'Source inventory differs')
    archive_proof(io)
    bodies, proofs, sources = read_bodies(io, inventory)
    checks = verify_cut(bodies)
    return {
        'schema': 'oneos-guest-fingerprint-attach-cut-source-audit/v1',
        'status': 'EXACT_OFFLINE_ATTACH_CUT_AND_RETIREMENT_BOUNDARIES_ONLY',
        'producerSha256': sha(Path(__file__).read_bytes()),
        'inventory': {'path': INVENTORY[0], 'sha256': INVENTORY[1]},
        'archive': {'path': ARCHIVE, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA, 'physicalDexSha256': PHYSICAL_SHA},
        'sources': sources, 'methods': proofs, 'selectedInstructionChecks': checks,
        'candidateSourceEdge': {'inner': INNER, 'edgePc': [797, 800], 'originalMonitorExitPc': 793,
                                'recordRegisterAtReturn': 2, 'originalCallPc': 67, 'originalRestorePc': 70},
        'nonIssuingEdges': {'innerErrorReturns': [461, 959], 'outerEarlyReturns': [53, 62],
                            'outerGenericReturn': 93, 'internalNoWaitCall': 1911},
        'retirement': {
            'sameRecordBranchPc': [15, 175], 'pidReuseMergePc': [66, 175],
            'matchingAttachedBinderBranchPc': [334, 363], 'alternateThreadMergePcs': [342, 358],
            'reattachPriorThreadCleanupPc': [317, 327], 'bindFailureCleanupPc': [2294, 2301, 2310],
            'requirement': 'Retire only the previously retained record and attached-thread generation. Common blocks and a numeric PID do not identify it.',
        },
        'limits': [
            'The audit checks saved normalized instructions and original local callsites. No transformed DEX, external caller closure or actual event delivery is produced.',
            'Before any retained issuance, recheck the actual PID map record, attached thread, selected package generation and ownership after the original Binder restore.',
            'The original no-wait caller remains nonissuing. No wait flag or generic void return is used as authority.',
        ],
        'retargetEmitted': False, 'operationAuthorityIssued': False, 'androidExecuted': False, 'deviceAction': False,
    }


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
