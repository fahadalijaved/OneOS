# App prompt parcel and action contract

**Disposition: finite source contract; no runtime converter or receiver carrier.** Selected IAuth and SysuiReceiver outer wires match between the supplied Samsung and ColorOS frameworks. Whole PromptInfo parcels do **not** share the same layout: Samsung has five additional fields after the common 31-field sequence. Genuine ordinary non-Sem requests are nevertheless source-supported; absent vendor features must be distinguished from missing real caller or policy metadata.

[The inventory](../inventory/prompt-wire-contract.json) pins 68 code bodies, ten selected request/action pairs, four paired nested schemas, exact fields/order/PCs and 32 raw receipts. [The verifier](../tools/audit_prompt_wire_contract.py) passes eleven source assertion groups and two in-memory conditional-guard sensitivity checks. PCs are decimal DEX code units. These are static source checks, not an Android parcel roundtrip, Binder execution, cryptographic acceptance or device evidence. No OEM class, native service or phone operation ran. Frozen policy findings remain unchanged.

## Selected app ingress and action wires

`IAuthService.authenticate(IBinder token, long operationId, int userId, IBiometricServiceReceiver receiver, String package, PromptInfo prompt)` is transaction **5**, two-way, returning the real request ID as a long. `cancelAuthentication(token, package, requestId)` is transaction **6**, two-way. Both supplied proxies and selected Stub cases have the same ordered outer writes/reads; the Stub checks interface/data framing. The request's typed PromptInfo still requires its target-side schema.

| IBiometricSysuiReceiver action | Transaction | Payload after interface token | Flag |
| --- | --- | --- | --- |
| `onDialogDismissed` | 1 | reason int, byte array | one-way |
| `onTryAgainPressed` | 2 | none | one-way |
| `onDeviceCredentialPressed` | 3 | none | one-way |
| `onSystemEvent` | 4 | event int | one-way |
| `onDialogAnimatedIn` | 5 | boolean | one-way |
| `onStartFingerprintNow` | 6 | none | one-way |
| `onPauseAuthentication` | 7 | none | one-way |
| `onResumeAuthentication` | 8 | none | one-way |

All eight selected receiver proxy/Stub request shapes match, including the actually reached credential-fallback `onResumeAuthentication` action. Matching wires do not prove the meaning of every reason/event or the authenticity of byte-array contents. In particular, no arbitrary array becomes a credential result or authentication token because the type matches. One-way submission is not application completion, readiness, removal or drain. Cancellation's two-way return likewise does not acknowledge the whole operation/callback tail.

These actions carry no request ID in their payload. The genuine canonical Binder carrier must therefore retain the issued source session/request and original action target. Preserve the immediate admission and actual UI-ready timing established by [the UI authority card](biometric-ui-authority.md); an unbound global receiver or a stale queued action is not sufficient. The source session receiver's null `asBinder` is not a usable canonical guest Binder endpoint.

## Exact PromptInfo common sequence

Both selected constructors read the following fields in this order, and both writers emit them in the same order and with the listed operation. Inventory records reader/writer PCs, exact method descriptors and original typed creators. This is an untagged sequence, not a versioned field map.

| Order | Field | Declared type | Original write |
| --- | --- | --- | --- |
| 1 | `mLogoRes` | `I` | `writeInt` |
| 2 | `mLogoBitmap` | `Landroid/graphics/Bitmap;` | `writeTypedObject` |
| 3 | `mLogoDescription` | `Ljava/lang/String;` | `writeString` |
| 4 | `mTitle` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 5 | `mUseDefaultTitle` | `Z` | `writeBoolean` |
| 6 | `mSubtitle` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 7 | `mUseDefaultSubtitle` | `Z` | `writeBoolean` |
| 8 | `mDescription` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 9 | `mContentView` | `Landroid/hardware/biometrics/PromptContentViewParcelable;` | `writeParcelable` |
| 10 | `mDeviceCredentialTitle` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 11 | `mDeviceCredentialSubtitle` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 12 | `mDeviceCredentialDescription` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 13 | `mNegativeButtonText` | `Ljava/lang/CharSequence;` | `writeCharSequence` |
| 14 | `mConfirmationRequested` | `Z` | `writeBoolean` |
| 15 | `mDeviceCredentialAllowed` | `Z` | `writeBoolean` |
| 16 | `mAuthenticators` | `I` | `writeInt` |
| 17 | `mDisallowBiometricsIfPolicyExists` | `Z` | `writeBoolean` |
| 18 | `mReceiveSystemEvents` | `Z` | `writeBoolean` |
| 19 | `mAllowedSensorIds` | `Ljava/util/List;` | `writeList` |
| 20 | `mAllowBackgroundAuthentication` | `Z` | `writeBoolean` |
| 21 | `mIgnoreEnrollmentState` | `Z` | `writeBoolean` |
| 22 | `mIsForLegacyFingerprintManager` | `Z` | `writeBoolean` |
| 23 | `mShowEmergencyCallButton` | `Z` | `writeBoolean` |
| 24 | `mUseParentProfileForDeviceCredential` | `Z` | `writeBoolean` |
| 25 | `mRealCallerForConfirmDeviceCredentialActivity` | `Landroid/content/ComponentName;` | `writeParcelable` |
| 26 | `mClassNameIfItIsConfirmDeviceCredentialActivity` | `Ljava/lang/String;` | `writeString` |
| 27 | `mFallbackOptions` | `Ljava/util/List;` | `writeTypedList` |
| 28 | `mIsSystemCaller` | `Z` | `writeBoolean` |
| 29 | `mIdentityCheckInfo` | `Landroid/hardware/biometrics/IdentityCheckInfo;` | `writeParcelable` |
| 30 | `mDisplayId` | `I` | `writeInt` |
| 31 | `mNotifyVdmAuthenticationRequested` | `Z` | `writeBoolean` |

Samsung then writes, in order, `mSemDisplayId:int`, `mSemTaskId:int`, `mSemBiometricType:int`, `mSemPrivilegedFlag:int`, and `mSemChallengeData:byte[]`. The first four use `writeInt`. Challenge data has an explicit length marker: null or empty emits zero only; positive length emits the length followed by the original `writeByteArray`. The matching Samsung reader consumes that marker and conditionally allocates/reads the array. ColorOS ends after the common sequence. Forwarding either entire foreign parcel is not established compatible; the selected outer IAuth request framing does not make an unmatched tail safe.

The fields are also policy-bearing values: authenticators, confirmation, device-credential fallback, parent-profile use, enrollment/background behavior, caller identity and Identity Check must retain genuine source/server semantics. Do not replace them with constructor defaults merely because a converter has not supplied their actual values.

## Genuine ordinary producer versus Sem features

The original Samsung Builder constructs a real `new PromptInfo()` at 11/13 and sets the common display ID from its actual Context (20/24). Its `build` retains that PromptInfo and original client button/fallback owners. PromptInfo's actual no-argument constructor does not write any of the five Sem fields. For a **genuinely fresh** ordinary Builder/request with no Sem mutation, genuine instance initialization therefore supplies Sem biometric type 0, privileged flag 0 and challenge null. This is a source-supported absence profile, not a fabricated authentication result or permission. It cannot be applied to a reused object or explicit Sem request whose state differs.

Samsung `authenticateInternal` applies `semSetExtraInfo` to the exact outgoing prompt at 107 before IAuth at 125. That producer uses actual `Context.getDisplayId` (6), its original exception branch/fallback, and only for Activity Context the real `Activity.getTaskId` (43/47). Non-Activity/fresh-state behavior remains the original behavior. A server Context is not a replacement app Context; a converter cannot claim these values merely by filling zero.

Samsung's explicit Builder Sem type/privilege setters check `com.samsung.android.permission.BIOMETRICS_PRIVILEGED`. The guest Builder has no matching Sem methods or fields. Ordinary guest requests must not acquire those privileges through conversion. Conversely, the missing vendor API alone is no reason to reject an otherwise admitted ordinary generic request.

Both original `authenticateInternal` bodies preserve real operation-ID/CryptoObject checks, original prompt cloning/normalization, token, callback receiver, package/user and returned request ID/cancellation ownership. Preserve those contracts rather than rebuilding a prompt from its title alone. Samsung's real AuthService ingress checks Binder calling user/UID/PID, AppOps and test/internal/advanced permissions; it additionally checks Sem privilege/type before clearing identity and calling BiometricService. Guest ingress has its own actual caller/AppOps/permission checks. A transport hop must preserve genuine authorization; client fields such as `mIsSystemCaller` do not establish the calling identity.

## Nested payload closure and remaining bounds

| Selected nested type | Observed parcel order | Bounded result |
| --- | --- | --- |
| `IdentityCheckInfo` | Active boolean and inactive-reason int are unconditional. Clear-fallback boolean is present only under `Flags.clearFallbackOption`; credential-and-identity-check boolean only under `Flags.doubleAuth`. | Matching **conditional source shape**; effective producer/consumer flag profiles remain unknown and unadmitted. |
| `FallbackOption` | text CharSequence, icon-type int | Paired schema matches; ordered list and original client callback slots still matter. The actual class is `android.hardware.biometrics.FallbackOption`. |
| `PromptContentViewWithMoreOptionsButton` | description String | Original button/listener owners are not serialized by this body; they remain at the original client. |
| `PromptVerticalListContentView` | content list, description String | Reader requires `PromptContentItemParcelable`; concrete item/subclass schemas remain unclosed here. |

IdentityCheckInfo requires a separate effective flag-profile gate. In both writers, `clearFallbackOption` at PC10 controls branch14→21 around the third boolean; `doubleAuth` at21 controls branch25→32 around the fourth. In both readers the corresponding calls/branches are 24/28→36 and 36/40→48. A disabled flag skips that value entirely, rather than writing false. Equal method bodies or linear field lists do not establish that the two runtimes execute the same layout. The selected flag producers and effective values were not executed or otherwise established.

The initial `cbe2a341…9366ff0` freeze is preserved under `out/prompt-wire-contract/history/initial-freeze-cbe2a341/`; its fixed-layout implication for this nested type is superseded by this qualification. Raw source pins and all other request/action evidence remain unchanged.

Bitmap/native graphics parcel contents, CharSequence spans, ComponentName/resource/package identity, concrete list items/custom content classes, the app `IBiometricServiceReceiver` callback wire/executor lifecycle, and Samsung wrapper Bundle construction are separate remaining contracts. A matching class name or typed outer list does not close them. No arbitrary Bundle field is present in PromptInfo itself.

## Typed construction required before implementation

A reviewed converter would construct a **real target-side PromptInfo** carrying all 31 actual common values, with target-owned nested payloads admitted by their real schemas. For an admitted fresh ordinary non-Sem request, it can use the source-supported absent Sem feature profile while supplying genuine caller display/task metadata under the original producer rules. Explicit Sem data and privileged features require their genuine producer/authorization and cannot silently be zeroed, exposed through the guest ordinary API or claimed rendered by guest fields that do not exist. The Samsung authority retains its actual policy/operation/challenge state when ColorOS presents supported common UI.

That describes the object and evidence obligations; no runtime conversion API, defaults table or Binder carrier is implemented or approved. Exact caller/user/profile/resource identity, authenticators/confirmation, current request/session, callback ownership, real hardware/factor results and completion fences remain mandatory.

IStatusBarService/IStatusBar/CommandQueue request wiring belongs to the separately assigned UI followup. This card does not derive its first effective boolean from raw `deviceCredentialAllowed`; source policy can compute a different effective value. Keyguard and enrollment routes are excluded. No whole-prompt compatibility, complete app authentication, firmware selection or device candidate follows.
