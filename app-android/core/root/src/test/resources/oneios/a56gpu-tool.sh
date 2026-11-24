#!/bin/sh
# A stand-in for the staged runtime's bin/oneios-tool, as `image a56-gpu-place --stage STAGE --out DIR` answers
# (OneiOS tools/oneios-tool README "image a56-gpu-place"), for OneiosScriptTest. What it does is the file
# $ONEIOS_TEST_ROOT/a56gpu/mode: placed (default), stray (placed, and one file more), none, old (a runtime's tool
# from before the command: image's usage on stderr, exit 1), error, crash. Every call is appended to
# $ONEIOS_TEST_ROOT/a56gpu/calls. placed writes $ONEIOS_TEST_ROOT/a56gpu/addon and .../trust, and the stage's
# manifest.json with the owner-trust.json entry's sha256 and size set to the new file's.
R="$ONEIOS_TEST_ROOT/a56gpu"
echo "$*" >> "$R/calls"
mode=$(cat "$R/mode" 2>/dev/null)
[ "$1 $2 $3 $5" = "image a56-gpu-place --stage --out" ] || { echo "a56gpu-tool.sh: not a stand-in for: $*" >&2; exit 9; }
stage=$4 out=$6
case "$mode" in
    old)
        echo "The OneiOS image set: profile, inputs, hash lists, Data seed, manifest, archive." >&2
        echo "    oneios-tool image profile PROFILE [--shell | --members]      check a profile" >&2
        exit 1 ;;
    none)
        echo "a56-gpu-place: $stage/image/manifest.json is 20F66"
        echo "@@A56GPU none: the runtime carries no A56 plug-ins"
        exit 0 ;;
    error)
        echo "@@A56GPU error: the plug-ins are for iPhone10,3 20F65, the set is 20F66"
        exit 1 ;;
    crash)
        echo "thread 'main' panicked at crates/oneios-image/src/a56gpu.rs:1:1 (a56-gpu-place)" >&2
        exit 101 ;;
esac
[ -z "$(ls -A "$out")" ] || { echo "@@A56GPU error: $out is not empty"; exit 1; }
cp "$R/addon" "$out/kernel.kc.gpuaddon" || exit 1
cp "$R/trust" "$out/owner-trust.json" || exit 1
old=$(sha256sum "$stage/image/overlay/userland/owner-trust.json" | cut -d' ' -f1)
new=$(sha256sum "$out/owner-trust.json" | cut -d' ' -f1)
size=$(wc -c < "$out/owner-trust.json" | tr -d ' ')
sed "/owner-trust.json/{s/$old/$new/;s/\"size\": [0-9]*/\"size\": $size/;}" "$stage/image/manifest.json" > "$out/manifest.json" || exit 1
[ "$mode" != stray ] || echo leftover > "$out/kernel.kc.gpuaddon.part"
a=$(sha256sum "$out/kernel.kc.gpuaddon" | cut -d' ' -f1)
b=$(wc -c < "$out/kernel.kc.gpuaddon" | tr -d ' ')
m=$(sha256sum "$out/manifest.json" | cut -d' ' -f1)
echo "a56-gpu-place: 2 bundles, 3 CDHashes"
echo "@@A56GPU placed: kernel.kc.gpuaddon $a $b; owner-trust.json $new; manifest.json $m"
