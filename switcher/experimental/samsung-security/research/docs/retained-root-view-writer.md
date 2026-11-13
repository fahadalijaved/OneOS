# Cooperative view/writer exclusion: source patch

`compat/handoff-view/root-view-writer.patch` is a source-reviewed, unapplied
candidate over six exact held inputs. It changes the GVI source/header and both
held base/derived RootScript/rootsh variants. Core sources, ignored candidate
outputs/receipts and the independent native view patch remain unchanged. No
worker executed a shell, lock, compiler, native helper or phone operation.
Independent source proof `out/root-view-writer-review/trust/SOURCE-PASS.json`
(`25008b5b…`) checks the exact patch, six forward/inverse targets, held preimages
and composition with the separate descriptor repairs. It establishes no build,
kernel, provisioning or runtime result.

The fixed profile requires a pre-provisioned root-owned protected
`/dev/oneos-retained-view` directory (0:0/0700) and regular single-link empty
`lease` file (0:0/0600). It does not create/repair them or any stage. Missing or
unsupported objects refuse. File contents, PID strings and ready flags are not
used. The actual opened file must match the fixed pathname; exclusion comes
from exclusive nonblocking kernel flock on that same open description.

## Provider ordering and durable cutoff

GVI retains its original opaque owner before acquiring the actual lease and
before image/data adoption. Under the lock it refuses writer/legacy/view negative
reservations, creates its own `view-blocked` directory, retains its opened
identity and only then adopts stage/image/ID/data inputs. Accordingly
`open_existing` now has a guard-reservation effect; stage inputs remain read-only
and no mount occurs until the original `begin_view` path. The header says so.

Every currentness check validates the retained lock/parent/reservation objects
and the fixed paths. The actual original GVO begin/close methods remain intact.
`view-blocked` persists after a begin without genuine zero-effect drain proof,
terminal 3, HOLD, uncertain close or process death. Terminal 3 still means kernel
release unconfirmed. No process exit, lock drop or CLOSED response clears it.
Persistence here covers process death within the current mounted `/dev`
lifetime; reboot/crash durability or survival of that filesystem is not proved.

Only zero-effect terminal 0 with every original local input and guard close
known may remove the exact reservation it created. This covers no-begin refusal
and a begun refusal whose actual retained original `gvo_close` returned 0. A
private progress record is set only from that real drain result before dropping
the owner pointer; the provider's default terminal value cannot supply it.
The negative remains through the last lease close; other cooperative acquirers
still refuse it.
The final fixed-path identity checks and one rmdir happen without acquiring any
new FD. Failure stays uncertain without retry. No other owner's reservation is
removed, and no reconciliation/reset API is introduced.

## Actual OneOS writer entry

RootScript prepends a guard before either bootstrap template can write. It
verifies the fixed profile, claims its own descriptor 8, explicitly exports it
to the actual flock command, creates a source-owned `writer-blocked` directory
before original effects and retains that creator record through its child and
bootstrap cleanup. The ordinary fast/fallback rootsh invocation becomes a
waited original child with the same arguments and error status, rather than an
exec that discards the creator record. No generic supplied-command factory is
added. Only this actual creator can remove its exact marker after normal child
return and known local cleanup/lease close; failures/death leave it in place.

The selected rootsh receives the same open description as descriptor 3. It
checks the actual object and reacquires exclusive flock on it, then refuses a
view cutoff before any migration/dispatch. It requires the outer creator's
negative and never clears it. Raw/direct old launchers without this source
issuer refuse; inherited FD/name alone is not source or security attestation.
Correct original launcher/rootsh code admission remains an external prerequisite.

The common guard covers migration, nominal old-list migration, image/record
receive/keep/finish, stage rename/purge/restore/remove, self-update and both
installers. It uses an object outside stage, so moving/removing the stage cannot
remove the lease. The installer retains its parent FD8; its child gets public
FD3 and closes only its child copy of FD8. Reserved installer slots 5-9 remain
free. A literal final template expansion adds this lease export without touching
the separately patched FD4 child source line. The image/installer FD patches
still require explicit composition and fresh evidence.

The patch installs `legacy-blocked` before original launch or recover. That
negative is never removed here, even after a normal ACK or wrapper exit. The
background nsenter/setsid/switch lifetime therefore cannot accidentally admit
GVI after a process drops the lock. A genuine completed-return/kernel-release
issuer remains missing; normal return is not fabricated or relabeled complete.

## Evidence and remaining limits

Root's read-only phone capture of `/system/bin/flock --help` identifies Toybox
0.8.13-android and its fd-only `-sxun` interface. It proves primitive availability,
not successful locking. Root's separate harmless descriptor probe confirms
explicit command-edge export is required; all new lock/path calls account for
that. This author made only data-only source derivations and inverse checks.
Exact preimages/afterimages/edits are in `out/root-view-writer/SOURCE-PATCH.json`;
whole original Kotlin/shell copies stay under ignored `firmware/root-view-writer`.

No target source is applied, compiled or executed by this work. Provisioning,
original source/namespace cohort admission, standalone bypass writers, real
kernel lock behavior, legacy return reconciliation and kernel release beyond
terminal 3 remain unresolved. Advisory cooperation does not isolate an image
from arbitrary root. This is not a beta feature, guest launch, image authenticity
or shared-security readiness; all reciprocal security/data/return requirements
and device acceptance remain intact.
