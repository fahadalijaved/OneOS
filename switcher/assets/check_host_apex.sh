#!/system/bin/sh
# Read back every file of the host's APEXes that live on /data (decompressed
# or updated APEXes). After some switch sessions these returned dm-verity I/O
# errors and every One UI process that mapped them died with SIGBUS.
#
# Prints a summary; exits 1 if any read failed. Usage: check_host_apex.sh [label]
LABEL="${1:-check}"
STAMP=/data/local/tmp/oneos/host_apex.checked
BOOT=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
SIG=$(stat -c '%s:%Y' /apex/apex-info-list.xml 2>/dev/null)
if [ "$(cat "$STAMP" 2>/dev/null)" != "$BOOT $SIG" ]; then
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
echo "[$LABEL] host APEXes on /data: $(echo $modules | wc -w) modules, $files files, $bad unreadable${badlist:+:$badlist}"
if [ "$bad" -eq 0 ] && [ -n "$BOOT" ] && [ -n "$SIG" ]; then
    printf '%s %s\n' "$BOOT" "$SIG" > "$STAMP" 2>/dev/null
else
    rm -f "$STAMP" 2>/dev/null
fi
[ "$bad" -eq 0 ]
