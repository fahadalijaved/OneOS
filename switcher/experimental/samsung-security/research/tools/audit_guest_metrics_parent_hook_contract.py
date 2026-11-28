"""Plan exact original DMS hook maps from frozen bytes; never emit/execute OEM code."""
import hashlib
import bisect
import json
from pathlib import Path
import runpy
import zipfile

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / 'firmware/donor/extracted/system/framework/services.jar'
ARCHIVE_SHA = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
DEX_SHA = 'c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f'
PREFLIGHT = ROOT / 'tools/preflight_guest_metrics_parent_payload.py'
PREFLIGHT_SHA = 'd076c60a4c16774e1a8b75377661caf814a4eb4a72420f4082bc493dc4dce9ea'
PINS = {
    'inventory/guest-metrics-parent-payload-preflight.json': '006e31d5621b3009e0e7e9605a09dd91f88a3bfeb396fc5f51bd176e74851865',
    'inventory/guest-metrics-parent-transport.json': 'c7d0b900ec59e701eac64ba4189d2bc84849d99103142a85894843588d32b09f',
    'inventory/guest-metrics-endpoint.json': '847affee9f18fa16b09c5d064b4bf247c7f70ae76dc797f54048b0e2d766c015',
    'inventory/guest-metrics-parent-cell.json': '15885b7e0ab51c5024f5447022711d39e727f9a7795833ca2535666420341fc8',
}
DMS = 'Lcom/android/server/display/DisplayManagerService;'
BINDER = DMS[:-1] + '$BinderService;'
CELL = 'Lcom/appleexploit/oneos/security/authority/PreparedGuestMetricsParentCell;'
DISPATCH = 'dispatchOneOsGuestMetricsFromParent(Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def header(dex, member):
    p = member['codeOffset']
    return {'registers': dex.u16(p), 'ins': dex.u16(p + 2), 'outs': dex.u16(p + 4),
            'tries': dex.u16(p + 6), 'debugInfoOffset': dex.u32(p + 8),
            'units': dex.u32(p + 12)}


def debug(data, offset, units):
    """Read selected original debug streams only; return state/events, no encoder."""
    if not offset:
        return {'present': False, 'events': []}
    cursor = offset

    def uleb():
        nonlocal cursor
        value = 0
        for shift in range(0, 35, 7):
            if cursor >= len(data):
                raise ValueError('Debug ULEB extent')
            byte = data[cursor]
            cursor += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('Debug ULEB bound')

    def sleb():
        nonlocal cursor
        value = 0
        shift = 0
        for _ in range(5):
            byte = data[cursor]
            cursor += 1
            value |= (byte & 127) << shift
            shift += 7
            if byte < 128:
                return value - (1 << shift) if byte & 64 else value
        raise ValueError('Debug SLEB bound')

    line_start = uleb()
    parameters = uleb()
    if parameters > 256:
        raise ValueError('Debug parameter bound')
    names = [uleb() - 1 for _ in range(parameters)]
    pc, line, events = 0, line_start, []
    while True:
        if cursor >= len(data) or cursor - offset > 65536:
            raise ValueError('Debug stream bound')
        opcode = data[cursor]
        cursor += 1
        row = {'opcode': opcode}
        if opcode == 0:
            row['kind'] = 'END_SEQUENCE'
        elif opcode == 1:
            pc += uleb()
            row['kind'] = 'ADVANCE_PC'
        elif opcode == 2:
            line += sleb()
            row['kind'] = 'ADVANCE_LINE'
        elif opcode in (3, 4):
            row.update(kind='START_LOCAL_EXTENDED' if opcode == 4 else 'START_LOCAL',
                       register=uleb(), nameIndex=uleb() - 1, typeIndex=uleb() - 1)
            if opcode == 4:
                row['signatureIndex'] = uleb() - 1
        elif opcode in (5, 6):
            row.update(kind='END_LOCAL' if opcode == 5 else 'RESTART_LOCAL', register=uleb())
        elif opcode in (7, 8):
            row['kind'] = 'PROLOGUE_END' if opcode == 7 else 'EPILOGUE_BEGIN'
        elif opcode == 9:
            row.update(kind='SET_FILE', nameIndex=uleb() - 1)
        else:
            adjusted = opcode - 10
            pc += adjusted // 15
            line += adjusted % 15 - 4
            row['kind'] = 'LINE'
        if not 0 <= pc <= units:
            raise ValueError('Debug PC outside method')
        row.update(pc=pc, line=line)
        events.append(row)
        if opcode == 0:
            break
    return {'present': True, 'offset': offset, 'bytes': cursor - offset,
            'sha256': hashlib.sha256(data[offset:cursor]).hexdigest(),
            'lineStart': line_start, 'parameterNameIndices': names, 'events': events}


def raw_tries(dex, member, h):
    if not h['tries']:
        return []
    data = dex.d
    table = member['codeOffset'] + 16 + h['units'] * 2 + (2 if h['units'] & 1 else 0)
    base = table + h['tries'] * 8
    cursor = base

    def leb(signed=False):
        nonlocal cursor
        value, shift = 0, 0
        for _ in range(5):
            byte = data[cursor]
            cursor += 1
            value |= (byte & 127) << shift
            shift += 7
            if byte < 128:
                return value - (1 << shift) if signed and byte & 64 else value
        raise ValueError('Raw handler LEB bound')

    count = leb()
    handlers = {}
    for _ in range(count):
        offset = cursor - base
        size = leb(True)
        rows = []
        for _ in range(abs(size)):
            typ, target = leb(), leb()
            rows.append({'typeIndex': typ, 'exceptionType': dex.types[typ], 'handlerPc': target})
        if size <= 0:
            rows.append({'typeIndex': None, 'exceptionType': None, 'handlerPc': leb()})
        handlers[offset] = rows
    result = []
    for i in range(h['tries']):
        p = table + 8 * i
        result.append({'startPc': dex.u32(p), 'codeUnits': dex.u16(p + 4),
                       'handlerOffset': dex.u16(p + 6), 'handlers': handlers[dex.u16(p + 6)]})
    return result


def main():
    tool_pin = sha(__file__)
    for path, pin in PINS.items():
        if sha(ROOT / path) != pin:
            raise ValueError('Frozen input changed: ' + path)
    if sha(ARCHIVE) != ARCHIVE_SHA or sha(PREFLIGHT) != PREFLIGHT_SHA:
        raise ValueError('Source/archive parser drift')
    source_preflight = json.loads((ROOT / 'inventory/guest-metrics-parent-payload-preflight.json').read_text())
    if source_preflight['instructionScan']['widthImpactCount'] or source_preflight['instructionScan']['maxProjectedShortStringIndex'] != 65534:
        raise ValueError('Three-body string-width contract no longer applies')
    with zipfile.ZipFile(ARCHIVE) as archive:
        entries = [item for item in archive.infolist() if item.filename == 'classes2.dex']
        if len(entries) != 1 or entries[0].file_size != 10042704:
            raise ValueError('Exact original DEX entry required')
        data = archive.read(entries[0])
    if hashlib.sha256(data).hexdigest() != DEX_SHA:
        raise ValueError('Original DEX drift')
    dex = runpy.run_path(str(PREFLIGHT))['Dex'](data)
    if 'Ljava/lang/Throwable;' not in dex.types or dex.hapi()['present']:
        raise ValueError('Throwable/source HAPI absence profile changed')
    string_insertions = [item['originalInsertionIndex'] for item in source_preflight['newStrings']]
    type_insertions = [bisect.bisect_left(dex.types, typ) for typ in source_preflight['missingTypes']]
    remap_string = lambda index: index + sum(p <= index for p in string_insertions) if index >= 0 else -1
    remap_type = lambda index: index + sum(p <= index for p in type_insertions) if index >= 0 else -1
    members = {item['descriptor']: item for item in dex.codes}
    ledger = [{'descriptor': key, 'memberIndex': member['memberIndex'], 'accessFlags': member['accessFlags'],
               'partition': member['partition'], 'codeOffset': member['codeOffset'],
               **header(dex, member)} for key, member in sorted(members.items())]
    raw = ROOT / 'firmware/guest-metrics-parent-hook-contract'
    out = ROOT / 'out/guest-metrics-parent-hook-contract'
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = raw / 'original-code-headers.json'
    ledger_path.write_text(json.dumps(ledger, separators=(',', ':')) + '\n')
    bodies = {}
    ep = json.loads((ROOT / 'inventory/guest-metrics-endpoint.json').read_text())
    parent = json.loads((ROOT / 'inventory/guest-metrics-parent-transport.json').read_text())
    for evidence in ep['methodEvidence'] + parent['methodEvidence']:
        if sha(ROOT / evidence['receipt']) != evidence['receiptSha256'] or sha(ROOT / evidence['raw']) != evidence['rawSha256']:
            raise ValueError('Frozen method proof drift')
        for line in (ROOT / evidence['raw']).read_text().splitlines():
            row = json.loads(line)
            if row.get('record') == 'method':
                body = row['body']
                bodies[body['owner'] + '->' + body['signature']] = body
    start = DMS + '->onStart()V'
    phase = DMS + '->onBootPhase(I)V'
    transact = BINDER + '->onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'
    configs = {
        start: {'insertAt': 53, 'addedUnits': 8, 'newTry': {'startPc': 53, 'codeUnits': 6, 'exceptionType': 'Ljava/lang/Throwable;', 'handlerPc': 60},
                'header': {'registers': 4, 'ins': 1, 'outs': 4, 'tries': 3, 'units': 65},
                'newBlocks': [{'pc': 53, 'width': 3, 'operation': 'INVOKE_STATIC {v3,v0} captureAfterOnStart'}, {'pc': 56, 'width': 1, 'operation': 'MOVE_RESULT_OBJECT v1'}, {'pc': 57, 'width': 2, 'operation': 'IPUT_OBJECT v1,v3 new private volatile field'}, {'pc': 59, 'width': 1, 'operation': 'GOTO originalReturn@61'}, {'pc': 60, 'width': 1, 'operation': 'MOVE_EXCEPTION v1; fall through originalReturn@61'}]},
        phase: {'insertAt': 276, 'addedUnits': 9, 'newTry': {'startPc': 280, 'codeUnits': 3, 'exceptionType': 'Ljava/lang/Throwable;', 'handlerPc': 284},
                'header': {'registers': 12, 'ins': 2, 'outs': 3, 'tries': 6, 'units': 286},
                'newBlocks': [{'pc': 276, 'width': 2, 'operation': 'CONST_16 v0,100'}, {'pc': 278, 'width': 2, 'operation': 'IF_NE v11,v0 originalReturn@285'}, {'pc': 280, 'width': 3, 'operation': 'INVOKE_STATIC {v10,v11} onOriginalBootPhaseCompleted; ignore enum result'}, {'pc': 283, 'width': 1, 'operation': 'GOTO originalReturn@285'}, {'pc': 284, 'width': 1, 'operation': 'MOVE_EXCEPTION v0; fall through originalReturn@285'}]},
        transact: {'insertAt': 0, 'addedUnits': 12, 'newTry': None,
                   'header': {'registers': 7, 'ins': 5, 'outs': 5, 'tries': 0, 'units': 39},
                   'newBlocks': [{'pc': 0, 'width': 3, 'operation': 'CONST v0,0x00fe0001'}, {'pc': 3, 'width': 2, 'operation': 'IF_NE v3,v0 originalBody@12'}, {'pc': 5, 'width': 2, 'operation': 'IGET_OBJECT v0,v2 existing this$0'}, {'pc': 7, 'width': 3, 'operation': 'INVOKE_VIRTUAL {v0,v2,v4,v5,v6} new DMS dispatch'}, {'pc': 10, 'width': 1, 'operation': 'MOVE_RESULT v0'}, {'pc': 11, 'width': 1, 'operation': 'RETURN v0'}]},
    }
    field_ref = DMS + '->mOneOsGuestMetricsLifecycle:' + CELL
    formal = {
        start: [dict(opcode='INVOKE_STATIC', registers=[3, 0], reference=CELL + '->captureAfterOnStart(Ljava/lang/Object;Landroid/os/Binder;)' + CELL),
                dict(opcode='MOVE_RESULT_OBJECT', registers=[1]), dict(opcode='IPUT_OBJECT', registers=[1, 3], reference=field_ref),
                dict(opcode='GOTO', targetPc=61), dict(opcode='MOVE_EXCEPTION', registers=[1])],
        phase: [dict(opcode='CONST_16', registers=[0], literal=100), dict(opcode='IF_NE', registers=[11, 0], targetPc=285),
                dict(opcode='INVOKE_STATIC', registers=[10, 11], reference=CELL + '->onOriginalBootPhaseCompleted(Ljava/lang/Object;I)' + CELL[:-1] + '$PhaseDisposition;'),
                dict(opcode='GOTO', targetPc=285), dict(opcode='MOVE_EXCEPTION', registers=[0])],
        transact: [dict(opcode='CONST', registers=[0], literal=0x00fe0001), dict(opcode='IF_NE', registers=[3, 0], targetPc=12),
                   dict(opcode='IGET_OBJECT', registers=[0, 2], reference=BINDER + '->this$0:' + DMS),
                   dict(opcode='INVOKE_VIRTUAL', registers=[0, 2, 4, 5, 6], reference=DMS + '->' + DISPATCH),
                   dict(opcode='MOVE_RESULT', registers=[0]), dict(opcode='RETURN', registers=[0])],
    }
    for identity, rows in formal.items():
        configs[identity]['newBlocks'] = [{**old, **new} for old, new in zip(configs[identity]['newBlocks'], rows, strict=True)]
    selected = []
    source_debug = {}
    for identity, config in configs.items():
        member = members[identity]
        old = header(dex, member)
        body = bodies[identity]
        at, delta = config['insertAt'], config['addedUnits']
        mapped = lambda pc: pc + delta if pc >= at else pc
        branch_target = lambda pc: at if pc == at and at else mapped(pc)
        pc_map = [{'oldPc': i['pc'], 'newPc': mapped(i['pc']), 'width': i['codeUnits']} for i in body['instructions']]
        covered = set()
        for item in pc_map:
            covered.update(range(item['newPc'], item['newPc'] + item['width']))
        for item in config['newBlocks']:
            block = set(range(item['pc'], item['pc'] + item['width']))
            if covered & block:
                raise ValueError('Planned authored block overlaps original instruction')
            covered.update(block)
        if covered != set(range(old['units'] + delta)):
            raise ValueError('Planned code units have a gap/extent drift')
        if max(i['pc'] + i['codeUnits'] for i in body['instructions']) != old['units']:
            raise ValueError('Original body/header extent mismatch')
        if any(catch['startPc'] < at < catch['startPc'] + catch['codeUnits'] for catch in body['catches']):
            raise ValueError('New block crosses an original protected interval')
        try_map = []
        for catch in body['catches']:
            end = catch['startPc'] + catch['codeUnits']
            new_start = mapped(catch['startPc'])
            new_end = at if end == at else mapped(end)
            try_map.append({'original': catch, 'mapped': {**catch, 'startPc': new_start,
                           'codeUnits': new_end - new_start, 'handlerPc': mapped(catch['handlerPc'])}})
        branch_map = [{'oldPc': i['pc'], 'newPc': mapped(i['pc']), 'oldTarget': i['targetPc'],
                       'newTarget': branch_target(i['targetPc'])} for i in body['instructions'] if 'targetPc' in i]
        if any(i.get('switchElements') for i in body['instructions']):
            raise ValueError('Unexpected selected payload; requires explicit contract')
        dbg = debug(data, old['debugInfoOffset'], old['units'])
        end_sequences = [event for event in dbg['events'] if event['opcode'] == 0]
        if len(end_sequences) != 1 or dbg['events'][-1] != end_sequences[0]:
            raise ValueError('Exact raw debug END_SEQUENCE missing')
        source_debug[identity] = dbg
        debug_map = [{'ordinal': n, 'kind': event['kind'], 'oldPc': event['pc'], 'newPc': mapped(event['pc']),
                      'line': event['line'], **{k: v for k, v in event.items() if k in ['register', 'nameIndex', 'typeIndex', 'signatureIndex']}}
                     for n, event in enumerate(dbg['events'])]
        for event in debug_map:
            if 'register' in event and not 0 <= event['register'] < old['registers']:
                raise ValueError('Selected debug register outside source header')
            for key in ['nameIndex', 'signatureIndex']:
                if key in event:
                    event[key + 'New'] = remap_string(event[key])
            if 'typeIndex' in event:
                event['typeIndexNew'] = remap_type(event['typeIndex'])
        own_try = config['newTry']
        if own_try:
            own_try = {**own_try, 'originalTypeIndex': dex.types.index('Ljava/lang/Throwable;'),
                       'mappedTypeIndex': remap_type(dex.types.index('Ljava/lang/Throwable;'))}
        raw_items = raw_tries(dex, member, old)
        flattened = [{'startPc': item['startPc'], 'codeUnits': item['codeUnits'],
                      'exceptionType': handler['exceptionType'], 'handlerPc': handler['handlerPc']}
                     for item in raw_items for handler in item['handlers']]
        if flattened != body['catches']:
            raise ValueError('Raw try items disagree with frozen expanded catch proof')
        raw_try_map = []
        for item in raw_items:
            end = item['startPc'] + item['codeUnits']
            new_start = mapped(item['startPc'])
            new_end = at if end == at else mapped(end)
            raw_try_map.append({'original': item, 'mapped': {'startPc': new_start, 'codeUnits': new_end - new_start,
                                'handlers': [{**h, 'handlerPc': mapped(h['handlerPc']),
                                              'typeIndexNew': remap_type(h['typeIndex']) if h['typeIndex'] is not None else None}
                                             for h in item['handlers']]}})
        aliases = [key for key, value in members.items() if value['codeOffset'] == member['codeOffset']]
        if aliases != [identity]:
            raise ValueError('Selected edit aliases another original code item')
        actual = {key: value for key, value in config['header'].items() if key != 'tries'}
        expected = {key: old[key] + delta if key == 'units' else old[key] for key in actual}
        if actual != expected or config['header']['tries'] != old['tries'] + (1 if config['newTry'] else 0):
            raise ValueError('Declared exact header change differs')
        selected.append({'identity': identity, 'originalHeader': old, 'expectedHeader': config['header'],
                         'originalCodeOffset': member['codeOffset'], 'sourceCodeGroup': aliases,
                         'newBlocks': config['newBlocks'], 'forwardPcMap': pc_map,
                         'inversePcMap': [{'newPc': p['newPc'], 'oldPc': p['oldPc']} for p in pc_map],
                         'originalCodeEnd': old['units'], 'newCodeEnd': old['units'] + delta,
                         'tryPaddingBytes': {'original': 2 if old['tries'] and old['units'] & 1 else 0,
                                             'expected': 2 if config['header']['tries'] and config['header']['units'] & 1 else 0},
                         'branchMap': branch_map, 'originalTryMap': try_map, 'newOwnTry': own_try,
                         'rawTryItemMap': raw_try_map,
                         'debug': {'sourceSha256': dbg.get('sha256'), 'sourceOffset': old['debugInfoOffset'],
                                   'lineStart': dbg.get('lineStart'), 'parameterNameIndices': dbg.get('parameterNameIndices'),
                                   'parameterNameIndicesNew': [remap_string(i) for i in dbg.get('parameterNameIndices', [])],
                                   'initialSourcePcMapsTo': mapped(0), 'events': debug_map,
                                   'rawStateEventCount': len(debug_map),
                                   'semanticEventCountIncludingEndSequence': sum(e['kind'] not in ['ADVANCE_PC', 'ADVANCE_LINE'] for e in dbg['events']),
                                   'rawEndSequencePc': end_sequences[0]['pc'], 'expectedRawEndSequencePc': mapped(end_sequences[0]['pc']),
                                   'doNotNormalizeEndSequenceToCodeEnd': True,
                                   'rawIndexRemap': 'Existing names/signatures via seven-string insertion map; types via two-type insertion map; source register numbers unchanged'}})
    constructors = []
    for identity in [DMS + '-><init>(Landroid/content/Context;)V',
                     DMS + '-><init>(Landroid/content/Context;Lcom/android/server/display/DisplayManagerService$Injector;)V',
                     BINDER + '-><init>(Lcom/android/server/display/DisplayManagerService;)V']:
        member = members[identity]
        h = header(dex, member)
        dbg = debug(data, h['debugInfoOffset'], h['units'])
        source_debug[identity] = dbg
        constructors.append({'identity': identity, 'header': h, 'accessFlags': member['accessFlags'],
                             'codeOffset': member['codeOffset'], 'instructionSha256': hashlib.sha256(data[member['codeOffset'] + 16:member['codeOffset'] + 16 + h['units'] * 2]).hexdigest(),
                             'debugSha256': dbg.get('sha256'), 'allOriginalInstructionsTriesDebugAndDeclarationsUnchanged': True,
                             'forwardAndInversePcMap': [{'oldPc': i['pc'], 'newPc': i['pc'], 'width': i['codeUnits']} for i in bodies[identity]['instructions']],
                             'originalTriesUnchanged': bodies[identity]['catches'],
                             'debugIdentityPcMap': [{'kind': e['kind'], 'oldPc': e['pc'], 'newPc': e['pc'], 'line': e['line'],
                                                    **{key: e[key] for key in ['register', 'nameIndex', 'typeIndex', 'signatureIndex'] if key in e},
                                                    **{key + 'New': remap_string(e[key]) for key in ['nameIndex', 'signatureIndex'] if key in e},
                                                    **({'typeIndexNew': remap_type(e['typeIndex'])} if 'typeIndex' in e else {})}
                                                   for e in dbg['events']],
                             'parameterNameIndices': dbg.get('parameterNameIndices'),
                             'parameterNameIndicesNew': [remap_string(i) for i in dbg.get('parameterNameIndices', [])],
                             'unchangedMeaning': 'Exact source-normalized opcode/register/literal/reference/width/branch/debug/declaration; only declared pool IDs and physical offsets relocate, source hashes are provenance not unrelocated output hashes'})
    debug_path = raw / 'original-selected-debug.json'
    debug_path.write_text(json.dumps(source_debug, indent=2) + '\n')
    dispatch = {'identity': DMS + '->' + DISPATCH, 'partition': 'virtualMethods', 'accessFlags': 0,
                'header': {'registers': 6, 'ins': 5, 'outs': 6, 'tries': 0, 'units': 11, 'debugInfoOffset': 0},
                'parameters': ['v1=this', 'v2=actualBorn', 'v3=data', 'v4=reply', 'v5=flags'], 'local': 'v0=cell/result',
                'instructions': [{'pc': 0, 'width': 2, 'operation': 'IGET_OBJECT v0,v1 new private field'},
                                 {'pc': 2, 'width': 2, 'operation': 'IF_EQZ v0 unhandled@9'},
                                 {'pc': 4, 'width': 3, 'operation': 'INVOKE_VIRTUAL_RANGE v0..v5 Cell.dispatchFromParent'},
                                 {'pc': 7, 'width': 1, 'operation': 'MOVE_RESULT v0'}, {'pc': 8, 'width': 1, 'operation': 'RETURN v0'},
                                 {'pc': 9, 'width': 1, 'operation': 'CONST_4 v0,0'}, {'pc': 10, 'width': 1, 'operation': 'RETURN v0'}],
                'annotations': [], 'parameterNames': [None, None, None, None], 'parameterAnnotations': [[], [], [], []]}
    new_dispatch_rows = [dict(opcode='IGET_OBJECT', registers=[0, 1], reference=field_ref), dict(opcode='IF_EQZ', registers=[0], targetPc=9),
                         dict(opcode='INVOKE_VIRTUAL_RANGE', registerStart=0, registerCount=6, reference=CELL + '->dispatchFromParent(Ljava/lang/Object;Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z'),
                         dict(opcode='MOVE_RESULT', registers=[0]), dict(opcode='RETURN', registers=[0]),
                         dict(opcode='CONST_4', registers=[0], literal=0), dict(opcode='RETURN', registers=[0])]
    dispatch['instructions'] = [{**old, **new} for old, new in zip(dispatch['instructions'], new_dispatch_rows, strict=True)]
    result = {'schema': 'guest-metrics-parent-hook-contract/v1', 'status': 'STATIC_TRANSFORMATION_CONTRACT_NO_EMISSION_BASELINE_PENDING',
              'inputPins': [{'path': p, 'sha256': h} for p, h in PINS.items()],
              'sourceArchiveSha256': ARCHIVE_SHA, 'sourceDex': {'entry': 'classes2.dex', 'bytes': len(data), 'sha256': DEX_SHA},
              'numericParser': {'path': PREFLIGHT.relative_to(ROOT).as_posix(), 'sha256': PREFLIGHT_SHA},
              'originalAllHeaders': {'raw': ledger_path.relative_to(ROOT).as_posix(), 'sha256': sha(ledger_path), 'methodCount': len(ledger),
                                     'policy': 'Every original registers/ins/outs/tries/units header exact by identity except three explicitly listed units/tries changes; source outs unchanged even if overprovisioned. Absolute code/debug offsets relocate; debug presence/semantic target must preserve exact mapped original records.'},
              'hooks': selected, 'constructors': constructors, 'newDispatch': dispatch,
              'newField': {'identity': DMS + '->mOneOsGuestMetricsLifecycle:' + CELL, 'partition': 'instanceFields', 'accessFlags': 66, 'accessMeaning': 'PRIVATE|VOLATILE; root approved new field only for Binder-thread reference publication', 'initialValue': 'implicit null; no encoded initializer or constructor edit'},
              'sourceDebug': {'raw': debug_path.relative_to(ROOT).as_posix(), 'sha256': sha(debug_path)},
              'poolDebugIndexMaps': {'stringInsertionPositions': string_insertions, 'typeInsertionPositions': type_insertions,
                                     'rule': 'old nonnegative index plus number of declared insertion positions <= it; -1 absent stays -1'},
              'stringAndHapiGate': {'declaredNewStrings': source_preflight['newStrings'], 'maxProjectedShortStringIndex': 65534,
                                    'extraPrimaryDebugOrLoggerStringsForbidden': True, 'shortConstStringWideningsAllowed': 0,
                                    'rawHiddenApi': source_preflight['rawHiddenApi'], 'helperDefinitionsMergedIntoPrimary': False},
              'inverse': ['Delete only authored blocks and own catch entries; map all original PCs/targets/try boundaries/debug states back using exact tables',
                          'Remove declared field/method and exactly declared reference pools; no extra strings/metadata',
                          'Compare entire original normalized metadata/header/group/pool/debug/HAPI profile and admitted corrected no-edit canonical output; no baseline approval implied'],
              'openRuntimeGates': ['No retirement hook/control supplied', 'Actual current parent/source/phase/code/profile/loader admission unassembled',
                                   'Seven fixed-OFF guest helper definitions (Cell and two enums, Producer and Sample and marker, Endpoint) stay in a separate authored DEX under the actual DMS services loader; placement admission remains unselected',
                                   'ParentClient caller-side BOOT/loader binding is separate, future and unselected; it is not placed in the guest services loader by this contract',
                                   'Root-reviewed corrected no-edit baseline and this contract required before any original writer/producer'],
              'writerInvoked': False, 'modifiedOemBytesEmitted': False, 'oemExecuted': False, 'phoneChanged': False, 'toolSha256': tool_pin}
    for path, pin in PINS.items():
        if sha(ROOT / path) != pin:
            raise ValueError('Input changed during static planning: ' + path)
    if sha(ARCHIVE) != ARCHIVE_SHA or sha(PREFLIGHT) != PREFLIGHT_SHA or sha(__file__) != tool_pin:
        raise ValueError('Input/tool changed during static planning')
    (out / 'contract.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'inventory/guest-metrics-parent-hook-contract.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'hooks': 3, 'constructorsUnchanged': 3, 'originalHeaderMethods': len(ledger),
                      'debugEvents': sum(len(v['events']) for v in source_debug.values()), 'writerInvoked': False}))


if __name__ == '__main__':
    main()
