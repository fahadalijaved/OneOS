# Samsung Camera in a non-Samsung guest

Nothing OS's own camera (com.nothing.camera) cannot work on a Samsung phone: it
loads `libcameradecision.so` and talks to `vendor.noth.hardware.camera`, both on
Nothing's vendor partition, written for Nothing's sensors (Nothing run 11:
`UnsatisfiedLinkError: libcameradecision.so`, then the UFS service's null
`INtCamSession`). The guest already uses this phone's camera HAL and camera
service, which are Samsung's, so One UI's own camera app runs in the guest
instead.

## What it needs, and where it comes from (2026-10-31, Z Fold8 Ultra, One UI 9, Camera 17.0.00.85)

| Need | Count | Source |
| --- | --- | --- |
| Samsung-only framework classes (`SemFloatingFeature`, `SemCscFeature`, MotionPhoto core, `SemMediaPlayer`, CoverManager, `CameraServiceWorkerCompat`...) | 51 used directly, 341 with what they reach | One UI's `framework.jar` and `worker_wrapper_compat.jar`, copied into `oneos-camera-compat.jar` |
| `sem*` members of platform classes (`View.semSetHoverPopupType`, `MediaRecorder.semSetCameraInfo`, `Build.VERSION.SEM_PLATFORM_INT`, `IWindowManager` extras...) | 171 (124 from the camera, the rest from the One UI classes) | rewritten to static shims in `Loneos/semcompat/Sem;` (generated, `gen_sem.py`) |
| Native libraries | 101 (44 the camera names, the rest what they need) | One UI's `/system/lib64`, bound as they are; two from `com.samsung.android.media.imagecodec.system` copied |
| Framework resources | 629 ids | all the same in Nothing's framework-res: nothing to do |
| `floating_feature.xml` | 1 | One UI's, bound at `/system_ext/etc` (the compat copy of `SemFloatingFeature` reads it there) |

The guest's own classes are never changed: apps detect a Samsung phone by these
very members (`SEM_PLATFORM_INT`), so adding them to the guest's framework would
send other apps down Samsung code paths. The rewrite touches only the camera,
its two library jars and the compat copy.

Shim values: builders return themselves, `semSetMarginsRelative` sets the
margins, `semCreateOutputConfiguration` builds a real `OutputConfiguration`,
`Configuration.semDisplayDeviceType` is 0 (main, the inner panel) from sw600dp
and 5 (sub, the cover) below, `SEM_PLATFORM_INT` 180000 (One UI 9),
`UserHandle.SEM_*` the real handles; the rest are no-ops or safe defaults
(`gen_sem.py`, `SPECIAL`).

## Build and stage

`scripts/samsung-camera/build.sh <system.img> <overlay set> <work dir> <out dir>`
builds the set from the phone over adb (about 400 MB pulled once: the APK,
One UI's framework jars and framework-res are only read). Push `<out dir>` to
`$STAGE/samcam_build`; `guest_prepare.sh` then binds the app, the jars and the
permission files onto the guest's system_ext (mount points in that overlay's
tmpfs layer, so the read-only form the signal poll needs takes it too), and the
native libraries, `/system/cameradata` (376 MB), `/system/saiv` (230 MB) and
`floating_feature.xml` onto the guest's `/system` through a read-only overlay of
its own, made before anything else is bound under `/system`: the native code
opens One UI's own paths (run 12: the Java feature loader threw "Feature file is
not valid", no `/system/cameradata`; 25 of the libraries name `/system/cameradata`,
`/system/saiv` or `/system/lib64` paths). `ONEOS_GUEST_SAMSUNG_CAMERA=0` leaves it
out.

Nothing of Samsung's is in a package set: the set is built from the phone it
runs on and must not be published.

## Open

- Run 12 (first): the camera died in its settings provider at start, no
  `/system/cameradata` (fixed as above).
- Video and motion photos lean on Samsung's media framework extensions
  (`MediaRecorder.sem*` are no-ops here); photos first.
- `ICameraServiceWorker` (Samsung's camera service worker) does not exist in the
  guest; the camera's Compat wrappers are expected to cope.
