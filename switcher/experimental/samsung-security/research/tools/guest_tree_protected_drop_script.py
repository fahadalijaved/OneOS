"""Render the fixed protected-drop shell payload. This module never opens a connection."""

import hashlib
import re

from check_file_stage_device_preflight import DEPLOY_DROP, DROP_ARTIFACTS, drop_artifacts


_, INSTALLER_BYTES, INSTALLER_SHA = DROP_ARTIFACTS['deploy_installer']
_, PUBLISHER_BYTES, PUBLISHER_SHA = DROP_ARTIFACTS['deploy_publisher']
NUMBER = r"[1-9][0-9]{0,19}"
NAMESPACE = rf"mnt:\[{NUMBER}\]"
CONTEXT = r"u:r:[a-zA-Z0-9_]{1,48}:s0(?::c[0-9]{1,4}(?:[.,]c[0-9]{1,4}){0,15})?"
DATA_STAT = rf"41f9\|771\|1000\|1000\|({NUMBER})\|({NUMBER})"
LOCAL_STAT = rf"41e9\|751\|0\|0\|({NUMBER})\|({NUMBER})"


def drop_command(boot_digest, namespace, actor_context, data_stat, local_stat, nonce,
                 *, carrier_protocol="v1"):
    """Bind preobserved identities and a nonce to the fixed shell-v2 operation."""
    values = (boot_digest, namespace, actor_context, data_stat, local_stat, nonce)
    if any(type(value) is not str for value in values):
        raise ValueError("Invalid protected-drop target")
    artifacts = drop_artifacts(carrier_protocol)
    _, installer_bytes, installer_sha = artifacts['deploy_installer']
    _, publisher_bytes, publisher_sha = artifacts['deploy_publisher']
    data = re.fullmatch(DATA_STAT, data_stat)
    local = re.fullmatch(LOCAL_STAT, local_stat)
    if (not re.fullmatch(r"[0-9a-f]{64}", boot_digest) or not re.fullmatch(NAMESPACE, namespace)
            or not re.fullmatch(CONTEXT, actor_context)
            or not re.fullmatch(r"[0-9a-f]{32}", nonce) or not data or not local
            or data[1] != local[1] or data[2] == local[2]):
        raise ValueError("Invalid protected-drop target")
    # The full matches above admit only literal fields safe inside single quotes.
    grant = f"ONEOS_PROTECTED_DROP_GRANT_V1 {nonce}\n".encode("ascii")
    replacements = {
        "@BOOT@": boot_digest, "@NS@": namespace, "@ACTOR@": actor_context,
        "@DATA@": data_stat, "@LOCAL@": local_stat, "@DEV@": data[1], "@NONCE@": nonce,
        "@DROP@": DEPLOY_DROP, "@I_SIZE@": str(installer_bytes), "@P_SIZE@": str(publisher_bytes),
        "@I_SHA@": installer_sha, "@P_SHA@": publisher_sha,
        "@G_SIZE@": str(len(grant)), "@G_SHA@": hashlib.sha256(grant).hexdigest(),
    }
    return re.sub(r"@[A-Z_]+@", lambda match: replacements[match[0]], _SCRIPT)


_SCRIPT = r"""
export LC_ALL=C
set -f
set -o pipefail || exit 2
umask 077
tb=/system/bin/toybox
proc=/proc/$$
data_fd=$proc/fd/3
local_fd=$proc/fd/4
drop_fd=$proc/fd/5
drop='@DROP@'
leaf=.oneos-file-stage-803691c5
directory_format='%f|%a|%u|%g|%d|%i'
file_format='%f|%a|%u|%g|%h|%s|%d|%i|%Y|%Z'

number() {
    case "$1" in ''|0*|*[!0-9]*) return 1;; esac
    [ "${#1}" -le 20 ]
}

same_host() {
    [ "$(/system/bin/getprop ro.product.model)" = SM-S948U1 ] &&
    [ "$(/system/bin/getprop ro.build.display.id)" = CP2A.260605.016.S948U1UES4BZIG ] &&
    [ "$(/system/bin/getprop ro.build.fingerprint)" = 'samsung/m3quew/m3q:17/CP2A.260605.016/S948U1UES4BZIG_OYM4BZIG:user/release-keys' ] &&
    [ "$(/system/bin/getprop ro.build.version.sdk)" = 37 ] &&
    [ "$("$tb" id -u)" = 0 ] && [ "$("$tb" id -ru)" = 0 ] &&
    [ "$("$tb" id -g)" = 0 ] && [ "$("$tb" id -rg)" = 0 ] &&
    [ "$(/system/bin/getenforce)" = Enforcing ] &&
    [ "$("$tb" stat -f -c '%t' /proc)" = 9fa0 ] &&
    [ "$("$tb" readlink "$proc/ns/mnt")" = '@NS@' ] || return 1
    context=$("$tb" head -c 192 "$proc/attr/current" | "$tb" tr -d '\000') || return 1
    [ "$context" = '@ACTOR@' ] || return 1
    case "$("$tb" uname -r)" in 6.12.69-android16-6-*) ;; *) return 1;; esac
    boot=$("$tb" cat /proc/sys/kernel/random/boot_id) || return 1
    printf '%s\n' "$boot" | "$tb" grep -Eq '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' || return 1
    boot_line=$(printf '%s' "$boot" | "$tb" sha256sum) || return 1
    [ "${boot_line%% *}" = '@BOOT@' ]
}

fd_mount() {
    mount_value=
    while read -r key value extra; do
        [ "$key" = mnt_id: ] || continue
        number "$value" && [ -z "$mount_value" ] && [ -z "$extra" ] || return 1
        mount_value=$value
    done < "$proc/fdinfo/$1" || return 1
    [ -n "$mount_value" ] && printf '%s\n' "$mount_value"
}

parents_current() {
    [ "$("$tb" stat -c "$directory_format" /data)" = '@DATA@' ] &&
    [ "$("$tb" stat -Lc "$directory_format" "$data_fd")" = '@DATA@' ] &&
    [ "$("$tb" stat -c "$directory_format" /data/local)" = '@LOCAL@' ] &&
    [ "$("$tb" stat -c "$directory_format" "$data_fd/local")" = '@LOCAL@' ] &&
    [ "$("$tb" stat -Lc "$directory_format" "$local_fd")" = '@LOCAL@' ] &&
    [ "$("$tb" stat -f -c '%t' "$data_fd")" = f2f52010 ] &&
    [ "$("$tb" stat -f -c '%t' "$local_fd")" = f2f52010 ] &&
    [ "$(fd_mount 3)" = "$mount_id" ] && [ "$(fd_mount 4)" = "$mount_id" ]
}

drop_current() {
    parents_current &&
    [ "$("$tb" stat -c "$directory_format" "$local_fd/$leaf")" = "$drop_stat" ] &&
    [ "$("$tb" stat -c "$directory_format" "$drop")" = "$drop_stat" ] &&
    [ "$("$tb" stat -Lc "$directory_format" "$drop_fd")" = "$drop_stat" ] &&
    [ "$(fd_mount 5)" = "$mount_id" ]
}

missing() {
    [ ! -e "$1" ] && [ ! -L "$1" ]
}

writer_identity() {
    [ "$(fd_mount "$1")" = "$mount_id" ] || return 1
    writer=$("$tb" stat -Lc '%f|%a|%u|%g|%h|%s|%d|%i' "$proc/fd/$1") || return 1
    case "$writer" in '8180|600|0|0|1|0|@DEV@|'*) ;; *) return 1;; esac
    # Android mksh treats a bare pipe in a trim pattern as alternation.
    writer_ino=${writer##*\|}
    number "$writer_ino" || return 1
    [ "$("$tb" stat -c '%f|%a|%u|%g|%h|%s|%d|%i' "$drop_fd/$2")" = "$writer" ] &&
    printf '%s\n' "$writer_ino"
}

checked_file() {
    held=$("$tb" stat -Lc "$file_format" "$proc/fd/$1") || return 1
    case "$held" in "$5|0|0|1|$3|@DEV@|$4|"*) ;; *) return 1;; esac
    [ "$(fd_mount "$1")" = "$mount_id" ] &&
    [ "$("$tb" stat -c "$file_format" "$drop_fd/$2")" = "$held" ] &&
    [ "$("$tb" stat -c "$file_format" "$drop/$2")" = "$held" ] &&
    printf '%s\n' "$held"
}

verify_hash() {
    actual=$("$tb" sha256sum "$proc/fd/$1") || return 1
    [ "${actual%% *}" = "$2" ]
}

same_host || exit 2
[ -L "$proc/fd/0" ] && [ -L "$proc/fd/1" ] && [ -L "$proc/fd/2" ] || exit 2
for slot in 3 4 5 6 7 8 9; do
    missing "$proc/fd/$slot" || exit 2
done
[ "$("$tb" stat -c "$directory_format" /data)" = '@DATA@' ] || exit 2
exec 3< /data || exit 2
[ "$("$tb" stat -c "$directory_format" "$data_fd/local")" = '@LOCAL@' ] || exit 2
exec 4< "$data_fd/local" || exit 2
mount_id=$(fd_mount 3) || exit 2
parents_current && missing "$drop" && missing "$local_fd/$leaf" || exit 2
printf 'ONEOS_PROTECTED_DROP_HELLO_V1 @NONCE@\n' || exit 2
grant=$("$tb" dd bs=128 iflag=count_bytes count=@G_SIZE@ status=none | "$tb" sha256sum) || exit 2
[ "${grant%% *}" = '@G_SHA@' ] || exit 2

# From here on any failure retains the attempt and any actual drop. Never adopt,
# remove, rename, relabel or retry an existing object.
same_host && parents_current && missing "$drop" && missing "$local_fd/$leaf" || exit 3
"$tb" mkdir -m 0700 "$local_fd/$leaf" || exit 3
drop_stat=$("$tb" stat -c "$directory_format" "$local_fd/$leaf") || exit 3
case "$drop_stat" in '41c0|700|0|0|@DEV@|'*) ;; *) exit 3;; esac
drop_ino=${drop_stat##*\|}
number "$drop_ino" || exit 3
exec 5< "$local_fd/$leaf" || exit 3
drop_current && missing "$drop_fd/installer" && missing "$drop_fd/publisher" || exit 3

set -C
exec 6> "$drop_fd/installer" || exit 3
installer_ino=$(writer_identity 6 installer) || exit 3
exec 7> "$drop_fd/publisher" || exit 3
publisher_ino=$(writer_identity 7 publisher) || exit 3
[ "$installer_ino" != "$publisher_ino" ] && drop_current || exit 3
printf 'ONEOS_PROTECTED_DROP_READY_V1 @NONCE@\n' || exit 3

# count_bytes caps each kernel input request, preserving the next record.
"$tb" dd bs=65536 iflag=count_bytes count=@I_SIZE@ status=none conv=fsync >&6 || exit 3
"$tb" dd bs=65536 iflag=count_bytes count=@P_SIZE@ status=none conv=fsync >&7 || exit 3
extra=$("$tb" dd bs=1 iflag=count_bytes count=1 status=none | "$tb" wc -c) || exit 3
[ "$extra" -eq 0 ] && drop_current || exit 3

# Work on the held files. Open read holders before consuming the write holders.
exec 8< "$proc/fd/6" || exit 3
exec 9< "$proc/fd/7" || exit 3
checked_file 8 installer @I_SIZE@ "$installer_ino" '8180|600' >/dev/null &&
checked_file 9 publisher @P_SIZE@ "$publisher_ino" '8180|600' >/dev/null &&
verify_hash 8 '@I_SHA@' && verify_hash 9 '@P_SHA@' || exit 3
"$tb" chmod 0500 "$proc/fd/6" "$proc/fd/7" || exit 3
installer_stat=$(checked_file 8 installer @I_SIZE@ "$installer_ino" '8140|500') || exit 3
publisher_stat=$(checked_file 9 publisher @P_SIZE@ "$publisher_ino" '8140|500') || exit 3
verify_hash 8 '@I_SHA@' && verify_hash 9 '@P_SHA@' || exit 3
"$tb" fsync "$proc/fd/8" "$proc/fd/9" "$drop_fd" "$local_fd" || exit 3
exec 6>&- 7>&- || exit 3
missing "$proc/fd/6" && missing "$proc/fd/7" || exit 3
same_host && drop_current &&
[ "$(checked_file 8 installer @I_SIZE@ "$installer_ino" '8140|500')" = "$installer_stat" ] &&
[ "$(checked_file 9 publisher @P_SIZE@ "$publisher_ino" '8140|500')" = "$publisher_stat" ] || exit 3
exec 8<&- 9<&- 5<&- 4<&- 3<&- || exit 3
for slot in 3 4 5 8 9; do
    missing "$proc/fd/$slot" || exit 3
done
printf 'ONEOS_PROTECTED_DROP_V1 PUBLISHED_CLOSED @DEV@:%s\n' "$drop_ino" || exit 3
""".lstrip()
