# Retained Samsung fingerprint enrollment reports

The [closed enrollment capture](retained-fingerprint-enrollment-query.md)
now retains the five checked row accessors from the canonical Samsung
framework class. Its package-private copy method accepts the rows after the
original query returns. It checks the exact row class, preserves order and
copies the display name and four numeric fields into an immutable report.
The copy preserves the original accessor exception if a getter throws.
This component supplies no query invocation or caller admission.
[Host row copy](../compat/android/com/appleexploit/oneos/security/authority/PreparedRetainedFingerprintEnrollmentQuery.java)

The [report format](../compat/android/com/appleexploit/oneos/security/transport/RetainedFingerprintEnrollmentReport.java)
carries a version, row count and the name, biometric ID, device ID, group ID
and Samsung duplicated-image count in that order. The private format accepts
up to 64 rows and 512 UTF-16 code units per name. A malformed row refuses the
whole report. Empty names and signed numeric values are preserved. The original
Samsung parser can supply `-1` for an unreadable duplicated-image count.
The reader refuses descriptor-bearing data. A future active transport must
also own and validate the Binder object envelope before delivering this report.

A present report of zero rows preserves what the wrapper returned. The original
wrapper can return empty on policy refusal or when its selected provider is
missing. Its cold-state path can rename a legacy file, delete an unreadable
state file or queue a repair. Parsing can also leave a partial list. A returned
report supplies neither completeness nor a repair-drain acknowledgment.

The eventual ColorOS consumer can construct its genuine four-argument
`Fingerprint(name, groupId, biometricId, deviceId)` after admission of the
selected extension and the removal or adaptation of flag-dependent clone
paths. Keep Samsung's duplicated-image count separate. The donor Settings
[name-log leaf](coloros-settings-fingerprint-name-log.md) removes the separate
diagnostic path and is available for later selection. Category clearing and
count persistence require authoritative
list readiness. The Settings evidence is from the donor APK. The held staged
framework establishes the constructor, while the selected Settings APK and
extension still need admission. Genuine caller, user, sensor and provider
admission remains part of the live path. [Caller source seam](retained-fingerprint-caller-ingress.md)

The [SDK 37 and D8 build](../out/retained-fingerprint-enrollment-successor-build/r-70f182bb/receipt.json)
emitted four definitions in a 12,256-byte DEX with SHA-256 prefix `d21c6c22`.
Family and Registry were compiler dependencies and stayed out of the emitted
DEX. The [inert Parcel model](../out/retained-fingerprint-enrollment-report-model/r-cbe17305/receipt.json)
passed 82 cases, including exact signed values and rejection of truncated,
trailing and descriptor-bearing reports. The [row-copy model](../out/retained-fingerprint-row-copy/bd784ca0/saved-readback.json)
passed 23 checks, including one invocation of each getter and exact exception
identity. Its outer wrapper expected 22 checks and returned failure after the
JVM completed successfully. Saved readback records the actual count. No Android
or Samsung code ran.
