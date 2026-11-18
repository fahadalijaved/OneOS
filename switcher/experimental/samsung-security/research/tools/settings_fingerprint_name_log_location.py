"""Locate the exact donor Settings fingerprint-name log slice in ordinary DEX039."""

from hashlib import sha256
import struct

from compose_coloros_ui_removals import instruction_owner
from preserve_dex_code_headers import Dex039, need


DEX_NAME = 'classes2.dex'
DEX_BYTES = 5_737_616
DEX_SHA256 = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
OWNER = 'Lcom/oplus/settings/feature/fingerprint/OplusFingerprintSettings$FingerprintSettingsFragment;'
METHOD = 'addFingerprintItemPreferences(Ljava/util/List;)V'
FIRST = 86
END = 110
RANGE_SHA256 = 'ac8ce72525f41e208a514a3a519b833d01bdf23e5ced0bee5b0fe2b310c17cd2'

_METHOD_ID = 14225
_CODE_OFFSET = 0x1879c0
_HEADER = (12, 2, 3, 0, 188)
_WIDTHS = {opcode: width for width, opcodes in (
    (1, (0x01, 0x0a, 0x0c, 0x0e, 0x12, 0x28, 0xb0)),
    (2, (0x1a, 0x1f, 0x22, 0x34, 0x35, 0x38, 0x39, 0x54, 0xd8)),
    (3, (0x14, 0x6e, 0x70, 0x71, 0x72)),
) for opcode in opcodes}
_CUT_OPCODES = (0x22, 0x70, 0x1a, 0x6e, 0x6e, 0x0c, 0x6e, 0x6e, 0x0c, 0x71)


def _signed(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def _instruction_boundaries(data, offset, count):
    words = struct.unpack_from(f'<{count}H', data, offset)
    opcodes = {}
    targets = []
    pc = 0
    while pc < count:
        opcode = words[pc] & 0xff
        width = _WIDTHS.get(opcode)
        need(width is not None and pc + width <= count, 'Unexpected selected Settings opcode or extent')
        opcodes[pc] = opcode
        if opcode == 0x28:
            targets.append(pc + _signed(words[pc] >> 8, 8))
        elif opcode in (0x34, 0x35, 0x38, 0x39):
            targets.append(pc + _signed(words[pc + 1], 16))
        pc += width
    need(FIRST in opcodes and END in opcodes and opcodes.get(count - 1) == 0x0e
         and tuple(op for pc, op in opcodes.items() if FIRST <= pc < END) == _CUT_OPCODES,
         'Fingerprint log cut does not match whole instruction boundaries')
    need(all(target in opcodes and not FIRST < target < END for target in targets),
         'Original branch enters the cut interior or an unaligned instruction')
    return len(opcodes), len(targets)


def locate(data):
    """Return (location, ownership) from the exact source DEX without writing it."""
    need(type(data) is bytes and len(data) == DEX_BYTES and sha256(data).hexdigest() == DEX_SHA256,
         'Expected the exact donor Settings classes2.dex')
    dex = Dex039(data)
    target = dex.methods.get(f'{OWNER}->{METHOD}'.encode('ascii'))
    need(target is not None and target['flags'] == 2 and target['partition'] == 'direct'
         and target['methodIndex'] == _METHOD_ID and target['codeOffset'] == _CODE_OFFSET
         and target['header'] == _HEADER, 'Exact private Settings target method differs')
    code = dex.codes[_CODE_OFFSET]
    registers, incoming, outgoing, tries, units = _HEADER
    instructions = _CODE_OFFSET + 16
    need(code['debugOffset'] == 0 and code['end'] == instructions + 2 * units,
         'Target instruction/try/debug extent differs')
    start, end = instructions + 2 * FIRST, instructions + 2 * END
    need((start, end) == (0x187a7c, 0x187aac) and sha256(data[start:end]).hexdigest() == RANGE_SHA256,
         'Exact fingerprint-name log bytes differ')
    instruction_count, branch_count = _instruction_boundaries(data, instructions, units)

    # Dex039 walks all encoded method entries and rejects partial code-item
    # overlap. Include each method's full code extent here to reject aliases.
    ranges = [(row['methodIndex'], row['codeOffset'], dex.codes[row['codeOffset']]['end'])
              for row in dex.methods.values() if row['codeOffset']]
    need(instruction_owner(ranges, start, end) == _METHOD_ID and len(ranges) == len(dex.codes),
         'An encoded method aliases the target or another code item')
    return ({'methodId': _METHOD_ID, 'codeOffset': _CODE_OFFSET, 'instructionsOffset': instructions,
             'instructionUnits': units, 'registers': registers, 'incomingWords': incoming,
             'outgoingWords': outgoing, 'tryItems': tries, 'debugInfoOffset': code['debugOffset'],
             'accessFlags': target['flags'], 'firstPc': FIRST, 'endExclusivePc': END,
             'byteStart': start, 'byteEndExclusive': end, 'rangeSha256': RANGE_SHA256,
             'decodedInstructions': instruction_count, 'checkedBranchTargets': branch_count},
            {'encodedMethods': len(dex.methods), 'codeBodies': len(ranges),
             'uniqueCodeItems': len(dex.codes), 'otherMethodOverlapCount': 0})
