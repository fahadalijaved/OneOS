# Independent app prompt-wire review

Status: accepted as a corrected finite source contract, with runtime conversion
and effective feature profiles unadmitted. No converter or runtime code is
implemented or approved by this review. Earlier reviews and the permission bridge
remain frozen.

The selected IAuth authenticate5/cancel6 outer wire and eight SysuiReceiver action
shapes are supported by the pinned source. I checked discriminating authenticate
and resume Proxy edges: authenticate is synchronous and reads the original
exception/long request result; resume is code8 with null reply and one-way1.
This is outer framing only. The action payload has no request ID; the issued
real receiver/session owner must authenticate queued callbacks, and submission
never establishes applied state or drain.

The 31-field PromptInfo order matches in the selected bodies, but a raw foreign
whole object/parcel is not admitted. Samsung continues with four Sem ints and
an explicitly marked challenge array. Null/empty challenge emits only zero;
positive challenge emits length and writeByteArray. The source constructor reads
that extra marker/array while ColorOS ends. Policy fields and nested payloads
need target-side construction with their actual values and provenance.

Fresh ordinary Samsung absence is a real source case: Builder creates actual
PromptInfo and sets the common display from its real Context; the no-argument
PromptInfo constructor writes no Sem fields. Absent explicit Sem mutation on a
fresh object, VM-initialized type0/privilege0/challenge-null is supported. This
does not authorize overwriting reused/privileged requests. Actual outgoing
prompt identity is preserved through conditional cloning/normalization and
semSetExtraInfo before IAuth. That producer uses real app Context display with
its original exception fallback and an Activity-only task branch. Server Context,
assumed task0 or title-only reconstruction is not equivalent. Authenticator,
operation, real caller/package/user/profile, callback and factor policy remain
required; client isSystemCaller is not authorization.

## Concrete correction

IdentityCheckInfo is not an unconditional four-value wire. Both original writers
emit active/reason first, then call Flags.clearFallbackOption at10 with branch14
to21, conditionally skipping boolean3. Flags.doubleAuth at21 with branch25 to32
conditionally skips boolean4. Both readers have corresponding guards24/28->36
and36/40->48. The initial report/table and flattened nestedSchemas omitted this
conditionality. Matching source guards does not prove matching effective flags
in both runtimes, and different profiles can misalign a raw nested parcel before
the following outer PromptInfo fields. The author confirmed and corrected this omission using the unchanged raw inputs.

The corrected report and metadata now qualify matching conditional source shape
and preserve real reader/writer flag-profile admission as open. A future implementation must not patch policy flags,
assume true/false, drop an extra factor or claim a fixed four-value payload.
Any future typed conversion still needs actual flag/policy semantics rather
than exporting a foreign nested parcel.

The other selected nested schemas have the stated bounded shape: FallbackOption
text/icon; MoreOptionsButton description only; vertical list uses the actual
PromptContentItemParcelable classloader/type before description. The latter does
not close concrete item schemas. Original client listeners/executors and ordered
fallback slots are not supplied by the serialized descriptions. Bitmap/native
graphics, CharSequence spans, ComponentName/resource identity, arbitrary/custom
items, app callback wire/lifecycle, Sem Bundle and full statusbar policy/queue
transport remain explicit gates. Same class names establish none of those.

The review reads authored report/tool/metadata plus saved discriminating source
windows. The ignored source-edge receipt pins inspected methods/raw inputs and
records the exact conditional branches. No audit producer, build, OEM/Android
code, parcel roundtrip, crypto operation or phone action ran. The corrected three files and freeze are pinned in the review inventory. The
author reports eleven source assertion groups plus two in-memory guard mutations;
I inspected the new guard checks and their scope, without rerunning them.
Current metadata preserves both flag conditions and explicitly refuses effective
cross-runtime layout admission. Comparison with the preserved initial snapshot
confirms the 32 source inputs and all 68 selected method records are unchanged.
The historical fixed-layout implication is superseded. No other concrete source
contradiction remains in this bounded review; all device cases remain pending.
