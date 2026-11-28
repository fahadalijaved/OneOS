"""Restore source outgoing-word extents after the static AMS writer."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from audit_guest_fingerprint_attach_pool import AMS, DEX_BYTES, DEX_SHA, OBSERVATION
from preserve_dex_code_headers import Dex039, _assert_byte_whitelist, seal


ROOT = Path(__file__).resolve().parents[1]
OUTER = AMS + b'->finishAttachApplication(JJ)V'
INNER = AMS + b'->finishAttachApplicationInner(JII)V'
CLONE = AMS + b'->finishAttachApplicationForFingerprintObservation(JII)' + OBSERVATION


def restore_headers(original, writer, *, writer_sha256):
    if len(original) != DEX_BYTES or sha256(original).hexdigest() != DEX_SHA:
        raise ValueError('Unexpected exact staged AMS source')
    if sha256(writer).hexdigest() != writer_sha256:
        raise ValueError('Unexpected static writer output')
    source, candidate = Dex039(original), Dex039(writer)
    if (source.classes != candidate.classes or candidate.methods.keys() != source.methods.keys() | {CLONE}
            or candidate.u32(88) != source.u32(88) + 2 or candidate.u32(80) != source.u32(80)):
        raise ValueError('Unexpected staged AMS class, method or field identity set')

    wants = {}
    for identity, actual in candidate.methods.items():
        expected = source.methods[INNER if identity == CLONE else identity]
        if any(actual[key] != expected[key] for key in ('flags', 'partition')):
            raise ValueError('Unexpected staged AMS method declaration change')
        old, new = expected['header'], actual['header']
        if old is None:
            if new is not None:
                raise ValueError('Unexpected staged AMS method code')
            continue
        regs, incoming, outgoing, tries, units = old
        if identity == OUTER:
            units += 1
        elif identity == CLONE:
            units += 14
        if (new is None or (new[0], new[1], new[3], new[4]) != (regs, incoming, tries, units)
                or new[2] > outgoing):
            raise ValueError('Unexpected staged AMS code header for ' + identity.decode('ascii', 'replace'))
        offset = actual['codeOffset'] + 4
        if wants.setdefault(offset, outgoing) != outgoing:
            raise ValueError('Conflicting outgoing-word bounds for shared code')

    changed = {offset: words for offset, words in wants.items() if candidate.u16(offset) != words}
    patched = bytearray(writer)
    for offset, words in changed.items():
        struct.pack_into('<H', patched, offset, words)
    final = seal(patched)
    _assert_byte_whitelist(writer, final, changed)
    check = Dex039(final)
    if any(check.u16(offset) != words for offset, words in wants.items()):
        raise ValueError('Outgoing-word readback differs')
    return final, {'checkedCodeItems': len(wants), 'restoredOutgoingWords': len(changed),
                   'outerHeader': check.methods[OUTER]['header'], 'cloneHeader': check.methods[CLONE]['header']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('writer', type=Path)
    parser.add_argument('writer_sha256')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    paths = tuple(path.absolute() for path in (args.original, args.writer, args.output))
    if any(path.resolve() != path or not path.is_relative_to(ROOT / 'firmware') for path in paths):
        parser.error('Use exact DEX paths within the ignored firmware tree')
    if paths[0].stat().st_size != DEX_BYTES or not 112 <= paths[1].stat().st_size <= 32 * 1024 * 1024:
        parser.error('Unexpected source or writer DEX extent')
    final, headers = restore_headers(paths[0].read_bytes(), paths[1].read_bytes(),
                                     writer_sha256=args.writer_sha256)
    with paths[2].open('xb') as stream:
        stream.write(final)
    print(json.dumps({'status': 'PASS_STATIC_GUEST_ATTACH_OUTGOING_WORD_READBACK_ONLY',
                      'sha256': sha256(final).hexdigest(), 'bytes': len(final), **headers}))


if __name__ == '__main__':
    main()
