#!/bin/sh
# host-tools.sh BIN: the core:root tests' stand-ins for the tools whose options the root scripts take
# from the phone (toybox, busybox: GNU's `stat -c`, `sha256sum`, `timeout`, `tac`, `sed -i`) where this
# machine's own differ, written into BIN, which the harnesses (HostTools, FakeRoot.kt) put on PATH
# after their own stubs and before the machine's folders. Each is chosen by what the machine's tool
# does, never by the system's name: on Linux with GNU coreutils BIN stays empty and nothing changes.
# On macOS: Homebrew's GNU tool (gstat, gsha256sum, ...) where there is one, else a translation
# (gnu-stat.sh over BSD stat, shasum, awk, perl). One line on stdout for each stand-in.
# The scripts themselves are not changed: on the phone none of this exists.
set -u
BIN=$1
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$BIN"
probe=$(mktemp -d "${TMPDIR:-/tmp}/oneos-hosttools-probe.XXXXXX")
trap 'rm -rf "$probe"' EXIT
printf 'a\n' > "$probe/f"

# Homebrew's g-prefixed GNU tool, on PATH or where Homebrew puts it (a Gradle daemon's PATH can be short).
gnu() {
    for d in $(printf '%s' "$PATH" | tr ':' ' ') /opt/homebrew/bin /usr/local/bin; do
        [ -x "$d/g$1" ] && { echo "$d/g$1"; return 0; }
    done
    return 1
}
wrap() { # <name> <why> <body>
    printf '#!/bin/sh\n%s\n' "$3" > "$BIN/$1"
    chmod 755 "$BIN/$1"
    echo "$1: $2"
}
use_gnu() { # <name>: Homebrew's g<name>, if there is one
    g=$(gnu "$1") || return 1
    wrap "$1" "$g" "exec '$g' \"\$@\""
}

# stat -c: GNU's format, checked on a file of ours (BSD's stat refuses -c: the owner check then reads
# nothing and every stage folder "is not root's").
if [ "$(stat -c '%u' "$probe/f" 2>/dev/null)" != "$(id -u)" ]; then
    if use_gnu stat; then :
    elif real=$(command -v stat) && [ "$("$real" -f '%u' "$probe/f" 2>/dev/null)" = "$(id -u)" ]; then
        sed "s|@REAL_STAT@|'$real'|" "$HERE/gnu-stat.sh" > "$BIN/stat"
        chmod 755 "$BIN/stat"
        echo "stat: gnu-stat.sh over BSD's $real"
    else
        echo "stat: neither GNU's -c nor BSD's -f works here; the root script tests will refuse" >&2
    fi
fi

# sha256sum: GNU's output (hash, two spaces, name) and -c.
if ! command -v sha256sum >/dev/null 2>&1; then
    use_gnu sha256sum || { command -v shasum >/dev/null 2>&1 && wrap sha256sum "shasum -a 256" 'exec shasum -a 256 "$@"'; }
fi

# timeout DURATION COMMAND...: GNU's 124 when the time ran out.
if ! command -v timeout >/dev/null 2>&1; then
    use_gnu timeout || { command -v perl >/dev/null 2>&1 && wrap timeout perl '
d=${1%s}; shift
exec perl -MTime::HiRes=alarm -e '\''
    my $d = shift; my $pid = fork; defined $pid or exit 125;
    if (!$pid) { exec @ARGV; exit 127 }
    local $SIG{ALRM} = sub { kill "TERM", $pid; waitpid $pid, 0; exit 124 };
    alarm $d; waitpid $pid, 0;
    exit(($? & 127) ? 128 + ($? & 127) : $? >> 8);
'\'' "$d" "$@"'; }
fi

# tac.
if ! command -v tac >/dev/null 2>&1; then
    use_gnu tac || wrap tac awk 'exec awk '\''{ l[NR] = $0 } END { for (i = NR; i > 0; i--) print l[i] }'\'' "$@"'
fi

# sed -i without a suffix (BSD's takes the next word as one).
cp "$probe/f" "$probe/s"
if ! sed -i 's/a/b/' "$probe/s" 2>/dev/null || [ "$(cat "$probe/s")" != b ]; then
    use_gnu sed || echo "sed: this machine's sed -i is not GNU's and there is no gsed (brew install gnu-sed)" >&2
fi
exit 0
