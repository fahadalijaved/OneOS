#!/bin/sh
# Assemble the facehal-rs payload that guest_prepare.sh stages on the phone:
# the built HAL plus the five runtime libraries under staging/.
#
# The libraries are Samsung vendor blobs (staging/README.md lists them with their
# hashes), so they are not in git: this checks whatever staging/ holds instead of
# shipping it. The HAL itself comes from scripts/build-production.sh; a payload
# directory with a stale binary is worse than no directory, so the binary is only
# copied when it is newer than every source file under native/ and rust/.
#
# scripts/deploy-phone.sh pushes the result to /data/local/tmp/facehal, which is
# where guest_prepare.sh reads it from.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
payload="$root/payload"
binary="$root/android.hardware.biometrics.face-service.facehal"
staging="$root/staging/system_ext/lib64/facehal"

[ -f "$binary" ] || {
    echo "missing $binary: run scripts/build-production.sh first" >&2
    exit 1
}
stale=$(find "$root/native" "$root/rust" "$root/Cargo.toml" -newer "$binary" -print 2>/dev/null | head -1)
[ -z "$stale" ] || {
    echo "$binary is older than $stale: run scripts/build-production.sh" >&2
    exit 1
}

rm -rf "$payload"
mkdir -p "$payload/bin/hw" "$payload/lib64"
install -m 0755 "$binary" "$payload/bin/hw/android.hardware.biometrics.face-service.facehal"

missing=0
while read -r name want; do
    [ -n "$name" ] || continue
    [ -f "$staging/$name" ] || { echo "missing $staging/$name" >&2; missing=1; continue; }
    have=$(sha256sum "$staging/$name" | cut -d' ' -f1)
    [ "$have" = "$want" ] || {
        echo "$name is $have, staging/README.md documents $want" >&2
        missing=1
        continue
    }
    install -m 0644 "$staging/$name" "$payload/lib64/$name"
done <<'LIBS'
libc++_shared.so 95f1dd493ef287b4cf6befba91bc4f994235fffe768dd055bbb10c81854de694
libfacehal_jni.so 042cb2f414888fce962fc74ed00de97161837f6fa8e3e16511bf7df08df7c199
libjni_stfaceunlock_api.so c1824b6ef157352f2ea117ade8319ba3e02f5d193f0047ad6f31e2948452d12b
libtensorflowlite_gpu_delegate.so c516c7be3e6d42af942d8753ecc2a2be31215779f34b8b7e746ca6672b52fc9c
libtensorflowlite.so ca085b6abfa19ee8c5d836efd1d93c180c101b450dbdb8d00064e154d790ad9b
LIBS
[ "$missing" = 0 ] || {
    echo "the payload needs Samsung's SM-S938B vendor libraries (staging/README.md)" >&2
    rm -rf "$payload"
    exit 1
}

du -sh "$payload"
echo "payload ready: $payload"
