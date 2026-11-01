#!/bin/sh
# Rebuild the root-only handoff renderer; no signing key or third-party dependency.
set -eu
cd "$(dirname "$0")/.."
sdk=${ANDROID_HOME:?Set ANDROID_HOME to the Android SDK}
javac=${JAVA_HOME:+$JAVA_HOME/bin/}javac
jar=$(find "$sdk/platforms" -name android.jar | sort -V | tail -1)
d8=$(find "$sdk/build-tools" -name d8 | sort -V | tail -1)
[ -n "$jar" ] && [ -n "$d8" ]
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
"$javac" --release 17 -cp "$jar" -d "$tmp" switcher/patches/OneOSBootStatus.java
"$d8" --min-api 31 --lib "$jar" --output "$tmp" "$tmp/OneOSBootStatus.class"
cp "$tmp/classes.dex" switcher/assets/OneOSBootStatus.dex
