# Samsung's IMS stack in the guest (VoLTE, VoWiFi, SMS over IMS)

Status (2026-10-29): staged and bound by the scripts behind `ONEOS_GUEST_SEC_IMS=1`.
The guest-side package-manager change it needs (below) is written
(`switcher/patches/guest_sec_ims_signature.py`), checked offline (apktool
reassembles, `scripts/check-dex.py` passes, dexdump shows the carve-out), and
built into the **infinityx** set (`out/overlays_infinityx/services_patched.jar`,
with `packages/infinityx.{sha256,guards.txt}` regenerated). The other sets still
need their overlays rebuilt from each set's `system.img`; not yet booted on a phone.

## Why every guest runs calls on 3G

On a Samsung phone VoLTE is not in the modem or on the vendor side. It is the
system app `com.sec.imsservice` (`/system/priv-app/imsservice`, 10 MB; the SIP
stack is its `libsec-ims.so`, mapped in that process only). It reaches the modem
through the vendor HAL channel `vendor.samsung.hardware.radio.channel.ISehRadioChannel/imsd`
and the host daemon `/system/bin/imsd` (68 KB, a socket helper for routing, not
the registration) over `/dev/socket/imsd`. Both survive the switch and the guest
sees the host's `/dev`; the app dies with One UI's framework. So the guest's
telephony finds no `ImsService`, calls fall back to 3G, and a VoLTE-only carrier
(T-Mobile US, AT&T) gets no calls at all. Keeping `imsd` alive (the IMS gate in
`oneos_switch.sh`) only keeps SMS prompt.

The app is a plain `android.telephony.ims.ImsService` (manifest action,
`BIND_IMS_SERVICE`), so a guest's phone process can bind it like its own.
Inventory of the Fold (F8U, One UI 8.5), read-only, 2026-10-26:

| Part | Where on the host |
| --- | --- |
| `com.sec.imsservice` 6.0.260923.0, `sharedUserId=android.uid.system` | `/system/priv-app/imsservice/imsservice.apk` |
| `uses-library` imsmanager, rcsopenapi, org.apache.http.legacy; optional secimshttpclient, vsimmanager, EpdgManager, telephony-common, ims-common | `/system/framework/{imsmanager,rcsopenapi,vsimmanager,EpdgManager}.jar`; One UI defines no `secimshttpclient` |
| native | `/system/lib64/libsec-ims.so` (needs the AOSP libs plus `libaresdns.so`), `libresampler_ims.so` |
| privileged permissions | `/system/etc/permissions/privapp-permissions-com.sec.imsservice.phone.xml` |
| VoWiFi | `com.sec.epdg` (`/system/priv-app/EpdgService`), `epdgService` (not staged yet) |
| daemon | `/system/bin/imsd` (`imsd.rc`: class main, user system, socket imsd 0660 system) |
| modem | `ISehRadioChannel/imsd`, `/imsd2` (vendor, shared); no Qualcomm IMS HAL instance is registered although the manifest declares them |

Class dependencies (dex type tables, `imsservice.apk` + `imsmanager.jar` +
`rcsopenapi.jar` against the ColorOS X9U guest's `framework.jar`,
`ims-common.jar`, `telephony-common.jar`): 8,328 referenced, 119 not in those
three jars; most of those are APEX classes the guest has at run time
(`android.net`, `android.location`, `com.android.i18n`). The Samsung gap is 33
classes (`com.samsung.android.feature.Sem{Csc,Carrier,Floating}Feature`,
`com.samsung.android.ims.*` AIDL, `com.android.internal.telephony.ISemTelephony`,
`android.sec.enterprise.*`, `SemWifiManager`, `SemSystemProperties`, the
`ISehRadioChannel` stubs), whose transitive closure inside One UI's
`framework.jar` is 307 classes (98 of them Samsung Wi-Fi, 48 `com.samsung.android.ims`,
28 telephony sysprops). Two more sets come from the optional libraries
(`com.sec.vsim.*`, `com.sec.epdg.*`); `gov.nist.javax.sip.*` and
`com.stanfy.gsonxml` are referenced but absent on One UI too.

## What the scripts do with `ONEOS_GUEST_SEC_IMS=1`

`guest_prepare.sh` (section "Samsung's IMS stack in the guest"), at every prepare,
from this phone's One UI, never from the package: copies the APK (as
`priv-app/OneOSSecIms`), the jars, the three native libraries and the
privapp-permissions list into `$STAGE/secims`, writes library XMLs that name the
guest's copies under `/system_ext/framework`, and copies One UI's `framework.jar`
as `oneos-secims-compat.jar`, defined as the library `secimshttpclient` the
manifest already declares as optional. The directory is the top lower layer of
the guest's system_ext overlay (both its forms), so the guest sees a system_ext
priv-app with its permissions list, and the app's class loader resolves the
Samsung classes from the compat jar while every duplicate name stays the guest's
boot class. Refused, with the reason in the prepare log, when One UI lacks one
of the files, defines `secimshttpclient` itself, the guest has no system_ext or
an earlier prepare's overlay is still mounted. `data/oneos_sec_ims` marks a
staged set for the activator.

The UI activator, after boot: `cmd phone cc set-value -s <slot> -p
config_ims_mmtel_package_override_string com.sec.imsservice` for both slots,
then logs the package's path, the override and the ImsResolver lines of
`dumpsys phone`.

## The guest package-manager carve-out (written)

`com.sec.imsservice` asks for `android.uid.system` with Samsung's signature, which
is not the guest image's platform signature, so the scan logs "has no signatures
that match those in shared user android.uid.system; ignoring" and the package
never exists in the guest. `switcher/patches/guest_sec_ims_signature.py` adds one
carve-out to `PackageManagerServiceUtils.verifySignatures` (services.jar): at the
`PackageManagerException` throw site it returns normally (compatMatch = false)
instead of throwing **only** when the package is `com.sec.imsservice` **and** its
code path (`PackageSetting.getPathString()`) is the staged
`/system_ext/priv-app/OneOSSecIms`. The path gate is the point, not the name: a
user-installed app named `com.sec.imsservice` lands under `/data/app` and never
matches that read-only `system_ext` path, so it cannot gain system rights this
way. `scripts/make-overlays.sh` applies it with the other services.jar patches
and records `secims` in `guards.txt`.

Built so far: **infinityx** (from `out/OneOS_InfinityX_FindX9Ultra.img.gz`),
with only `services_patched.jar` (and `guards.txt`) changed in the set — the other
overlay files were kept, so `packages/infinityx.{sha256,guards.txt}` differ from
before only in those two lines. Still to do for the other sets: rebuild their
overlays and **regenerate the package lists** (`app-android/packages/<set>.sha256`
and `<set>.guards.txt`) — each needs that set's `system.img`, as the weaver guard
did (app-android/README.md, "The four set lists in `packages/` were regenerated").

## What is still missing

- The session key in the app's root script (`env_value`), so the app can set it;
  the owner's adb loop can export it today.
- Unknown until a run: the app against guest services it expects from One UI
  (`ISemTelephony` in the phone process, Samsung Wi-Fi, Knox, HQM), whether
  `imsd` accepts a client from the guest's namespace, CSC data it reads from
  host partitions (`/optics`, `/prism`), and call audio over IMS through the
  call-audio loop. Success for the first run: ImsResolver binds the Samsung
  service, registration callbacks fire, a call shows as IMS in the guest's logs.
- VoWiFi (`com.sec.epdg`) and RCS: later.

## SMS: the IMS fallback works, the radio's answer did not (0.4.58)

What a guest SMS does on a carrier that rejects SMS over IMS (0.4.40 report
190a9dcd, S25U on Partner IL, ColorOS X9U IN): the guest's ImsSmsDispatcher
sends over Samsung's ImsService, the network answers SIP 404 "Called User
Unknown", Samsung's ImsSmsImpl answers `SEND_SMS ... status = 4 (Fallback)`
(the 0.4.40 per-slot canFallback fix), the guest's ImsSmsDispatcher calls
fallbackToPstn (AOSP's SEND_STATUS_ERROR_FALLBACK is 4, the same value), and
GsmSMSDispatcher resends the PDU over CS (`RILJ: > SEND_SMS`). The modem sends
it (`RILD: SMS message send SUCCESS`), but Samsung's radio HAL gives no result
payload (`RILC: Invalid response: NULL`) and so answers RadioError 66
INVALID_RESPONSE: the guest marks the text failed (125) although the recipient
got it. Every guest SEND_SMS in the reports to 11-05 ends like this on success,
on Snapdragon and Exynos, with or without Samsung IMS. A failed send keeps its
own error (49, 39, 10). `patches/guest_sms_invalid_response.py`
(telephony-common.jar, MessagingResponse.responseSms) counts 66 as sent and
logs `OneOS-SMS: SEND_SMS error 66 ... counted as sent`.

## SMS: inbound, the vendor queue waited for One UI's handshake (0.4.61)

An inbound SMS in the guest reached the modem but not the app: the radio log
showed `RILD: Received New GW SMS Message` and then no
`RILJ [UNSL]< UNSOL_RESPONSE_NEW_SMS`, no `SmsBroadcastReceiver`, and no row in
the telephony provider. The guest's own `SET_UNSOLICITED_RESPONSE_FILTER 127`
completed without error; it does not touch this path.

Samsung's `libsec-ril.so` has two unsolicited-response paths.
`SecRilProxy::OnUnsolicitedResponse` translates AOSP's new-SMS ID 1003 to
Samsung's extended ID 2201003 (2,201,003), then checks the enable flag at
`[SecRil+0x101]`. With the flag clear it puts the response on a pending list;
with the flag set it sends it to the RIL environment immediately. The flag is
set by `SecRil::SetEnableUnsolResponse(true)`, whose only caller is
`EnableUnsolResponseHandler::DoEvent`. That handler is reached through the
`FW_READY=1` vendor configuration: One UI's `VendorConfigurationTracker` sends
it over Samsung's HIDL radio interface
(`ISehRadioNetwork.setVendorSpecificConfiguration`), and
`VendorConfigManager::DoSetVendorConfiguration` calls
`EnableUnsolResponse()` for the `FW_READY` entry. An AOSP guest's RILJ has no
Samsung HIDL client and never sends that configuration. The legacy RIL request
10093 is not a substitute: its payload is a `hidl_vec<SehVendorConfiguration>`
(count plus native string pointers), not a socket parcel.

The session therefore bypasses the queue at the branch itself.
`switcher/assets/libsec-ril-patch.sh` finds this ten-byte sequence in
`/vendor/lib64/libsec-ril.so`—

```
a8 06 40 f9   ldr  x8, [x21, #8]
08 05 44 39   ldrb w8, [x8, #0x101]
a8 01 00 34   cbz  w8, <queue>
```

—and replaces the `cbz` with `1f 20 03 d5` (NOP), which forces the direct
path for every unsolicited response with ID >= 1,000,000, including 2201003.
It copies the library to `$STAGE/session/libsec-ril.session.so`, bind-mounts
the copy over `/vendor/lib64/libsec-ril.so`, and restarts `ril-daemon` and
`multiclient-daemon` so rild loads it. `return_to_oneui.sh` calls the same
script's `restore` after the guest is dead and before its stage-mount check
(which would otherwise find the bind's `/local/tmp/oneos/` source and
reboot). The scan requires exactly one match; an unknown library is left
alone, and inbound SMS then stays as it was.

Tested on the 0.4.59 S25U (host One UI 9) with `libsec-ril.so` sha256
`318e15d8f884c717463e46eb0b2a4b4dd4969799b69a50cebd7c69fd39e76dfc`: the
sequence is at offset 4,123,036 (0x3ee99c), and the patched copy's sha256 is
`ed57995023e8906693600374e66c6e88422940be8e2cdc36c8002dd18cd399a3`. This is
a host runtime patch, not a guest image patch: the host rild serves every
guest, so the session applies it for every image.

## Prior art: jameskdev/android_samsung_imsservice

https://github.com/jameskdev/android_samsung_imsservice (last push 2024-05): Samsung's
`imsservice.apk` from A21s firmware (Exynos, Android 11), patched at the smali level
and re-signed with the ROM's platform key, VoLTE confirmed on LineageOS 18.1. It
proves the app runs under a non-Samsung framework (SELinux permissive) and lists
what it touched: `SemSystemProperties`, `SemHqmManager`, `UserHandle.SEM_CURRENT`,
`Build.VERSION.SEM_INT`, `Debug.semIsProductDev` (all in our compat jar), and
reflection into hidden Samsung-only `ServiceState` / `TelephonyManager` methods
(`ServiceStateWrapper`, `TelephonyManagerWrapper`), which the guest's own classes
lack: the first thing to read in our first run's log; their constants are the
fallback if the wrappers do not fail gracefully. Not transferable: the Android 11
"ims.compat" service namespace, the offline smali patching (we take each phone's
own APK at stage time) and the platform-key signing (their answer to our step 5;
the app wants to stay in `android.uid.system`, so dropping `sharedUserId` is no
shortcut).
