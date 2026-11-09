# Guest runtime sources

The bundled injection files are modified NeoZygisk, GPL-3.0, based on
[`c4caec94c950da36bedfbe20e84a849d269175ef`](https://github.com/JingMatrix/NeoZygisk/tree/c4caec94c950da36bedfbe20e84a849d269175ef).
The complete local changes are in `neozygisk.patch`. Apply with `git apply --unidiff-zero` to
that checkout after initializing its submodules. Copy the committed `Cargo.lock`
from this directory to `zygiskd/Cargo.lock` before the locked Cargo build. License texts are shipped in
`app-android/app/src/full/assets/guest-runtime`.

The patch disables global monitor/boot-stage entry points, keeps the guest mount
namespace, replaces host root-policy lookups with guest grants, removes monitor
IPC, and avoids changing host kernel module-unmount policy. Namespace caching authenticates peer credentials and pins guest namespace FDs;
grant lookups revalidate package/UID associations. The tracer requires a target
owned by its invoking launcher in the same guest filesystem root. The native OneOS
broker/launcher lives in `switcher/native/guest_root.c` (GPL-3.0-or-later).

Build the broker as a static arm64 Android executable using the Android NDK
Clang wrapper (`aarch64-linux-android29-clang -static -O2 -s`), then run
`llvm-strip --strip-all guest_root` (`-s` alone retains the `.comment` section). For NeoZygisk,
use its CMake loader project with the Android toolchain, API 29, arm64-v8a,
`WORK_DIRECTORY=\"/data/adb/oneos/run/zygisk\"`, and a guest-specific
`ZKSU_VERSION`. Build `zygisk` and `libzygisk_ptrace.so`, then strip and copy to
`guest_zygisk.so` and `guest_zygisk_ptrace`. Build its Rust `zygiskd` with
`cargo ndk --platform 29 -t arm64-v8a build --release --locked`, setting
`MIN_APATCH_VERSION=10762`, `MIN_KSU_VERSION=10940`, `MIN_MAGISK_VERSION=26402`,
and `ZKSU_VERSION`. Strip/copy as `guest_zygiskd`. The checked-in arm64 artifacts
used NDK 28.2.13676358. Rebuilt binaries require device validation before release.

Vector is the official [v2.2 release](https://github.com/JingMatrix/Vector/releases/tag/v2.2),
GPL-3.0; matching source commit is `88f8e1faa8b4e7ce20aefabe9c295cd746ea038e`.
Run `scripts/normalize-guest-vector.py vector-v2.2.zip output.bundle`. The script
verifies the official ZIP SHA-256 and produces the checked-in bundle byte for
byte. It maps ABI-specific files to the installed layout and removes the daemon
shell script's `/data/local/tmp/daemon.apk` debug override. APK/DEX bytes are
unchanged. No installer is executed on the build host.

`artifacts.sha256` records the bundled native/framework bytes. The generated
guest manager APK is intentionally absent: build it from the repository's
`:guest` sources with `scripts/build-guest-manager.sh` before the host app.
Production APKs must use the real OneOS release key; local signature-metadata
transplants used for device experiments are outside the contribution.

Security regression checks run with `python3 scripts/test-guest-security.py`.
They compile the actual broker descriptor parser and the Rust/C++ policies from
this patch. They require C/C++ compilers and Cargo; the pinned anyhow/libc crates
must be cached for the offline Rust tests. These host checks do not replace an
Android guest boot test of the rebuilt injector.
