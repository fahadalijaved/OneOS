"""Read saved process/source evidence for an unimplemented retained-mode plan.

No subprocess, script execution, phone access, OEM loading or control operation.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/retained-process-lifetime-plan'
RAW = ROOT / 'firmware/retained-process-lifetime-plan'
ASSETS = 'firmware/installed-oneos-code-profile/static/assets/'
PARENT_OBSERVATION = 'out/retained-parent-readonly-preflight/20261106T043716560466Z-9d3000e929354e3b9293c070abc2ae3d/observation.json'
PINS = {
    ASSETS + 'oneos_switch.sh': 'e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150',
    ASSETS + 'guest_prepare.sh': '000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70',
    ASSETS + 'guest_start.sh': '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446',
    ASSETS + 'return_to_oneui.sh': '04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03',
    'firmware/retained-authority-control/captured/system/etc/init/hw/init.zygote64.rc': '55d71c63fcccb7b84664593f0bb1aebe7b54b07a04cea32b84427657b733debc',
    'firmware/retained-authority-control/captured/system/etc/init/init.sysfw.rc': 'db9688ba524c09d891f3498efacb0b1a8d303409df510164de0197f76e0475d9',
    'inventory/retained-authority-control.json': 'cc41e15f1da4fbe85c9af0dea0f5f776cbefc073399e0116d60b5dac9be4614d',
    'inventory/retained-authority-dependencies.json': 'efbc601283878491fb3f4e159117f9b1c5b096fd649466aef483da43a0d004c8',
    'inventory/security-authority-quiescence.json': '352d9b2ddd3f003f49b6027e2f9bb13dbad57f09a0e8208c562e220847ff43bd',
    'inventory/installed-oneos-code-profile.json': 'e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a',
    'inventory/guest-installd-data-view.json': 'b1381a57c778366a5e3c6586dfffd58c63b89ef237a2bd10c0b39448dbf64801',
    'inventory/retained-user-registry-capture-v2-review.json': '213867642258be2b8ab3dceab771ac8f88f4b048831b771ccb749544b0e225a9',
    'inventory/retained-security-family-implementation-review.json': '0be621fa6d707b84160ccb57bea706c5db548b63084a528702fe5db3f806c6a6',
    PARENT_OBSERVATION: '6cd6c6307fdf58b1d1a0b0d7b703be8a2b7113aba1816ac967ab7959ba03f443',
}

# Exact installed sites, not a transformation or executable action list.
SITES = [
    ('presentation', 'oneos_switch.sh', 963, 'kill -STOP', 'Source-owned physical UI handoff required; do not freeze a required host producer'),
    ('host-primary-stop', 'oneos_switch.sh', 971, 'ctl.stop zygote', 'Retained mode must not issue this host service stop'),
    ('host-secondary-stop', 'oneos_switch.sh', 979, 'ctl.stop zygote_secondary', 'Preserve any admitted original secondary service'),
    ('name-kill-first', 'oneos_switch.sh', 995, 'pidof app_process64', 'Replace the whole995..999 name-kill block; no host-name exemption trick'),
    ('name-kill-ss', 'oneos_switch.sh', 999, 'pidof system_server', 'Never kill the retained writer'),
    ('keeper', 'oneos_switch.sh', 1011, 'while true', 'Replace recurring host-stop producer, not just its first command'),
    ('watchdog-close', 'oneos_switch.sh', 1017, 'printf V', 'No retained-mode watchdog takeover without actual owner transfer'),
    ('softdog-close', 'oneos_switch.sh', 1027, 'printf V', 'Keep original watchdog owner instead of closing a guessed node'),
    ('softdog-off', 'oneos_switch.sh', 1047, 'persist.vendor.softdog off', 'Do not disable original protection for the retained path'),
    ('prepare', 'oneos_switch.sh', 1087, 'guest_prepare.sh', 'Use a separately admitted guest-only producer before global overbinds'),
    ('guest-properties', 'oneos_switch.sh', 1149, 'guest_props.sh', 'Do not expose retained workers to unadmitted global property replacement'),
    ('guest-launch', 'oneos_switch.sh', 1418, 'unshare -m', 'Own exact guest root/descendants; this does not move existing host threads'),
    ('host-socket-pin', 'oneos_switch.sh', 1457, 'mount --bind', 'Retained mode must not pin guest socket objects in init view'),
    ('socket-pin-worker', 'oneos_switch.sh', 1464, 'protect_zygote_sockets', 'No surviving background host-socket takeover worker'),
    ('guest-death-test', 'oneos_switch.sh', 3014, 'pidof system_server', 'Replace global-name liveness with the owned guest generation'),
    ('feeder-kill', 'guest_prepare.sh', 186, 'pkill', 'No broad watchdog-worker kill'),
    ('feeder-write', 'guest_prepare.sh', 208, 'printf V', 'Existing recurring feeder is not retained watchdog custody'),
    ('feeder-start', 'guest_prepare.sh', 236, 'oneos_wdog_feeder.sh', 'Do not start competing feeder in retained mode'),
    ('global-data-bind', 'guest_prepare.sh', 3244, 'mount', 'Host data paths must remain authoritative; private view producer is unclosed'),
    ('guest-socket-unlink', 'guest_start.sh', 1264, '/dev/socket/zygote', 'A private guest socket view must exist before this destructive unlink'),
    ('guest-zygote-exec', 'guest_start.sh', 1284, 'exec /data/zygote_exec', 'Preserve root UID launch semantics under a real guest owner; no UID1000 probe substitute'),
    ('return-keeper-kill', 'return_to_oneui.sh', 216, 'ctl.stop zygote', 'New retained return branch must precede broad helper kills'),
    ('return-ss-kill', 'return_to_oneui.sh', 225, 'system_server', 'Stop guest admission and drain real work before any owned guest teardown'),
    ('return-zygote-kill', 'return_to_oneui.sh', 228, 'zygote64', 'No global name-based zygote kill'),
    ('return-sweep', 'return_to_oneui.sh', 278, 'kill -9', 'Namespace/root-device sampling is not process custody or drain'),
    ('return-socket-unmount', 'return_to_oneui.sh', 309, 'umount', 'Tear down only owned guest objects, never retained canonical socket paths'),
    ('return-mode', 'return_to_oneui.sh', 422, 'ONEOS_RETURN_MODE:-reboot', 'A retained branch must precede destructive teardown, not merely select old inplace mode'),
    ('return-host-absence', 'return_to_oneui.sh', 709, 'init.svc.zygote', 'Replace reconstruction absence gate with same-authority identity/ownership checks'),
    ('return-recovery-properties', 'return_to_oneui.sh', 722, 'crashrecovery.rescue_boot_start', 'Do not replay old recovery-property snapshots while the original host remains live'),
    ('return-recovery-count', 'return_to_oneui.sh', 726, 'sys.rescue_boot_count 0', 'Do not reset host recovery accounting as a resume acknowledgement'),
    ('return-persist-restore', 'return_to_oneui.sh', 740, 'restore-persist', 'Restore only genuinely session-owned changes under current ownership'),
    ('return-fuse-abort', 'return_to_oneui.sh', 880, 'abort_fuse', 'No replay of destructive stock reconstruction tail'),
    ('return-next-restart', 'return_to_oneui.sh', 892, 'ctl.restart zygote_next', 'Preserve independently owned root zygote_next generation'),
    ('return-netd-restart', 'return_to_oneui.sh', 894, 'ctl.restart netd', 'Avoid restarting host dependency as a proxy for resume'),
    ('return-primary-start', 'return_to_oneui.sh', 897, 'ctl.start zygote', 'Never start a second stock framework over the retained writer'),
    ('return-next-start', 'return_to_oneui.sh', 906, 'ctl.start zygote_next', 'No substitute native parent generation'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert all(sha(ROOT / name) == pin for name, pin in PINS.items())
    selected, boundaries = [], []
    for label, file, line, fragment, change in SITES:
        path = ROOT / (ASSETS + file)
        text = path.read_text().splitlines()[line - 1]
        assert fragment in text, (label, file, line)
        selected.append({'id': label, 'path': ASSETS + file, 'line': line, 'text': text})
        boundaries.append({'id': label, 'source': ASSETS + file, 'line': line,
                           'sourceSha256': PINS[ASSETS + file],
                           'lineSha256': hashlib.sha256(text.encode()).hexdigest(),
                           'requiredChange': change, 'implemented': False})
    observation = json.loads((ROOT / PARENT_OBSERVATION).read_text())
    primary, native_next = observation['parents']
    assert observation['systemServer']['parentPid'] == primary['identity']['pid'] == observation['reportedPrimaryZygotePid']
    assert primary['identity']['parentPid'] == native_next['identity']['parentPid'] == 1
    assert primary['identity']['pid'] != native_next['identity']['pid'] == observation['reportedNextZygotePid']
    assert primary['domain'] == 'u:r:zygote:s0' and native_next['domain'] == 'u:r:zygote_next:s0'
    for parent in [primary, native_next]:
        lines = parent['ids'].splitlines()
        assert lines[0].split()[1:] == ['0'] * 4 and lines[1].split()[1:] == ['0'] * 4
    roles = {'systemServer': observation['systemServer'],
             'primaryParent': {'identity': primary['identity'], 'uids': [0] * 4, 'gids': [0] * 4, 'domain': primary['domain']},
             'zygoteNext': {'identity': native_next['identity'], 'uids': [0] * 4, 'gids': [0] * 4, 'domain': native_next['domain']},
             'scope': 'Stable individual point samples; not atomic, controlled survival, all-thread view or code/native attestation'}
    RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    raw = RAW / 'selected-installed-sites.json'
    raw.write_text(json.dumps(selected, indent=2) + '\n', encoding='utf-8')
    doc = ROOT / 'docs/retained-process-lifetime-plan.md'
    result = {'schema': 'retained-process-lifetime-source-plan/v1',
              'status': 'SOURCE_SUPPORTED_PRESERVE_IN_PLACE_CANDIDATE_NOT_IMPLEMENTED_OR_SELECTED',
              'selected': False, 'inputPins': PINS, 'observedRoleBinding': roles,
              'installedSourceBoundaries': boundaries,
              'controlContract': {
                  'retention': 'Keep actual original SS, init-owned primary root parent and separate root zygote_next running in place',
                  'preserve': ['actual UID/GID/domain/task profiles and parent roles',
                               'canonical host zygote/usap objects and required native-only routing',
                               'original policy/Handler/alarm/AM/biometric/native callbacks and watchdog ownership'],
                  'forbiddenSubstitutes': ['SIGSTOP or freezing required producers', 'reparent/re-exec/UID1000 parent substitute',
                                          'global-name kill or first-PID selector', 'empty router count/queue marker as drain',
                                          'caller Boolean as source/readiness authority'],
                  'writer': 'Original Samsung security authority remains sole physical writer; no transfer to a cold guest graph',
                  'guestProcessOwner': 'Unimplemented; exact root/descendant fork/exec/terminal ownership, not a PID file or namespace label',
                  'switchOrdering': ['bind actual original source/process/family before takeover',
                                      'admit physical presentation and guest-only state/socket/property/endpoint views',
                                      'preserve original init/zygote/watchdog paths without stop/kill/keeper',
                                      'suppress competing guest security constructors/publications and admit real guest ingress',
                                      'launch only under real guest process custody'],
                  'returnOrdering': ['close new guest frontend and app/fork producers, including cached/local routes',
                                      'retain accepted original operations and actual callback/child/native work',
                                      'obtain real terminal acknowledgements or hold uncertainty without retry',
                                      'retire only owned guest processes/views/endpoint writers',
                                      'check same retained host parent/family/native roles and restore genuine foreground ownership',
                                      'never fall through to host-absence or stock reconstruction tail'],
                  'realTailExamples': ['AM unlock listener beyond ignored15s wait', 'biometric challenge/reset/remove callbacks',
                                       'nested/delayed Handler and DPM/StrongAuth work',
                                       'Gatekeeper reenrollment/state sync, vold/keystore/storage/native outcomes'],
                  'uncertainty': 'Refuse new guest ingress; preserve still-live original owners; no drain claim, blind credential retry or second writer',
                  'reboot': 'Separate admitted recovery, never same-process resume or hardware rollback'},
              'raw': {'path': raw.relative_to(ROOT).as_posix(), 'sha256': sha(raw)},
              'pcWorkCanPrepare': ['Profile-pinned script derivative/dry action-plan validator',
                                  'Guest process-custody and source callback enrollment contracts with authored fixtures',
                                  'Exact original ingress/callback hooks and compile-only API integration after root approval'],
              'pcWorkCannotProve': ['Actual init/kernel child/process-group or zygote death/restart behavior',
                                    'Actual watchdog FD/heartbeat/driver/failure owner',
                                    'Guest-only socket/app-data/Binder/property/physical-display topology',
                                    'Original asynchronous native/worker completion and uncertain commit reconciliation'],
              'noPauseOrResumePrimitive': True, 'authorityWriterTransferred': False,
              'scriptsExecuted': False, 'oemAndroidOrNativeExecuted': False, 'phoneActions': [],
              'reportSha256': sha(doc), 'toolSha256': sha(Path(__file__))}
    assert all(sha(ROOT / name) == pin for name, pin in PINS.items())
    (ROOT / 'inventory/retained-process-lifetime-plan.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (OUT / 'source-readback.json').write_text(json.dumps({'pass': True, 'inputPins': PINS,
        'rawSha256': sha(raw), 'roleBinding': roles, 'noScriptsOrProcessesExecuted': True}, indent=2) + '\n')
    print(json.dumps({'pass': True, 'sourcePlanOnly': True, 'roleBinding': 'original primary parent distinct from zygote_next'}))


if __name__ == '__main__':
    main()
