"""Compose two reviewed Settings code cuts into the held source-access DEX."""

import hashlib

from check_guest_fingerprint_preference_bind_retarget import FRAGMENT, load_readers
from prepare_guest_policy_init_retarget import code, expected_code, header
from preserve_dex_code_headers import seal


ORIGINAL_SHA = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
STRUCTURAL_SHA = 'edf71b9a7040ab9df3bd5e95dd50111a7b3c2add3369d4dd5b9cea0cbafe8dbe'
PRIOR_COMPOSED_SHA = 'c566e0f8c027404bd91250db0321afc5b92364102faf160c5358bea4dde82d40'
CUTS = (
    (FRAGMENT + '->addFingerprintItemPreferences(Ljava/util/List;)V',
     14225, 14235, 86, bytes(48), 0x187a7c, 0x3d8c1c,
     'c453a6106e58da7c80a8fb5f10f20db0adba20201b665faa93a5c5e9c7cd2c75'),
    ('Lcom/oplus/settings/utils/SysFeatureUtils;->isSupportPasswordRetrieve()Z',
     26158, 26175, 0, b'\x12\x00\x0f\x00', 0x262794, 0x4b3de4,
     '3e9246268b9c02c1346a9d5d191c3f5a6dd68e7b498412697c29d2153e79176a'),
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compose_dex(original: bytes, structural: bytes, prior_composed: bytes) -> tuple[bytes, dict]:
    """Return the DEX and proof as data. The caller owns any output publication."""
    for raw, size, sha in (
        (original, 5_737_616, ORIGINAL_SHA),
        (structural, 5_752_952, STRUCTURAL_SHA),
        (prior_composed, 5_737_616, PRIOR_COMPOSED_SHA),
    ):
        require(type(raw) is bytes and len(raw) == size and digest(raw) == sha,
                'Exact held Settings classes2.dex input required: ' + sha)

    dex = load_readers()['Dex']
    source, target = dex(original), dex(structural)
    source_rows = {row['descriptor']: row for row in source.codes}
    target_rows = {row['descriptor']: row for row in target.codes}
    index_maps = {kind: {value: idx for idx, value in enumerate(getattr(target, kind))}
                  for kind in ('strings', 'types', 'protos', 'fields', 'methods')}

    previous, merged = bytearray(original), bytearray(structural)
    proof = []
    for name, source_id, target_id, pc, patch, source_at, target_at, target_preimage in CUTS:
        require(source.methods[source_id] == target.methods[target_id] == name,
                'Relocated method ID differs: ' + name)
        source_row, target_row = source_rows[name], target_rows[name]
        source_code, target_code = code(source, source_row), code(target, target_row)
        start, end = 2 * pc, 2 * pc + len(patch)
        require(source_row['codeOffset'] + 16 + start == source_at
                and target_row['codeOffset'] + 16 + start == target_at
                and end <= len(source_code) == len(target_code),
                'Relocated method extent differs: ' + name)
        require(header(source, source_row) == header(target, target_row)
                and target_code == expected_code(source, target, source_row, False, index_maps),
                'Relocated symbolic preimage differs: ' + name)
        target_end = target_at + len(patch)
        owners = []
        for row in target.codes:
            code_at = row['codeOffset'] + 16
            code_end = code_at + 2 * target.u32(code_at - 4)
            if code_at < target_end and target_at < code_end:
                owners.append(row['descriptor'])
        require(owners == [name] and digest(target_code[start:end]) == target_preimage,
                'Relocated cut ownership or bytes differ: ' + name)
        previous[source_at:source_at + len(patch)] = patch
        merged[target_at:target_end] = patch
        proof.append({
            'method': name, 'sourceMethodId': source_id, 'structuralMethodId': target_id,
            'firstPc': pc, 'endExclusivePc': end // 2,
            'originalByteOffset': source_at, 'composedByteOffset': target_at,
            'structuralPreimageSha256': target_preimage, 'replacementSha256': digest(patch),
        })

    require(seal(previous) == prior_composed, 'Existing composition is not the exact two original cuts')
    output = seal(merged)
    # Whole-image inverse also checks every byte outside the cuts and integrity fields.
    restored = bytearray(output)
    for row, cut in zip(proof, CUTS):
        at, size = row['composedByteOffset'], len(cut[4])
        require(output[at:at + size] == cut[4], 'Composed cut readback differs')
        restored[at:at + size] = structural[at:at + size]
    require(seal(restored) == structural, 'Composed DEX does not invert to the exact structural input')
    dex(output)
    return output, {
        'sourceSha256': ORIGINAL_SHA, 'structuralSha256': STRUCTURAL_SHA,
        'priorComposedSha256': PRIOR_COMPOSED_SHA, 'outputSha256': digest(output),
        'outputBytes': len(output), 'cuts': proof, 'exactStructuralInverse': True,
        'priorOriginalCutsReproduced': True, 'selected': False,
    }
