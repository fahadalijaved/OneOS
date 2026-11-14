#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ndk=${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME to your NDK path}
cxx="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang++"

[ -x "$cxx" ] || {
    echo "missing Android NDK compiler: $cxx" >&2
    exit 1
}

cd "$root"

"$cxx" -std=c++17 -Wall -Wextra -Werror -fPIC -shared \
    native/JniGraphicsShim.cpp -o /tmp/libfacehal_jni.so
cargo test -p facehal_core

"$cxx" -std=c++17 -Wall -Wextra -Werror -I native \
    -c native/CameraBridge.cpp -o /tmp/facehal-CameraBridge.o
"$cxx" -std=c++17 -Wall -Wextra -Werror -I native \
    -c native/PreviewBridge.cpp -o /tmp/facehal-PreviewBridge.o
"$cxx" -std=c++17 -Wall -Wextra -Werror -I native \
    -c native/SenseTimeBridge.cpp -o /tmp/facehal-SenseTimeBridge.o

cat >/tmp/facehal-bridge-link.cpp <<'BRIDGE'
#include "CameraBridge.h"
#include "PreviewBridge.h"
#include "SenseTimeBridge.h"
int main() {
    (void)facehal_camera_open;
    (void)facehal_preview_render_nv21;
    (void)facehal_algorithm_open;
    return 0;
}
BRIDGE

"$cxx" -std=c++17 -I native /tmp/facehal-bridge-link.cpp \
    /tmp/facehal-CameraBridge.o /tmp/facehal-PreviewBridge.o /tmp/facehal-SenseTimeBridge.o \
    -lcamera2ndk -lmediandk -landroid -llog -ldl \
    -o /tmp/facehal-bridge-link

file /tmp/facehal-bridge-link
echo "host and ARM64 native checks passed"
