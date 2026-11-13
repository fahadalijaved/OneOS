"""Verify the saved VIEW host APK and its selected app from public bytes."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile

from check_guarded_stage_bundle import Dex, require


ROOT = Path(__file__).resolve().parents[1]
APP = 'out/retained-view-ingress/r-f5883e23/apk-receipt.json'
DEX = 'out/retained-view-ingress-host-dex/r-1f7af7d81f40/receipt.json'
SDK = 'out/retained-view-ingress-build/r-2dc4e293/receipt.json'
OLD = 'out/retained-guard-module-preparation/r-ea9310713eea/OneOS-Retained-Guard-Host-debug.apk'
OLD_SHA = '2d05cb9b4f9817894dbdb37724ad9cde4af41fcf77300841169489dbae00bafe'
OLD_CERT = '81e516ed4312eeb0e0e57bacc55618acff32aabf5f2ee4a14eac256e2ce927dd'
VIEW = b'Lcom/fahadali/oneos/core/root/RetainedViewAppProtocol;'
VIEW_CONSTANTS = {'APP_VIEW_PREPARE': 3, 'APP_VIEW_STOP': 4, 'APP_VIEW_STATUS': 5,
                  'UNAVAILABLE': 0, 'QUEUED': 1, 'UNCERTAIN': -1,
                  **{'STATUS_' + name: i for i, name in enumerate((
                      'PENDING', 'PARTIAL', 'NEED_STAGE', 'REFUSED', 'CLOSING', 'CLEANUP_UNCONFIRMED',
                      'LOCAL_TERMINAL', 'LOCAL_CLEANUP_OBSERVED', 'STOPPED_BEFORE_DISPATCH', 'UNAVAILABLE'))}}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, expected):
    raw = (ROOT / path).read_bytes()
    require(sha(raw) == expected, f'Saved pin differs: {path}')
    return raw


def receipt(path, expected):
    return json.loads(read(path, expected))


def lp(data, offset=0):
    size = struct.unpack_from('<I', data, offset)[0]
    start = offset + 4
    require(size <= len(data) - start, 'Signing record length exceeds its envelope')
    return data[start:start + size], start + size


def only_lp(data):
    value, end = lp(data)
    require(end == len(data), 'Unexpected extra signing record')
    return value


def der(data, offset):
    tag, size = data[offset:offset + 2]
    start = offset + 2
    if size >= 128:
        width = size & 127
        require(1 <= width <= 4, 'Unexpected DER length width')
        size = int.from_bytes(data[start:start + width], 'big')
        start += width
    end = start + size
    require(end <= len(data), 'DER record out of bounds')
    return tag, data[start:end], end


def der_sequence(data):
    tag, body, end = der(data, 0)
    require(tag == 0x30 and end == len(data), 'Expected a complete DER sequence')
    return body


def certified_spki(certificate):
    body = der_sequence(certificate)
    tag, tbs, _ = der(body, 0)
    require(tag == 0x30, 'Expected TBSCertificate')
    pos = der(tbs, 0)[2] if tbs[0] == 0xa0 else 0
    for _ in range(5):  # serial, signature algorithm, issuer, validity, subject
        pos = der(tbs, pos)[2]
    require(tbs[pos] == 0x30, 'Expected certificate public key')
    return tbs[pos:der(tbs, pos)[2]]


def signature_v3(raw):
    eocd = raw.rfind(b'PK\x05\x06', max(0, len(raw) - 65557))
    require(eocd >= 0 and eocd + 22 + struct.unpack_from('<H', raw, eocd + 20)[0] == len(raw),
            'APK EOCD framing')
    central = struct.unpack_from('<I', raw, eocd + 16)[0]
    require(24 <= central < eocd and raw[central-16:central] == b'APK Sig Block 42', 'APK Signing Block framing')
    size = struct.unpack_from('<Q', raw, central - 24)[0]
    start = central - size - 8
    require(start >= 0 and struct.unpack_from('<Q', raw, start)[0] == size, 'APK Signing Block size')
    pos, blocks = start + 8, {}
    while pos < central - 24:
        length, key = struct.unpack_from('<QI', raw, pos)
        require(length >= 4 and pos + 8 + length <= central - 24 and key not in blocks, 'APK Signing Block entry')
        blocks[key] = raw[pos + 12:pos + 8 + length]
        pos += 8 + length
    require(pos == central - 24 and set(blocks) == {0x7109871a, 0xf05368c0, 0x42726577},
            'Unexpected scheme or supplemental signing block')
    signer = only_lp(only_lp(blocks[0xf05368c0]))
    signed, pos = lp(signer)
    sdk = struct.unpack_from('<II', signer, pos)
    signatures, pos = lp(signer, pos + 8)
    public_key, pos = lp(signer, pos)
    require(pos == len(signer) and sdk[0] <= 37 <= sdk[1], 'V3 signer does not cover target API')
    signature = only_lp(signatures)
    require(struct.unpack_from('<I', signature)[0] == 0x0103, 'Expected RSA PKCS1 SHA256 signature')
    signature = only_lp(signature[4:])
    digests, pos = lp(signed)
    certs, pos = lp(signed, pos)
    require(struct.unpack_from('<II', signed, pos) == sdk, 'Unsigned and signed SDK ranges differ')
    attrs, end = lp(signed, pos + 8)
    require(end == len(signed) and not attrs, 'Unexpected v3 additional attribute or lineage')
    certificate = only_lp(certs)
    require(certified_spki(certificate) == public_key, 'V3 signing key differs from certificate')
    spki = der_sequence(public_key)
    tag, _, pos = der(spki, 0)
    bits_tag, bits, end = der(spki, pos)
    require(tag == 0x30 and bits_tag == 3 and bits[0] == 0 and end == len(spki), 'Invalid RSA public key')
    key = der_sequence(bits[1:])
    n_tag, n, pos = der(key, 0)
    e_tag, e, end = der(key, pos)
    modulus, exponent = int.from_bytes(n, 'big'), int.from_bytes(e, 'big')
    require(n_tag == e_tag == 2 and end == len(key) and modulus.bit_length() == 3072 and exponent == 65537,
            'Unexpected debug RSA profile')
    width = (modulus.bit_length() + 7) // 8
    encoded = bytes.fromhex('3031300d060960864801650304020105000420') + hashlib.sha256(signed).digest()
    sig = int.from_bytes(signature, 'big')
    require(len(signature) == width and sig < modulus and pow(sig, exponent, modulus).to_bytes(width, 'big') ==
            b'\x00\x01' + b'\xff' * (width - len(encoded) - 3) + b'\x00' + encoded, 'V3 signature did not verify')
    eocd_bytes = bytearray(raw[eocd:])
    struct.pack_into('<I', eocd_bytes, 16, start)
    chunks = []
    for section in (raw[:start], raw[central:eocd], eocd_bytes):
        for offset in range(0, len(section), 1024 * 1024):
            part = section[offset:offset + 1024 * 1024]
            chunks.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(part)) + part).digest())
    expected = hashlib.sha256(b'\x5a' + struct.pack('<I', len(chunks)) + b''.join(chunks)).digest()
    digest = only_lp(digests)
    require(struct.unpack_from('<I', digest)[0] == 0x0103 and only_lp(digest[4:]) == expected,
            'V3 APK content digest did not verify')
    return {'certificateSha256': sha(certificate), 'publicKeySha256': sha(public_key), 'verifiedV3': True,
            'v3SdkRange': sdk, 'v3AdditionalAttributes': 0, 'schemeBlockIds': [hex(k) for k in blocks]}


def verify(apk, expected_sha):
    require(not Path(apk).is_absolute() and '..' not in Path(apk).parts and Path(apk).parts[0] == 'out',
            'Expected a saved repository-local APK')
    sdk = receipt(SDK, '621a3f712028582463e5cbd3500bfd49cf87c53910689b72d6596df49dd60f44')
    dex = receipt(DEX, '9554b9c0da952f340e72491c03cabd0aa2d6a09a77117a7f52d8a640bd12e7fd')
    app = receipt(APP, '82b189032640633f9f5161ea5045e74bc8a9a3c3f9b99788d408b45a99625ad9')
    require(dex['sdkReceipt']['path'] == SDK and dex['programClasses'] ==
            {name: rec['sha256'] for name, rec in sdk['cohorts']['host']['classes'].items()}, 'Host program input differs')
    for name, hash_value in dex['programClasses'].items():
        read(sdk['cohorts']['host']['classDirectory'] + '/' + name, hash_value)
    require(all(row['exitCode'] == 0 and row['ownedProcessReaped'] for row in
                [*sdk['commands'].values(), *dex['commands'].values()]), 'Saved compile/D8 terminal differs')
    app_raw = read(app['apk']['path'], '57cd32299db8561f10f4c7031d1754860926bf9b60a71f42bd52c9ffacac95fb')
    protocol_members = []
    with zipfile.ZipFile(io.BytesIO(app_raw)) as archive:
        require(sha(archive.read('assets/root/oneos_retained_root_handoff')) == app['apk']['packagedNativeSha256'],
                'App native asset differs')
        for member in app['apk']['dex']:
            raw = archive.read(member)
            require(sha(raw) == app['apk']['dex'][member]['sha256'], 'App DEX input differs')
            if VIEW in raw:
                parsed = Dex(raw)
                if VIEW in parsed.classes:
                    parsed.constants(VIEW, VIEW_CONSTANTS)
                    protocol_members.append(member)
    require(len(protocol_members) == 1, 'Expected exactly one app-side VIEW protocol')

    raw, old = read(apk, expected_sha), read(OLD, OLD_SHA)
    signature = signature_v3(raw)
    require(signature_v3(old)['certificateSha256'] == OLD_CERT, 'Old signer differs')
    payloads = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive, zipfile.ZipFile(io.BytesIO(old)) as prior:
        names = archive.namelist()
        require(len(names) == 6 and len(set(names)) == 6 and set(names) == set(prior.namelist()),
                'Exact six host module payload names required')
        for entry in archive.infolist():
            offset = entry.header_offset
            require(raw[offset:offset + 4] == b'PK\x03\x04' and entry.compress_type == 0, 'Unexpected local ZIP entry')
            lengths = struct.unpack_from('<HH', raw, offset + 26)
            require((offset + 30 + sum(lengths)) % 4 == 0, 'Stored entry is not four-byte aligned')
            data = archive.read(entry)
            payloads[entry.filename] = {'sha256': sha(data), 'bytes': len(data)}
            if entry.filename != 'classes.dex':
                require(data == prior.read(entry.filename), f'Host module metadata differs: {entry.filename}')
                continue
            require(data == read(dex['dex']['path'], '54955e1321d252deb20947c9b10933f3639e31b89b1a03522a7156c95725c745'),
                    'Packaged host DEX differs from exact saved D8 bytes')
            parsed = Dex(data)
            expected = {('L' + name.removesuffix('.class') + ';').encode() for name in dex['programClasses']}
            require(len(expected) == 47 and parsed.classes.keys() == expected, 'Unexpected host DEX closure')
            parsed.constants(VIEW, VIEW_CONSTANTS)

    return {'status': 'PASS_SAVED_HOST_APK_AND_APP_PAIR_ONLY', 'apk': {'path': apk, 'sha256': sha(raw), 'bytes': len(raw)},
            'pairedAppSha256': sha(app_raw), 'appProtocolPhysicalDex': protocol_members[0], 'hostClasses': 47,
            'payloads': payloads, 'unchangedManifestIdentity': {'package': 'com.appleexploit.oneos.security.retainedguard',
                'versionCode': 1, 'versionName': '0.0.1-source-only', 'minSdk': 37, 'targetSdk': 37},
            'signature': signature, 'priorHostCertificateSha256': OLD_CERT,
            'matchesPriorHostSigner': signature['certificateSha256'] == OLD_CERT,
            'signatureCompatibleWithPriorHost': signature['certificateSha256'] == OLD_CERT,
            'installedActivatedOrExecuted': False}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--apk', required=True, help='repository-relative path to the actual new host APK')
    cli.add_argument('--sha256', required=True, help='exact saved APK SHA-256')
    args = cli.parse_args()
    print(json.dumps(verify(args.apk, args.sha256), indent=2))
