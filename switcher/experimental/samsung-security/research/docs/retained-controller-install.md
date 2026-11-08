# Fixed closed-controller installer

Status: standalone actual handler source reviewed; full launcher/feed integration
review remains separate and pending. No shell,
root script, compiler, native controller, model or device workflow ran here.

The new internal verb is `install-closed-controller <bytes> <sha256>`. Its only
input is the remaining native payload on stdin followed by EOF. Byte count must
be canonical positive decimal1..2097152 and SHA exactly64 lowercase hex. No
filename, path, user, guest, profile or command is accepted. Both new publication
and same-image idempotence return exactly `@@OK closed-controller-installed`,
and only after the handler's checked cleanup. That line alone is not process
exit, durable storage or native-session acceptance.

## Actual files and insertion

The authored normal fragment is
`compat/app-integration/retained-controller-install.sh`. It defines only the new
subshell handler and invokes nothing when sourced. The identical handler is
embedded immediately before Main in the ignored upstream clone's
`app-android/app/src/full/assets/root/oneos_root.sh`, plus one verb documentation
line and one dispatch entry. Removing precisely these additions reproduces the
captured beforeimage. Original handlers/guards are unchanged. The new verb is
absent from migrate_legacy's cases, so it cannot rename an older stage.
The clone's existing CRLF is preserved for that inverse; the beforeimage's LF
projection is the original82,529-byte upstream script. Selecting runnable LF
asset bytes and their actual pins remains a packaging step, not a runtime claim
from this Windows checkout.

The containing script supplies its existing fixed STAGE/ROOT_UID/ROOT_OWNER,
byte comparison/hash, idle refusal and result/error helpers. The new handler
adds no generic receive name and does not change existing SCRIPTS, package sets,
launch, return or OneOS data ownership. The selected launcher bootstrap is a
separate ColorOS-owned change: verified temporary root-script prefix plus native
DATA, existing safe stage/bin only, no repair/chown/migration or normal-root-script
replacement. The handler sees only the native remainder and EOF.

## Source ownership and publication

Existing stage and bin must be nonlink directories, owned by the selected root
UID and readable/executable with no group/other write or special mode bits. The
handler refuses occupied inherited FD5..9, then retains actual stage/bin on8/9
and compares their kernel device/inode with the checked fixed paths. It rechecks
those identities around work/publication, and uses the existing read-only
mount/bridge/loop idle refusal. That check is not evidence that no orphan
controller exists.

An exclusive mkdir creates `.oneos-retained-controller-install` inside the actual
bin. An existing directory is another or uncertain owner and is never removed.
The handler retains its new directory onFD5 before further checks. It creates
the payload with noclobber onFD6, retaining the acquisition before reading.
Only these newly created objects receive chown/chmod. The descriptor and entry
device/inode must agree. `head -c expected+1` bounds bytes written and requires
EOF to finish an exact-size feed. Short/extra input and wrong hash fail; there is
no timer-as-completion or pretend EOF. A stalled external producer can block the
actual read; the app's real root process/feed owner must retain that uncertainty.

The target is always `STAGE/bin/oneos_retained_root_session`. Existing targets
must be nonlink regular root-owned executable images with exact size/hash from
their opened FD7; otherwise replacement is refused. A matching image receives
no chmod/chown, unlink, replacement or execution. A new target is published by
`ln -T /proc/self/fd/5/payload <fixed-target>`, without `-f`: its final source is
the actual regular/nonlink name in the owned0700 directory, rechecked against
held FD6 immediately before linking. The intermediate directory-FD component
follows normally; no final-magic-link `-L` support is required. Never overwrite
an entry or allow directory-target fallback. The published inode must match
retained FD6. The selected platform must support these flags/proc-fd semantics;
unsupported publication fails closed, with no
weaker cp/mv/ln fallback. Source inspection is not platform execution proof.
After external hashing, the named target's regular/nonlink/root profile and
inode are compared again with held FD7. Those checks run once more after private
temporary cleanup while target/parent descriptors remain held; only descriptor
closes and ACK follow. This does not claim an atomic lease against arbitrary
privileged mutation after the last observation.

## Failure and cleanup

Each descriptor slot and temporary object is recorded before subsequent fallible
work. Cleanup is consumed once, closes its own descriptors, and only removes the
private payload/workdir after identity checks. Failure to identify or clean a
created object is explicit uncertainty, not permission to remove a replacement
or somebody else's lock. No retry of an uncertain cleanup is attempted. The
target is never removed on failure after publication: another process could
already have opened it. An interrupted/failed install may therefore leave an
installed image or private work state requiring explicit reconciliation.

The fragment's cleanup/error statuses are source-level shell/tool observations,
not a native FD-drain or fsync guarantee. The app must require actual complete
feed, exact ACK, successful root process completion and absence of refusal,
failure, cancellation or timeout before continuing. It must not invoke the native
factory after an ambiguous installer outcome. No controller is executed by this
handler, and no host authority/guest operation or protected profile is enabled.

The immutable standalone disposition is
`out/full-app-integration-review/HANDLER-SOURCE-PASS.json` for fragment903a and
embedded script4cda. It verifies the exact original-source inverse and the named
leaf checks after hash/cleanup. This is source evidence, not a model run or
Android/Toybox execution result.
