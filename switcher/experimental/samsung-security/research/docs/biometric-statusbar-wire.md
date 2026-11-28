# Selected ColorOS biometric statusbar transport

**Observed source contract; no runtime adapter or selected integration.** The
captured guest provides a complete typed route for the five selected operations:
`IStatusBarService` → `StatusBarManagerService` → `IStatusBar` → `CommandQueue.H`
→ original callbacks, including `AuthController`. Its unchanged wire carries
insufficient session identity for safe forwarding of delayed Samsung
authenticated/help/error events. An owner-bound request/epoch transport and a
delivery-time guard remain required; matching this ABI does not supply them.

The [inventory](../inventory/biometric-statusbar-wire.json) pins 47 methods in 17
bounded queries, ten sender/Stub contracts and 41 source assertions. Decimal PCs
are DEX code-unit positions. `python -B tools/audit_biometric_statusbar_wire.py`
rechecks the original archives and saved receipts; `--collect` reads only named
methods. Original donor bytes, installed OneOS behavior and runtime acceptance
remain distinct. No OEM/Android code or hardware operation was executed.

## Two original Binder hops

Descriptors are exactly `com.android.internal.statusbar.IStatusBarService` and
`com.android.internal.statusbar.IStatusBar`. Their transaction numbers differ:

| Operation | Service transaction | SystemUI transaction | Payload after interface token |
| --- | ---: | ---: | --- |
| `showAuthenticationDialog` | 50 | 47 | Typed guest PromptInfo, receiver Binder, int[] sensor IDs, B1, B2, int user, long operation ID, String package, long request ID |
| `onBiometricAuthenticated` | 51 | 48 | Int modality |
| `onBiometricHelp` | 52 | 49 | Int modality, String message |
| `onBiometricError` | 53 | 50 | Int modality, int error, int vendor code |
| `hideAuthenticationDialog` | 54 | 51 | Long request ID |

All five service proxies use `transact(...,reply,0)` and `readException`.
All five SystemUI proxies use `transact(...,null,1)` and no reply reader.
Show writes its typed object with Parcelable flags 0, then `writeStrongInterface`,
`writeIntArray`, two `writeBoolean` calls, int, long, String and long, in that
order. The auditor follows actual source argument registers, including the two
words of each long; B1/B2 are not interchangeable.

Both original Stubs enforce their interface token for ordinary transaction
codes. Each selected arm reads the corresponding typed sequence, wraps the
receiver with the guest `IBiometricSysuiReceiver.Stub.asInterface`, then calls
`enforceNoDataAvail` before dispatch. The service writes `writeNoException` after
normal return; the SystemUI arms write no reply. These are original sender
flags and reply shapes, not a claim that the Stub independently rejects every
incorrect caller flag.

Use admitted guest types and the prompt-wire audit's schema conversion. Do not
relay a Samsung PromptInfo parcel into this creator, append a guessed vendor
Bundle, cast source classes across loaders or reuse service transaction numbers
on the SystemUI interface. The receiver is a genuine guest canonical Binder
carrier bound to the actual source session, as required by the preceding UI card.
Equal field widths also do not establish Samsung/OPPO modality, error or vendor
enum equivalence. Unknown vendor values require explicit semantic admission;
an unsupported presentation extra cannot erase a genuine terminal failure.

## Caller checks and forwarding

All five `StatusBarManagerService` methods first invoke
`enforceBiometricDialog` at 0 and `enforceValidCallingUser` at 3. The former calls
`Context.enforceCallingOrSelfPermission` for
`android.permission.MANAGE_BIOMETRIC_DIALOG` at 6. It is an actual caller/self
permission check, not a request-token or source-realm authenticity proof.

The user check is conditional on `mVisibleBackgroundUsersEnabled`. With that
feature disabled it returns at 4. When enabled it uses actual
`UserHandle.getCallingUserId` at 5; calling user 0 or `mCurrentUserId` returns.
For other users it calls `isVisibleBackgroundUser`: a visible background full
user is rejected with SecurityException; the false result returns. The helper
queries real `UserManagerInternal.isVisibleBackgroundFullUser` at 8. Do not
describe this as equality between the payload user and caller, or as complete
Samsung profile authorization. Real source caller/user policy remains mandatory.

The selected generated action objects preserve the arguments in fields and
their `execute(IStatusBar)` methods call the corresponding five exact service
lambda bodies. Those bodies forward the same logical arguments to the original
`IStatusBar` method. `runWithStatusBarIfPresent` reads `mBar` at 0 and executes
the action at 4. It returns false if the bar is absent or that execute throws
RemoteException; all five public void methods discard that boolean. Thus a
normal synchronous reply does not prove a live UI endpoint, accepted prompt,
window, animation readiness or authentication. Original endpoint registration,
object/loader identity, native Binder identity and death/lifetime admission are
separate owner obligations; this report does not publish or replace `mBar`.

## Queue and original controller delivery

The actual `CommandQueue` constructs its `H` with `Looper.getMainLooper` at 19
and stores the Handler at 26; `H.<init>` passes that Looper to Handler. Each
selected Binder entry acquires `mLock`, creates original `SomeArgs`, sends a
message and releases the lock. The native Binder caller is not an authenticated
session owner merely because processing later occurs on this Handler.

| Operation | Message | SomeArgs payload | H entry / original callback PC |
| --- | --- | --- | --- |
| Show | `0x270000` | arg1 prompt, arg2 receiver, arg3 sensors, arg4 B1, arg5 B2, argi1 user, arg6 package, argl1 operation, argl2 request | 1594 / 1688 |
| Authenticated | `0x280000` | argi1 modality | 1560 / 1586 |
| Help | `0x290000` | argi1 modality, arg1 message | 1522 / 1552 |
| Error | `0x2a0000` | argi1 modality, argi2 error, argi3 vendor code | 1484 / 1514 |
| Hide | `0x2b0000` | argl1 request | 1450 / 1476 |

H decodes those fields, iterates the current CopyOnWrite callback list and calls
the original `CommandQueue.Callbacks` methods. It recycles each SomeArgs on the
selected normal completion path. Show explicitly marks its Message asynchronous;
the four other selected senders do not. No cross-message ordering or full
consumer drain is established by the sender's return.

Before delivering show, H globally removes pending error/help/authenticated
messages at 1600/1609/1618. That removal is by message code, without a request.
It can remove work belonging to another session if stale show work is admitted.
The three update arms likewise carry no request/user/token and apply no source
epoch guard. Removal of some queued work cannot exclude an event already being
handled or a later event from an old source session.

The inherited UI card proves `AuthController` reboxes B1 but its selected
`showDialog` path merely checks that boxed object is nonnull; B2 is unboxed and
stored as `mRequireConfirmation` at 79. Both booleans are preserved through all
transport hops. This does not establish B1's effective source producer or permit
equating it with raw `PromptInfo.deviceCredentialAllowed`. Source effective
pre-authentication/confirmation policy must determine the supplied values.

`AuthController.start` registers itself on its own CommandQueue at 2. That method
also registers fingerprint/face manager callbacks, a task listener and display
listener, updates sensor locations, and writes Global
`scene_container_enabled=0` at 53. It is not a standalone callback-registration
helper. Require the admitted initialized original controller and genuine manager,
user and display owners; do not invoke startup merely to acquire this route.

## Narrow source patch/API consequence

Retain the original UI controller, policy checks, callback actions and readiness
semantics. The unchanged selected global wire cannot transport the Samsung
session's request/epoch on authenticated/help/error. A check before sending then
recovery of “the current session” on receipt would attach old work to a new
dialog. Numeric UID or request equality alone cannot authenticate that binding.

The next proposal must retain an authenticated source session envelope through
the guest delivery queue, including request/epoch, actual issued callback/token,
user, operation and sensor/display context, then validate it on the actual main
thread before original side effects. For show this includes admission before
H's global message removal; for updates it includes admission before the
request-unscoped controller method. Hide retains its real request check and also
needs owner/epoch admission. A new private typed transport or equivalent proved
bound carrier requires root API/ownership review; no such runtime API or patch
is authored here. No identity clear or permission bypass is proposed.

Reverse readiness, dismissal, retry, delayed fingerprint and credential actions
remain the actual `IBiometricSysuiReceiver` methods. The separately owned
[prompt-wire contract](prompt-wire-contract.md) covers all eight declared action
wires, including pause and the reached
`onResumeAuthentication` credential-fallback action. The original UI card retains
real animated-in readiness, confirmation reasons, genuine HAT/native token
processing and the terminal-versus-resume split. Neither this transport nor a UI
callback provides native authentication, additional-factor completion or a new
CryptoObject. Prompt/nested-schema admission, complete source outbound
notifications, native credential fallback, UDFPS/TSP/HBM and device acceptance
remain explicit open gates.
