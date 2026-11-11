#!/system/bin/sh
# OneOS lock state: read One UI's lock material once, stage a copy for the
# guest, and fail closed if the host copy changes. Host paths are never
# mounted writable from the guest and the guest copy is never written back.
#
# Usage:
#   oneos_lockstate.sh snapshot
#   oneos_lockstate.sh stage
#   oneos_lockstate.sh verify
#   oneos_lockstate.sh restore --confirm
#   oneos_lockstate.sh status
#
# Test hooks:
#   ONEOS_LOCKSTATE_HOST_ROOT  prefix for the host lock paths
#   ONEOS_LOCKSTATE_GUEST_DATA guest data root (default $STAGE/data)
#   ONEOS_LOCKSTATE_GUARD      guard directory (default $STAGE/lockstate)

set -u

STAGE=${STAGE:-/data/local/tmp/oneos}
HOST_ROOT=${ONEOS_LOCKSTATE_HOST_ROOT:-}
GUEST_DATA=${ONEOS_LOCKSTATE_GUEST_DATA:-$STAGE/data}
GUARD=${ONEOS_LOCKSTATE_GUARD:-$STAGE/lockstate}
SNAP=$GUARD/snapshot
BACK=$GUARD/backup
MAN=$GUARD/SHA256SUMS

DB=data/system/locksettings.db
GK=data/misc/gatekeeper/user0_handle
BIO=data/system/users/0
SPB=data/system_de/0/spblob
BIO_FILES="settings_fingerprint_0.xml settings_face.xml face_enrolled_position_0.xml"

say() {
    echo "$(date +%H:%M:%S) lockstate: $*"
}

die() {
    say "FAIL: $*" >&2
    exit 1
}

hostpath() {
    echo "$HOST_ROOT$1"
}

own_guest() {
    if id system >/dev/null 2>&1; then
        chown system:system "$@" || die "chown $*"
    fi
}

copy_file() {
    src=$(hostpath "/$1")
    dst="$SNAP/$1"
    [ -e "$src" ] || return 0
    mkdir -p "$(dirname "$dst")" || die "mkdir $dst"
    cp -a "$src" "$dst" || die "copy $src"
}

snapshot() {
    if pidof system_server >/dev/null 2>&1; then
        die "One UI system_server is running; snapshot after it stops"
    fi
    umask 077
    rm -rf "$SNAP" || die "clear snapshot"
    mkdir -p "$SNAP" "$BACK" || die "mkdir $GUARD"
    chmod 700 "$GUARD" "$SNAP" "$BACK"

    copy_file "$DB" "$DB"
    copy_file "$DB-wal" "$DB-wal"
    copy_file "$DB-shm" "$DB-shm"
    copy_file "$GK" "$GK"
    for f in $BIO_FILES; do
        copy_file "$BIO/$f" "$BIO/$f"
    done
    if [ -d "$(hostpath "/$SPB")" ]; then
        for f in "$(hostpath "/$SPB")"/*; do
            [ -f "$f" ] || continue
            b=$(basename "$f")
            case "$b" in *.metrics|*.bku) continue ;; esac
            copy_file "$SPB/$b" "$SPB/$b"
        done
    fi

    (cd "$SNAP" && find . -type f ! -name SHA256SUMS -exec sha256sum {} + |
        sed 's|  \./|  |') > "$MAN" || die "hash snapshot"
    [ -s "$MAN" ] || die "no lock-state files found"

    if [ -d "$BACK" ]; then
        chmod -R u+w "$BACK" 2>/dev/null || true
    fi
    rm -rf "$BACK" || die "clear backup"
    mkdir -p "$BACK" || die "mkdir backup"
    cp -a "$SNAP/." "$BACK/" || die "copy backup"
    chmod -R a-w "$BACK" || die "seal backup"
    say "snapshot: $(wc -l < "$MAN") files, hashes in $MAN"
}

stage() {
    [ -s "$MAN" ] || die "no snapshot; run snapshot first"
    (cd "$SNAP" && sha256sum -c "$MAN" >/dev/null 2>&1) ||
        die "snapshot is corrupted"

    mkdir -p "$GUEST_DATA/system" "$GUEST_DATA/system_de/0/spblob" \
        "$GUEST_DATA/system/users/0" || die "mkdir guest data"
    cp -a "$SNAP/$DB" "$GUEST_DATA/${DB#data/}" || die "stage locksettings.db"
    rm -f "$GUEST_DATA/${DB#data/}-wal" "$GUEST_DATA/${DB#data/}-shm" \
        "$GUEST_DATA/${DB#data/}-journal"
    # One UI 9 writes SQLite user_version 3; the ColorOS 17 guest's
    # LockSettingsStorage is version 2 and SQLiteOpenHelper refuses a
    # downgrade (system_server died in LockSettingsService.onBootPhase). The
    # schema is identical and unknown rows are ignored, so stamp the copy's
    # header (offset 60) to 2. The host file is never touched.
    printf '\000\000\000\002' | dd of="$GUEST_DATA/${DB#data/}" bs=1 seek=60 conv=notrunc 2>/dev/null ||
        die "stamp guest locksettings.db version"
    own_guest "$GUEST_DATA/${DB#data/}"
    chmod 600 "$GUEST_DATA/${DB#data/}"

    if [ -d "$SNAP/$SPB" ]; then
        rm -f "$GUEST_DATA/${SPB#data/}"/* || die "clear guest spblob"
        for f in "$SNAP/$SPB"/*; do
            [ -f "$f" ] || continue
            b=$(basename "$f")
            cp -a "$f" "$GUEST_DATA/${SPB#data/}/$b" || die "stage $b"
            own_guest "$GUEST_DATA/${SPB#data/}/$b"
            chmod 600 "$GUEST_DATA/${SPB#data/}/$b"
        done
    fi

    # ColorOS reads the legacy AOSP name settings_fingerprint.xml; Samsung's
    # One UI file is settings_fingerprint_0.xml. Face already uses the plain
    # settings_face.xml, so only the fingerprint name is mapped. The snapshot
    # and the host hash fence keep Samsung's name.
    rm -f "$GUEST_DATA/${BIO#data/}/settings_fingerprint_0.xml" ||
        die "remove stale fingerprint file"
    for f in $BIO_FILES; do
        [ -e "$SNAP/$BIO/$f" ] || continue
        out=$f
        [ "$f" = settings_fingerprint_0.xml ] && out=settings_fingerprint.xml
        cp -a "$SNAP/$BIO/$f" "$GUEST_DATA/${BIO#data/}/$out" || die "stage $f"
        own_guest "$GUEST_DATA/${BIO#data/}/$out"
        chmod 644 "$GUEST_DATA/${BIO#data/}/$out"
    done

    own_guest "$GUEST_DATA/system" "$GUEST_DATA/system_de" \
        "$GUEST_DATA/system_de/0" "$GUEST_DATA/system_de/0/spblob" \
        "$GUEST_DATA/system/users" "$GUEST_DATA/system/users/0"
    chmod 700 "$GUEST_DATA/system" "$GUEST_DATA/system_de" \
        "$GUEST_DATA/system_de/0" "$GUEST_DATA/system_de/0/spblob" \
        "$GUEST_DATA/system/users" "$GUEST_DATA/system/users/0"

    # guest_start.sh clears Samsung's stale lockscreen.disabled row in the
    # guest's copy once the guest has booted; this marker scopes that to a
    # session that actually staged a snapshot. /data/system is the staged
    # tree the guest sees, unlike /data itself (host user data).
    mkdir -p "$GUEST_DATA/system/oneos_lockstate" || die "mkdir guest lockstate marker"
    : > "$GUEST_DATA/system/oneos_lockstate/enabled" || die "write guest lockstate marker"
    own_guest "$GUEST_DATA/system/oneos_lockstate" "$GUEST_DATA/system/oneos_lockstate/enabled"
    chmod 700 "$GUEST_DATA/system/oneos_lockstate"
    chmod 600 "$GUEST_DATA/system/oneos_lockstate/enabled"
    say "staged read-only snapshot into $GUEST_DATA"
}

verify() {
    [ -s "$MAN" ] || die "no snapshot manifest"
    bad=0
    n=0
    while read -r hash rel; do
        [ -n "$hash" ] || continue
        n=$((n + 1))
        p=$(hostpath "/$rel")
        if [ ! -f "$p" ]; then
            say "MISSING $rel"
            bad=1
            continue
        fi
        now=$(sha256sum "$p" | awk '{print $1}')
        if [ "$now" != "$hash" ]; then
            say "CHANGED $rel"
            bad=1
        fi
    done < "$MAN"
    [ "$bad" -eq 0 ] || die "host lock-state hash mismatch"
    say "host lock-state hashes OK ($n files)"
}

restore() {
    [ "${1:-}" = "--confirm" ] || die "restore requires --confirm"
    [ -d "$BACK" ] || die "no backup"
    (cd "$BACK" && sha256sum -c "$MAN" >/dev/null 2>&1) ||
        die "backup is corrupted; refusing to restore"
    while read -r hash rel; do
        [ -n "$hash" ] || continue
        src="$BACK/$rel"
        dst=$(hostpath "/$rel")
        mkdir -p "$(dirname "$dst")" || die "mkdir $dst"
        cp -a "$src" "$dst" || die "restore $rel"
        say "restored $rel"
    done < "$MAN"
    say "restore complete"
}

status() {
    if [ -s "$MAN" ]; then
        say "snapshot: $(wc -l < "$MAN") files under $GUARD"
    else
        say "no snapshot under $GUARD"
    fi
}

case "${1:-}" in
    snapshot) snapshot ;;
    stage) stage ;;
    verify) verify ;;
    restore) shift; restore "$@" ;;
    status) status ;;
    *)
        die "usage: $0 snapshot|stage|verify|restore --confirm|status"
        ;;
esac
