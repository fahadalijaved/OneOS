# Retained capture: actual Vector log channel

**Source route closed; current diagnostic writer unproved.** For the unchanged
reviewed v1 module, the concrete observation channel is Android's **main log
buffer**, priority INFO, tag `OneOSRetainedCapture`. This is derived from the
captured Vector and Samsung bodies, not from the API declaration or a guessed
module-log file. No phone operation, log write, log clearing or module change
was performed by this audit.

## Exact dispatch and message

Captured Vector `vector.dex` SHA `b75c8894…` supplies these actual edges:

| Actual member | Discriminating source edge |
| --- | --- |
| `XposedInterfaceWrapper.log(int,String,String)` | `ensureAttached` PC0; reads `mBase` PC3; invokes its three-argument logger PC5. |
| Module loader `b3.a(t0,boolean,String)` | Allocates `g2` PC168, constructs it PC196 from the module record, and attaches that same instance PC316. |
| `g2.log(int,String,String)` | Calls the four-argument overload PC4 with null Throwable. |
| `g2.log(int,String,String,Throwable)` | Preserves supplied nonnull tag; appends the module-record prefix plus `: ` when nonempty, then the supplied code. Reads quiet flag PC61; Android `Log.println` is PC69. |

The unchanged module source `bea37efa…` supplies INFO4, its fixed tag and only
`HOOK_INSTALLED`, `INSTALL_REFUSED`, `CAPTURE_BOUND`, `CAPTURE_REFUSED`. The three-
argument path cannot append a Throwable stack: its fourth argument is null.
The rendered message can include the loaded module record's prefix; readers
must not assume the message consists of the code alone. The prefix/log line is
an observation, not caller/source authentication. Logger return status is
discarded, and the module contains logger errors.

Samsung framework `8095a9ae…`, `classes4.dex`, actual
`Log.println(int,String,String)` body hash
`f3faf8a57e86ab06990572652d246b70a9ca5acf7be3d7a68000297bbc9a87d5`
loads buffer ID0 at PC0 and calls `println_native` at PC1. Actual encoded static
fields establish `LOG_ID_MAIN=0` and `INFO=4`; hidden-API metadata is not discarded
or treated as absent.

Captured `libandroid_runtime.so` `f77d49dc…` has the exact RELR-backed JNI triplet
at `0x2e1868`: `println_native`,
`(IILjava/lang/String;Ljava/lang/String;)I`, function `0x1df41c`. That bounded
360-byte function preserves buffer/priority/tag/message and calls
`__android_log_buf_write` at `0x1df4a4`. The call's PLT instructions, GOT
`0x2f4188` and actual relocation resolve that symbol. No OEM library was loaded
or executed. Live liblog/logd filtering, retention or delivery is not established
by this static edge.

## INFO suppression is real policy

In `g2.log4`, `u1.b=false` branches from PC63 to the sink. If true, only priority
at least6 reaches it; INFO4 returns at PC68 without writing anything. A complete
238-class direct-field scan finds one writer of `u1.b`:
`Main.forkCommon` PC238. During bootstrap it reads
`IFrameworkService` transaction1, synchronous flags0. The daemon's actual
`vc.onTransact` case1 starts PC486, calls `yf.b`, inverts its result PC492 and
returns that boolean. No per-log Binder or module-file write occurs here.

Daemon `c48a8fb2…` proves `yf.b()` reads Boolean `enable_verbose_log`. Missing
or non-Boolean values return true. Its actual source selector is:
`/data/adb/lspd/config/modules_config.db`, table `configs`,
`module_pkg_name='config'`, `user_id=0`, `group='lspd'`.
The query selects key/data and decodes Java-serialized values. These are source
names and default semantics; **no current private database contents were read**.
The process caches the inverse at bootstrap. Service absence/error takes its
source false-quiet fallback, not evidence that a particular process did so.
Changing the daemon setting later is not proof of updating this cached flag.
This audit proposes no setting change or suppression bypass.

## Bounded operational observation

Root's separate read-only preflight `2648148b…` records a successful main-buffer
metadata read: ring5MiB, and an empty bounded exact-probe-tag/code observation.
It also found no dedicated probe package. This establishes **reader availability
only**, not this APK's INFO delivery or current quiet-flag value.

The concrete proposal can use that verified main-buffer reader, bounded in time
and output, retaining only the exact tag and four fixed code values (allowing the
source prefix). Root must bind observations to the actual new SystemServer
identity and approved test interval, discard unknown/raw messages, and keep
silence inconclusive. No new command, alternate privilege, log generation,
buffer clearing or phone permission is introduced by this card.

The daemon also names `/data/adb/lspd/log` and `modules_` files, with Java
`LogcatMonitor.refreshFd(false)` preparing a modules file. Its selected
`runLogcat()` is native: this audit does not close that native monitor's tag/
priority/filter/rotation rules. Those files are **not admitted as an equivalent
fallback** for INFO events suppressed before `Log.println`. No whole log archive
or unrelated user/process output is required.

All source proofs, raw method/body hashes and exact input pins are recorded in
[the inventory](../inventory/retained-capture-log-channel.json). This closes the
source-supported channel selection only; it adds no capture, early-callback,
authentication, authority, native-owner or full-goal acceptance.
