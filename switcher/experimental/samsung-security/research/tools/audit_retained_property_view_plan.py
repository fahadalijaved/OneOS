"""Saved installed-script/property-body join; no runtime/property/tool execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'firmware/installed-oneos-code-profile/static/assets'
RAW = ROOT / 'firmware/retained-property-view-plan'
WORK = ROOT / 'out/retained-property-view-plan'
HOSTS = {'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
         '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'}
SCRIPT_PINS = {
    'guest_props.sh': 'f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a',
    'oneos_switch.sh': 'e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150',
    'guest_prepare.sh': '000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70',
    'guest_start.sh': '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446',
    'return_to_oneui.sh': '04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03',
}
INPUTS = ['authority-bootstrap-users', 'authority-bootstrap-storage', 'samsung-user-registry-owner',
          'retained-user-registry-binding', 'retained-guest-user-lifecycle', 'construction-credentials']
WANTED = {
    'Lcom/android/internal/os/RoSystemProperties;-><clinit>()V',
    'Landroid/sysprop/CryptoProperties;->state()Ljava/util/Optional;',
    'Landroid/sysprop/CryptoProperties;->type()Ljava/util/Optional;',
    'Lcom/android/server/locksettings/LockSettingsService;->isSupportWeaver()Z',
    'Lcom/android/server/locksettings/LockSettingsService;->isEnablePrevCredential()Z',
    'Lcom/android/server/locksettings/LockSettingsService;->maybeShowEncryptionNotificationForUser(ILjava/lang/String;)V',
    'Lcom/android/server/pm/UserManagerService;->isDefaultHeadlessSystemUserMode()Z',
    'Lcom/android/server/pm/UserManagerService;->isCreationOverrideEnabled()Z',
    'Lcom/android/server/pm/UserManagerService;->setContainerInfo()V',
    'Lcom/android/server/pm/UserTypeFactory;->getDefaultBuilders()Landroid/util/ArrayMap;',
    'Lcom/android/server/pm/PackageManagerService;-><init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    checks, inputs, receipts, raws, methods, raw_methods = [], {}, {}, {}, {}, []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    for name in INPUTS:
        p = ROOT / 'inventory' / (name + '.json')
        inputs[str(p.relative_to(ROOT))] = sha(p)
        data = json.loads(p.read_text())
        for path, pin in data.get('receiptPins', {}).items():
            assert sha(ROOT / path) == pin
            rec = json.loads((ROOT / path).read_text())
            if rec.get('archiveSha256') in HOSTS:
                receipts[path] = pin
                raws[rec['raw']] = (rec['rawSha256'], path, rec['archiveSha256'])
        for proof in data.get('methodProofs', {}).values():
            if isinstance(proof, dict) and 'receipt' in proof and 'raw' in proof:
                path = proof['receipt']
                rec = json.loads((ROOT / path).read_text())
                if rec.get('archiveSha256') in HOSTS:
                    receipts[path] = sha(ROOT / path)
                    raws[rec['raw']] = (rec['rawSha256'], path, rec['archiveSha256'])
    for path, (pin, receipt, archive) in raws.items():
        assert sha(ROOT / path) == pin
        for row in map(json.loads, (ROOT / path).read_text().splitlines()):
            if row.get('record') != 'method':
                continue
            body = row['body']
            key = body['owner'] + '->' + body['signature']
            if key not in WANTED:
                continue
            if key in methods:
                assert methods[key]['bodySha256'] == row['normalizedBodySha256']
                continue
            methods[key] = {'bodySha256': row['normalizedBodySha256'], 'raw': path, 'rawSha256': pin,
                            'receipt': receipt, 'receiptSha256': receipts[receipt], 'archiveSha256': archive,
                            'physicalDex': row['physicalDex'], 'logicalHeaderOffset': row['logicalHeaderOffset']}
            raw_methods.append(row)
    check('all11 narrowly selected original Samsung methods already captured; missing=' + repr(sorted(WANTED - set(methods))), set(methods) == WANTED)
    body_map = {m['body']['owner'] + '->' + m['body']['signature']: m['body'] for m in raw_methods}
    def at(fragment, pc, ref):
        body = next(v for k, v in body_map.items() if fragment in k)
        check(fragment + '@' + str(pc), any(i['pc'] == pc and ref in i.get('reference', '') for i in body['instructions']))
    for pc, ref in [(28, 'SystemProperties;->get'), (32, 'CONTROL_PRIVAPP_PERMISSIONS:'),
                    (99, 'CryptoProperties;->state'), (111, 'CRYPTO_STATE:'),
                    (113, 'CryptoProperties;->type'), (125, 'CRYPTO_TYPE:'),
                    (151, 'CONTROL_PRIVAPP_PERMISSIONS_LOG:'), (159, 'CONTROL_PRIVAPP_PERMISSIONS_ENFORCE:')]:
        at('RoSystemProperties;-><clinit>', pc, ref)
    at('CryptoProperties;->state()', 0, 'string=ro.crypto.state')
    at('CryptoProperties;->type()', 0, 'string=ro.crypto.type')
    at('LockSettingsService;->isSupportWeaver()', 0, 'string=security.securehw.available')
    at('LockSettingsService;->isSupportWeaver()', 4, 'SystemProperties;->getBoolean')
    at('LockSettingsService;->isEnablePrevCredential()', 0, 'string=ro.organization_owned')
    at('LockSettingsService;->isEnablePrevCredential()', 4, 'SystemProperties;->get')
    at('UserManagerService;->setContainerInfo()', 100, 'string=persist.sys.knox.userinfo')
    at('UserManagerService;->setContainerInfo()', 103, 'SystemProperties;->set')
    at('PackageManagerService;-><init>', 689, 'Build$VERSION;->DEVICE_INITIAL_SDK_INT:')
    scripts = {}
    asset_ledger = ROOT / 'out/installed-oneos-code-profile/static/script-asset-pins.json'
    check('frozen installed APK script asset ledger', sha(asset_ledger) == 'aa6548534b44c9a5978e320fd401c4274f88ff712180c022b196797f82decaf3')
    inputs[str(asset_ledger.relative_to(ROOT))] = sha(asset_ledger)
    assets = json.loads(asset_ledger.read_text())
    for name in ['guest_props.sh', 'oneos_switch.sh', 'guest_prepare.sh', 'guest_start.sh', 'return_to_oneui.sh']:
        path = ASSETS / name
        check('literal installed script ' + name, sha(path) == SCRIPT_PINS[name])
        assert assets[name]['sha256'] == SCRIPT_PINS[name]
        inputs[str(path.relative_to(ROOT))] = sha(path)
        scripts[name] = path.read_text().splitlines()
    selected_lines = []
    def line(name, number, text, label):
        actual = scripts[name][number - 1]
        check(label, text in actual)
        selected_lines.append({'asset': name, 'line': number, 'text': actual})
    for spec in [
        ('oneos_switch.sh', 311, 'persist.oneos.probe', 'global persist write/delete test precedes snapshot'),
        ('oneos_switch.sh', 320, 'snapshot-persist', 'persist snapshot before guest overrides'),
        ('oneos_switch.sh', 751, 'ro.control_privapp_permissions log', 'permission property changes before host stop'),
        ('oneos_switch.sh', 755, 'persist.sys.disable_rescue true', 'rescue global override'),
        ('oneos_switch.sh', 759, 'crashrecovery.rescue_boot_count 0', 'shared crash recovery reset'),
        ('oneos_switch.sh', 810, 'persist.sys.assert.panic true', 'ColorOS logging global property'),
        ('oneos_switch.sh', 814, 'persist.sys.oplus.aotcrash_controller_enabled false', 'ColorOS crash policy global override'),
        ('oneos_switch.sh', 971, 'ctl.stop zygote', 'old Java stop occurs later'),
        ('oneos_switch.sh', 1149, 'guest_props.sh', 'late guest property helper add'),
        ('guest_prepare.sh', 316, '--rbind /dev', 'device-tree bind is not independent property owner'),
        ('guest_props.sh', 147, '(key in host)', 'generic adds exclude host-defined names'),
        ('guest_props.sh', 154, 'ro\\.crypto', 'generic physical crypto/boot families filtered'),
        ('guest_props.sh', 159, '/_for_attestation$/', 'generic attestation keys filtered'),
        ('guest_props.sh', 181, '"$RP" -n "$BLUR" 1', 'explicit blur override bypasses no-existing-name rule'),
        ('guest_props.sh', 207, '"$RP" -n "$UCK" "$nuv"', 'explicit USB override'),
        ('guest_props.sh', 576, '"$RP" -n "$key" 0', 'explicit ColorOS first-boot property override'),
        ('guest_props.sh', 702, '"$RP" -n -f "$NEW"', 'generic manifest applied to shared area'),
        ('guest_props.sh', 727, '"$RP" -n "$key" "$g"', 'ringtone name explicit overrides'),
        ('guest_props.sh', 748, '"$RP" -n "$key" "$g"', 'audio extension explicit override'),
        ('guest_props.sh', 772, '"$RP" -n "$key" "$g"', 'conditional ABI explicit overrides'),
        ('guest_props.sh', 791, 'ro.boot.hardware qcom', 'conditional boot-hardware explicit override'),
        ('guest_props.sh', 803, '"$RP" -n "$key" false', 'isolated compilation explicit override'),
        ('guest_props.sh', 812, '"$RP" -n', 'remove restores override values'),
        ('guest_props.sh', 852, '-p --delete', 'remove can delete stored guest persist values'),
        ('guest_props.sh', 958, 'normal return', 'normal restore not restricted to guest allowlist'),
        ('guest_props.sh', 974, '--recover', 'new-key guest ownership filtering applies only on recovery'),
        ('guest_props.sh', 975, '-p --delete', 'normal restore deletes names absent from snapshot'),
        ('guest_props.sh', 983, '--recover', 'old-value guest ownership filtering applies only on recovery'),
        ('guest_props.sh', 984, '"$RP" -p "$key"', 'normal restore overwrites changed snapshot values'),
    ]:
        line(*spec)
    candidates = []
    literal_targets = {}
    for name, lines in scripts.items():
        for n, text in enumerate(lines, 1):
            if text.lstrip().startswith('#'):
                continue
            if re.search(r'\bsetprop\s+|\bset_prop\s+|"\$RP"\s+(?:-n\b|-p\b|--delete\b)', text):
                candidates.append({'asset': name, 'line': n, 'classification': 'syntactic mutation candidate; conditions/variables require original source'})
                selected_lines.append({'asset': name, 'line': n, 'text': text})
            for match in re.finditer(r'\b(?:setprop|set_prop)\s+([A-Za-z0-9_.-]+)\s+', text):
                literal_targets.setdefault(name, {}).setdefault(match[1], []).append(n)
    RAW.mkdir(parents=True, exist_ok=True)
    lifecycle = json.loads((ROOT / 'inventory/retained-guest-user-lifecycle.json').read_text())
    staged_key = 'stage:Lcom/android/server/pm/UserDataPreparer;->prepareUserDataLI(Ljava/lang/String;Landroid/content/pm/UserInfo;IZ)V'
    staged_proof = lifecycle['methodProofs'][staged_key]
    check('existing actual-stage CE property writer raw hash', sha(ROOT / staged_proof['raw']) == staged_proof['rawSha256'])
    staged = next(x for x in map(json.loads, (ROOT / staged_proof['raw']).read_text().splitlines()) if
                  x.get('record') == 'method' and staged_key.endswith(x['body']['owner'] + '->' + x['body']['signature']))
    check('existing actual-stage CE property writer body pin', staged['normalizedBodySha256'] == staged_proof['bodySha256'])
    for pc, reference in [(115, 'string=sys.user.'), (126, 'string=.ce_available'), (164, 'string=true'), (167, 'SystemProperties;->set')]:
        check('actual-stage CE property writer@' + str(pc), any(x['pc'] == pc and reference in x.get('reference', '') for x in staged['body']['instructions']))
    raw = RAW / 'selected-source.json'
    raw.write_text(json.dumps({'methods': raw_methods, 'actualStagedRuntimeWriter': staged, 'scriptLines': selected_lines}, indent=2) + '\n')
    native = ROOT / 'inventory/retained-installd-native-owner.json'
    check('frozen native property evidence', sha(native) == '14d15d212d09deffd0decd0a2c0657af79e15dedadaa7251322bfaa0da2f9f47')
    inputs[str(native.relative_to(ROOT))] = sha(native)
    result = {'schema': 'retained-property-view-plan/v1', 'status': 'NO_SHARED_AREA_COHERENCE_OR_PRIVATE_PROPERTY_OWNER_ADMITTED',
              'selected': False, 'inputs': inputs, 'methodProofs': methods, 'checkCount': len(checks), 'checks': checks,
              'syntacticMutationSites': candidates, 'syntacticMutationSiteCount': len(candidates),
              'literalSetpropTargets': literal_targets,
              'actualStagedRuntimeWriter': {'method': staged_key, **staged_proof},
              'rawSourceSlice': {'path': str(raw.relative_to(ROOT)), 'sha256': sha(raw)},
              'nativePropertySplit': {'persist.zygote.app_data_isolation': 'start@0x263e8 caches@0x263f8 after publication/thread startup',
                                      'persist.sys.fuse': 'invalidateMounts@0x3ef60 reads during rebuild; source view and property view distinct'},
              'concreteLostUpdateCounterexample': 'Samsung UMS.setContainerInfo writes persist.sys.knox.userinfo; normal guest_props restore-persist restores old snapshot or deletes newly added persist key, unable to distinguish legitimate retained-host writes.',
              'firstMissingOwner': 'Guest-native property-area/client/service initialization and write/persistence routing before first guest-specific global mutation and before guest static/native caches initialize.',
              'nextEngineeringCut': 'Prepare a source-bound guest property manifest without applying it globally; close exact guest native client/area/service bootstrap separately, leaving host canonical area and host persistent writer untouched. Hardware/init controls require explicit genuine shared ownership.',
              'limits': ['Eleven original Samsung source methods and installed script mutation candidates only, not complete framework/native/property reachability.',
                         'Actual guest image property manifests/runtime values and branch outcomes not captured here.',
                         'Five direct packaged scripts only; no exhaustive transitive helper, persistent background writer or generated/native sysprop consumer closure.',
                         'Generic filtering preserves host-defined/crypto/boot/attestation families; no proven current change to firstAPI/FBE/attestation policy inferred.',
                         'An already initialized static field is distinct from future direct SystemProperties/native queries; actual initialization generations unobserved.',
                         'No libc/property-service implementation/new tool/phone/property write/runtime executed.'],
              'toolSha256': sha(Path(__file__)), 'phoneActions': [], 'propertiesWritten': False, 'oemExecuted': False}
    WORK.mkdir(parents=True, exist_ok=True)
    (ROOT / 'inventory/retained-property-view-plan.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': len(checks), 'methods': len(methods), 'syntacticMutationSites': len(candidates), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true', required=True)
    parser.parse_args()
    audit()
