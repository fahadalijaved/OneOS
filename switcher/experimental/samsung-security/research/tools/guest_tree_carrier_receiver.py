"""Fixed carrier receiver for a separately approved device operation.

This module has no execution CLI. Observing and opening the waiting shell
are read-only. Granting that shell starts the exact staged installer.
"""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
import hashlib
import re
import secrets
import shlex
import socket
import struct
import subprocess
import sys
import time

import check_file_stage_device_preflight as preflight
from check_file_stage_device_preflight import (BUILD, DEPLOY_DROP, DROP_PARENT, ENDPOINT, FINGERPRINT, GUARD, MODEL, STAGE,
                                               exact, require, service, shell_reply, shell_script, timeout)
import run_guest_tree_install_transport as pinned


DROP = DEPLOY_DROP
DROP_LEAF = DROP.rsplit('/', 1)[-1]
INSTALLER = 'installer'
CARRIER_BYTES = 13_890_850_816
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
DECIMAL = re.compile(r'[1-9][0-9]{0,19}\Z')


@dataclass(frozen=True)
class DropParentTarget:
    transport: str = field(repr=False)
    boot_digest: str = field(repr=False)
    namespace: str = field(repr=False)
    actor_context: str = field(repr=False)
    data_stat: str = field(repr=False)
    local_stat: str = field(repr=False)


@dataclass(frozen=True)
class CarrierTarget:
    parent: DropParentTarget
    drop_stat: str = field(repr=False)
    installer_stat: str = field(repr=False)
    carrier_protocol: str = 'v1'


@dataclass(frozen=True, repr=False)
class _BoundObservations:
    target: CarrierTarget
    controller: str
    readback: str


def online_transport_ids(raw):
    require(raw.isascii(), 'Non-ASCII ADB device inventory')
    result = []
    for line in raw.decode('ascii').splitlines():
        fields = line.split()
        require(len(fields) >= 2, 'Malformed ADB device inventory')
        if fields[1] != 'device':
            continue
        ids = [item.removeprefix('transport_id:') for item in fields[2:] if item.startswith('transport_id:')]
        require(len(ids) == 1 and DECIMAL.fullmatch(ids[0]) and int(ids[0]) < 2**64,
                'Missing or ambiguous ADB transport id')
        result.append(ids[0])
    require(len(set(result)) == len(result), 'Repeated ADB transport id')
    return result


def online_transport():
    deadline = time.monotonic() + 5
    with socket.create_connection(ENDPOINT, timeout=5) as sock:
        service(sock, 'host:devices-l', deadline)
        length = exact(sock, 4, deadline)
        require(re.fullmatch(rb'[0-9a-fA-F]{4}', length) and int(length, 16) <= 16384,
                'Invalid ADB device inventory length')
        targets = online_transport_ids(exact(sock, int(length, 16), deadline))
    require(len(targets) == 1, 'A unique paired ADB device is required')
    return targets[0]


def validate_parent(target):
    require(type(target) is DropParentTarget and DECIMAL.fullmatch(target.transport)
            and int(target.transport) < 2**64 and HEX64.fullmatch(target.boot_digest)
            and re.fullmatch(r'mnt:\[[1-9][0-9]{0,19}\]', target.namespace), 'Invalid observed target binding')
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,32}:[A-Za-z0-9_.-]{1,32}:[A-Za-z0-9_.-]{1,64}:'
                         r's[0-9][s0-9c,.:\-]{0,80}', target.actor_context), 'Invalid current SELinux context')
    fields = r'\|[1-9][0-9]{0,19}\|[1-9][0-9]{0,19}'
    require(re.fullmatch(r'41f9\|771\|1000\|1000' + fields, target.data_stat)
            and re.fullmatch(r'41e9\|751\|0\|0' + fields, target.local_stat)
            and target.data_stat.split('|')[-2] == target.local_stat.split('|')[-2],
            'Expected the root-protected parent on the current /data filesystem')


def validate_target(target):
    require(type(target) is CarrierTarget, 'Invalid carrier target binding')
    validate_parent(target.parent)
    pin = pinned.carrier_installer_pin(target.carrier_protocol)
    require(re.fullmatch(r'41c0\|700\|0\|0\|[1-9][0-9]{0,19}\|[1-9][0-9]{0,19}', target.drop_stat),
            'The fixed drop directory must be root-owned mode 0700')
    installer = rf'8140\|500\|0\|0\|1\|{pin.artifact_bytes}(?:\|[1-9][0-9]{{0,19}}){{4}}'
    require(re.fullmatch(installer, target.installer_stat), 'Unexpected staged installer identity')
    require(target.drop_stat.split('|')[-2] == target.installer_stat.split('|')[-4]
            == target.parent.local_stat.split('|')[-2],
            'The staged installer must be on the drop directory filesystem')
    return pin


def identity_checks():
    return f"""same_target() {{
    [ "$(/system/bin/getprop ro.product.model)" = {shlex.quote(MODEL)} ] &&
    [ "$(/system/bin/getprop ro.build.display.id)" = {shlex.quote(BUILD)} ] &&
    [ "$(/system/bin/getprop ro.build.fingerprint)" = {shlex.quote(FINGERPRINT)} ] &&
    [ "$(/system/bin/getprop ro.build.version.sdk)" = '37' ] &&
    [ "$(/system/bin/toybox id -u)" = '0' ] && [ "$(/system/bin/toybox id -ru)" = '0' ] &&
    [ "$(/system/bin/toybox id -g)" = '0' ] && [ "$(/system/bin/toybox id -rg)" = '0' ] &&
    [ "$(/system/bin/getenforce)" = 'Enforcing' ] || return 1
    case "$(/system/bin/toybox uname -r)" in 6.12.69-android16-6-*) ;; *) return 1;; esac
    boot=$(/system/bin/toybox cat /proc/sys/kernel/random/boot_id) || return 1
    printf '%s\\n' "$boot" | /system/bin/toybox grep -Eq '^[0-9a-f]{{8}}(-[0-9a-f]{{4}}){{3}}-[0-9a-f]{{12}}$' || return 1
    digest=$(printf '%s' "$boot" | /system/bin/toybox sha256sum) || return 1
    boot_digest=${{digest%% *}}
    namespace=$(/system/bin/toybox readlink /proc/self/ns/mnt) || return 1
    actor_context=$(/system/bin/toybox cat /proc/$$/attr/current | /system/bin/toybox tr -d '\\000') || return 1
}}
same_target || exit 2
"""


def inventory_command(with_drop):
    start = ("export LC_ALL=C\nset -f\n" + identity_checks()
             + "[ \"$(/system/bin/toybox stat -f -c %t /data)\" = 'f2f52010' ] || exit 2\n"
             + "/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' /data || exit 2\n"
             + f"/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' {DROP_PARENT} || exit 2\n"
             + "printf '%s\\n' \"$boot_digest\" \"$namespace\" \"$actor_context\"\n")
    if with_drop:
        return (start + f"/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' {DROP} || exit 2\n"
                + f"/system/bin/toybox stat -c '%f|%a|%u|%g|%h|%s|%d|%i|%Y|%Z' {DROP}/{INSTALLER} || exit 2\n")
    return (start + f"entry=$(/system/bin/toybox stat -c '%i' {DROP} 2>&1) && exit 2\n"
            + "case \"$entry\" in *'No such file or directory') :;; *) exit 2;; esac\n")


def shell_service(sock, transport, command, deadline):
    service(sock, 'host:transport-id:' + transport, deadline)
    shell_script(sock, command, deadline)


def observe_inventory(transport, with_drop):
    deadline = time.monotonic() + 12
    with socket.create_connection(ENDPOINT, timeout=5) as sock:
        shell_service(sock, transport, inventory_command(with_drop), deadline)
        exit_code, stdout, stderr = shell_reply(sock, deadline)
    require(exit_code == 0 and not stderr and stdout.isascii() and b'\0' not in stdout,
            'Read-only staged installer observation refused')
    lines = stdout.decode('ascii').splitlines()
    require(len(lines) == (7 if with_drop else 5), 'Unexpected staged installer observation')
    data, local, boot, namespace, actor, *drop = lines
    target = DropParentTarget(transport, boot, namespace, actor, data, local)
    validate_parent(target)
    return target, drop


def observe_drop_parent():
    """Read the exact protected parent and require the fixed drop to be absent."""
    target, _ = observe_inventory(online_transport(), False)
    return target


def observe_target(parent, published_identity, *, carrier_protocol='v1'):
    """Join the read-only carrier observation to the prior actual drop receipt."""
    validate_parent(parent)
    pinned.carrier_installer_pin(carrier_protocol)
    require(re.fullmatch(r'[1-9][0-9]{0,19}:[1-9][0-9]{0,19}', published_identity),
            'Missing exact published drop identity')
    transport = online_transport()
    require(transport == parent.transport, 'Current ADB transport differs from the published drop')
    observed, drop = observe_inventory(transport, True)
    require(observed == parent and ':'.join(drop[0].split('|')[-2:]) == published_identity,
            'The observed drop does not match the published generation')
    target = CarrierTarget(parent, *drop, carrier_protocol=carrier_protocol)
    validate_target(target)
    return target


def _verified_installer_preamble(target):
    pin = validate_target(target)
    parent = target.parent
    return "export LC_ALL=C\nset -f\n" + identity_checks() + f"""
check_boot() {{
    [ "$boot_digest" = {shlex.quote(parent.boot_digest)} ] &&
    [ "$namespace" = {shlex.quote(parent.namespace)} ] &&
    [ "$actor_context" = {shlex.quote(parent.actor_context)} ]
}}
check_boot || exit 2
drop={shlex.quote(DROP)}
exe={shlex.quote(INSTALLER)}
expected_dir={shlex.quote(target.drop_stat)}
expected_exe={shlex.quote(target.installer_stat)}
expected_data={shlex.quote(parent.data_stat)}
expected_parent={shlex.quote(parent.local_stat)}
exec 9< /data || exit 2
exec 8< /proc/self/fd/9/local || exit 2
mount_id() {{ /system/bin/toybox sed -n 's/^mnt_id:[[:space:]]*//p' "/proc/$$/fdinfo/$1"; }}
data_mount=$(mount_id 9) || exit 2
case "$data_mount" in ''|*[!0-9]*) exit 2;; esac
parents_current() {{
    [ "$(mount_id 9)" = "$data_mount" ] && [ "$(mount_id 8)" = "$data_mount" ] &&
    [ "$(/system/bin/toybox stat -f -c %t /proc/self/fd/9 9<&9)" = 'f2f52010' ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' /data)" = "$expected_data" ] &&
    [ "$(/system/bin/toybox stat -Lc '%f|%a|%u|%g|%d|%i' /proc/self/fd/9 9<&9)" = "$expected_data" ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' /proc/self/fd/9/local 9<&9)" = "$expected_parent" ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' {DROP_PARENT})" = "$expected_parent" ] &&
    [ "$(/system/bin/toybox stat -Lc '%f|%a|%u|%g|%d|%i' /proc/self/fd/8 8<&8)" = "$expected_parent" ]
}}
parents_current || exit 2
exec 5< /proc/self/fd/8/{DROP_LEAF} || exit 2
directory_current() {{
    parents_current && [ "$(mount_id 5)" = "$data_mount" ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' "$drop")" = "$expected_dir" ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%d|%i' /proc/self/fd/8/{DROP_LEAF} 8<&8)" = "$expected_dir" ] &&
    [ "$(/system/bin/toybox stat -Lc '%f|%a|%u|%g|%d|%i' /proc/self/fd/5 5<&5)" = "$expected_dir" ]
}}
directory_current || exit 2
exec 3< "/proc/self/fd/5/$exe" || exit 2
executable_current() {{
    [ "$(mount_id 3)" = "$data_mount" ] &&
    [ "$(/system/bin/toybox stat -c '%f|%a|%u|%g|%h|%s|%d|%i|%Y|%Z' "/proc/self/fd/5/$exe" 5<&5)" = "$expected_exe" ] &&
    [ "$(/system/bin/toybox stat -Lc '%f|%a|%u|%g|%h|%s|%d|%i|%Y|%Z' /proc/self/fd/3 3<&3)" = "$expected_exe" ]
}}
executable_verified() {{
    directory_current && executable_current || return 1
    digest=$(/system/bin/toybox sha256sum /proc/self/fd/3 3<&3) || return 1
    [ "${{digest%% *}}" = '{pin.artifact_sha256}' ] && directory_current && executable_current
}}
executable_verified || exit 2
"""


def launch_command(target, nonce):
    preamble = _verified_installer_preamble(target)
    require(target.carrier_protocol == 'v1', 'V2 requires the bound carrier renderer')
    require(re.fullmatch(r'[0-9a-f]{32}', nonce), 'Invalid carrier grant nonce')
    return preamble + f"""printf 'ONEOS_CARRIER_HELLO_V1 {nonce}\\n' || exit 2
IFS= read -r grant || exit 2
[ "$grant" = 'ONEOS_CARRIER_GRANT_V1 {nonce}' ] || exit 2
same_target && check_boot && executable_verified || exit 2
exec 5<&- 8<&- 9<&-
printf 'ONEOS_CARRIER_READY_V1 {nonce}\\n' || exit 2
exec /proc/self/fd/3 --install-verified-carrier 3<&3
"""


def bound_bootstrap_command(target):
    """Render the V2 bootstrap witness verb on the exact held installer."""
    preamble = _verified_installer_preamble(target)
    require(target.carrier_protocol == 'v2', 'Bound bootstrap requires the V2 installer')
    return preamble + """same_target && check_boot && executable_verified || exit 2
exec 5<&- 8<&- 9<&- || exit 2
exec /proc/self/fd/3 --bootstrap-empty-stage-with-witness 3<&3 </dev/null
"""


def _bound_installer_preamble(target, stage_stat, guard_stat, *, mounts=None):
    preamble = _verified_installer_preamble(target)
    require(target.carrier_protocol == 'v2', 'Bound carrier operation requires the V2 installer')
    for name, observed in (('stage', stage_stat), ('guard', guard_stat)):
        require(isinstance(observed, str) and re.fullmatch(
            r'41c0\|700\|0\|0\|[1-9][0-9]{0,19}\|[1-9][0-9]{0,19}', observed),
            f'Invalid earlier {name} observation')
    require(stage_stat != guard_stat, 'Bound stage and guard observations alias')
    require(stage_stat.split('|')[-2] == target.parent.data_stat.split('|')[-2],
            'The observed bound stage must be on the /data filesystem')
    if mounts is None:
        mount_setup = """guard_mount=$(mount_id 7) || exit 2
case "$guard_mount" in ''|*[!0-9]*) exit 2;; esac
"""
    else:
        require(type(mounts) is tuple and len(mounts) == 2
                and all(type(mount) is int and 0 < mount < 2**64 for mount in mounts)
                and mounts[0] != mounts[1], 'Invalid bound bootstrap mount IDs')
        mount_setup = f"""[ "$data_mount" = '{mounts[0]}' ] || exit 2
guard_mount='{mounts[1]}'
"""
    return preamble + f"""stage={shlex.quote(STAGE)}
guard={shlex.quote(GUARD)}
expected_stage={shlex.quote(stage_stat)}
expected_guard={shlex.quote(guard_stat)}
bound_format='%f|%a|%u|%g|%d|%i'
bound_names_current() {{
    [ "$(/system/bin/toybox stat -c "$bound_format" "$stage")" = "$expected_stage" ] &&
    [ "$(/system/bin/toybox stat -c "$bound_format" "$guard")" = "$expected_guard" ]
}}
bound_names_current || exit 2
exec 6< "$stage" || exit 2
exec 7< "$guard" || exit 2
{mount_setup}bound_current() {{
    same_target && check_boot && executable_verified &&
    [ "$(mount_id 6)" = "$data_mount" ] && [ "$(mount_id 7)" = "$guard_mount" ] &&
    [ "$(/system/bin/toybox stat -Lc "$bound_format" "/proc/$$/fd/6")" = "$expected_stage" ] &&
    [ "$(/system/bin/toybox stat -Lc "$bound_format" "/proc/$$/fd/7")" = "$expected_guard" ] &&
    bound_names_current
}}
bound_current || exit 2
"""


def bound_launch_command(target, nonce, stage_stat, guard_stat, *, mounts=None):
    """Render the V2 controller and carrier in one descriptor-owning shell."""
    require(isinstance(nonce, str) and re.fullmatch(r'[0-9a-f]{32}', nonce), 'Invalid bound grant nonce')
    return _bound_installer_preamble(target, stage_stat, guard_stat, mounts=mounts) + f"""printf 'ONEOS_BOUND_HELLO_V2 {nonce}\\n' || exit 2
IFS= read -r grant || exit 2
[ "$grant" = 'ONEOS_BOUND_CONTROLLER_GRANT_V2 {nonce}' ] || exit 2
bound_current || exit 2
controller=$(
    /proc/self/fd/3 --install-preparation-controller-with-bound-stage 3<&3 6<&6 7<&7 </dev/null 2>&1 &&
    printf '.'
) || exit 2
[ "$controller" = "$(printf 'ONEOS_CONTROLLER_V1 PUBLISHED_CLOSED\\n.')" ] || exit 2
bound_current || exit 2
printf 'ONEOS_CONTROLLER_V1 PUBLISHED_CLOSED\\nONEOS_BOUND_CONTROLLER_CLOSED_V2 {nonce}\\n' || exit 2
IFS= read -r grant || exit 2
[ "$grant" = 'ONEOS_BOUND_CARRIER_GRANT_V2 {nonce}' ] || exit 2
bound_current || exit 2
exec 5<&- 8<&- 9<&- || exit 2
printf 'ONEOS_BOUND_CARRIER_READY_V2 {nonce}\\n' || exit 2
exec /proc/self/fd/3 --install-verified-carrier-with-witness 3<&3 6<&6 7<&7
"""


def readback_command(target, stage_stat, guard_stat, *, mounts=None, inventory_identity=None, confirmation=False):
    """Render a separate point observation bracketed by the same V2 identities."""
    require(type(confirmation) is bool and (not confirmation or inventory_identity is not None),
            'Confirmation observation requires the bound inventory')
    if inventory_identity is None:
        preamble = _bound_installer_preamble(target, stage_stat, guard_stat, mounts=mounts)
    else:
        preamble = bound_controller_readback_command(target, inventory_identity, stage_stat, guard_stat,
                                                      mounts=mounts, confirmation=confirmation)
    command = preamble + """observed=$(
    /proc/self/fd/3 --observe-published-carrier 3<&3 6<&6 7<&7 </dev/null 2>&1 &&
    printf '.'
) || exit 2
bound_current || exit 2
printf '%s' "${observed%.}" || exit 2
"""
    require(command.isascii() and len(command) < 16384, 'Bound carrier observation exceeds the shell source bound')
    return command


def bound_controller_readback_command(target, identity, stage_stat, guard_stat, *, mounts=None, confirmation=False):
    """Render the fixed inventory between checks of the same retained V2 identities."""
    preamble = _bound_installer_preamble(target, stage_stat, guard_stat, mounts=mounts)
    require(type(identity) in (list, tuple) and len(identity) == 12
            and all(type(value) is str and re.fullmatch(r'[ -~]+', value) for value in identity),
            'Invalid bound controller inventory identity')
    boot = identity[10]
    require(tuple(identity[:4]) == (MODEL, BUILD, FINGERPRINT, '37')
            and identity[4].startswith('6.12.69-android16-6-')
            and tuple(identity[5:10]) == ('0', '0', '0', '0', 'Enforcing')
            and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot)
            and hashlib.sha256(boot.encode('ascii')).hexdigest() == target.parent.boot_digest
            and identity[11] == target.parent.namespace, 'Inventory identity does not match the bound target')
    command = (preamble + preflight.inventory_command(identity, carrier_protocol='v2', confirmation=confirmation)
               + '\nbound_current || exit 2\n')
    require(command.isascii() and len(command) < 16384, 'Bound controller inventory exceeds the shell source bound')
    return command


def verify_bound_controller_reply(code, stdout, stderr):
    """Check only the exact reply returned by shell_reply after remote exit and EOF."""
    require(type(code) is int and code == 0 and type(stdout) is bytes and type(stderr) is bytes and not stderr
            and 0 < len(stdout) < preflight.LIMIT and stdout.endswith(b'\n') and re.fullmatch(rb'[ -~\n]+', stdout),
            'Bound controller inventory reply refused')
    lines = stdout[:-1].decode('ascii').split('\n')
    require(lines[0] == 'inventory_identity|begin' and lines[-1] == 'inventory_identity|end',
            'Bound controller inventory identity boundaries missing')
    evidence = preflight.inventory(lines[1:-1], carrier_protocol='v2')
    paths, contents = evidence['paths'], evidence['contents']
    for role in ('stage', 'guard', 'deploy_drop'):
        row = paths[role]
        require((row.get('type'), row.get('mode'), row.get('uid'), row.get('gid')) == ('directory', '0700', 0, 0),
                f'Unexpected bound controller directory: {role}')
    controller_size, _ = preflight.controller_artifact('v2')
    files = {'controller': (controller_size, '0500', 0),
             'host_permit': (len(preflight.HOST_PERMIT_MARKER), '0440', 1000)}
    files.update({role: (size, '0500', 0) for role, (_, size, _) in preflight.drop_artifacts('v2').items()})
    for role, (size, mode, gid) in files.items():
        require(paths[role] == {'state': 'present', 'type': 'regular', 'mode': mode, 'uid': 0, 'gid': gid,
                                'links': 1, 'bytes': size} and contents[role] == 'exact_bytes',
                f'Unexpected bound controller file: {role}')
    require(paths['lease'] == {'state': 'present', 'type': 'regular', 'mode': '0600', 'uid': 0, 'gid': 0,
                               'links': 1, 'bytes': 0}, 'Unexpected bound stage lease')
    empty_slots = ('carrier', 'carrier_tmp', 'controller_tmp', 'stage_tmp', 'guard_tmp',
                   'writer_blocked', 'legacy_blocked', 'view_blocked')
    require(all(paths[role] == {'state': 'absent'} for role in empty_slots),
            'Carrier, temporary publication or guard marker is occupied or unobserved')
    require(evidence['nestedIsolatedMounts'] == evidence['nestedDropMounts'] == 0
            and all(evidence[flag] for flag in ('imageAndHeadroomAvailable', 'protectedDropParentObserved',
                                                'stageParentsOnData', 'dataWritableF2fs', 'dataExecutableF2fs',
                                                'sameDataDeviceAdvertisesVerity')),
            'Bound controller storage or mount evidence refused')
    return True


@contextmanager
def _open_bound_observation(target, command):
    require(online_transport() == target.parent.transport, 'Current ADB transport differs from the bound target')
    with socket.create_connection(ENDPOINT, timeout=5) as sock:
        shell_service(sock, target.parent.transport, command, time.monotonic() + 12)
        yield sock


def observe_bound_controller(target, identity, stage_stat, guard_stat, *, mounts):
    require(mounts is not None, 'Missing bound bootstrap mount IDs')
    command = bound_controller_readback_command(target, identity, stage_stat, guard_stat, mounts=mounts)
    with _open_bound_observation(target, command) as sock:
        return verify_bound_controller_reply(*shell_reply(sock, time.monotonic() + 90))


def open_bound_readback(target, stage_stat, guard_stat, *, mounts):
    require(mounts is not None, 'Missing bound bootstrap mount IDs')
    return _open_bound_observation(target, readback_command(target, stage_stat, guard_stat, mounts=mounts))


def expect_frame(sock, expected, deadline):
    data = bytearray()
    while len(data) < len(expected):
        kind, count = struct.unpack('<BI', exact(sock, 5, deadline))
        require(kind == 1 and 0 < count <= len(expected) - len(data), 'Unexpected carrier launch frame')
        data.extend(exact(sock, count, deadline))
        require(expected.startswith(data), 'Carrier launch identity differs')


def _send_grant(sock, line, deadline):
    timeout(sock, deadline)
    sock.sendall(struct.pack('<BI', 0, len(line)) + line)


class CarrierReceiver:
    """Own one waiting shell through grant and the actual installer transfer."""

    def __init__(self, sock, nonce, *, carrier_protocol='v1'):
        pinned.carrier_installer_pin(carrier_protocol)
        self.sock = sock
        self.nonce = nonce
        self._carrier_protocol = carrier_protocol
        self.engine = None
        self.producer = None
        self.state = 'waiting_for_grant'

    def retain_source(self, directory):
        """Start the exact PC-only feed before giving the receiver its grant."""
        from guest_tree_shell_v2_transfer import ShellV2Transfer

        require(self.state == 'waiting_for_grant' and self.producer is None, 'Carrier source is already owned')
        io = pinned.load_io()
        pinned.selected_inputs(io, carrier_protocol=self._carrier_protocol)
        producer_source = pinned.pinned(io, pinned.FEED, pinned.FEED_SHA, 64 * 1024)
        path = io['inside_repo'](str(directory))
        require(path.is_relative_to(pinned.ROOT / 'out') and path.parent.resolve() == path.parent
                and path.parent.is_dir() and not path.exists() and not path.is_symlink(),
                'Expected a fresh source receipt directory under out')
        expected = pinned.selected_source_receipt()

        def read_receipt():
            with io['checked_input'](path / 'source-receipt.json', size=len(expected)) as stream:
                return stream.read(len(expected) + 1)

        filename = str(pinned.ROOT / pinned.FEED)
        snapshot = (f'import sys\nsys.argv[0] = {filename!r}\n'
                    f'exec(compile({producer_source!r}, {filename!r}, "exec"), '
                    f'{{"__name__": "__main__", "__file__": {filename!r}}})')
        argv = [sys.executable, '-I', '-B', '-c', snapshot, '--receipt-dir', str(path)]
        self.producer = subprocess.Popen(argv, cwd=pinned.ROOT, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.engine = ShellV2Transfer(self.sock, self.producer, CARRIER_BYTES, expected, read_receipt,
                                      publication_witness=self._carrier_protocol == 'v2')

    def grant(self):
        """Caller invokes this only for an explicitly authorized device operation."""
        require(self._carrier_protocol == 'v1', 'V2 carrier grant requires native stage and guard binding')
        require(self.state == 'waiting_for_grant' and self.engine is not None, 'Carrier grant is unavailable')
        self.state = 'grant_attempted'
        deadline = time.monotonic() + 12
        line = f'ONEOS_CARRIER_GRANT_V1 {self.nonce}\n'.encode('ascii')
        _send_grant(self.sock, line, deadline)
        expect_frame(self.sock, f'ONEOS_CARRIER_READY_V1 {self.nonce}\n'.encode('ascii'), deadline)
        self.state = 'ready_for_transfer'

    def transfer(self, seconds):
        require(self.state == 'ready_for_transfer' and self.engine is not None,
                'The carrier receiver has no ready transfer')
        self.state = 'transferring'
        result = self.engine.run(seconds)
        if result['status'] == 'COMPLETE_SHELL_V2_TRANSFER_ONLY':
            self.state = 'terminal_transport'
        else:
            self.state = 'retained_transfer'
        return result

    def settle_local_feed_before_transfer(self):
        """Reap only the PC producer. Leave any remote effects uncertain."""
        require(self.state in ('waiting_for_grant', 'grant_attempted', 'ready_for_transfer')
                and self.producer is not None, 'No idle PC feed is retained')
        self.engine = None
        producer = self.producer
        if producer.poll() is None:
            producer.terminate()
        result = producer.wait(timeout=5)
        with ExitStack() as close_pipes:
            close_pipes.callback(producer.stdout.close)
            close_pipes.callback(producer.stderr.close)
        return result

    def close_after_transport(self):
        require(self.state == 'terminal_transport', 'Remote transport closure is unconfirmed')
        self.state = 'closing_terminal_transport'
        self.sock.close()
        self.state = 'closed_terminal_transport'

    def close_before_grant(self):
        require(self.state == 'waiting_for_grant' and self.producer is None, 'Receiver or source effects are retained')
        self.state = 'closed_before_grant'
        self.sock.close()


class _BoundCarrierReceiver(CarrierReceiver):
    """Own the two grants on one already-open bound V2 shell."""

    def __init__(self, sock, nonce, *, observations=None):
        require(isinstance(nonce, str) and re.fullmatch(r'[0-9a-f]{32}', nonce), 'Invalid bound grant nonce')
        super().__init__(sock, nonce, carrier_protocol='v2')
        self.state = 'waiting_for_hello'
        self._readback_attempted = False
        self._observations = observations

    def accept_hello(self):
        require(self.state == 'waiting_for_hello', 'Bound carrier hello is unavailable')
        self.state = 'hello_attempted'
        deadline = time.monotonic() + 12
        expect_frame(self.sock, f'ONEOS_BOUND_HELLO_V2 {self.nonce}\n'.encode('ascii'), deadline)
        self.state = 'waiting_for_controller_grant'

    def grant_controller(self):
        require(self.state == 'waiting_for_controller_grant', 'Bound controller grant is unavailable')
        self.state = 'controller_grant_attempted'
        deadline = time.monotonic() + 90
        _send_grant(self.sock, f'ONEOS_BOUND_CONTROLLER_GRANT_V2 {self.nonce}\n'.encode('ascii'), deadline)
        expected = (b'ONEOS_CONTROLLER_V1 PUBLISHED_CLOSED\n'
                    + f'ONEOS_BOUND_CONTROLLER_CLOSED_V2 {self.nonce}\n'.encode('ascii'))
        expect_frame(self.sock, expected, deadline)
        self.state = 'waiting_for_grant'

    def grant(self):
        require(self.state == 'waiting_for_grant' and self.engine is not None, 'Bound carrier grant is unavailable')
        self.state = 'grant_attempted'
        deadline = time.monotonic() + 12
        _send_grant(self.sock, f'ONEOS_BOUND_CARRIER_GRANT_V2 {self.nonce}\n'.encode('ascii'), deadline)
        expect_frame(self.sock, f'ONEOS_BOUND_CARRIER_READY_V2 {self.nonce}\n'.encode('ascii'), deadline)
        self.state = 'ready_for_transfer'

    def verify_readback(self, code, stdout, stderr, *, eof):
        require(self.state == 'closed_terminal_transport' and self.engine is not None and not self._readback_attempted,
                'Bound carrier readback is unavailable')
        self._readback_attempted = True
        return self.engine.verify_readback(code, stdout, stderr, eof=eof)

    def close_before_grant(self):
        require(self.state in ('waiting_for_hello', 'hello_attempted', 'waiting_for_controller_grant'),
                'Bound controller effects may have started')
        self.state = 'closing_before_grant'
        self.sock.close()
        self.state = 'closed_before_grant'


def complete_bound_carrier(receiver, source_dir, verify_controller, open_readback, seconds):
    """Drive one already-open bound shell and return its transfer and readback evidence.

    The controller check must return True after validating the fresh controller,
    stage and guard. The readback opener supplies the separate pinned read-only
    shell for this attempt. This coordinator reads its actual exit and EOF.
    The caller retains the receiver and owns any local feed settlement on error.
    """
    require(type(receiver) is _BoundCarrierReceiver, 'Expected the retained bound carrier receiver')
    require(callable(verify_controller) and callable(open_readback), 'Missing bound carrier observers')
    require(type(seconds) in (int, float) and 0 < seconds <= 24 * 3600, 'Invalid absolute transfer budget')
    receiver.accept_hello()
    receiver.grant_controller()
    require(verify_controller() is True, 'Fresh bound controller was not verified')
    receiver.retain_source(source_dir)
    receiver.grant()
    transfer = receiver.transfer(seconds)
    require(transfer['status'] == 'COMPLETE_SHELL_V2_TRANSFER_ONLY', 'Bound carrier transfer is unconfirmed')
    receiver.close_after_transport()
    with open_readback() as readback_socket:
        code, stdout, stderr = shell_reply(readback_socket, time.monotonic() + 90)
    readback = receiver.verify_readback(code, stdout, stderr, eof=True)
    return {'transfer': transfer, 'readback': readback}


def open_bound_receiver(target, identity, stage_stat, guard_stat, *, mounts):
    """Open the fixed bound waiting shell and retain its two observation commands."""
    require(mounts is not None, 'Missing bound bootstrap mount IDs')
    nonce = secrets.token_hex(16)
    launch = bound_launch_command(target, nonce, stage_stat, guard_stat, mounts=mounts)
    controller = bound_controller_readback_command(target, identity, stage_stat, guard_stat, mounts=mounts)
    readback = readback_command(target, stage_stat, guard_stat, mounts=mounts)
    require(all(command.isascii() and 0 < len(command) <= 16384 and '\0' not in command
                for command in (launch, controller, readback)), 'Invalid bound shell source')
    observations = _BoundObservations(target, controller, readback)
    require(online_transport() == target.parent.transport, 'Current ADB transport differs from the bound target')
    sock = socket.create_connection(ENDPOINT, timeout=5)
    try:
        shell_service(sock, target.parent.transport, launch, time.monotonic() + 12)
        return _BoundCarrierReceiver(sock, nonce, observations=observations)
    except BaseException:
        sock.close()
        raise


def complete_observed_bound_carrier(receiver, source_dir, seconds):
    """Complete the retained attempt using only its fixed observation commands."""
    require(type(receiver) is _BoundCarrierReceiver and type(receiver._observations) is _BoundObservations,
            'Expected a bound receiver with retained observations')
    observations = receiver._observations

    def verify_controller():
        with _open_bound_observation(observations.target, observations.controller) as sock:
            return verify_bound_controller_reply(*shell_reply(sock, time.monotonic() + 90))

    return complete_bound_carrier(receiver, source_dir, verify_controller,
                                  lambda: _open_bound_observation(observations.target, observations.readback), seconds)


def open_receiver(target):
    """Open the read-only waiting shell. This does not send a grant."""
    validate_target(target)
    require(target.carrier_protocol == 'v1', 'Live bound V2 carrier transport is not enabled')
    require(online_transport() == target.parent.transport, 'Current ADB transport differs from the observed target')
    nonce = secrets.token_hex(16)
    deadline = time.monotonic() + 12
    sock = socket.create_connection(ENDPOINT, timeout=5)
    try:
        shell_service(sock, target.parent.transport, launch_command(target, nonce), deadline)
        expect_frame(sock, f'ONEOS_CARRIER_HELLO_V1 {nonce}\n'.encode('ascii'), deadline)
        return CarrierReceiver(sock, nonce, carrier_protocol=target.carrier_protocol)
    except BaseException:
        # No grant was sent on this connection.
        sock.close()
        raise
