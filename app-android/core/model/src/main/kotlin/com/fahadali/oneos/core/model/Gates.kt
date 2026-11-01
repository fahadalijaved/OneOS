package com.fahadali.oneos.core.model

/** When the gates run: before staging (Prepare) or right before the launch (Switch). */
enum class GatePhase { PREPARE, SWITCH }

/**
 * One gate result. BLOCK has no override. [ack] non-null: a WARN the user
 * must tick, with exactly this text, before Switch ([GateReport.allows]).
 */
data class Gate(val finding: Finding, val ack: String? = null) {
    val id: String get() = finding.id
    val level: Level get() = finding.level

    /** What the app stores when the user ticks [ack]; a changed text needs a new tick. */
    val tickKey: String? get() = ack?.let { "$id|$it" }
}

data class GateReport(
    val phase: GatePhase,
    /** The matched profile (also a disabled one); null = no profile. */
    val profile: PhoneProfile?,
    /**
     * The image these gates are for, one [profile] accepts: PREPARE the picked
     * .gz (or the image already on this phone), SWITCH the staged one; null =
     * none yet (the image gate then BLOCKs).
     */
    val image: ImageRef?,
    /** The set that goes with [image] on this phone ([ImageChoice]). */
    val set: PackageSet?,
    val gates: List<Gate>,
) {
    val blocked: Boolean get() = gates.any { it.level == Level.BLOCK }

    /** The warnings the user must tick, in gate order. */
    val toTick: List<Gate> get() = gates.filter { it.ack != null }

    /** True only when nothing BLOCKs and every [toTick] gate's [Gate.tickKey] is in [ticked]. */
    fun allows(ticked: Set<String>): Boolean = !blocked && toTick.all { it.tickKey in ticked }

    fun find(id: String): Gate? = gates.firstOrNull { it.id == id }

    /** The findings, for the same list UI as the device report (worst first via [CompatReport.sorted]). */
    val report: CompatReport get() = CompatReport(gates.map { it.finding })
}

/**
 * `$STAGE/.oneos_stage` (PLAN.md contract): which app build staged which image
 * and file set for which profile. JSON, one flat object; from 0.3.3
 * (`oneos.stage/2`) with the set, because a phone may take more than one image:
 * `{"schema": "oneos.stage/2", "versionCode": 11, "profile": "f8u", "image": "pixel11fold-yogi", "set": "pixel-f8u", "created": 1792000000}`.
 * A `oneos.stage/1` marker (0.3.0-0.3.2, no set, [setId] null) is still read,
 * so an older stage stays OneOS's (keep, restore); nothing switches with one.
 */
data class StageMarker(val versionCode: Int, val profileId: String, val imageId: String, val setId: String?, val createdEpoch: Long) {
    fun toJson(): String = Json.write(
        linkedMapOf<String, Any>(
            "schema" to if (setId != null) SCHEMA else SCHEMA_V1,
            "versionCode" to versionCode,
            "profile" to profileId,
            "image" to imageId,
        ).apply {
            if (setId != null) put("set", setId)
            put("created", createdEpoch)
        },
    )

    companion object {
        const val SCHEMA = "oneos.stage/2"
        const val SCHEMA_V1 = "oneos.stage/1"
        const val FILE_NAME = ".oneos_stage"
        private const val MAX_BYTES = 4096
        private val PAIR = Regex("""\s*"([A-Za-z]+)"\s*:\s*(?:"([a-z0-9./-]*)"|(\d{1,18}))\s*""")
        private val ID = Regex("[a-z0-9][a-z0-9-]{0,63}")

        /** Null for anything but a well-formed marker (fail closed: no marker = not OneOS's stage). */
        fun parse(text: String): StageMarker? {
            if (text.length > MAX_BYTES) return null
            val t = text.trim()
            if (!t.startsWith("{") || !t.endsWith("}")) return null
            val strings = mutableMapOf<String, String>()
            val numbers = mutableMapOf<String, Long>()
            for (part in t.substring(1, t.length - 1).split(',')) {
                val m = PAIR.matchEntire(part) ?: return null
                val key = m.groupValues[1]
                if (key in strings || key in numbers) return null
                val s = m.groups[2]?.value
                if (s != null) strings[key] = s else numbers[key] = m.groupValues[3].toLongOrNull() ?: return null
            }
            val v2 = strings["schema"] == SCHEMA
            if (!v2 && strings["schema"] != SCHEMA_V1) return null
            val want = if (v2) setOf("schema", "profile", "image", "set") else setOf("schema", "profile", "image")
            if (strings.keys != want || numbers.keys != setOf("versionCode", "created")) return null
            val profile = strings.getValue("profile").takeIf(ID::matches) ?: return null
            val image = strings.getValue("image").takeIf(ID::matches) ?: return null
            val set = if (v2) strings.getValue("set").takeIf(ID::matches) ?: return null else null
            val code = numbers.getValue("versionCode").takeIf { it in 1..Int.MAX_VALUE.toLong() } ?: return null
            return StageMarker(code.toInt(), profile, image, set, numbers.getValue("created"))
        }
    }
}

/**
 * What root read about `$STAGE`: a read-only status before Prepare (so the
 * gates can show it before `begin`), and the launch preflight before Switch.
 */
data class StageState(
    /** Mount points at or under `$STAGE`, from init's mount namespace. */
    val mounts: List<String>,
    /** bridges.sh paths that are mount points right now. */
    val activeBridges: List<String>,
    /**
     * A session is running (a live guest mount namespace, the return watcher)
     * or OneOS's own stage still has persist_session.active. A foreign stage's
     * file does not count: it is never trusted (DA12) and the stage is moved aside.
     */
    val sessionActive: Boolean,
    /** `$STAGE/.oneos_stage`; null when absent or not well-formed. */
    val marker: StageMarker?,
    /** Root re-checked system.raw against system.raw.id and every files.sha256 entry. */
    val filesVerified: Boolean,
    /**
     * OneOS's own session never returned (a hard reset): nothing is mounted any
     * more, but its persist snapshot still has to be restored (Last session >
     * Restore). Distinguishes "reboot" advice from "restore" advice.
     */
    val unfinishedSession: Boolean = false,
)

/**
 * Everything the gates read. The app fills it right before it shows the
 * Prepare or Switch screen and again right before it starts root (the screen
 * lock must be a fresh `KeyguardManager.isDeviceSecure()`).
 */
data class GateInput(
    val facts: DeviceFacts,
    /** `KeyguardManager.isDeviceSecure()` read just now; null = could not read. */
    val screenLockSet: Boolean?,
    /** [SwitchGates.OLD_SWITCHER_PACKAGE] installed (PackageManager, needs a `<queries>` entry); null = could not check. */
    val oldSwitcherInstalled: Boolean?,
    /** One UI's installd table derived on this phone (HostInstalldTable); null = not derived. */
    val installd: InstalldDerivation?,
    /** Root's read of the stage; null = not read. */
    val stage: StageState?,
    /** Free bytes on /data (StatFs; root's df at launch); null = unknown. */
    val freeBytes: Long? = facts.storage?.freeBytes,
    val carrier: CarrierInfo? = facts.carrier,
    /** PREPARE: the picked .gz. */
    val imageFile: ImageFileCheck? = null,
    /** PREPARE with "Use the image already on this phone": the stage's system.raw (then [imageFile] is not used). */
    val onPhone: StagedRaw? = null,
    /** switcher/patches/host_installd.txt as the app ships it; null = compare with the pinned hash only. */
    val expectedInstalld: String? = null,
    /** PREPARE: bytes root frees before receiving (the old system.raw of an adopted stage). */
    val reclaimBytes: Long = 0,
    /** This app's versionCode; when set, a stage marked by another build must be prepared again. */
    val appVersionCode: Int? = null,
    /** The last session's logs are not collected yet (WARN only). */
    val uncollectedLogs: Boolean = false,
    /**
     * The series this APK was built for (BuildConfig.SERIES); null = the
     * all-in-one build with every set. A phone of another series gets
     * [SwitchGates.R_IMAGE_OTHER_SERIES].
     */
    val series: ApkSeries? = null,
    /**
     * 0.4.32: Advanced's "Switch with a screen lock set" is on, so a set lock warns
     * instead of blocking. Last, with a default, so the positional constructors in
     * the tests keep working. An unreadable lock state blocks whatever this says.
     */
    val allowScreenLock: Boolean = false,
)

/**
 * The build 2 gates as rules (AA14, PLAN.md "B1"). Fail closed: a gate that
 * cannot be evaluated is BLOCK. The root script checks the same things again
 * at launch (root, profile ids, SDK, image identity, files, installd, mounts,
 * screen lock); these are what the app shows and refuses first.
 *
 * Gate ids: [ID_ROOT], [ID_PROFILE], [ID_ANDROID], [ID_FORM], [ID_IMAGE],
 * [ID_INSTALLD], [ID_OLD_SWITCHER], [ID_STAGE], [ID_SPACE], [ID_SCREEN_LOCK],
 * [ID_BATTERY] (Switch only), [ID_CARRIER], the CPU finding's own id
 * ([CpuRules]), the profile's notes, and [ID_LOGS] (Switch only, when set).
 * Must-tick at Switch: an untested (profile, image) pair and a VoLTE-only (or
 * unknown) carrier.
 *
 * A profile may take more than one image ([PhoneProfile.choices]); the gates
 * are for one of them ([chosen]): PREPARE the picked .gz or the image already
 * on this phone, SWITCH the staged one. Its set, CPU rule, free space and
 * whether it was tested on this phone come with it.
 */
object SwitchGates {
    const val ID_ROOT = "gate-root"
    const val ID_PROFILE = "gate-profile"
    const val ID_ANDROID = "gate-android"
    const val ID_FORM = "gate-form"
    const val ID_IMAGE = ImageIdentifier.ID
    const val ID_INSTALLD = "gate-installd"
    const val ID_OLD_SWITCHER = "gate-old-switcher"
    const val ID_STAGE = "gate-stage-idle"
    const val ID_SPACE = "gate-free-space"
    const val ID_SCREEN_LOCK = ScreenLockRule.ID_GATE
    const val ID_BATTERY = "gate-battery"
    const val ID_CARRIER = CarrierRules.ID
    const val ID_LOGS = "gate-logs"

    /** The OneLineage switcher: it copies its own scripts into the stage every time it opens. */
    const val OLD_SWITCHER_PACKAGE = "com.wewaffles.onelineage"

    // [Finding.reason]s, per gate (Plain picks the message by id and reason).
    const val R_ROOT_UNCHECKED = "unchecked"
    const val R_ROOT_DENIED = "denied"
    const val R_ROOT_NO_SU = "no-su"
    const val R_ROOT_TIMEOUT = "timeout"
    const val R_ROOT_ERROR = "error"
    const val R_PROFILE_NONE = "none"
    const val R_PROFILE_DISABLED = "disabled"
    const val R_PROFILE_UNTESTED = "untested"
    const val R_ANDROID_DIFFERS = "differs"
    const val R_FORM_MISMATCH = "mismatch"
    const val R_IMAGE_NOT_IN_BUILD = "not-in-build"
    const val R_IMAGE_OTHER_SERIES = "other-series"
    const val R_IMAGE_NONE = "none"
    const val R_IMAGE_NOT_READ = "not-read"
    const val R_IMAGE_NOTHING = "nothing"
    const val R_IMAGE_OTHER_PHONE = "other-phone"
    const val R_IMAGE_OTHER_VERSION = "other-version"
    const val R_IMAGE_OTHER_SET = "other-set"
    const val R_IMAGE_FILES_CHANGED = "files-changed"
    const val R_INSTALLD_DIFFERS = "differs"
    const val R_OLD_SWITCHER_INSTALLED = "installed"
    const val R_OLD_SWITCHER_UNKNOWN = "unknown"
    const val R_STAGE_NOT_READ = "not-read"
    const val R_STAGE_MOUNTED = "mounted"
    const val R_STAGE_BRIDGE = "bridge"
    const val R_STAGE_UNFINISHED = "unfinished"
    const val R_STAGE_RUNNING = "running"
    const val R_SPACE_UNKNOWN = "unknown"
    const val R_SPACE_SETUP = "short-setup"
    const val R_SPACE_SWITCH = "short-switch"
    const val R_BATTERY_NOT_READ = "not-read"
    const val R_BATTERY_LOW = "low"
    const val R_BATTERY_HOT = "hot"
    const val R_LOGS = "not-collected"

    const val BATTERY_MIN_PERCENT = 30
    const val BATTERY_MAX_C = 42f

    /**
     * The tick text for an untested (profile, image) pair, naming the system
     * ([Images.systemName]: with its variant when the phone takes two of that
     * name). The text is part of the tick's key, so another system asks again.
     */
    fun untestedAck(p: PhoneProfile?, image: ImageRef? = null, images: List<ImageRef> = Images.ALL): String =
        if (image == null) {
            "I understand no session has run on this phone yet"
        } else {
            "I understand this phone hasn't run ${Images.systemName(image, p, images)} before"
        }

    /**
     * The image the gates are for, and how the image gate sees it (PREPARE).
     * PREPARE: what [GateInput.onPhone] or [GateInput.imageFile] is, when
     * [profile] accepts it; SWITCH: the marker's image, when [profile] accepts
     * it with the marker's set. Null: none (the image gate BLOCKs).
     */
    fun chosen(phase: GatePhase, input: GateInput, profile: PhoneProfile, images: List<ImageRef> = Images.ALL): Pair<ImageChoice?, ImageIdentity?> {
        if (phase == GatePhase.SWITCH) {
            val m = input.stage?.marker ?: return null to null
            val c = profile.choice(m.imageId)?.takeIf { it.packageSetId == m.setId }
            return c to null
        }
        val identity = when {
            input.onPhone != null -> ImageIdentifier.identifyStaged(input.onPhone, profile, images)
            input.imageFile != null -> ImageIdentifier.identify(input.imageFile, profile, images)
            else -> null
        }
        return identity?.image?.let { profile.choice(it.id) } to identity
    }

    fun evaluate(
        phase: GatePhase,
        input: GateInput,
        profiles: List<PhoneProfile> = Profiles.BUILT_IN,
        images: List<ImageRef> = Images.ALL,
        sets: List<PackageSet> = PackageSets.ALL,
    ): GateReport {
        val f = input.facts
        val switching = phase == GatePhase.SWITCH
        val out = mutableListOf<Gate>()
        val resolution = Profiles.resolve(f, profiles)
        val profile = resolution.profile
        val (choice, identity) = profile?.let { chosen(phase, input, it, images) } ?: (null to null)
        val image = choice?.let { Images.byId(it.imageId, images) }
        val set = choice?.let { PackageSets.byId(it.packageSetId, sets) }

        out += Gate(root(f))
        out += profileGate(f, resolution, profiles, switching, choice, image, images)
        out += Gate(android(f, image, images))
        if (profile != null) {
            out += Gate(form(f, profile))
            out += Gate(
                when {
                    profile.choices.isEmpty() || profile.choices.any { c ->
                        val i = Images.byId(c.imageId, images)
                        val s = PackageSets.byId(c.packageSetId, sets)
                        i == null || s == null || s.imageId != i.id
                    } -> block(ID_IMAGE, "No image for this phone", "Profile ${profile.id} names an image or file set this build does not have.", R_IMAGE_NOT_IN_BUILD)
                    // The phone's own series (0.4.27: the Infinity-X set is in every series, so
                    // carrying one of the phone's sets no longer tells); a profile in no series
                    // is another series' when this APK carries none of its sets.
                    input.series != null && (ApkSeries.of(profile.id)?.let { it != input.series }
                        ?: profile.choices.none { it.packageSetId in input.series.setIds(profiles) }) ->
                        otherSeries(profile, input.series)
                    switching -> stagedImage(input, profile, choice, image, images)
                    identity != null -> identity.finding
                    else -> block(ID_IMAGE, "Pick the image first", "${ImageIdentifier.accepts(profile, images)}.", R_IMAGE_NONE)
                },
            )
        }
        out += Gate(installd(input))
        out += Gate(oldSwitcher(input.oldSwitcherInstalled))
        out += Gate(stageIdle(input.stage))
        space(phase, input, image, set)?.let { out += Gate(it) }
        out += Gate(
            if (switching) {
                ScreenLockRule.switchGate(input.screenLockSet, input.allowScreenLock)
            } else {
                ScreenLockRule.finding(input.screenLockSet).copy(id = ID_SCREEN_LOCK)
            },
        )
        if (switching) out += Gate(battery(f.battery))
        val system = Images.systemName(image, profile, images)
        out += Gate(CarrierRules.finding(input.carrier, system), if (switching) CarrierRules.ackText(input.carrier, system) else null)
        if (image != null) out += Gate(CpuRules.forImage(image, f.cpu))
        if (profile != null) {
            out += profile.notes.map { n ->
                Gate(n, if (switching && n.id == Profiles.ID_NOTE_EXPECT_NO_START) Profiles.expectNoStartAck(system) else null)
            }
        }
        if (switching && input.uncollectedLogs) {
            out += Gate(
                Finding(
                    ID_LOGS, Level.WARN, "Last session's logs not collected",
                    "Switching again moves them aside and the session after that replaces them. Collect them " +
                        "first in Last session if something went wrong.",
                    R_LOGS,
                ),
            )
        }
        return GateReport(phase, profile, image, set, out)
    }

    private fun block(id: String, title: String, detail: String, reason: String) = Finding(id, Level.BLOCK, title, detail, reason)

    /** A series APK on a phone of another series: which download it needs. */
    private fun otherSeries(profile: PhoneProfile, series: ApkSeries): Finding {
        val needed = ApkSeries.of(profile.id)
        return block(
            ID_IMAGE,
            "This OneOS is for the ${series.label}",
            if (needed != null) {
                "Your ${profile.label} needs OneOS for the ${needed.label} (the file ending in -${needed.id}.apk) from the OneOS download folder."
            } else {
                "No OneOS download has the systems for your ${profile.label} yet."
            },
            R_IMAGE_OTHER_SERIES,
        )
    }

    private fun root(f: DeviceFacts): Finding = rootFinding(f.root.probe)

    /** The root gate for one `su -c id` ([probe] null: not run yet); also what Home shows when the check stopped at root. */
    fun rootFinding(probe: SuProbeResult?): Finding =
        if (probe?.state == SuState.GRANTED && probe.uid == 0) {
            Finding(ID_ROOT, Level.OK, "Root works", "su -c id answered uid 0${probe.context?.let { " ($it)" } ?: ""}.")
        } else {
            block(
                ID_ROOT, "Root does not work for OneOS",
                (probe?.let { "su -c id: ${it.state.name.lowercase().replace('_', ' ')}. " } ?: "Root not checked yet. ") +
                    "Allow OneOS in your root manager (KernelSU, Magisk or APatch), then check root again.",
                when (probe?.state) {
                    null -> R_ROOT_UNCHECKED
                    SuState.NOT_FOUND -> R_ROOT_NO_SU
                    SuState.TIMEOUT -> R_ROOT_TIMEOUT
                    SuState.ERROR -> R_ROOT_ERROR
                    SuState.DENIED, SuState.GRANTED -> R_ROOT_DENIED
                },
            )
        }

    private fun profileGate(
        f: DeviceFacts,
        r: ProfileResolution,
        profiles: List<PhoneProfile>,
        switching: Boolean,
        choice: ImageChoice?,
        image: ImageRef?,
        images: List<ImageRef>,
    ): Gate {
        val p = r.profile
        if (p == null) {
            val known = profiles.filter { it.enabled }.joinToString("; ") { "${it.label} (${it.ids})" }
            val near = r.nearest?.let { n -> " Closest is the ${n.label} profile: ${r.mismatches.joinToString(", ")}." }.orEmpty()
            return Gate(
                block(
                    ID_PROFILE, "No OneOS profile for this phone",
                    "${f.model} (codename ${f.device.ifEmpty { "unknown" }}, chip ${f.soc.model.ifEmpty { "unknown" }}). " +
                        "This build switches only on: $known.$near",
                    R_PROFILE_NONE,
                ),
            )
        }
        if (!p.enabled) {
            return Gate(
                block(
                    ID_PROFILE, p.disabledReason ?: "${p.label} is not enabled in this build",
                    "${p.label} (${p.ids}) is known, but this build does not switch on it.",
                    R_PROFILE_DISABLED,
                ),
            )
        }
        // The chosen pair decides; with none yet (the image gate BLOCKs), the phone's record.
        val tested = choice?.tested ?: p.testedWithAnyImage
        if (!tested) {
            val finding = if (image != null && p.testedWithAnyImage) {
                Finding(
                    ID_PROFILE, Level.WARN, "First sessions of the ${image.shortName} image",
                    "${p.label} (${p.ids}): sessions have run on it with " +
                        p.choices.filter { it.tested }.joinToString(" and ") { Images.byId(it.imageId)?.shortName ?: it.imageId } +
                        ", not yet with this image.",
                    R_PROFILE_UNTESTED,
                )
            } else {
                Finding(
                    ID_PROFILE, Level.WARN, "First sessions on the ${p.label}",
                    "${p.label} (${p.ids}): OneOS has a package for it, but no session has run on one yet.",
                    R_PROFILE_UNTESTED,
                )
            }
            return Gate(finding, if (switching) untestedAck(p, image, images) else null)
        }
        return Gate(
            Finding(ID_PROFILE, Level.OK, "Tested phone: ${p.label}", "${p.ids}" + (image?.let { ", with the ${it.shortName} image." } ?: ".")),
        )
    }

    private fun android(f: DeviceFacts, image: ImageRef?, images: List<ImageRef>): Finding {
        val sdks = (image?.let { listOf(it.sdk) } ?: images.map { it.sdk }).distinct().sorted()
        return if (f.sdk in sdks) {
            Finding(ID_ANDROID, Level.OK, "Android ${AndroidRelease.name(f.sdk)}", "SDK ${f.sdk}, the same as the image.")
        } else {
            block(
                ID_ANDROID, "Android version differs from the image",
                "This phone runs Android ${f.androidRelease.ifEmpty { AndroidRelease.name(f.sdk) }} (SDK ${f.sdk}); " +
                    "the image is Android ${sdks.joinToString { AndroidRelease.name(it) }} (SDK ${sdks.joinToString()}). " +
                    "The other system shares One UI's system services, so both must be the same Android version.",
                R_ANDROID_DIFFERS,
            )
        }
    }

    private fun form(f: DeviceFacts, p: PhoneProfile): Finding =
        if (f.form.form == p.form) {
            Finding(ID_FORM, Level.OK, "Form factor: ${p.form.label}", f.form.evidence.joinToString("; "))
        } else {
            block(
                ID_FORM, "Form factor does not match the profile",
                "The hardware says ${f.form.form.label} (${f.form.evidence.joinToString("; ")}); the ${p.label} " +
                    "profile is ${p.form.label}. Its session settings would be wrong for this phone.",
                R_FORM_MISMATCH,
            )
        }

    private fun stagedImage(input: GateInput, p: PhoneProfile, choice: ImageChoice?, image: ImageRef?, images: List<ImageRef>): Finding {
        val stage = input.stage ?: return block(ID_IMAGE, "Stage not checked", "Root could not read the stage. Check root and try again.", R_IMAGE_NOT_READ)
        val m = stage.marker ?: return block(ID_IMAGE, "Nothing prepared yet", "Prepare an image first: ${ImageIdentifier.accepts(p, images)}.", R_IMAGE_NOTHING)
        return when {
            m.profileId != p.id || p.choice(m.imageId) == null -> block(
                ID_IMAGE, "Prepared for another phone or image",
                "The stage holds ${m.imageId} for ${m.profileId}; ${ImageIdentifier.accepts(p, images)}. Prepare again.",
                R_IMAGE_OTHER_PHONE,
            )
            input.appVersionCode != null && m.versionCode != input.appVersionCode -> block(
                ID_IMAGE, "Prepared by another OneOS version",
                "The stage was prepared by app build ${m.versionCode}, this is build ${input.appVersionCode}. Prepare again.",
                R_IMAGE_OTHER_VERSION,
            )
            // The staged image decides the set: another set with it is never switched to.
            choice == null || image == null -> block(
                ID_IMAGE, "Prepared with another file set",
                "The stage holds ${m.imageId} with the files ${m.setId ?: "of an older OneOS"}; on the ${p.label} it needs " +
                    "${p.choice(m.imageId)?.packageSetId}. Prepare again.",
                R_IMAGE_OTHER_SET,
            )
            !stage.filesVerified -> block(
                ID_IMAGE, "Prepared files changed",
                "The image or a staged file no longer matches what was verified when it was prepared. Prepare again.",
                R_IMAGE_FILES_CHANGED,
            )
            else -> Finding(ID_IMAGE, Level.OK, "${image.shortName} image prepared", "Image and files match what was verified.")
        }
    }

    private fun installd(input: GateInput): Finding {
        val p = InstalldExpected.problems(input.installd, input.expectedInstalld)
        return if (p.isEmpty()) {
            Finding(
                ID_INSTALLD, Level.OK, "installd interface matches the OneOS files",
                "${input.installd?.methods?.size} methods, the same table the guard jars carry.",
            )
        } else {
            block(
                ID_INSTALLD, "installd interface differs from the OneOS files",
                p.take(6).joinToString("; ") + ". The guard jars carry One UI's installd codes; a One UI " +
                    "update can change them, and switching waits for a OneOS build made for it.",
                R_INSTALLD_DIFFERS,
            )
        }
    }

    private fun oldSwitcher(installed: Boolean?): Finding = when (installed) {
        false -> Finding(ID_OLD_SWITCHER, Level.OK, "Old switcher not installed")
        true -> block(
            ID_OLD_SWITCHER, "Uninstall the old OneOS switcher",
            "The old switcher app is installed. It copies its own session scripts into the stage every time " +
                "it opens, over the ones this app checked. Uninstall it, then come back.",
            R_OLD_SWITCHER_INSTALLED,
        )
        null -> block(
            ID_OLD_SWITCHER, "Could not check for the old switcher",
            "Could not ask Android whether the old switcher app is installed.", R_OLD_SWITCHER_UNKNOWN,
        )
    }

    private fun stageIdle(s: StageState?): Finding = when {
        s == null -> block(ID_STAGE, "Stage not checked", "Root could not check the stage for mounts and sessions.", R_STAGE_NOT_READ)
        s.mounts.isNotEmpty() -> block(
            ID_STAGE, "Something is still mounted in the stage",
            "${s.mounts.take(5).joinToString(", ")}${if (s.mounts.size > 5) " and ${s.mounts.size - 5} more" else ""}. " +
                "Reboot the phone, then try again.",
            R_STAGE_MOUNTED,
        )
        s.activeBridges.isNotEmpty() -> block(
            ID_STAGE, "A guest bridge is still active",
            "${s.activeBridges.take(5).joinToString(", ")}. Reboot the phone, then try again.",
            R_STAGE_BRIDGE,
        )
        s.unfinishedSession -> block(
            ID_STAGE, "The last session did not end",
            "The last session was interrupted (a force restart), so One UI is still on the guest's settings. " +
                "Open Last session > Restore One UI's settings, then switch again.",
            R_STAGE_UNFINISHED,
        )
        s.sessionActive -> block(
            ID_STAGE, "A session is still running",
            "A guest session is still active (its image or mounts are in place). Reboot the phone, then try again.",
            R_STAGE_RUNNING,
        )
        else -> Finding(ID_STAGE, Level.OK, "Nothing mounted, no session running")
    }

    private fun space(phase: GatePhase, input: GateInput, image: ImageRef?, set: PackageSet?): Finding? {
        val need = when (phase) {
            GatePhase.SWITCH -> SpaceRule.LAUNCH_BYTES
            GatePhase.PREPARE -> image?.let { SpaceRule.toStage(it, set) } ?: return null
        }
        val what = if (phase == GatePhase.SWITCH) {
            "8 GB data + 1 GB logs + 2 GB margin"
        } else {
            "the ${image!!.shortName} image ${Units.bytes(image.rawBytes)} + files + 8 GB data + 1 GB logs + 2 GB margin"
        }
        val free = input.freeBytes ?: return block(
            ID_SPACE, "Free space unknown", "Could not read free space on /data; about ${Units.bytes(need)} is needed.", R_SPACE_UNKNOWN,
        )
        val have = free + input.reclaimBytes.coerceAtLeast(0)
        return if (have < need) {
            block(
                ID_SPACE, "Not enough free space",
                "${Units.bytes(free)} free on /data${if (input.reclaimBytes > 0) " (+ ${Units.bytes(input.reclaimBytes)} freed first)" else ""}; " +
                    "about ${Units.bytes(need)} needed ($what).",
                if (phase == GatePhase.SWITCH) R_SPACE_SWITCH else R_SPACE_SETUP,
            )
        } else {
            Finding(ID_SPACE, Level.OK, "Enough free space", "${Units.bytes(free)} free on /data; about ${Units.bytes(need)} needed.")
        }
    }

    private fun battery(b: BatteryInfo?): Finding {
        val rule = "at least $BATTERY_MIN_PERCENT% or charging, and under ${BATTERY_MAX_C.toInt()} °C"
        return when {
            b == null || b.temperatureC == null -> block(ID_BATTERY, "Battery not read", "A session needs the battery $rule.", R_BATTERY_NOT_READ)
            b.levelPercent < BATTERY_MIN_PERCENT && !b.charging -> block(
                ID_BATTERY, "Charge the battery first",
                "${b.levelPercent}%, not charging. A session needs the battery $rule.",
                R_BATTERY_LOW,
            )
            b.temperatureC >= BATTERY_MAX_C -> block(
                ID_BATTERY, "Battery too warm",
                "${b.temperatureC} °C. A session needs the battery $rule.",
                R_BATTERY_HOT,
            )
            else -> Finding(ID_BATTERY, Level.OK, "Battery ready", "${b.levelPercent}%${if (b.charging) ", charging" else ""}.")
        }
    }
}
