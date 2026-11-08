"""Bounded candidate-donor property classification, not installed/runtime proof."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
MANIFEST = PARENT / 'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/coloros-manifest.jsonl.gz'
MANIFEST_SHA = '09281dbbdb34c7795b82f0913d2b3aea7beff63cbcc404c292b3df1cc5205c61'
RAW = ROOT / 'firmware/retained-property-minimal-cut'
WORK = ROOT / 'out/retained-property-minimal-cut'
ASSETS = ROOT / 'firmware/installed-oneos-code-profile/static/assets'
FOCUS = ['ro.secure', 'ro.debuggable', 'ro.control_privapp_permissions', 'persist.sys.disable_rescue',
         'persist.sys.enable_rescue', 'persist.sys.device_first_boot', 'ro.config.isolated_compilation_enabled',
         'ro.audio.ihaladaptervendorextension_enabled', 'ro.build.version.sdk', 'persist.sys.saupwk_test',
         'ro.product.first_api_level', 'ro.crypto.type', 'ro.crypto.state']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    check('literal indexed donor manifest', sha(MANIFEST) == MANIFEST_SHA)
    selected = {}
    with gzip.open(MANIFEST, 'rt') as stream:
        for text in stream:
            row = json.loads(text)
            parts = row['path'].split('/')
            if row['kind'] == 'file' and (row['path'] in ['system/build.prop', 'system_ext/etc/build.prop', 'product/etc/build.prop'] or
                                          len(parts) == 2 and parts[0].startswith('my_') and parts[1] == 'build.prop'):
                check('bounded candidate prop file size ' + row['path'], row['size'] <= 65536)
                selected[row['path']] = row
    check('eleven top-level candidate donor property files', len(selected) == 11)
    bag, pins = {}, {}
    for name, record in selected.items():
        path = PARENT / 'firmware/donor/extracted' / record['extractedPath']
        check('indexed candidate bytes ' + name, path.stat().st_size == record['size'] and sha(path) == record['sha256'])
        pins[str(path)] = record['sha256']
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip() or line.lstrip().startswith(('#', 'import ')) or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip().removesuffix('?')
            if re.fullmatch(r'[A-Za-z0-9._-]+', key):
                bag.setdefault(key, []).append({'member': name, 'line': number, 'value': value})
    for key, value in [('ro.secure', '0'), ('ro.debuggable', '1'), ('ro.control_privapp_permissions', 'disable'),
                       ('persist.sys.disable_rescue', 'true'), ('ro.config.isolated_compilation_enabled', 'true'),
                       ('ro.audio.ihaladaptervendorextension_enabled', 'true')]:
        check('candidate value only ' + key + '=' + value, any(row['value'] == value for row in bag.get(key, [])))
    old = ROOT / 'inventory/retained-property-view-plan.json'
    check('old property plan remains exact', sha(old) == 'c108299ed2b0b68a116d465af59c657bc393e2afb2f22ff609ab4b70b0cb8cce')
    assets = json.loads((ROOT / 'out/installed-oneos-code-profile/static/script-asset-pins.json').read_text())
    helper = ASSETS / 'guest_props.sh'
    start = ASSETS / 'guest_start.sh'
    check('exact installed helper', sha(helper) == assets['guest_props.sh']['sha256'] == 'f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a')
    check('exact installed start', sha(start) == assets['guest_start.sh']['sha256'] == '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446')
    lines = helper.read_text().splitlines()
    check('preserves host-defined names before candidate application', '(key in host)' in lines[146])
    check('generic crypto filter remains source', 'ro\\.crypto' in lines[153])
    check('attestation exclusion remains source', '/_for_attestation$/' in lines[158])
    start_lines = start.read_text().splitlines()
    check('unchanged launch guard requires disable_rescue true', 'persist.sys.disable_rescue' in start_lines[702])
    check('unchanged launch guard rejects enable_rescue true', 'persist.sys.enable_rescue' in start_lines[703])
    time_receipt = ROOT / 'out/tooling/20261106T051015979651Z-de65dd13ac4e41c4ba7b7e4226fcfff5/receipt.json'
    rec = json.loads(time_receipt.read_text())
    check('peer actual staged OPPO archive identity', rec['archiveSha256'] == 'a854468fec404a8950f8f3c651f869f19ded098bb244fbef26880c2ece141fa8')
    check('peer actual time body raw pin', sha(ROOT / rec['raw']) == rec['rawSha256'])
    body = next(x for x in map(json.loads, (ROOT / rec['raw']).read_text().splitlines()) if x.get('record') == 'method' and x['body']['signature'] == 'checkSystemTime()V')
    check('actual optional time setter at178', any(i['pc'] == 178 and 'SystemClock;->setCurrentTimeMillis' in i.get('reference', '') for i in body['body']['instructions']))
    ins = {i['pc']: i for i in body['body']['instructions']}
    check('actual first-boot property defaulttrue', ins[15]['opcode'] == 'CONST_4' and ins[15]['literal'] == 1 and ins[16]['registers'] == [3, 4])
    check('false first-boot flag can fall through independent old-clock test', ins[46]['opcode'] == 'IF_NEZ' and ins[46]['targetPc'] == 55 and ins[48]['literal'] == 50000000)
    check('old-clock comparison bypasses only when current clock is high enough', ins[51]['opcode'] == 'CMP_LONG' and ins[53]['opcode'] == 'IF_GEZ' and ins[53]['targetPc'] == 208)
    time_proof = {'receipt': str(time_receipt.relative_to(ROOT)), 'receiptSha256': sha(time_receipt),
                  'raw': rec['raw'], 'rawSha256': rec['rawSha256'], 'bodySha256': body['normalizedBodySha256']}
    wrapper_path = ROOT / 'out/tooling/20261106T051245115835Z-623b11c362b2443489a1657da9447971/receipt.json'
    check('immutable peer wrapper receipt', sha(wrapper_path) == '7f9efd408d13efcc6c619469384bf0b31614af7c683b22297083ab03be11fd2f')
    wr = json.loads(wrapper_path.read_text())
    check('actual staged wrapper raw', wr['archiveSha256'] == rec['archiveSha256'] and sha(ROOT / wr['raw']) == wr['rawSha256'])
    wb = next(x for x in map(json.loads, (ROOT / wr['raw']).read_text().splitlines()) if x.get('record') == 'method')
    check('exact optional pregetter wrapper shape', wb['body']['owner'] == 'Lcom/android/server/NetworkTimeUpdateServiceExtImpl;' and
          wb['body']['signature'] == 'checkSystemTime()V' and [(x['pc'], x['opcode']) for x in wb['body']['instructions']] ==
          [(0, 'INVOKE_DIRECT'), (3, 'MOVE_RESULT_OBJECT'), (4, 'INVOKE_INTERFACE'), (7, 'RETURN_VOID')])
    check('exact optional wrapper body pin', wb['normalizedBodySha256'] == 'fee9acf2def335b4f44020e5228547dd5145f6a6b7b591bdecf1eb4355ab163b')
    wrapper_proof = {'receipt': str(wrapper_path.relative_to(ROOT)), 'receiptSha256': sha(wrapper_path),
                     'raw': wr['raw'], 'rawSha256': wr['rawSha256'], 'bodySha256': wb['normalizedBodySha256']}
    RAW.mkdir(parents=True, exist_ok=True)
    raw = RAW / 'candidate-property-bag.json'
    raw.write_text(json.dumps({'schema': 'candidate-property-bag/v1', 'source': 'PC donor only; not installed/effective property manifest; no host absence inference',
                               'files': selected, 'properties': bag}, indent=2) + '\n')
    result = {'schema': 'retained-property-minimal-cut/v1', 'status': 'ADDITIVE_MINIMAL_CUT_FIRST_NO_PRIVATE_SERVICE_NECESSITY_PROVED',
              'selected': False, 'manifest': {'path': str(MANIFEST), 'sha256': MANIFEST_SHA}, 'donorInputPins': pins,
              'candidateFileCount': len(selected), 'candidateUniqueKeyCount': len(bag), 'candidateFocus': {k: bag.get(k, []) for k in FOCUS},
              'candidateEffectiveOrderSimulated': False, 'installedManifestProved': False, 'hostPropertyAbsenceProved': False,
              'candidateBag': {'path': str(raw.relative_to(ROOT)), 'sha256': sha(raw)},
              'oldPropertyPlanPin': {'path': str(old.relative_to(ROOT)), 'sha256': sha(old)},
              'scriptPins': {str(helper.relative_to(ROOT)): sha(helper), str(start.relative_to(ROOT)): sha(start)},
              'peerActualTimeConsumer': time_proof, 'peerExactPreGetterWrapper': wrapper_proof,
              'checks': checks, 'checkCount': len(checks),
              'approvedAdditiveKeySet': [], 'sourceClosedRequiredConflictingKeySet': [],
              'absenceMeaning': 'No set is asserted complete. No required conflict is established by these bounded inputs; zero approvals do not mean propertyless boot works.',
              'nextCut': 'Keep genuine host values and remove broad global apply/restore only together with reviewed guest writer/consumer replacements; first close optional OPPO clock action and actual guest rescue/privapp/native-control consumers. Consider isolated property service only after an actual required conflicting key/consumer remains.',
              'limits': ['No complete ColorOS startup or property read/write closure; no prefix implies host nonuse.',
                         'Candidate source exposes debug/security-relaxing values which must not replace genuine host security policy.',
                         'No image/property manifest/phone acquisition, script or OEM execution, property write or source hook change.',
                         'One exact RescueParty class query in staged services refused absent; actual module/registration owner remains open, not a proven removable method.'],
              'toolSha256': sha(Path(__file__)), 'phoneActions': [], 'propertiesWritten': False, 'oemExecuted': False}
    WORK.mkdir(parents=True, exist_ok=True)
    (ROOT / 'inventory/retained-property-minimal-cut.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': len(checks), 'candidateFiles': len(selected), 'candidateKeys': len(bag), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true', required=True)
    parser.parse_args()
    audit()
