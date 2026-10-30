#!/bin/sh
# Builds the static aarch64 helpers in this directory into ../assets/.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
NDK="${ANDROID_NDK_HOME:-$(ls -d "$ANDROID_HOME"/ndk/* | sort -V | tail -1)}"
CC="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"
STRIP="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"

"$CC" --target=aarch64-linux-android29 -static -O2 -Wall -Wextra \
    -o "$DIR/../assets/zygote_exec" "$DIR/zygote_launcher.c"
"$STRIP" "$DIR/../assets/zygote_exec"
ls -la "$DIR/../assets/zygote_exec"

"$CC" --target=aarch64-linux-android29 -static -O2 -Wall -Wextra \
    -o "$DIR/bin/socket_exec" "$DIR/socket_exec.c"
"$STRIP" "$DIR/bin/socket_exec"
ls -la "$DIR/bin/socket_exec"
