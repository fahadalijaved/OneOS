"""Read back the two fixed donor PIN lifecycle inserts from ordinary DEX bytes."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from preflight_guest_metrics_parent_payload import Dex


OWNER = 'Lcom/oplus/keyguard/security/view/OplusKeyguardAbsKeyInputViewController;'
BRIDGE = OWNER + '->oneos$retirePinAtLifecycleEntry(' + OWNER + ')V'
SOURCE_SHA = '793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071'
MAX_DEX_BYTES = 64 * 1024 * 1024
# Signature, cut, code offset, access, raw code_item header, raw code_item SHA-256.
SITES = (
    ('onPause()V', 0, 4331620, 0x1, (2, 1, 1, 0, 0, 21),
     '2350237fac6a63df8858b779982e432f9b5b361977c1ecc7b1c4c70b6189daa9'),
    ('verifyPasswordAndUnlock()V', 5, 4332368, 0x11, (5, 1, 5, 0, 0, 33),
     '8e5d5d76ee27d5308ac88f30f812931778148e115d79360d6d1e48047cedc583'),
)
REF_POOLS = {0x1f: 'types', 0x54: 'fields', 0x55: 'fields', 0x5b: 'fields',
             0x62: 'fields', 0x6e: 'methods', 0x6f: 'methods'}
WIDTHS = {0x0c: 1, 0x0e: 1, 0x12: 1, 0x38: 2, 0x1f: 2, 0x54: 2,
          0x55: 2, 0x5b: 2, 0x62: 2, 0x6e: 3, 0x6f: 3}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_dex(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_DEX_BYTES + 1)
    require(112 <= len(raw) <= MAX_DEX_BYTES, 'DEX input size bound')
    return raw


def body(dex, signature, access, expected):
    descriptor = OWNER + '->' + signature
    hits = [method for method in dex.members if method['descriptor'] == descriptor]
    require(len(hits) == 1, 'Expected one selected declaration: ' + descriptor)
    method = hits[0]
    require(method['partition'] == 'virtualMethods' and method['accessFlags'] == access,
            'Selected method partition/access drift: ' + descriptor)
    offset = method['codeOffset']
    require(offset and offset % 4 == 0, 'Selected code item alignment: ' + descriptor)
    require(sum(other['codeOffset'] == offset for other in dex.codes) == 1,
            'Selected code item is aliased: ' + descriptor)
    sections = [row['offset'] for row in dex.map if row['type'] == 0x2001]
    require(len(sections) == 1, 'Expected one code item map section')
    start = sections[0]
    end = min((row['offset'] for row in dex.map if row['offset'] > start), default=len(dex.d))
    units = expected[-1]
    require(start <= offset and offset + 16 + 2 * units <= min(end, len(dex.d)),
            'Selected code item extent: ' + descriptor)
    header = struct.unpack_from('<4H2I', dex.d, offset)
    require(header == expected, 'Selected raw header drift: ' + descriptor)
    words = struct.unpack_from(f'<{units}H', dex.d, offset + 16)
    return offset, words


def baseline(raw):
    require(sha(raw) == SOURCE_SHA, 'Exact donor SystemUI classes3.dex required')
    dex = Dex(raw)
    require(BRIDGE not in dex.methods, 'Bridge reference exists in original donor')
    selected = {}
    for signature, cut, expected_offset, access, header, code_sha in SITES:
        offset, words = body(dex, signature, access, header)
        require(offset == expected_offset and sha(raw[offset:offset + 16 + 2 * len(words)]) == code_sha,
                'Original code item drift: ' + signature)
        if cut:
            require(words[2:5] == (0x0038, 3, 0x000e), 'Original submit guard/return drift')
        else:
            require(words[:3] == (0x106f, 0xaf71, 1) and words[5:7] == (0x0038, 5),
                    'Original pause super/timer drift')
        selected[signature] = words
    return dex, selected


def inverse_words(old, new, original, candidate, cut):
    # Walk source instruction boundaries. Only symbolic reference indices can differ.
    restored = list(candidate[:cut] + candidate[cut + 3:])
    pc = 0
    while pc < len(original):
        opcode = original[pc] & 0xff
        width = WIDTHS.get(opcode, 0)
        require(width and pc + width <= len(original), 'Unexpected original instruction shape')
        require(restored[pc] == original[pc], 'Original opcode/register word drift at PC ' + str(pc))
        kind = REF_POOLS.get(opcode)
        if kind:
            old_pool, new_pool = getattr(old, kind), getattr(new, kind)
            old_index, new_index = original[pc + 1], restored[pc + 1]
            require(new_index < len(new_pool) and new_pool[new_index] == old_pool[old_index],
                    'Original symbolic reference drift at PC ' + str(pc))
            restored[pc + 1] = old_index
        pc += width
    require(tuple(restored) == original, 'Original operand/branch words drift after inverse')


def check(old_raw, new_raw):
    old, selected = baseline(old_raw)
    require(112 <= len(new_raw) <= MAX_DEX_BYTES, 'Candidate DEX size bound')
    new = Dex(new_raw)
    require(new.methods.count(BRIDGE) == 1, 'Exact unique bridge method reference required')
    bridge_index = new.methods.index(BRIDGE)
    require(bridge_index <= 0xffff, 'Bridge method index exceeds invoke-static encoding')
    definitions = [method for method in new.codes if method['descriptor'] == BRIDGE]
    require(len(definitions) == 1 and definitions[0]['partition'] == 'directMethods'
            and definitions[0]['accessFlags'] & 0xf == 0xa,
            'Bridge must be a coded private static method on the original controller')
    sites = []
    for signature, cut, old_offset, access, header, _ in SITES:
        regs, ins, outs, tries, debug, units = header
        receiver = regs - ins
        new_offset, candidate = body(new, signature, access, (regs, ins, outs, tries, debug, units + 3))
        require(candidate[cut:cut + 3] == (0x1071, bridge_index, receiver),
                'Expected exact three-unit invoke-static with the original receiver: ' + signature)
        if cut:
            # The old branch still lands at PC 5, which now starts the call, not the relocated iget.
            require(candidate[2:5] == (0x0038, 3, 0x000e), 'Submit must branch to bridge and preserve PC 4 return')
        else:
            require(candidate[8:10] == (0x0038, 5), 'Pause timer branch target changed')
        inverse_words(old, new, selected[signature], candidate, cut)
        sites.append({'method': OWNER + '->' + signature, 'oldCodeOffset': old_offset,
                      'newCodeOffset': new_offset, 'cutPc': cut, 'resumeOriginalAtPc': cut + 3,
                      'registersSize': regs, 'insSize': ins, 'outsSize': outs, 'receiver': receiver,
                      'triesSize': tries, 'debugInfoOffset': debug, 'oldCodeUnits': units,
                      'newCodeUnits': units + 3, 'exactInverseWords': True})
    return {'status': 'PASS_TWO_LIFECYCLE_CALL_SITES_ONLY', 'originalDexSha256': SOURCE_SHA,
            'candidateDexSha256': sha(new_raw), 'bridgeReference': BRIDGE, 'sites': sites}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(read_dex(args.original), read_dex(args.candidate)), indent=2))


if __name__ == '__main__':
    main()
