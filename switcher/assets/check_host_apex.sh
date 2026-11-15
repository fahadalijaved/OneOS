#!/system/bin/sh
# Read back every file of the host's APEXes that live on /data (decompressed
# or updated APEXes). After some switch sessions these returned dm-verity I/O
# errors and every One UI process that mapped them died with SIGBUS.
#
# Prints a summary; exits 1 if any read failed. Usage: check_host_apex.sh [label]
LABEL="${1:-check}"
STAMP=${ONEOS_APEX_STAMP:-/data/local/tmp/oneos/host_apex.checked}
BOOT=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
SIG=$(stat -c '%s:%Y' /apex/apex-info-list.xml 2>/dev/null)
# Reading from disk means dropping the page cache first, and everything after
# that starts cold. Only the look before the setup may skip it, and only when
# the last look of the session before (after-inplace, read from disk, nothing
# unreadable) left its stamp in this boot with the same APEX list: nothing of
# ours has run since. Every other look reads from disk: the one after the setup
# would otherwise be answered from the cache the look before it just filled.
FROM_DISK=1
[ "$LABEL" = before-setup ] && [ -n "$BOOT" ] && [ -n "$SIG" ] &&
    [ "$(cat "$STAMP" 2>/dev/null)" = "$BOOT $SIG" ] && FROM_DISK=0
# A session starts here or is still running: the stamp ends with this look.
rm -f "$STAMP" 2>/dev/null
if [ "$FROM_DISK" = 1 ]; then
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
fi
modules=$(grep -o '<apex-info [^>]*>' /apex/apex-info-list.xml |
    grep 'isActive="true"' | grep 'modulePath="/data/apex/' |
    sed 's/.*moduleName="\([^"]*\)".*/\1/' | sort -u)
files=0; bad=0; badlist=""
for m in $modules; do
    [ -d "/apex/$m" ] || continue
    n=$(find "/apex/$m" -type f 2>/dev/null | wc -l)
    files=$((files + n))
    if ! find "/apex/$m" -type f -print0 2>/dev/null | xargs -0 cat > /dev/null 2>&1; then
        for f in $(find "/apex/$m" -type f 2>/dev/null); do
            cat "$f" > /dev/null 2>&1 || {
                bad=$((bad + 1))
                badlist="$badlist $f"
            }
        done
    fi
done
src="read from disk"; [ "$FROM_DISK" = 1 ] || src="page cache kept: the last session's final look read them from disk"
echo "[$LABEL] host APEXes on /data: $(echo $modules | wc -w) modules, $files files, $bad unreadable${badlist:+:$badlist} ($src)"
if [ "$LABEL" = after-inplace ] && [ "$bad" -eq 0 ] && [ -n "$BOOT" ] && [ -n "$SIG" ]; then
    printf '%s %s\n' "$BOOT" "$SIG" > "$STAMP" 2>/dev/null
fi
[ "$bad" -eq 0 ]
