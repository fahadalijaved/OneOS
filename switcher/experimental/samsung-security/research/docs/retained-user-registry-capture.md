# Prepared initialized-registry capture

Status: **unselected, capture-only PC component**. This component retains and
checks already existing Samsung local objects. It does not establish authority,
native ownership, a coherent policy/user generation, retirement, or shared
security readiness. No Android/OEM code, device action or live capture ran.

`PreparedRetainedUserRegistryCapture.captureExisting()` and `checkStillBound()`
are main-thread-only. The exact source contract is
[retained-user-registry-binding.md](retained-user-registry-binding.md), revision
`ef1f6ae4de8523d9e27f7b4d3a602d3f1fc211b979d54de9bbb1aac91a86ae03`;
its derived inventory is
`40c27af0b3b8b2b80ca2c4af3e2f237b13393df8ac966e892ae187ca3ab160c1`.
That contract pins six actual publication key/value/register sequences and the
actual parent writes, rather than selecting roots from abstract class names.

The capture compares the current main thread and context loader with the
existing boot-canonical Zygote cached SystemServer loader. It never invokes the
loader factory. Binder/Looper identity and exact service-class defining loaders
are checked. This Samsung profile defines LocalServices in the framework boot
cohort; the source card proves that placement explicitly. Main-thread identity,
loader names and matching class shapes do not authenticate code or a process.

Metadata is prepared once. The capture retains eighteen references: UMI, UMS,
PMS, PMI, UserDataPreparer, Persona, Installer, install/packages locks, Context,
the concrete SMS local implementation, SMS, Vold, AMI, AMS, UserController,
its cached Injector and SSM. Root keys and the original parent/owner links must
agree. Required Injector caches must already exist; an optional UMS PMI cache
may remain null, and a nonnull one must match. SSM phase at least 1000 excludes
known early publication, without asserting boot callback drain.

The SMS key is exactly
`StorageManagerService$StorageManagerInternalImpl.class`, whose captured
superclass is Object. The prior unbuilt abstract StorageManagerInternal-key
source and draft builder are preserved in
`out/retained-user-registry-capture/history/unbuilt-abstract-smi/`. Their earlier
source clearance was superseded before compilation or model execution. The
corrected fixtures preserve this concrete key and reject the old abstract key.

Only five pinned fields receive read-access preparation: Zygote's cached loader,
PMI implementation's parent, and three public fields declared by package-private
UserController.Injector. No generic access bypass or global hidden-API setting
is used. ART access admission remains unproved. Lookup uses initialize=false;
an early rejected attempt can still initialize the LocalServices utility when
its static method is invoked. The admitted placement must already be booted.

`checkStillBound()` rereads cached metadata and compares all retained identities
and placement twice; replacement fails without rebinding. It does not call
constructors, providers, lazy service getters, Binder services, current-user/CE
queries or state writers. It preserves original RuntimeException/Error identity.
Two package-private companion methods call this check before returning the exact
retained SSM or loader. Their consumers require the same package and defining
classloader; they are not public capability issuers.

The one approved build completed with exit 0 at
`out/retained-user-registry-capture/20261106T030902567133Z-b65df5309fc1409d824f36ba63beb3e4/`.
Source `26fcbb3089715aad31a40d17d74cb5ab9ea940d6950e88261f725722b1c0fb0f`
and producer `77b547332361705a0423870b24a8115cfc464905d9e814a5e37c7ee4e5d03281`
remain frozen. The receipt and normal inventory share SHA256
`f352aa64bdd1f3a88e99c7322dd1a1d2d426dbacca06cdb7584323cf58803ad4`.
SDK37 source/target8 compilation and D8 emit exactly the authored outer and
Metadata definitions. DEX039 integrity passes; D8's API37 unsupported/max36
warning is retained, not treated as runtime acceptance.

The unchanged SDK-compiled classes passed 53 authored scenarios / 73 checks on
JDK-only modeled framework/service boundaries. Tests cover real reference
retention, exact concrete keys, each owner drift, missing roots, coherent graph
replacement, metadata drift, main/loader refusal, exception identity and
same-package versus foreign-loader companion access. Models contain no OEM or
SDK runtime inputs. All subprocesses use their owned cwd/temp/home and empty
native directory, remove five inherited JVM/compiler option variables, and have
45-second/2-MiB output limits. No global environment changes occur.

Table independently reviewed source, model design and saved outputs without
rerunning the build/models and reported no remaining concrete defect. That
bounded review does not close source authenticity, initialized live placement,
ART access, all-thread/native lifetime, policy updates, guest app-data routing,
producer fencing or any of the eighteen device acceptance cases. The next
authorized integration is a default-OFF diagnostic package retaining these
exact references; enabling or running it requires separate device admission.
