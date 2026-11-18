# Direct host-control v2: independent Java source review

The reviewed app and host Java sources pass this bounded source review. The
immutable proof is `out/retained-root-handoff-review/java/SOURCE-PASS.json`,
SHA256 `f5472a16fbf9f710dccb90a673972f2df14d66e4f133d643ac4e6a9be13ab709`.
It retains ten exact source snapshots. No compiler, model, native helper,
Android/OEM implementation, root command or phone operation ran in this review.

The app's actual Binder BEGIN entry captures the kernel-provided host PID/UID.
Its retained one-shot launch owner starts only the fixed verified v2 image and
relays OFFER through the retained callback. It never opens a native control
socket, sends native PING/CLOSE, signals the child or retries uncertain startup.
Local stream close requires wrapper reap, actual started/finished readers,
normal EOF and a full OFFER. Those observations do not prove native exit.

The host derives Context and source association from its existing captured
module, Registry and Family. It checks protected profile, package/signature/APK
identity and callback occurrence. The actual private client is retained before
socket acquisition. It adopts received rights before refusal and validates
root peer, PID, pidfd kind/target and observed liveness. Only the source-owned
main continuation can issue COMMIT sequence 1; COMMITTED is required before
publishing the internal closed-link state. Subsequent control starts at
sequence 2. Lost commit replies retain uncertainty rather than enabling retry.

Review found and corrected an app observer-start/cleanup contour and a host
reconnect policy defect. After an adopted OFFER, genuine app disconnect, death
or reconnect now retains the original broker, one BEGIN and native client.
Transport notices trigger source/package rechecks without making app liveness
the owner of native control. Package/source changes still retire the link.

The v2 protected profile inherits the canonical loader's bounded parsing and
descriptor ownership, with only class, fixed file and version substitutions
after explicit newline normalization. The separate same-FQCN module variant
has an exact inverse through two type-name substitutions. Its selected compile
and class-loader cohort must remain explicit; this does not replace canonical
v1 code at runtime.

This is source acceptance only. The native implementation and irreversible
commit/detachment behavior have a separate review. Blocking socket operations
can remain retained; no hard completion deadline is claimed. SDK/models,
v2 native-image installation, full APK placement and activation remain separate.
The earlier installer acknowledges only a fixed v1 file, not the v2 image or a
running controller. Neither callback, descriptor, PID, profile nor Java state
grants PIN/biometric, guest or general root authority. Native custody and actual
kill/cgroup/property/display/backend lifetime, the full shared-security goal and
all 18 device acceptance cases remain open.
