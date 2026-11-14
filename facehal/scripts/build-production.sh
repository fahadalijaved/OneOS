#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
workspace="$root/standalone-build"
ndk=${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME to your NDK path}
toolchain="$ndk/toolchains/llvm/prebuilt/linux-x86_64"
api=${FACEHAL_MIN_SDK:-29}
case "$api" in
    ''|*[!0-9]*)
        echo "FACEHAL_MIN_SDK must be a numeric Android API level" >&2
        exit 1
        ;;
esac
[ "$api" -ge 29 ] || {
    echo "Face HAL Binder requires Android API 29 or newer" >&2
    exit 1
}

cxx="$toolchain/bin/aarch64-linux-android${api}-clang++"
linker="$toolchain/bin/aarch64-linux-android${api}-clang"
ar="$toolchain/bin/llvm-ar"
target=aarch64-linux-android
output=${FACEHAL_OUTPUT:-"$root/android.hardware.biometrics.face-service.facehal"}

[ -x "$cxx" ] || { echo "missing Android NDK compiler: $cxx" >&2; exit 1; }
[ -x "$linker" ] || { echo "missing Android NDK linker: $linker" >&2; exit 1; }
[ -d "$workspace/third_party/binder" ] || { echo "missing standalone Binder source" >&2; exit 1; }

mkdir -p "$workspace/native"
"$cxx" -DFACEHAL_VENDOR_CAMERA_NDK=1 -std=c++17 -O2 -fPIC -Wall -Wextra -Werror \
    -I "$root/native" -c "$root/native/CameraBridge.cpp" \
    -o "$workspace/native/CameraBridge.o"
"$cxx" -std=c++17 -O2 -fPIC -Wall -Wextra -Werror \
    -I "$root/native" -c "$root/native/PreviewBridge.cpp" \
    -o "$workspace/native/PreviewBridge.o"
"$cxx" -std=c++17 -O2 -fPIC -Wall -Wextra -Werror \
    -I "$root/native" -c "$root/native/SenseTimeBridge.cpp" \
    -o "$workspace/native/SenseTimeBridge.o"
"$ar" rcs "$workspace/native/libfacehal_bridge.a" \
    "$workspace/native/CameraBridge.o" \
    "$workspace/native/PreviewBridge.o" \
    "$workspace/native/SenseTimeBridge.o"

export FACEHAL_ROOT="$root"
export ANDROID_NDK_HOME="$ndk"
export BINDER_PLATFORM_HEADERS="$workspace/third_party/binder-headers/include_platform"
export BINDER_NDK_LIB_DIR=${BINDER_NDK_LIB_DIR:-"$toolchain/sysroot/usr/lib/aarch64-linux-android/$api"}
export LIBCLANG_PATH=${LIBCLANG_PATH:-"$toolchain/lib"}
export FACEHAL_ANDROID_API="$api"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$linker"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_AR="$ar"

[ -d "$BINDER_NDK_LIB_DIR" ] || {
    echo "missing Android NDK Binder library directory: $BINDER_NDK_LIB_DIR" >&2
    exit 1
}

cd "$workspace"
cargo build --release --target "$target" -p facehal_service
mkdir -p "$(dirname -- "$output")"
install -m 0755 "target/$target/release/facehal_service" "$output"

cd "$root"
echo "Built Android API $api+ production HAL: $output"
