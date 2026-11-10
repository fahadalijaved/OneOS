#!/system/bin/sh
# OneOS probe runner, Friend build 1 (0.2.1-probe).
# Stream format oneos.probe-stream/1 (docs/app/compat-safety-logs.md section 7.3).
#
# Usage, as root:  sh probe.sh <commands.list>
#
# Runs every entry of commands.list, the one list of probe commands, each with
# a timeout, and writes all output to stdout, base64 framed, for OneOS to save
# in its own cache folder. This script writes no file: its only redirections
# go to stdout, /dev/null and file descriptors 3 and 4 (pipes inside this
# process). Besides the entries it runs only printf, timeout, sh -c, base64,
# cat, unzip -p and stat. ProbeAudit.auditRunner checks this in the unit tests
# and again in the app before every run.

LIST="$1"
MAXFILE=67108864
PATH="/system/bin:$PATH"

# run <id> <timeout s> <output file> <command>
# The command's stdout and stderr become one file; its exit code is the status.
# A reader that is gone (OneOS cancelled the run: its end of the pipe is closed)
# ends the script at the next entry instead of running the rest of the list
# unread; root's process cannot be signalled by the app (0.4.76).
run() {
    printf "@@PROBE %s %s\n" "$1" "$2" || exit 0
    printf "@@FILE %s -\n" "$3"
    rc=$( { { timeout -k 2 "$2" sh -c "$4" </dev/null 2>&1; printf "%s\n" "$?" >&3; } | base64 >&4; } 3>&1 )
    printf "@@END %s\n" "$rc"
    printf "@@STATUS %s %s\n" "$1" "$rc"
}

# files <id> <timeout s> <output folder> <command>
# The command prints one path, or jar!entry, per line; each is read with cat
# (or unzip -p) and becomes one file. Nothing printed = not present (3).
# Only regular files are read (never a device, FIFO or folder).
files() {
    printf "@@PROBE %s %s\n" "$1" "$2" || exit 0
    list=$(timeout -k 2 "$2" sh -c "$4" </dev/null 2>/dev/null)
    rc=$?
    got=0
    bad=0
    for src in $list; do
        got=1
        jar="${src%%!*}"
        if [ ! -f "$jar" ]; then
            printf "@@NOTE %s skipped (not a regular file)\n" "$jar"
            bad=1
            continue
        fi
        if [ "$jar" != "$src" ]; then
            entry="${src#*!}"
            printf "@@FILE %s %s\n" "$3" "$src"
            frc=$( { { timeout -k 2 "$2" unzip -p "$jar" "$entry" </dev/null 2>/dev/null; printf "%s\n" "$?" >&3; } | base64 >&4; } 3>&1 )
        else
            size=$(stat -c %s "$src" 2>/dev/null)
            if [ -z "$size" ] || [ "$size" -gt "$MAXFILE" ]; then
                printf "@@NOTE %s skipped (size %s)\n" "$src" "$size"
                bad=1
                continue
            fi
            printf "@@FILE %s %s\n" "$3" "$src"
            frc=$( { { timeout -k 2 "$2" cat "$src" </dev/null 2>/dev/null; printf "%s\n" "$?" >&3; } | base64 >&4; } 3>&1 )
        fi
        printf "@@END %s\n" "$frc"
        [ "$frc" = 0 ] || bad=1
    done
    if [ "$rc" = 0 ] && [ "$got" = 0 ]; then rc=3; fi
    if [ "$rc" = 0 ] && [ "$bad" = 1 ]; then rc=1; fi
    printf "@@STATUS %s %s\n" "$1" "$rc"
}

set -f
command -v timeout >/dev/null 2>&1 || { printf "@@ERROR no timeout command\n"; exit 2; }
command -v base64 >/dev/null 2>&1 || { printf "@@ERROR no base64 command\n"; exit 2; }
[ -r "$LIST" ] || { printf "@@ERROR cannot read the command list\n"; exit 2; }
printf "@@ONEOS-PROBE 1\n"
{ . "$LIST"; } 4>&1
printf "@@DONE\n"
