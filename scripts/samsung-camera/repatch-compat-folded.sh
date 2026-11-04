#!/bin/sh
# A built samcam.tar's oneos-camera-compat.jar with gen_sem.py's 0.4.40 isFolded: a bar
# phone (fewer than two device states) reads as folded, so the Z Fold8 Ultra's camera
# takes its cover (phone) layout instead of its inner-screen one. For a set whose
# guest image is no longer on the server: decode the jar, rewrite that one branch of
# Sem.android_view_IWindowManager__isFolded (checked first), rebuild, put it back in
# the tar (other members as they are, in the same order).
# Usage: repatch-compat-folded.sh <samcam.tar> <out samcam.tar>
set -e
TAR="$1"; OUT="$2"
[ -f "$TAR" ] && [ -n "$OUT" ] || { echo "usage: $0 <samcam.tar> <out samcam.tar>" >&2; exit 2; }
R=/srv/projects/OneOS
APKTOOL=$(ls $R/mysticgsi/tools/apktool/*.jar | head -1)
TAR=$(realpath "$TAR"); OUT=$(realpath -m "$OUT")
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir "$W/t" && tar -xf "$TAR" -C "$W/t"
java -jar "$APKTOOL" d -q -f -r -o "$W/d" "$W/t/oneos-camera-compat.jar"
S=$(ls "$W"/d/smali*/oneos/semcompat/Sem.smali)
python3 -I - "$S" <<'EOF'
import re, sys
p = sys.argv[1]; s = open(p).read()
head = ".method public static android_view_IWindowManager__isFolded(Landroid/view/IWindowManager;)Z"
i = s.index(head); j = s.index(".end method", i)
body = s[i:j]
if ":oneos_foldable" in body:
    sys.exit("already patched")
m = re.search(r"(\n\s*add-int/lit8 v1, v1, -0x2\n(?:\s*\n)*)(\s*)if-ltz v1, (:cond_\d+)\n", body)
if not m or body.count("if-ltz v1,") != 1 or "const/4 v3, 0x0" not in body:
    sys.exit("isFolded is not the expected shim")
ind, label = m.group(2), m.group(3)
new = (m.group(1) + f"{ind}if-gez v1, :oneos_foldable\n\n{ind}const/4 v3, 0x1\n\n{ind}goto {label}\n\n"
       f"{ind}:oneos_foldable\n")
body = body[:m.start()] + new + body[m.end():]
open(p, "w").write(s[:i] + body + s[j:])
print("isFolded: a bar phone reads as folded")
EOF
java -jar "$APKTOOL" b -q -o "$W/t/oneos-camera-compat.jar" "$W/d"
python3 -I "$R/scripts/check-dex.py" "$W/t/oneos-camera-compat.jar"
(cd "$W/t" && tar -cf "$OUT" --owner=0 --group=0 $(tar -tf "$TAR"))
echo "built $OUT"
