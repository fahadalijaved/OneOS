#!/bin/sh
# Samsung Camera for another guest image from a cached phone pull (build.sh steps 2, 4, 5): the F8U's camera,
# One UI framework and library closure in /tmp/samcam (C=), the guest's framework read from its image.
# Usage: build-cached.sh <guest system.img | pulled folder> <guest overlay set dir> <work dir> <out dir>
# SAMCAM_CACHE: another phone's pull in the same layout (0.4.55: the S26 Ultra's, read from its firmware's
# system image, for the bar phones). SAMCAM_BAR=1: a bar phone's own camera, so no fix_bar_width.py (that
# bends the Z Fold8 Ultra's layouts to a bar phone's screen) and no fix_rear_selfie.py (a Fold feature).
set -e
IMG="$1"; SET="$2"; W="$3"; OUT="$4"
# Absolute: the steps below run in $W (a relative set dir found no *_payload.img there, so no APEX jars,
# and the shims then tried to stand in for APEX classes' constructors: "extraneous input '<init>'").
IMG=$(realpath "$IMG"); SET=$(realpath "$SET"); W=$(realpath -m "$W"); OUT=$(realpath -m "$OUT")
ls "$SET"/*_payload.img >/dev/null 2>&1 || { echo "$SET has no *_payload.img (APEX jars)" >&2; exit 1; }
C=${SAMCAM_CACHE:-/tmp/samcam}; R=/srv/projects/OneOS; HERE=$R/scripts/samsung-camera
APKTOOL=$(ls $R/mysticgsi/tools/apktool/*.jar | head -1); BT=$(ls -d /opt/android-sdk/build-tools/* | sort | tail -1)
mkdir -p "$W" "$OUT"; cd "$W"
# 2. the guest's framework jars and library names
rm -rf nt; mkdir -p nt/apex
if [ -d "$IMG" ]; then
    # A folder pulled from a phone's staged image instead (fw/ with the jars named
    # like the dumps below, guest_libs.txt): an image that is not on the server.
    cp "$IMG"/fw/*.jar nt/; cp "$IMG/guest_libs.txt" guest_libs.txt
else
for d in /system/framework /system_ext/framework /product/framework /system/system_ext/framework /my_product/framework; do
    for j in $(debugfs -R "ls $d" "$IMG" 2>/dev/null | tr -s ' ' '\n' | grep '\.jar$'); do
        debugfs -R "dump $d/$j $W/nt/$(echo $d | tr / _)_$j" "$IMG" 2>/dev/null; done
done
for d in /system/lib64 /system_ext/lib64 /system/system_ext/lib64; do debugfs -R "ls $d" "$IMG" 2>/dev/null | tr -s ' ' '\n' | grep '\.so$'; done | sort -u > guest_libs.txt
# The jars on the guest's boot class path (its classpaths/bootclasspath.pb), as named in nt/: only these (and
# the APEX jars) are classes the camera sees. A jar outside it can carry a stub or a private copy of a
# platform class: HyperOS's miuix.jar has a member-less android.view.WindowInsetsAnimation$Callback and
# xiaomi-telephony-common.jar its own org.tensorflow.lite, so scan.py thought their constructors missing and
# the shims tried to replace them ("extraneous input '<init>'"). scan.py uses nt/.bcp.txt when it is there.
for pb in /system/etc/classpaths/bootclasspath.pb /system_ext/etc/classpaths/bootclasspath.pb /system/system_ext/etc/classpaths/bootclasspath.pb; do
    debugfs -R "dump $pb $W/bcp.pb" "$IMG" 2>/dev/null && strings -n 6 bcp.pb | grep -o '/[A-Za-z0-9_./-]*\.jar' | sed 's|^//*|/|' && rm -f bcp.pb
done | sort -u | while read -r j; do echo "$(dirname "$j" | tr / _)_$(basename "$j")"; done > nt/.bcp.txt
[ -s nt/.bcp.txt ] || rm -f nt/.bcp.txt
fi
for p in "$SET"/*_payload.img; do
    n=$(basename "$p" _payload.img)
    for j in $(debugfs -R "ls /javalib" "$p" 2>/dev/null | tr -s ' ' '\n' | grep '\.jar$'); do
        debugfs -R "dump /javalib/$j $W/nt/apex/${n}_$j" "$p" 2>/dev/null; done
done
echo "guest jars: $(ls nt | wc -l) + apex $(ls nt/apex | wc -l); guest libs: $(wc -l < guest_libs.txt)"
# 4. decode, rewrite, shims, assemble
rm -rf dec_SamsungCamera; java -jar "$APKTOOL" d -r -f -q -o dec_SamsungCamera $C/SamsungCamera.apk
rm -rf dec_semextendedformat dec_secimaging dec_hostfw dec_wwc
cp -r $C/dec_semextendedformat $C/dec_secimaging .; cp -r $C/hostfw dec_hostfw; cp -r $C/dec_wwc .
rm -rf out && python3 -I "$HERE/build_samcam.py" nt,nt/apex dec_SamsungCamera,dec_semextendedformat,dec_secimaging dec_hostfw,dec_wwc out
# Rear Selfie is the Fold's (a bar phone's camera has no guide to hide).
[ "${SAMCAM_BAR:-0}" = 1 ] || python3 -I "$HERE/fix_rear_selfie.py" out/camera/dec_SamsungCamera
mkdir -p out/compat/smali/oneos/semcompat
python3 -I "$HERE/gen_sem.py" out/shims.txt out/compat/smali/oneos/semcompat/Sem.smali
sed -i 's|"/system/etc/floating_feature.xml"|"/system_ext/etc/floating_feature.xml"|' out/compat/smali/com/samsung/android/feature/SemFloatingFeature.smali
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
# 0.4.57: notification icons a guest's status bar can draw (the camera's are Samsung SPR vectors).
python3 -I "$HERE/fix_notification_icon.py" proj_SamsungCamera >/dev/null
# 0.4.59: videos kept on Stop (AOSP's recorder sends no track-started 905; the camera cancelled them).
python3 -I "$HERE/fix_recorder_track_started.py" proj_SamsungCamera >/dev/null
# 0.4.59: the thumbnail opens the guest's gallery when there is no Samsung Gallery.
python3 -I "$HERE/fix_gallery_fallback.py" proj_SamsungCamera >/dev/null
# 0.4.59: the recording timer (no 0x385 from AOSP's recorder), and media entries without Samsung's secmedia provider.
python3 -I "$HERE/fix_recorder_progress.py" proj_SamsungCamera >/dev/null
python3 -I "$HERE/fix_secmedia_insert.py" proj_SamsungCamera >/dev/null
[ "${SAMCAM_BAR:-0}" = 1 ] || python3 -I "$HERE/fix_bar_width.py" proj_SamsungCamera
java -jar "$APKTOOL" b -q -o SamsungCamera-rw.apk proj_SamsungCamera
java -jar "$APKTOOL" b -q -o semextendedformat-rw.jar proj_semextendedformat
java -jar "$APKTOOL" b -q -o secimaging-rw.jar proj_secimaging
python3 -I "$R/scripts/check-dex.py" SamsungCamera-rw.apk semextendedformat-rw.jar secimaging-rw.jar oneos-camera-compat.jar
# 5. sign and stage; the libraries the guest lacks come from One UI (system), two from its imagecodec APEX
"$BT/zipalign" -p -f 4 SamsungCamera-rw.apk aligned.apk
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android --out "$OUT/SamsungCamera.apk" aligned.apk
rm -f aligned.apk "$OUT/SamsungCamera.apk.idsig"
cp semextendedformat-rw.jar "$OUT/semextendedformat.jar"; cp secimaging-rw.jar "$OUT/secimaging.jar"; cp oneos-camera-compat.jar "$OUT/"
for f in libsimba.heifdec.media.samsung.so libimagecodec.media.quram.so OneOSSamFilterStub.apk scamera_sdk_util.jar; do cp $R/out/samcam_build/$f "$OUT/"; done
# The cache's own camera SDK jar when it has one (the S26 Ultra's goes with its camera), patched as
# every set's is (scamera_util/build.sh: CustomInterfaceHelper's CameraDevice.setParameters, a method
# no guest framework has, made by SamsungParams.set). 0.4.55 to 0.4.57 shipped it unpatched: "Fail to
# set samsung parameter", the HAL never got samsungcamera=true and ran the camera as a third-party app
# ("Unihal is bypass mode", isSamsungCamera(0): one lens, no Samsung processing; S25 Ultra 3715fe57,
# S23 Ultra 4a519895).
if [ -f "$C/scamera_sdk_util.jar" ]; then sh "$HERE/scamera_util/build.sh" "$PWD/scamera_util_work" "$OUT" "$C/scamera_sdk_util.jar"; fi
grep -q 'Lcom/oneos/camera/SamsungParams;' "$OUT/scamera_sdk_util.jar" || { echo "$OUT/scamera_sdk_util.jar has no SamsungParams (One UI's own jar)" >&2; exit 1; }
{ grep -vxFf guest_libs.txt $C/all_needed.txt | grep -v -E '^(libsimba.heifdec.media.samsung.so|libimagecodec.media.quram.so)$' | sed 's/$/ system/'; echo "libsimba.heifdec.media.samsung.so apex"; echo "libimagecodec.media.quram.so apex"; } > "$OUT/libs.txt"
echo "built $OUT ($(wc -l < "$OUT/libs.txt") libraries; Nothing's had $(wc -l < $R/out/samcam_build/libs.txt))"
