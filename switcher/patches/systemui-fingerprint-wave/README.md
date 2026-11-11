# Fingerprint pressed-wave SystemUI patch

Cosmetic ColorOS 17 SystemUI patch for the guest. It does not touch
credentials: One UI's PIN, fingerprint and face remain the backend, and the
guest still reads One UI's lock state through the staged snapshot.

## What it changes

The guest's native UDFPS flow plays the pressed wave as a one-shot when the
finger touches the sensor. On this phone the thumb is often already on the
sensor while the screen is waking, so the wave ran *before* the fingerprint
glyph and usually finished long before authentication. The patch:

- Records the wake time in `oneosWakeAt` when `onStartedWakingUp` runs.
- In `startPressedAnimation`, if the touch arrives within 1200 ms of that
  wake, skips the pressed wave and shows the glyph immediately through
  `OnScreenFingerprintIcon.setVisibility(0, "startPressedAnimation")`.
- Posts `OneOsGlyphShow` 300 ms later, after `onScreenTurnedOn`, which calls
  `showFingerprintIconTemporarily` and forces the icon visible/alpha 1. This
  covers the window where `fpIconShow` is rejected because the screen is
  still off.
- Intercepts the auth-success `hideUdfpsOverlay$1` call: unless the screen is
  off, the icon is missing, enrollment is showing, or a pressed animation is
  still running, it sets `pendingHide` and starts a fresh
  `OplusAnimationDrawable` (`oneosStartWave`). The full wave then plays over
  the home screen and the pending hide removes the ring at its end.
- Builds the auth wave with a 16 ms frame duration (the stock pressed asset
  uses 20 ms, which does not divide evenly into 120 Hz vsyncs).
- Disables `notifyHighlightVisibleUpdate`, keeping the full-screen black
  `OnScreenFingerprintDimLayer` window out of the unlock path.

Stock behavior is otherwise untouched: the pressed drawable, the listener,
`fpIconHide` and `onPressedAnimEnd` still drive the hide.

## Files

`systemui-fingerprint-wave.patch` is a unified diff against the stock
`smali_classes3/com/oplus/systemui/biometrics/finger/udfps/` files. It adds the
new `OneOsGlyphShow.smali` and changes:

| File | Change |
| --- | --- |
| `OnScreenFingerprintUiMech.smali` | `oneosWakeAt` field, auth intercept in `hideUdfpsOverlay$1`, `oneosStartWave()`, `notifyHighlightVisibleUpdate` no-op |
| `OnScreenFingerprintUiMech$1.smali` | wake stamp in `:pswitch_b`, glyph gate + delayed show in `:pswitch_3` |
| `OneOsGlyphShow.smali` | new `Runnable` for the delayed glyph show |

`scripts/make-systemui-wave.sh` decodes a stock APK, applies the patch,
rebuilds `classes3.dex` and replaces it in the original archive. It applies to
the ColorOS 17 SystemUI shipped on the test device:

```
SystemUI.apk        sha256 0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77
classes3.dex        sha256 793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071
```

Check `classes3.dex` before copying; a different ColorOS build will have
different offsets and must be re-patched from its own smali.

## Build

```sh
APKTOOL="java -jar apktool.jar" scripts/make-systemui-wave.sh \
    SystemUI.apk SystemUI_wave.apk
```

Without the first argument the script pulls
`/system/system_ext/priv-app/SystemUI/SystemUI.apk` from the connected guest;
that copy must be unpatched. The script refuses an APK whose sha256 is not the
tested build unless `ONEOS_WAVE_ALLOW_OTHER=1` is set.

If apktool produces a `classes.dex` whose first 112 bytes are zero, a smali
label was not placed. Delete the decoded tree's `build` directory and read the
real `DexWriter`/`Label.getLocation` exception; do not deploy that dex.

The replaced APK keeps the original signing block, so it must be installed as
a bind mount over the stock `SystemUI.apk` rather than through PackageManager.

## Stage once, apply on every boot

`scripts/install-systemui-wave.sh` builds the patched APK, pushes it to the
guest's `/data/local/tmp/SystemUI_wave.apk`, and writes
`SystemUI_wave.stock.size` and `SystemUI_wave.stock.sha256` next to it.
`guest_start.sh` binds both the APK and an empty `oat/arm64` before zygote
starts on every guest boot, so the patch survives a guest restart.

Two fences keep the APK off another firmware. The boot hook runs only when the
guest has ColorOS's `oplus-services.jar`; HyperOS, Pixel and Infinity-X keep
their own SystemUI. It also hashes the guest's SystemUI and binds only on an
exact match with the stock APK the patch was built from, so a ColorOS update
falls back to stock until `install-systemui-wave.sh` is run again. Size alone
is not used as the identity check.

```sh
APKTOOL="java -jar apktool.jar" scripts/install-systemui-wave.sh \
    --stock /path/to/SystemUI.apk
```

The stock APK is needed only once per ColorOS SystemUI build. Without
`--stock` the script uses `out/SystemUI_stock.apk`, or pulls the running
guest's (unpatched) copy and caches it there. `--no-push` stops after the
build. When the guest is running the script also binds the APK into zygote's
namespace and restarts SystemUI immediately.

The boot hook runs in `guest_start.sh` before `zygote_exec`: zygote and
SystemUI unshare their mount namespaces, so a bind made after they start (or
from another namespace) is not visible to them.

## Deploy manually (running guest)

The guest's `/data/local/tmp` is the host stage
`/data/local/tmp/oneos/data/local/tmp`. The file must stay
`root:root 0644 u:object_r:system_file:s0` or SystemUI dies with
`SecurityException: Writable dex file ... is not allowed`.

```sh
adb push SystemUI_wave.apk /data/local/tmp/
adb shell "su -c '
  mv /data/local/tmp/SystemUI_wave.apk /data/local/tmp/oneos/data/local/tmp/
  chown root:root /data/local/tmp/oneos/data/local/tmp/SystemUI_wave.apk
  chmod 644 /data/local/tmp/oneos/data/local/tmp/SystemUI_wave.apk
  chcon u:object_r:system_file:s0 /data/local/tmp/oneos/data/local/tmp/SystemUI_wave.apk
  nsenter -t <zygote64> -m -- mount -o bind \
    /data/local/tmp/SystemUI_wave.apk \
    /system/system_ext/priv-app/SystemUI/SystemUI.apk
  kill -9 <systemui pid>'"
```

`nsenter -t <zygote64> -m` is required: SystemUI lives in zygote's mount
namespace, not system_server's. Bind an empty directory over
`/system/system_ext/priv-app/SystemUI/oat/arm64` in the same namespace first if
a stale odex is picked up. Verify the new process maps the staged inode:

```sh
grep SystemUI.apk /proc/<pid>/maps
stat -c %i /data/local/tmp/oneos/data/local/tmp/SystemUI_wave.apk
```

## Also required

The wave is smooth only with a fixed 120 Hz floor; without it SurfaceFlinger
thrashes 10 Hz <-> 120 Hz and the wave looks like 30 fps. `guest_start.sh`
sets this after boot when it binds the wave APK. To apply it by hand:

```sh
nsenter -t <system_server> -m -- settings put system min_refresh_rate 120
``` Debug markers in logcat are `OneOS glyph
first`, `OneOS glyph post`, `OneOS glyph delayed`, `OneOS glyph forced` and
`OneOS auth wave`, filtered by `OnScreenFingerprintUiMech-->|OneOS `.
