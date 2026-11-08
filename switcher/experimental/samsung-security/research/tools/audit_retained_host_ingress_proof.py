"""Finite saved-source ingress readback; no OEM/phone calls or new collection."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/retained-host-ingress-proof'
PINS = {
 'inventory/authority-bootstrap-biometrics.json': 'b48f5fc8befb334ee41396fa356c29981e55dc560d8ad63eae2605af193f3d8a',
 'inventory/security-policy-owner.json': '9c0cd0207479795c632adaabb6c2c90f17b9a3f3a22ffeb1ee074b8a119a869b',
 'inventory/authority-bootstrap-policy.json': 'df78da9e85e05dd1528d69f6a7a51742be94e6fdc886cbe0d717c12c3baff640',
 'inventory/authority-bootstrap-users.json': '3be21cf44efd85ccd56ba75d4ec7cfe95070f34cdfba00dc5bc0efa8dd5f8b91',
 'inventory/retained-authority-dependencies.json': 'efbc601283878491fb3f4e159117f9b1c5b096fd649466aef483da43a0d004c8',
 'inventory/retained-process-lifetime-plan.json': '1cb63f9cdffd4cbb25e269499653039978eaa83869d3473c8a1bfa6fa4ee745b',
 'inventory/retained-display-handoff-plan.json': '59345160698fd7ed715c4c33182c4015c9f2bf8dff21e615ecc9df9ab34204ff',
 'firmware/authority-bootstrap-biometrics/20261105T184840373323Z-6781c5f2afc14a88a05120eff56fb4a1.jsonl': '75aeeacaf37a3acc381a6d3abc8f6febd3f3a6d76390dac77d9d79eea2e952bc',
 'firmware/security-policy-owner/20261105T194910589452Z-25b359968399445f81de6db032d7fb5d.jsonl': '86094232074da6b4b4af7d4fb29a67d42d1e28d562d473304b4f34ff6c9a725b',
 'firmware/authority-bootstrap-users/20261105T185029827311Z-55fd8bbc34b842faa4b6735d135105fc.jsonl': 'a79d0099f2e677bc0bf36149df9b19623104fe56d13f03ba641f24c8ca569425',
 'firmware/authority-bootstrap-policy/20261105T185808503261Z-434c980ae4e347f79c1ab8c85fc3ae43.jsonl': 'c6584cf3cb6c3fb4fcdd9a42ad80d6b5b2e16b74b23e9def80854bf696650f8d',
 'firmware/retained-user-registry-binding/20261106T020655056809Z-bc0b59b23a284a55ac064d4e5034af5e.jsonl': '612d16d3c8812a7cdc8850d24e1b294dc72528ff4702d1c1424782f6b96ba875',
 'firmware/installed-oneos-code-profile/static/assets/oneos_switch.sh': 'e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150',
 'firmware/installed-oneos-code-profile/static/assets/return_to_oneui.sh': '04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03',
}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def method(path, owner, signature):
    rows = [json.loads(line) for line in (ROOT / path).read_text().splitlines()]
    found = [row for row in rows if row.get('record') == 'method'
             and row['body']['owner'] == owner and row['body']['signature'] == signature]
    assert len(found) == 1
    return found[0]


def edge(record, pc, suffix):
    instruction = next(item for item in record['body']['instructions'] if item['pc'] == pc)
    assert instruction.get('reference', '').endswith(suffix), (pc, suffix)
    return {'owner': record['body']['owner'], 'signature': record['body']['signature'],
            'bodySha256': record['normalizedBodySha256'], 'pc': pc,
            'reference': instruction['reference']}


def main():
    assert all(sha(ROOT / name) == pin for name, pin in PINS.items())
    bio = 'firmware/authority-bootstrap-biometrics/20261105T184840373323Z-6781c5f2afc14a88a05120eff56fb4a1.jsonl'
    bind = method(bio, 'Lcom/android/server/biometrics/SemBiometricSysUiManager;', 'bind()V')
    opened = method(bio, 'Lcom/android/server/biometrics/SemBiometricSysUiManager;', 'openSession(Ljava/lang/String;Lcom/android/server/biometrics/SemBiometricSysUiManager$SysUiListener;)I')
    edges = [edge(opened, 120, '->bind()V'), edge(bind, 57, '->bindService(Landroid/content/Intent;ILjava/util/concurrent/Executor;Landroid/content/ServiceConnection;)Z'),
             edge(bind, 61, '->mIsWaitingForConnection:Z'), edge(bind, 69, '->postDelayed(Ljava/lang/Runnable;J)Z')]
    ins = {item['pc']: item for item in bind['body']['instructions']}
    assert ins[38]['reference'] == 'string=com.samsung.android.biometrics.app.setting'
    assert ins[41]['reference'] == 'string=com.samsung.android.biometrics.app.setting.BiometricsUIService'
    assert ins[54]['literal'] == 603979777 and ins[60]['opcode'] == 'CONST_4' and ins[67]['literal'] == 3000
    policy = 'firmware/security-policy-owner/20261105T194910589452Z-25b359968399445f81de6db032d7fb5d.jsonl'
    for signature, pc in [('reportFailedPasswordAttempt(IZ)V', 131), ('reportPasswordChanged(Landroid/app/admin/PasswordMetrics;I)V', 136)]:
        record = method(policy, 'Lcom/android/server/devicepolicy/DevicePolicyManagerService;', signature)
        edges.append(edge(record, pc, '->sendAdminCommandForLockscreenPoliciesLocked(IILjava/lang/String;)V'))
    supervision = method('firmware/authority-bootstrap-users/20261105T185029827311Z-55fd8bbc34b842faa4b6735d135105fc.jsonl',
                         'Lcom/android/server/supervision/SupervisionService;', '<init>(Lcom/android/server/supervision/SupervisionService$Injector;)V')
    edges += [edge(supervision, 113, '->addUserLifecycleListener(Lcom/android/server/pm/UserManagerInternal$UserLifecycleListener;)V'),
              edge(supervision, 153, '->addOnRoleHoldersChangedListenerAsUser(Ljava/util/concurrent/Executor;Landroid/app/role/OnRoleHoldersChangedListener;Landroid/os/UserHandle;)V')]
    receiver = method('firmware/authority-bootstrap-policy/20261105T185808503261Z-434c980ae4e347f79c1ab8c85fc3ae43.jsonl',
                      'Lcom/android/server/supervision/SupervisionService$Lifecycle$ProfileOwnerBroadcastReceiver;',
                      'onReceive(Landroid/content/Context;Landroid/content/Intent;)V')
    edges.append(edge(receiver, 4, '->getSendingUserId()I'))
    declaration_path = 'firmware/retained-user-registry-binding/20261106T020655056809Z-bc0b59b23a284a55ac064d4e5034af5e.jsonl'
    ams = next(row for row in map(json.loads, (ROOT / declaration_path).read_text().splitlines())
               if row.get('record') == 'class' and row['descriptor'] == 'Lcom/android/server/am/ActivityManagerService;')
    names = {'bindService', 'bindServiceInstance', 'startService', 'broadcastIntent', 'broadcastIntentWithFeature',
             'startActivity', 'startActivityAsUser', 'startActivityWithFeature'}
    declared = [item for item in ams['methods'] if item['signature'].split('(')[0] in names]
    assert {item['signature'].split('(')[0] for item in declared} == names
    scripts = []
    for file, line, fragment in [('oneos_switch.sh', 971, 'ctl.stop zygote'), ('oneos_switch.sh', 999, 'pidof system_server'),
                                  ('oneos_switch.sh', 1011, 'while true'), ('return_to_oneui.sh', 225, 'system_server')]:
        path = 'firmware/installed-oneos-code-profile/static/assets/' + file
        text = (ROOT / path).read_text().splitlines()[line - 1]
        assert fragment in text
        scripts.append({'path': path, 'line': line, 'sourceSha256': PINS[path],
                        'fact': 'Broad stop/kill or keeper; not semantic foreground ingress admission'})
    doc = ROOT / 'docs/retained-host-ingress-proof.md'
    result = {'schema': 'retained-host-ingress-readiness/v1',
              'status': 'KNOWN_REQUIRED_REQUEST_ROOTS; COMPLETE_HOST_INGRESS_POLICY_NOT_IMPLEMENTATION_READY',
              'selected': False, 'inputPins': PINS, 'observedSourceEdges': edges,
              'biometricUi': {'component': 'com.samsung.android.biometrics.app.setting/.BiometricsUIService',
                              'bindFlagsLiteral': 603979777, 'bindResultConsumed': False, 'connectionTimeoutMs': 3000},
              'actualAmsDeclaredEntryPoints': declared,
              'declaredEntryPointBodiesOrColdForkBranchesAuditedHere': False,
              'finiteRequiredRoles': ['Original AMS/ATMS request owners, UserController/UMS/PMS and their real user/package/policy state',
                                      'Original Fingerprint/Biometric/Auth, SysUiManager and genuine deferred BiometricsUIService operation/connection',
                                      'Original DPMS loaded administrators and dynamic receiver effects, Supervision user/role/profile-owner callbacks',
                                      'StrongAuth/SLD/Trust/AM-unlock Handler/alarm/native completions retained by their existing source owners'],
              'telephonySimColdOrRestartForkCohortProved': False,
              'fixedUidPackageOrProcessAllowlistDerived': False,
              'firstSourceCut': 'Follow known SysUi Context bind into exact original AMS bindService/Instance dispatch and cold/restart process admission; retain real request/user/package/session provenance before generic fork routing',
              'firstDisqualifier': 'Any design requiring blanket host forks/AM/zygote/UI suspension while mandatory service/admin/callback routes remain needed and unadmitted',
              'ordinaryHostForegroundClassification': 'Separate actual launcher/task/activity request roots and protected credential/admin UI; no source-closed discriminator yet',
              'installedControls': scripts, 'newOemQueries': False,
              'runtimePolicyOrSuccessApiImplemented': False, 'phoneActions': [], 'oemAndroidNativeExecuted': False,
              'reportSha256': sha(doc), 'toolSha256': sha(Path(__file__)),
              'limits': ['Finite caller/source frontier, not all host starts/forks or complete Samsung process closure',
                         'Known callback/bind request is not proof of a new fork, current process availability or native acceptance',
                         'Original parent may stay operational as a candidate; safe guest-front coexistence remains unproved']}
    assert all(sha(ROOT / name) == pin for name, pin in PINS.items())
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'inventory/retained-host-ingress-proof.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'source-readback.json').write_text(json.dumps({'pass': True, 'sourceEdges': edges,
        'declarationsOnly': declared, 'inputPins': PINS, 'noNewQueriesOrOemExecution': True}, indent=2) + '\n')
    print(json.dumps({'pass': True, 'finiteSourceReadinessOnly': True, 'completeHostIngressPolicyReady': False}))


if __name__ == '__main__': main()
