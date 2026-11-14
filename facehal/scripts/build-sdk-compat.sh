#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=${FACEHAL_SDK_COMPAT_OUTPUT_DIR:-"$root/out/android10-17"}
ndk=${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME to your NDK path}
cxx="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang++"

FACEHAL_MIN_SDK=29 "$root/scripts/build-production.sh"
mkdir -p "$output_dir"
install -m 0755 "$root/android.hardware.biometrics.face-service.facehal" \
    "$output_dir/android.hardware.biometrics.face-service.facehal"
"$cxx" -std=c++17 -Wall -Wextra -Werror -fPIC -shared \
    "$root/native/JniGraphicsShim.cpp" -o "$output_dir/libfacehal_jni.so"

echo "Built universal Android 10-17 Face HAL: $output_dir/android.hardware.biometrics.face-service.facehal"
