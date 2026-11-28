# Samsung physical-user writers at retained PIN admission

The initial user0 admission needs to account for an owned switch continuation
even when the visible target and queue look idle. In the captured Samsung
`UserController.endUserSwitch()`, the next target is polled at PC11. The method
clears pending logout and the target at PCs51 and53 under the original
`mLock`, exits that monitor at PC58, and calls `switchUser` with the dequeued
target at PC61. The still-live local continuation is absent from the fields
the existing Binding samples.

The writer cut uses the actual Samsung services archive `def967fb…` and its
full DEX041 containers. UserController and AMS evidence is in `classes.dex`
logical header0. UMS bodies include header10057984 in the same physical DEX.
PCs are decimal DEX code units. The inventory pins the method bodies, all
direct stores to the watched fields, and the selected instruction checks.
All 89 methods that directly reference the four watched containers have an
exact body proof. Direct-reference closure is scoped to this archive.

| Original owner path | Observed write or admission boundary |
| --- | --- |
| `AMS.switchUser(I)Z` | Delegates to `UserController.switchUser` at PC31 after the Samsung multiuser policy branch. The controller enters `mLock` at57, offers an additional target to the pending queue at273 or writes `mTargetUserId` at278, then exits at285 before posting UI message1000 or controller message120. A Boolean return does not acknowledge start or switch completion. |
| `AMS.startUserInForegroundWithListener` | Supplies foreground mode1 at17 and calls `startUserNoChecks` at20. That method reaches `startUserInternal` at190 without calling `AMS.switchUser`. The selected direct references also show an AMS synthetic callback calling `UserController.switchUser` at25, and controller-side start paths. |
| `UserController.startUserInternal` | Adds a new `mStartedUsers` entry at445 inside `mLock` at413–480. The actual current-user publication is PC530 inside the separate `mLock` region529–535. The complete direct store scan finds that single post-construction write to `mCurrentUserId`. |
| `AMS.logoutUser` | Refuses ID0 at24–43. For other users it can remove a queued target at60 and set the pending logout bit at84 under `mLock`. It can then call switch at119 and stop at147 outside that region. |
| Switch completion | `dispatchUserSwitchComplete` at141 and the actual controller synthetic worker at31 can call `endUserSwitch`. Its local queued-target and pending-stop handoffs follow the idle-looking field writes. `dispatchUserSwitch` sets `UserState.switching` at49 without an explicit monitor. `continueUserSwitch` clears it at65 before its first `mLock` entry at69. |
| `AMS.getCurrentUserId` | With an active target it returns that target at21 under `mLock`. PC24 is the current field fallback. This public query cannot stand in for the original physical current field. |

An ordinary user0 stop or removal refusal is a useful source precondition.
`UserController.stopUser` acquires the original `mLock` at87 and calls
`stopUsersLU` at88. The callee returns -3 for ID0 at6–9. Its -2 check at21–24
uses the active target if present, otherwise the current field. Actual entry includes the AMS stop variants,
`restartUserInBackground`, and `stopProfile` under `mLock` at55/61. The
controller also reaches the same stop method from switch continuation, scheduled
background stop and excess-user work. For an eligible stop it can set
`UserState` to4 at379 and queue continuations. The synthetic worker's
`finishUserStopped` call at74 is distinct from stop acceptance. That completion
checks the same started record and state5, removes it at81 under the real
`mLock`, and later removes the UMI state at194. The source has separate
state writers and CE lock work in the synthetic workers. The watched-map
transition alone supplies neither completion nor storage acknowledgement.

On the registry side `getUserRemovabilityLockedLU` returns -4 for ID0 at0–3.
The ordinary `removeUser`, `removeUserWhenPossible` and
`removeUserEvenWhenDisallowed` paths reach
`removeUserWithProfilesUnchecked`, which checks that predicate before removal.
`removeUserWhenPossible` can try deferred removal through
`setUserEphemeralUnchecked` at122. That method applies the same predicate at6.
`removeUserUnchecked` holds the packages/users locks at13/16, marks the
removing set at157, exits the users lock at160, and can mark the same
`UserInfo.partial` at163 while still in the packages lock. It calls the actual
AMS Binder stop with a retained callback at397. The callback can reach
`removeUserState` at59. Direct cleanup callers are indexed separately from
the normal admission guards. `removeUserInfo`, for example, removes its
supplied key at8 under the users lock and has zero direct callers in this
archive. It is not an additional user0 removal admission proof.

Ordinary user0 stop and removal refusal leave other invalidation paths.
Foreground switching can change the current field. The original LocalService
`setAttributes` and `clearAttributes` reach the same matching UserInfo at54 and56
under `mUsersLock`. `putUserInfo` can replace the actual UserData at19.
The inventory also records direct profile, flag, serial, partial and
pre-created stores, plus container accessors. Eligibility must follow the
actual retained UserData and UserInfo identity and their admitted metadata.

The existing source has two opposed monitor orders. A normal
`UserController.stopUser` can hold `mLock` through `stopUsersLU.getUserInfo`
at327. The controller's actual Injector gets the concrete UMS, whose
`getUserInfo` enters `mUsersLock` at23. In the other direction,
`UMS.removeUserState` holds `mUsersLock` from234 through the actual
`ActivityManagerInternal.onUserRemoved` at247. The same retained
`AMS.LocalService` enters the controller's `mLock` at6 and removes a
started-user entry at63. This is a source lock-order constraint on any new
admission design. It does not assert a runtime deadlock.

## Initial takeover and return precondition

Keep the same genuine SystemServer occurrence, Registry, Family, UserController
and UMS. Initial admission needs actual physical current ID0 and the same full
system-user0 UserData/UserInfo, serial, started UserState and UserHandle. The
existing Binding's main checks are the capture baseline. A worker must also
compete with the real writer owner for an occurrence before it can enter the
Samsung call. That owner has to account for pending targets, a target already
dequeued on a producer stack, direct foreground starts, stop and removal
continuations, and writes to the admitted record or its eligibility. A quiet
snapshot can be useful evidence within that occurrence. It cannot create the
occurrence.

The source cutoff must precede the first incompatible write or queued handoff.
When a worker is already admitted, a transition needs genuine completion or an
owned deferral before it can invalidate the admitted subject. Waiting while
holding either original monitor would introduce a new ordering dependency.
The design also needs an explicit rule for source reentry during an original
credential callback. Existing original permissions, asynchronous work and
return values need to survive any selected integration. Neither an interceptor
on `AMS.switchUser` alone nor a blanket hold of borrowed monitors supplies
this boundary.

For return, retire new guest admission first and retain admitted worker and
outer delivery ownership through completion or uncertainty. Then reconcile any
source transition and recheck the real retained host graph for the selected
return. Original policy, UMS, LockSettings and native owners remain
authoritative while presentation changes. This audit supplies the actual
writer cuts for admission design. Runtime writer interlocking, reconciliation
and the remaining security lifecycle are separate work.

The prior [worker discriminator](retained-pin-mutation-owner.md) exercised the
admission gap against authored JVM fixtures. This follow-up used static reader
commands only. Other archives, reflection, arbitrary alias escape, real
scheduling and native effects are outside its direct DEX evidence.
