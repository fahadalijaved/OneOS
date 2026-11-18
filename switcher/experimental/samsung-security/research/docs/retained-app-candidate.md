# OneOS full-edition closed-controller candidate

The local OneOS candidate now contains the actual full-edition service, setup,
fixed installer, native source recipe and opt-in asset packaging. It remains
default-off and admission-closed. It cannot start a guest or perform a credential
operation, and it is not an installed or beta-ready shared-security feature.

The authored delta is [oneos-retained-controller.patch](../compat/app-integration/oneos-retained-controller.patch),
SHA256 `773ac5cc79df8364c175b835b881d9ed8bc639d8ac0a7d8bb1248670e8971f70`.
Its seventeen paths apply to OneOS commit
`93c6da8053e3494b8732bc359b2095319ff93b6a`, the existing research-PR head.
The private candidate branch is `codex/retained-controller-app`. Git's reverse
index check passed; no candidate commit or push was made in that checkout.
[The manifest](../inventory/retained-app-candidate.json) records every staged
blob and working-source hash. Generated binaries and proprietary inputs are
excluded. The public draft PR remains unchanged.

The full edition gets six Java sources and an unexported service. A genuine
host BEGIN invokes the actual setup before the real session factory; retirement
is checked again before that factory can start. API37 admission precedes newer
Parcel calls. The canonical compatibility-tree service and its earlier model
results remain a distinct baseline, not proof of this derived app service.

Setup requires an opt-in controller asset matching the request and build pins.
It uses a separately framed, verified script prefix so an older installed root
script is not silently replaced. The installer requires an already prepared,
safe stage/bin, modifies only its owned temporary objects and fixed new image,
and refuses different existing controller bytes. It does not invoke prepare or
launch, repair ownership, migrate data or run the image. An installation ACK
proves a file outcome; native custody and drain remain separate.

The candidate's standalone native producer reproduced the admitted controller:
596,312 bytes, SHA256
`1cacc47717468c6e91b791126ce011af25dab9bdbde50765ec0a013cea2b116b`.
Actual receipt `38114a23...` and independent saved-output review `f6723185...`
cover that single compile. The produced controller was never executed. The
supported recipe uses the pinned existing Windows NDK profile; other build
hosts are not established. See [the native build report](retained-native-source-build.md).

Actual candidate source linkage also passed: 38 Kotlin files, six Java files and
the rendered selected configuration produced 206 classes and one Kotlin module
resource. Receipt `811cf190...` and independent readback `202cad4f...` cover the
three successful compiler commands and their retained source/output maps.
This used existing Kotlin2.1/SDK37 tools with a Java8 target, not the project's
matching Kotlin2.4/Gradle9.8/Java21 build. It is not an assembled APK, merged
manifest, executed asset task or Android loader test. See
[the focused build report](retained-controller-app-build.md).

Installer functions and setup source models are a separate validation stream.
The first attempt failed because its harness reused a snapshot variable for the
selected function. It remains a failed harness run; no production outcome is
inferred from it. The corrected functions-only test uses an inert asset and an
explicit RootShell process/path adapter. It never executes the full root script,
real su or the native controller. Its result is recorded separately after the
workflow finishes. Nineteen shell cases earned their required outcomes in the
second run; the next adversarial case did not perform its replacement. A focused
diagnostic recorded Windows `PermissionError` (errno13/winerror5) from the Python
rename adapter while the target descriptor was held. The original leaf remained
intact. This is a test-platform/action gap, not proof of installer mutation or a
passing replacement-race case. A real MSYS rename adaptation is being evaluated;
the thirteen setup cases have not yet run.

The matching full Gradle toolchain is not available in the existing cache. No
software was installed or project tool versions downgraded. Full APK validation,
real native-control transfer, retained host/native/data/display/property lifetime,
guest entry and genuine ColorOS security consumers remain open. Reciprocal PIN,
fingerprint, app-key, encrypted-data and return/reboot behavior still require all
eighteen device cases. Phone and ADB access remain prohibited by the current
offline-only decision.
