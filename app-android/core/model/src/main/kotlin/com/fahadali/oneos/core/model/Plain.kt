package com.fahadali.oneos.core.model

/**
 * What a plain message offers to fix the problem (docs: the UX redesign,
 * section 3.2). The app runs it (ui/FixActions.kt); [SWITCH],
 * [CHOOSE_SYSTEM] and [SHOW_PROGRESS] are also Home's everyday buttons.
 */
enum class FixAction {
    /** Nothing to tap: the user does it outside OneOS (restart, charge, wait). */
    NONE,
    TRY_AGAIN,
    OPEN_ROOT_APP,
    SEND_PHONE_DETAILS,
    CHOOSE_SYSTEM,
    OPEN_OLD_SWITCHER_INFO,
    RESTORE,
    DOWNLOAD_AGAIN,
    CHOOSE_FILE,
    SET_UP_AGAIN,
    /** Set up the system of the file the user chose (Home, before anything is set up). */
    SET_UP,
    /** Same system, another app version or file set: set up again keeping its apps and data, with no download when the installed system is reused. */
    UPDATE,
    /** Same system, some of its files changed since setup. */
    REPAIR,
    FREE_UP_SPACE,
    OPEN_LOCK_SETTINGS,
    /** A box to tick in the Switch dialog (asked once per phone and system). */
    ACKNOWLEDGE,
    SEND_REPORT,
    SWITCH,
    SHOW_PROGRESS,
}

/**
 * One problem in plain words: a short [title] (at most 40 characters), one
 * [line] (at most 140), and one [action] with its button text ([actionLabel],
 * null when there is no button). The technical finding stays under Details.
 */
data class PlainMessage(
    val title: String,
    val line: String,
    val action: FixAction,
    val actionLabel: String?,
    val level: Level = Level.BLOCK,
) {
    companion object {
        const val MAX_TITLE = 40
        const val MAX_LINE = 140
    }
}

/** What the plain texts may need besides the finding: the root app, sizes, the battery, the phone's Android. */
data class PlainFacts(
    /** "Magisk", "KernelSU", "APatch"; null = no root app found. */
    val rootApp: String? = null,
    val freeBytes: Long? = null,
    val needBytes: Long? = null,
    val batteryC: Float? = null,
    /** The phone's Android release, e.g. "17". */
    val phoneAndroid: String? = null,
    /** Update and repair can reuse the system already on the phone (no download). */
    val installedReusable: Boolean = true,
)

/**
 * The plain message for every protective check (section 3.2 of the redesign):
 * the same refusals as [SwitchGates], [ScreenLockRule], [CarrierRules],
 * [CpuRules] and [ImageIdentifier], in words a friend understands, with one
 * action each. Only the wording changes; whether something stops the switch
 * is still the finding's [Level]. Fixed texts never name a system: `{system}`
 * is the image table's [ImageRef.name], else "the other system".
 */
object Plain {
    /**
     * "the Galaxy Z Fold (F8U), S26 Ultra and S25", while that fits one line
     * after "OneOS works on "; past that (0.4.29, 15 phones) "15 Galaxy phones
     * so far: Z Fold, Z Flip, S and A models; the README lists them".
     */
    fun phoneList(profiles: List<PhoneProfile> = Profiles.BUILT_IN): String {
        // A regional variant ("Galaxy S26 (docomo)") is listed under its phone's name, and
        // "Galaxy" is said once: "Galaxy Z Fold (F8U), S26 Ultra and S25".
        val all = profiles.filter { it.enabled }.map { it.label.removePrefix("Galaxy ") }
        val names = all.filter { l -> all.none { l.startsWith("$it (") } }
        val list = when (names.size) {
            0 -> "the phones listed in About"
            1 -> "the Galaxy " + names.single()
            else -> "the Galaxy " + names.dropLast(1).joinToString(", ") + " and " + names.last()
        }
        if ("OneOS works on $list.".length <= PlainMessage.MAX_LINE) return list
        val families = names.map { n -> listOf("Z Fold", "Z Flip").firstOrNull { n.startsWith(it) } ?: n.take(1) }.distinct()
        return "${names.size} Galaxy phones so far: ${families.dropLast(1).joinToString(", ")} and ${families.last()} models; the README lists them"
    }

    /** [of] with the facts read from [report] and the phone's [facts]. */
    fun of(finding: Finding, report: GateReport, facts: DeviceFacts?, installedReusable: Boolean = true): PlainMessage {
        val need = when (report.phase) {
            GatePhase.SWITCH -> SpaceRule.LAUNCH_BYTES
            GatePhase.PREPARE -> report.image?.let { SpaceRule.toStage(it, report.set) }
        }
        return of(
            finding, report.image, report.profile,
            PlainFacts(
                rootApp = facts?.rootKind?.takeIf { it != RootKind.NONE && it != RootKind.OTHER }?.label,
                freeBytes = facts?.storage?.freeBytes,
                needBytes = need,
                batteryC = facts?.battery?.temperatureC,
                phoneAndroid = facts?.let { it.androidRelease.ifEmpty { AndroidRelease.name(it.sdk) } },
                installedReusable = installedReusable,
            ),
        )
    }

    fun of(
        f: Finding,
        image: ImageRef?,
        phone: PhoneProfile?,
        facts: PlainFacts = PlainFacts(),
        profiles: List<PhoneProfile> = Profiles.BUILT_IN,
    ): PlainMessage {
        val system = image?.name ?: Images.OTHER_SYSTEM
        val sys = Sentence.start(system)
        val yourPhone = phone?.let { "your ${it.label}" } ?: "your phone"
        val r = f.reason
        fun m(title: String, line: String, action: FixAction, label: String? = defaultLabel(action)) =
            PlainMessage(title, line, action, label, f.level)

        return when (f.id) {
            SwitchGates.ID_ROOT -> when (r) {
                SwitchGates.R_ROOT_TIMEOUT -> m("Root didn't answer", "Allow OneOS in your root app, then try again.", FixAction.TRY_AGAIN)
                SwitchGates.R_ROOT_ERROR -> m("Couldn't check root", "Try again in a moment. If it keeps happening, restart your phone.", FixAction.TRY_AGAIN)
                SwitchGates.R_ROOT_UNCHECKED -> m("Root not checked yet", "Allow OneOS when your root app asks.", FixAction.TRY_AGAIN)
                // KernelSU and APatch hide su from apps they have not allowed: with a root app found, it is a grant.
                SwitchGates.R_ROOT_NO_SU -> if (facts.rootApp == null) {
                    m("OneOS needs a rooted phone", "Install Magisk, KernelSU or APatch, then open OneOS again.", FixAction.TRY_AGAIN)
                } else {
                    allowRoot(f, facts.rootApp)
                }
                else -> allowRoot(f, facts.rootApp)
            }
            SwitchGates.ID_PROFILE -> when (r) {
                SwitchGates.R_PROFILE_DISABLED -> m(
                    "Not available on this phone yet",
                    (phone?.let { "This version of OneOS doesn't switch on the ${it.label}." } ?: "This version of OneOS doesn't switch on it."),
                    FixAction.NONE,
                )
                SwitchGates.R_PROFILE_UNTESTED -> m(
                    "Not tested on this phone yet",
                    SwitchGates.untestedAck(phone, image),
                    FixAction.ACKNOWLEDGE,
                )
                else -> m("This phone isn't supported yet", "OneOS works on ${phoneList(profiles)}.", FixAction.SEND_PHONE_DETAILS)
            }
            SwitchGates.ID_ANDROID -> {
                val want = image?.let { AndroidRelease.name(it.sdk) }
                val have = facts.phoneAndroid
                m(
                    if (want != null) "$sys needs Android $want" else "Your Android version differs",
                    if (have != null) {
                        "Your phone has Android $have. Choose another system, or wait for one made for Android $have."
                    } else {
                        "Choose another system, or wait for one made for your Android version."
                    },
                    FixAction.CHOOSE_SYSTEM,
                )
            }
            SwitchGates.ID_FORM -> m("Your phone doesn't match its profile", "OneOS can't be sure it's safe here.", FixAction.SEND_PHONE_DETAILS)
            SwitchGates.ID_INSTALLD -> m(
                "One UI was updated",
                "This OneOS version doesn't know your new One UI yet. Wait for a OneOS update before switching.",
                FixAction.SEND_PHONE_DETAILS,
            )
            SwitchGates.ID_OLD_SWITCHER -> when (r) {
                SwitchGates.R_OLD_SWITCHER_UNKNOWN -> m("Couldn't check for the old switcher", "Try again in a moment.", FixAction.TRY_AGAIN)
                else -> m(
                    "Remove the old switcher app",
                    "The old switcher app can't be on the phone with OneOS. Uninstall it, then come back.",
                    FixAction.OPEN_OLD_SWITCHER_INFO,
                )
            }
            SwitchGates.ID_STAGE -> when (r) {
                SwitchGates.R_STAGE_UNFINISHED -> m(
                    "One UI's settings need restoring",
                    "Your last session ended with a force restart. This puts One UI's settings back.",
                    FixAction.RESTORE,
                )
                SwitchGates.R_STAGE_NOT_READ -> m("Couldn't check your phone", "Root didn't answer. Try again in a moment.", FixAction.TRY_AGAIN)
                else -> m(
                    "Restart your phone first",
                    "Part of the last session is still running. Restart, then open OneOS.",
                    FixAction.NONE,
                )
            }
            SwitchGates.ID_IMAGE -> image(f, system, sys, yourPhone, facts) ?: unknown(f)
            SwitchGates.ID_SPACE -> when (r) {
                SwitchGates.R_SPACE_UNKNOWN -> m("Couldn't read free space", "Try again in a moment.", FixAction.TRY_AGAIN)
                SwitchGates.R_SPACE_SWITCH -> {
                    val missing = missing(facts)
                    m(
                        if (missing != null) "Free up $missing to switch" else "Free up space to switch",
                        "Switching needs about ${Units.bytes(facts.needBytes ?: SpaceRule.LAUNCH_BYTES)} free for $system's data.",
                        FixAction.FREE_UP_SPACE,
                    )
                }
                else -> {
                    val missing = missing(facts)
                    val need = facts.needBytes
                    m(
                        when {
                            missing != null && image != null -> "Free up $missing to set up $system"
                            missing != null -> "Free up $missing of space"
                            else -> "Free up space to set up $system"
                        },
                        when {
                            need != null && facts.freeBytes != null -> "It needs about ${Units.bytes(need)}; you have ${Units.bytes(facts.freeBytes)}."
                            need != null -> "It needs about ${Units.bytes(need)}."
                            else -> "Delete old copies or other files, then try again."
                        },
                        FixAction.FREE_UP_SPACE,
                    )
                }
            }
            SwitchGates.ID_SCREEN_LOCK, ScreenLockRule.ID_SET, ScreenLockRule.ID_UNKNOWN -> when (r) {
                ScreenLockRule.R_UNKNOWN -> m("Couldn't read your screen lock", "Set Screen lock type to None or Swipe, then try again.", FixAction.TRY_AGAIN)
                // 0.4.32: the owner turned Advanced's switch on, so this warns instead of stopping.
                ScreenLockRule.R_SET_ALLOWED -> m(
                    "Your screen lock is on",
                    "You chose to switch anyway. If the phone can't take your lock afterwards, the only way back erases it.",
                    FixAction.NONE,
                )
                else -> m(
                    "Turn off your screen lock",
                    "Set Screen lock type to None or Swipe. OneOS can't switch while a lock is on.",
                    FixAction.OPEN_LOCK_SETTINGS,
                )
            }
            SwitchGates.ID_BATTERY -> when (r) {
                SwitchGates.R_BATTERY_HOT -> m(
                    "Let your phone cool down",
                    (facts.batteryC?.let { "It's ${it.toInt()} °C. " } ?: "") + "Switching needs under ${SwitchGates.BATTERY_MAX_C.toInt()} °C.",
                    FixAction.NONE,
                )
                SwitchGates.R_BATTERY_NOT_READ -> m("Couldn't read the battery", "Try again in a moment.", FixAction.TRY_AGAIN)
                else -> m("Charge your phone", "Plug it in, or charge to at least ${SwitchGates.BATTERY_MIN_PERCENT}%.", FixAction.NONE)
            }
            SwitchGates.ID_CARRIER, CompatEvaluator.ID_CARRIER -> when (r) {
                CarrierRules.R_VOLTE_ONLY -> m("No phone calls in $system", CarrierRules.noCallsAck(system), FixAction.ACKNOWLEDGE)
                CarrierRules.R_UNKNOWN -> m("Phone calls may not work", CarrierRules.maybeCallsAck(system), FixAction.ACKNOWLEDGE)
                else -> m("Calls use 2G or 3G", "Calls in $system use 2G or 3G.", FixAction.NONE)
            }
            CpuRules.ID_MISSING, CpuRules.ID_APP_FEATURES -> m(
                "May not run well on this phone",
                "This phone's chip lacks some features $system uses.",
                FixAction.NONE,
            )
            Profiles.ID_NOTE_OLDER_VENDOR -> m(
                "Not tested on this phone yet",
                "This phone's software is older than on the phones where $system has run.",
                FixAction.NONE,
            )
            Profiles.ID_NOTE_EXPECT_NO_START -> m(
                "Most likely won't start on this phone",
                "Its software is too old. If the screen stays black, One UI comes back by itself. Then share the " +
                    "session logs from Advanced.",
                FixAction.ACKNOWLEDGE,
            )
            SwitchGates.ID_LOGS -> m(
                "Last session's logs aren't read yet",
                "OneOS reads them by itself after you come back.",
                FixAction.NONE,
            )
            else -> unknown(f)
        }
    }

    private fun allowRoot(f: Finding, rootApp: String?): PlainMessage =
        if (rootApp != null) {
            PlainMessage("Allow root access", "Open $rootApp and allow OneOS, then come back.", FixAction.OPEN_ROOT_APP, "Open $rootApp", f.level)
        } else {
            PlainMessage("Allow root access", "Open your root app and allow OneOS, then come back.", FixAction.TRY_AGAIN, defaultLabel(FixAction.TRY_AGAIN), f.level)
        }

    private fun image(f: Finding, system: String, sys: String, yourPhone: String, facts: PlainFacts): PlainMessage? {
        fun m(title: String, line: String, action: FixAction) = PlainMessage(title, line, action, defaultLabel(action), f.level)
        return when (f.reason) {
            // Setting up: the picked file.
            SwitchGates.R_IMAGE_NONE -> m("Choose a system first", "Pick the system you want to set up.", FixAction.CHOOSE_SYSTEM)
            ImageIdentifier.R_DAMAGED -> m("The download is damaged", "It may not have finished. Download $system again.", FixAction.DOWNLOAD_AGAIN)
            ImageIdentifier.R_WRONG_PHONE -> m("That file is for another phone", "Choose the file you downloaded for $yourPhone.", FixAction.CHOOSE_FILE)
            ImageIdentifier.R_UNCOMPRESSED, ImageIdentifier.R_NOT_OURS, ImageIdentifier.R_SIZE_UNKNOWN ->
                m("That isn't a OneOS system file", "Choose the file you downloaded for $system.", FixAction.CHOOSE_FILE)
            ImageIdentifier.R_RETIRED -> m("OneOS no longer sets up that system", "Choose the file you downloaded for $system.", FixAction.CHOOSE_FILE)
            ImageIdentifier.R_NOT_CHECKED -> m("The download isn't checked yet", "OneOS checks it first when you set up $system.", FixAction.NONE)
            ImageIdentifier.R_NO_RAW, ImageIdentifier.R_RAW_NOT_OURS, ImageIdentifier.R_RAW_WRONG_PHONE, ImageIdentifier.R_RAW_DAMAGED ->
                m("The system on this phone can't be used", "Choose the file you downloaded for $system.", FixAction.CHOOSE_FILE)
            SwitchGates.R_IMAGE_NOT_IN_BUILD -> m("No system for this phone in this version", "Update OneOS.", FixAction.NONE)
            // The series download: the finding names the right one.
            SwitchGates.R_IMAGE_OTHER_SERIES -> m(f.title, f.detail, FixAction.NONE)
            // Switching: what is set up.
            SwitchGates.R_IMAGE_NOTHING -> m("Set up a system first", "Choose one and set it up. It takes about 15 minutes.", FixAction.CHOOSE_SYSTEM)
            SwitchGates.R_IMAGE_NOT_READ -> m("Couldn't check your phone", "Root didn't answer. Try again in a moment.", FixAction.TRY_AGAIN)
            SwitchGates.R_IMAGE_OTHER_PHONE -> m("Set up $system again", "What's installed was made for another phone or system.", FixAction.SET_UP_AGAIN)
            SwitchGates.R_IMAGE_OTHER_VERSION, SwitchGates.R_IMAGE_OTHER_SET -> m(
                "Finish updating $system",
                if (facts.installedReusable) {
                    "OneOS was updated. No download, about 2 minutes. Your apps and data stay."
                } else {
                    "OneOS was updated. Set it up again with its download. Your apps and data stay."
                },
                FixAction.UPDATE,
            )
            SwitchGates.R_IMAGE_FILES_CHANGED -> m("$sys needs a repair", "Some of its files changed since setup.", FixAction.REPAIR)
            else -> null
        }
    }

    private fun missing(facts: PlainFacts): String? {
        val need = facts.needBytes ?: return null
        val free = facts.freeBytes ?: return null
        return if (need > free) Units.bytes(need - free) else null
    }

    /** A finding [of] has no message for (a fix pack's new rule): never its technical text. */
    private fun unknown(f: Finding) = PlainMessage(
        if (f.level == Level.BLOCK) "OneOS found a problem" else "OneOS found something to check",
        "Details shows what it found.",
        FixAction.NONE,
        null,
        f.level,
    )

    /** True when [of] has a message of its own for [f] (not the fallback). */
    fun knows(f: Finding, image: ImageRef?, phone: PhoneProfile?): Boolean {
        val m = of(f, image, phone)
        return m.title != "OneOS found a problem" && m.title != "OneOS found something to check"
    }

    fun defaultLabel(a: FixAction): String? = when (a) {
        FixAction.NONE, FixAction.ACKNOWLEDGE -> null
        FixAction.TRY_AGAIN -> "Try again"
        FixAction.OPEN_ROOT_APP -> "Open root app"
        FixAction.SEND_PHONE_DETAILS -> "Send phone details"
        FixAction.CHOOSE_SYSTEM -> "Choose a system"
        FixAction.OPEN_OLD_SWITCHER_INFO -> "Open app info"
        FixAction.RESTORE -> "Restore now"
        FixAction.DOWNLOAD_AGAIN -> "Download again"
        FixAction.CHOOSE_FILE -> "Choose another file"
        FixAction.SET_UP_AGAIN -> "Set up again"
        FixAction.SET_UP -> "Set up"
        FixAction.UPDATE -> "Update now"
        FixAction.REPAIR -> "Repair"
        FixAction.FREE_UP_SPACE -> "Free up space"
        FixAction.OPEN_LOCK_SETTINGS -> "Open lock settings"
        FixAction.SEND_REPORT -> "Send report"
        FixAction.SWITCH -> "Switch"
        FixAction.SHOW_PROGRESS -> "Show progress"
    }

    /** Appended to a refusal at switch time: nothing was done. */
    const val SWITCH_REFUSED_TAIL = "Nothing changed. One UI keeps running."

    /**
     * Root's refusal at switch time (`LaunchJob`: "Root refused to switch: …"),
     * matched by phrase, for [image] on [phone]. Anything not matched is
     * "Couldn't switch" with Send report.
     */
    fun switchRefused(problem: String, image: ImageRef?, phone: PhoneProfile?): PlainMessage {
        val p = problem.lowercase()
        fun gate(id: String, reason: String) = of(Finding(id, Level.BLOCK, "", "", reason), image, phone)
        return when {
            "busybox" in p || "resetprop" in p -> PlainMessage(
                "Your root app is missing a tool",
                "OneOS needs a tool your root app doesn't have. Update Magisk, KernelSU or APatch.",
                FixAction.NONE, null,
            )
            "volume up key" in p || "volume down key" in p -> PlainMessage(
                "OneOS can't read the volume keys",
                "You need them to come back. Restart your phone and try again.",
                FixAction.NONE, null,
            )
            "free on /data" in p -> gate(SwitchGates.ID_SPACE, SwitchGates.R_SPACE_SWITCH)
            "battery too warm" in p -> gate(SwitchGates.ID_BATTERY, SwitchGates.R_BATTERY_HOT)
            "battery" in p && "not readable" in p -> gate(SwitchGates.ID_BATTERY, SwitchGates.R_BATTERY_NOT_READ)
            "battery" in p -> gate(SwitchGates.ID_BATTERY, SwitchGates.R_BATTERY_LOW)
            "old switcher" in p -> gate(SwitchGates.ID_OLD_SWITCHER, SwitchGates.R_OLD_SWITCHER_INSTALLED)
            "screen lock" in p -> gate(SwitchGates.ID_SCREEN_LOCK, ScreenLockRule.R_SET)
            "never returned" in p -> gate(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_UNFINISHED)
            "restart the phone" in p || "still running" in p -> gate(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_RUNNING)
            "no oneos marker" in p || "prepare first" in p -> gate(SwitchGates.ID_IMAGE, SwitchGates.R_IMAGE_NOTHING)
            "prepare again" in p -> gate(SwitchGates.ID_IMAGE, SwitchGates.R_IMAGE_OTHER_VERSION)
            else -> PlainMessage("Couldn't switch", "Something didn't check out. Send a report so the OneOS team can look.", FixAction.SEND_REPORT, defaultLabel(FixAction.SEND_REPORT))
        }
    }

    /**
     * Why setup stopped (`PrepareJob`'s message), for [image]: the damaged
     * download, the app's own files, One UI changing underneath, a file that
     * could not be read, or anything else. [stopped]: the user tapped Stop.
     */
    fun setupFailed(message: String, stopped: Boolean, image: ImageRef?): PlainMessage {
        val system = image?.name ?: Images.OTHER_SYSTEM
        val sys = Sentence.start(system)
        val p = message.lowercase()
        return when {
            stopped -> PlainMessage("Setup stopped", "$sys isn't ready. Set it up again whenever you like.", FixAction.SET_UP_AGAIN, defaultLabel(FixAction.SET_UP_AGAIN), Level.WARN)
            "in the app is damaged" in p || "not the pinned one" in p -> PlainMessage(
                "This copy of OneOS is damaged", "Reinstall OneOS, then set up $system again.", FixAction.NONE, null,
            )
            "services.jar is not the jar" in p -> PlainMessage(
                "One UI changed during setup", "Restart your phone and try again.", FixAction.NONE, null,
            )
            "sha-256 differs" in p || "the .gz has" in p || "unpacked to" in p || "unpacks to more" in p ||
                "not an ext4 image" in p || "corrupt" in p || "crc" in p || "unexpected end" in p ->
                PlainMessage("The download is damaged", "It may not have finished. Download $system again.", FixAction.DOWNLOAD_AGAIN, defaultLabel(FixAction.DOWNLOAD_AGAIN))
            "ioexception" in p || "could not read" in p || "cannot open the picked file" in p -> PlainMessage(
                "Couldn't read the download", "Choose the file again.", FixAction.CHOOSE_FILE, defaultLabel(FixAction.CHOOSE_FILE),
            )
            else -> PlainMessage(
                "Setup didn't finish", "One UI wasn't changed. Try again, or send a report to the OneOS team.",
                FixAction.SEND_REPORT, defaultLabel(FixAction.SEND_REPORT),
            )
        }
    }
}
