# facehal-rs

Rust vendor HAL for Android **Biometric Face AIDL v4** (`IFace/default`).

OEM-agnostic Framework Face HAL: no APK, no private Binder service, no framework
adapter, no `mifaced` dependency. Verified against ColorOS Keyguard / Settings /
`BiometricPrompt`; also handles Xiaomi camera-role metadata when present.

## Layout

| Path | Role |
|------|------|
| `rust/core` | Storage, engine, lockout, algorithm abstractions |
| `rust/service` | Face AIDL v4 service |
| `native` | Camera2, preview, algorithm, and JNI bridges |
| `config` | init `.rc` and VINTF manifest |
| `staging` | Runtime `.so` payloads for Soong packaging |
| `product` | Product makefile fragment |
| `scripts` | Host / production / SDK-compat builds |
| `standalone-build` | Offline Binder/AIDL cross-build workspace |

## Runtime libraries

Required under `staging/system_ext/lib64/facehal/`:

- `libjni_stfaceunlock_api.so`
- `libtensorflowlite.so`
- `libtensorflowlite_gpu_delegate.so`
- `libc++_shared.so`
- `libfacehal_jni.so` (also buildable from `native/JniGraphicsShim.cpp`)

## Build

```sh
export ANDROID_NDK_HOME=/path/to/ndk
export ANDROID_SYSTEM_LIB64=/path/to/system/lib64
export ANDROID_VENDOR_LIB64=/path/to/vendor/lib64

scripts/build-host.sh
scripts/build-production.sh
scripts/make-payload.sh      # -> payload/, what scripts/deploy-phone.sh pushes
scripts/build-sdk-compat.sh
```

`build-production.sh` hands the Binder crates to bindgen, which reads NDK headers.
Two environment variables are needed when the NDK sysroot is not a full platform
tree: `LIBCLANG_PATH` pointing at the host's `libclang`, and
`BINDGEN_EXTRA_CLANG_ARGS=-I<dir>` when `android/llndk-versioning.h` lives outside
the sysroot. On this build machine:

```sh
export LIBCLANG_PATH=/usr/lib
export BINDGEN_EXTRA_CLANG_ARGS=-I/tmp/opencode/android-libs/include
```

`make-payload.sh` copies the binary and the five runtime libraries from
`staging/system_ext/lib64/facehal/` into `payload/`, checking each library against
the hashes in `staging/README.md` and refusing a binary older than the sources.
The libraries are Samsung's SM-S938B vendor blobs and are not in git, so a fresh
checkout has to restore them before a payload can be built.

Output binary: `android.hardware.biometrics.face-service.facehal` (API 29+).

## Integrate

**File overlay:** install the HAL binary, `config/*.rc` / `config/*.xml`, JNI shim,
and staging libraries under `/vendor`.

**AOSP:** copy this tree to `vendor/facehal`, include `product/facehal.mk`, build
with Soong. Expected paths:

```text
/vendor/bin/hw/android.hardware.biometrics.face-service.facehal
/vendor/etc/init/android.hardware.biometrics.face-service.facehal.rc
/vendor/etc/vintf/manifest/android.hardware.biometrics.face-service.facehal.xml
/vendor/lib64/libfacehal_jni.so
/vendor/lib64/libjni_stfaceunlock_api.so
/vendor/lib64/libtensorflowlite.so
/vendor/lib64/libtensorflowlite_gpu_delegate.so
```

## OneOS changes

This tree started from [LazyBonesLZY/facehal-rs](https://github.com/LazyBonesLZY/facehal-rs).
OneOS adds what a guest ROM needs:

- `rust/service/src/dialect.rs`: AOSP, ColorOS/OxygenOS/OriginOS (`oplus`) and
  HyperOS (`miui`) enrollment semantics, picked from guest props or
  `FACEHAL_DIALECT`.
- `rust/service/src/session.rs`: vendor help codes and progress steps per
  dialect.
- `native/PreviewBridge.cpp`: cover-cropped, mirrored preview on the real
  surface size, BT.601 YUV.
- `scripts/build-production.sh`: builds the NDK/standalone Binder target used
  for the session payload.

## License

Apache-2.0 for first-party code. Bundled third-party binaries keep their original
licenses.
