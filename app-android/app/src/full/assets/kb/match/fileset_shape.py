"""Compare code across compiler-inserted arm64e authentication checks.

This only normalizes analysis. Emitted instructions keep every native check.
"""
import struct

from kc_image import scan, signed


def checked_shape(code, pc):
    words = list(struct.unpack('<' + 'I' * (len(code) // 4), code))
    removed = set()
    for i in range(len(words)):
        # mov x17,x16; xpac[di] x17; cmp x16,x17; b.eq +8;
        # brk #0xc47[02]. Only accept the complete compiler sequence.
        block = words[i:i + 5]
        if block in ([0xaa1003f1, 0xdac147f1, 0xeb11021f, 0x54000040, 0xd4388e40],
                     [0xaa1003f1, 0xdac143f1, 0xeb11021f, 0x54000040, 0xd4388e00]):
            # AUTIA/AUTDA x16,x17 must immediately precede the check.
            if i and words[i - 1] in (0xdac11230, 0xdac11a30):
                removed.update(range(i, i + 5))
        # Compiler's LR authentication check before a tail branch.
        if (words[i:i + 3] == [0xca1e07d0, 0xb6f00050, 0xd4388e20] and
                i + 3 < len(words) and words[i + 3] & 0xfc000000 == 0x14000000):
            removed.update(range(i, i + 3))

    calls, refs, shape = scan(code, pc)
    positions = {i * 4: j * 4 for j, i in enumerate(i for i in range(len(words)) if i not in removed)}
    normalized = []
    for i, word in enumerate(words):
        if i in removed:
            continue
        bits, shift = (26, 0) if word & 0x7c000000 == 0x14000000 else \
                      (19, 5) if word & 0xff000010 == 0x54000000 or word & 0x7e000000 == 0x34000000 else \
                      (14, 5) if word & 0x7e000000 == 0x36000000 else (0, 0)
        value = shape[i]
        if bits:
            mask = (1 << bits) - 1
            target = i * 4 + signed((word >> shift) & mask, bits) * 4
            if 0 <= target < len(code):
                if target not in positions:
                    # Another edge enters a check: it is not disposable padding.
                    return shape, {j * 4: j * 4 for j in range(len(words))}, calls, refs
                immediate = (positions[target] - positions[i * 4]) // 4
                value = (word & ~(mask << shift)) | ((immediate & mask) << shift)
        normalized.append(value)
    return normalized, positions, calls, refs
