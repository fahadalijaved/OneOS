#!/bin/sh
# Build the staged set that runs One UI's camera in a non-Samsung guest
# (switcher/samsung-camera.md): SamsungCamera.apk rewritten against the guest's
# framework, its two library jars likewise, oneos-camera-compat.jar (the One UI
# classes it reaches plus the sem* shims), the two imagecodec APEX libraries
# and libs.txt (what guest_prepare.sh binds from One UI's /system/lib64).
#
# Everything Samsung comes from the phone's own One UI (ANDROID_SERIAL picks
# it) and stays in the work dir and the output: it is not part of any package
# set and must not be published.
#
# Usage: scripts/samsung-camera/build.sh <guest system.img> <guest overlay set dir> <work dir> <out dir>
#   e.g. build.sh out/nothing-local/OneOS_NothingOS5_Metroid.img out/overlays_nothing_r13 /tmp/samcam out/samcam_build
set -e
IMG="$1"; SET="$2"; W="$3"; OUT="$4"
[ -f "$IMG" ] && [ -d "$SET" ] && [ -n "$W" ] && [ -n "$OUT" ] || { echo "usage: $0 <system.img> <overlay set> <work dir> <out dir>" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
APKTOOL=$(ls "$ROOT"/mysticgsi/tools/apktool/*.jar | head -1)
BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
mkdir -p "$W" "$OUT"
cd "$W"

# 1. From the phone: the camera, its jars, One UI's framework.jar and
#    worker_wrapper_compat.jar, and the camera's native library closure.
for f in /system/priv-app/SamsungCamera/SamsungCamera.apk /system/framework/semextendedformat.jar \
         /system/framework/secimaging.jar; do adb pull "$f" . >/dev/null; done
mkdir -p host && for f in /system/framework/framework.jar /system/framework/worker_wrapper_compat.jar; do
    adb pull "$f" host/ >/dev/null; done
adb shell "ls /system/lib64" | tr -d '\r' | grep '\.so$' > host_lib64.txt

# 2. The guest's framework: every jar of its system, system_ext and product
#    framework dirs and of the staged APEX payloads; its library names.
mkdir -p nt/apex
for d in /system/framework /system_ext/framework /product/framework; do
    for j in $(debugfs -R "ls $d" "$IMG" 2>/dev/null | tr -s ' ' '\n' | grep '\.jar$'); do
        debugfs -R "dump $d/$j $W/nt/$(echo $d | tr / _)_$j" "$IMG" 2>/dev/null; done
done
for p in "$SET"/*_payload.img; do
    n=$(basename "$p" _payload.img)
    for j in $(debugfs -R "ls /javalib" "$p" 2>/dev/null | tr -s ' ' '\n' | grep '\.jar$'); do
        debugfs -R "dump /javalib/$j $W/nt/apex/${n}_$j" "$p" 2>/dev/null; done
done
for d in /system/lib64 /system_ext/lib64; do
    debugfs -R "ls $d" "$IMG" 2>/dev/null | tr -s ' ' '\n' | grep '\.so$'
done | sort -u > nt_libs.txt

# 3. The native library closure: what the camera declares, then whatever those
#    need that the guest lacks, from One UI's /system/lib64, until nothing new.
mkdir -p libs
adb shell "dumpsys package com.sec.android.app.camera" | tr -d '\r' |
    sed -n '/usesNativeLibraries:/,/usesLibraryFiles:/p' | grep '\.so' | tr -d ' ' > want.txt
grep -xFf host_lib64.txt want.txt > fetch.txt || true
while [ -s fetch.txt ]; do
    adb shell "cd /system/lib64 && tar -czf /data/local/tmp/samcam_libs.tgz $(tr '\n' ' ' < fetch.txt)"
    adb pull /data/local/tmp/samcam_libs.tgz . >/dev/null && adb shell rm -f /data/local/tmp/samcam_libs.tgz
    tar -xzf samcam_libs.tgz -C libs
    for f in libs/*.so; do readelf -d "$f" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'; done | sort -u |
        while read -r l; do [ -f "libs/$l" ] || grep -qx "$l" nt_libs.txt || ! grep -qx "$l" host_lib64.txt || echo "$l"; done > fetch.txt
done
APEX=/apex/com.samsung.android.media.imagecodec.system/lib64
for l in libsimba.heifdec.media.samsung.so libimagecodec.media.quram.so; do adb pull "$APEX/$l" libs/ >/dev/null; done

# 4. Decompile, rewrite (build_samcam.py), shims (gen_sem.py), the floating
#    feature path, assemble.
for x in SamsungCamera.apk semextendedformat.jar secimaging.jar; do java -jar "$APKTOOL" d -r -f -q -o "dec_${x%.*}" "$x"; done
java -jar "$APKTOOL" d -r -f -q -o dec_hostfw host/framework.jar
java -jar "$APKTOOL" d -r -f -q -o dec_wwc host/worker_wrapper_compat.jar
rm -rf out && python3 -I "$HERE/build_samcam.py" nt,nt/apex dec_SamsungCamera,dec_semextendedformat,dec_secimaging dec_hostfw,dec_wwc out
python3 -I "$HERE/fix_rear_selfie.py" out/camera/dec_SamsungCamera
mkdir -p out/compat/smali/oneos/semcompat
python3 -I "$HERE/gen_sem.py" out/shims.txt out/compat/smali/oneos/semcompat/Sem.smali
sed -i 's|"/system/etc/floating_feature.xml"|"/system_ext/etc/floating_feature.xml"|' out/compat/smali/com/samsung/android/feature/SemFloatingFeature.smali
# SemWindowManager.setForcedDefaultDisplayDevice asks the device state manager
# for a fold state (the camera on the cover asks for the main panel's); One UI's
# camera holds CONTROL_DEVICE_STATE, this one does not, and the guest's fold
# states are OneOS's: "Permission required to request device state", crash on
# every cover start (run 18). The request is dropped; cancel and the log stay.
sed -i '/DeviceStateManagerGlobal;->requestState(Landroid\/hardware\/devicestate\/DeviceStateRequest;/d' out/compat/smali/com/samsung/android/view/SemWindowManager.smali
# The executor that request took is then unused; an image without One UI's
# PendingIntent$$ExternalSyntheticLambda1 (the Find N6 build) got a constructor
# shim named <init>, which smali refuses. Both lines and that shim go.
sed -i '/PendingIntent\$\$ExternalSyntheticLambda1/d' out/compat/smali/com/samsung/android/view/SemWindowManager.smali
grep -q 'PendingIntent__ExternalSyntheticLambda1__<init>' out/shims.txt && {
    sed -i '/PendingIntent__ExternalSyntheticLambda1__<init>/d' out/shims.txt
    python3 -I "$HERE/gen_sem.py" out/shims.txt out/compat/smali/oneos/semcompat/Sem.smali
}
rm -rf proj_compat && mkdir proj_compat && cp -r out/compat/smali proj_compat/smali
cp -r "$HERE/compat_extra/." proj_compat/smali/
printf 'version: 3.0.3\napkFileName: oneos-camera-compat.jar\nsdkInfo:\n  minSdkVersion: 36\ndoNotCompress:\n- dex\n' > proj_compat/apktool.yml
java -jar "$APKTOOL" b -q -o oneos-camera-compat.jar proj_compat
for n in SamsungCamera semextendedformat secimaging; do
    rm -rf "proj_$n" && cp -r "dec_$n" "proj_$n"
    [ -d "out/camera/dec_$n" ] && cp -r "out/camera/dec_$n/." "proj_$n/"
done
python3 -I "$HERE/fix_recorder_location.py" proj_SamsungCamera
python3 -I "$HERE/fix_bar_width.py" proj_SamsungCamera
java -jar "$APKTOOL" b -q -o SamsungCamera-rw.apk proj_SamsungCamera
java -jar "$APKTOOL" b -q -o semextendedformat-rw.jar proj_semextendedformat
java -jar "$APKTOOL" b -q -o secimaging-rw.jar proj_secimaging
python3 -I "$ROOT/scripts/check-dex.py" SamsungCamera-rw.apk semextendedformat-rw.jar secimaging-rw.jar oneos-camera-compat.jar

# 5. Sign (any key: a system_ext priv-app outside every shared uid) and stage.
"$BT/zipalign" -p -f 4 SamsungCamera-rw.apk aligned.apk
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey \
    --key-pass pass:android --out "$OUT/SamsungCamera.apk" aligned.apk
rm -f aligned.apk "$OUT/SamsungCamera.apk.idsig"
cp semextendedformat-rw.jar "$OUT/semextendedformat.jar"; cp secimaging-rw.jar "$OUT/secimaging.jar"
cp oneos-camera-compat.jar "$OUT/"
cp libs/libsimba.heifdec.media.samsung.so libs/libimagecodec.media.quram.so "$OUT/"
for f in $(ls libs); do
    case $f in libsimba.heifdec.media.samsung.so|libimagecodec.media.quram.so) echo "$f apex" ;; *) echo "$f system" ;; esac
done > "$OUT/libs.txt"
echo "built $OUT ($(wc -l < "$OUT/libs.txt") libraries)"
