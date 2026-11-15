package com.fahadali.oneos.core.model

/**
 * What an iOS 27 (OneiOS) screen offers to fix a refusal (docs/oneios.md, "In the app"), as [FixAction]
 * is the Android guests'. The app runs it (ui/OneiosActions.kt); none of them changes what root checks.
 */
enum class OneiosFix {
    /** Nothing to tap: the user does it outside OneOS (charge, cool down, restart), then checks again. */
    NONE,

    /** Ask root's `status` again (its preflight, read only). */
    CHECK_AGAIN,

    /** The runtime: "Do you have the file?" (yes: the picker; no: OneiOS's latest release). */
    GET_RUNTIME,

    /** The latest release's runtime again (a download that did not finish). */
    DOWNLOAD_RUNTIME,

    /** The picker for a runtime package. */
    IMPORT_RUNTIME,

    /** The picker for the image set (never downloaded). */
    IMPORT_IMAGE,

    /** Root's `return`: oneios_return.sh, for a session that is still open. */
    BACK_TO_ONE_UI,

    /** Root's `remove`, after asking: the stage is not safe to use as it is. */
    REMOVE,

    /** The Session logs screen. */
    SESSION_LOGS,
}

/**
 * Which step of the iOS flow a message belongs to, in the order oneios_switch.sh's preflight checks
 * them: this phone and root, then the runtime, then the image set, then everything else of the
 * phone's state before a switch. [OTHER]: not a preflight line (root's own refusal, the app's).
 */
enum class OneiosPart { PHONE, RUNTIME, IMAGE, SWITCH, OTHER }

/**
 * One refusal in plain words, as [PlainMessage]: a short [title] (at most 40 characters), one [line]
 * (at most 140), the one [fix] with its button text ([fixLabel]), the step it is about, and the
 * script's own words ([detail]) for Details. [Level.INFO] is not a fault: the next step to take.
 */
data class OneiosMessage(
    val title: String,
    val line: String,
    val fix: OneiosFix,
    val part: OneiosPart,
    val level: Level = Level.BLOCK,
    val detail: String = "",
) {
    val fixLabel: String? get() = OneiosPlain.label(fix)

    /** The usual next step (no runtime, no image set yet), not something that went wrong. */
    val isNextStep: Boolean get() = level == Level.INFO
}

/**
 * The iOS screens' plain words for what root and the app answer, matched by the scripts' own phrases
 * (`@@REFUSED` of oneios_root.sh, `PREFLIGHT REFUSED:` of oneios_switch.sh, which root passes on as
 * `ready 0 <why>` and as the switch's refusal) and by [OneiosJob]'s and [OneiosImport]'s failures.
 * Anything not matched is "Couldn't finish" with Session logs. The words follow [Plain]'s: say what
 * to do, not what the script found.
 */
object OneiosPlain {
    const val MAX_TITLE = PlainMessage.MAX_TITLE
    const val MAX_LINE = PlainMessage.MAX_LINE

    fun label(fix: OneiosFix): String? = when (fix) {
        OneiosFix.NONE -> null
        OneiosFix.CHECK_AGAIN -> "Check again"
        OneiosFix.GET_RUNTIME -> "Get the runtime"
        OneiosFix.DOWNLOAD_RUNTIME -> "Download again"
        OneiosFix.IMPORT_RUNTIME -> "Choose the runtime file"
        OneiosFix.IMPORT_IMAGE -> "Import the image set"
        OneiosFix.BACK_TO_ONE_UI -> "Back to One UI"
        OneiosFix.REMOVE -> "Remove the iOS files"
        OneiosFix.SESSION_LOGS -> "Session logs"
    }

    private val LIST_CHECK = Regex("^(runtime|image)(\\.sha256|\\.ids|/)")
    private val BATTERY_AT = Regex("battery at ([0-9]{1,3})%")
    private val WARM = Regex("too warm \\(([0-9]{1,3}) c\\)")

    /**
     * [problem] in plain words. [kind]: the package being staged when it came (a download or an
     * import), so that a damaged file names the right one; null for the preflight, the switch, the
     * return and remove.
     */
    fun refused(problem: String, kind: OneiosKind? = null): OneiosMessage {
        val raw = problem.trim().removePrefix("PREFLIGHT REFUSED:").removePrefix("root refused:").trim()
        val p = raw.lowercase()
        val label = kind?.label ?: "file"
        val part = when (kind) {
            OneiosKind.RUNTIME -> OneiosPart.RUNTIME
            OneiosKind.IMAGE -> OneiosPart.IMAGE
            null -> OneiosPart.OTHER
        }
        // The same package again: the runtime by its question (file or download), the image set by the picker.
        val again = when (kind) {
            OneiosKind.RUNTIME -> OneiosFix.GET_RUNTIME
            OneiosKind.IMAGE -> OneiosFix.IMPORT_IMAGE
            null -> OneiosFix.CHECK_AGAIN
        }
        fun m(title: String, line: String, fix: OneiosFix, at: OneiosPart, level: Level = Level.BLOCK) =
            OneiosMessage(title, line, fix, at, level, raw)
        val listCheck = LIST_CHECK.find(p)?.groupValues?.get(1)
        return when {
            p.isEmpty() -> m("Couldn't finish", "Root gave no reason. Check again; if it stays, open Session logs.", OneiosFix.CHECK_AGAIN, OneiosPart.OTHER)
            // Before every phrase: what follows these may be anything (the preflight's last line, an argument).
            p.startsWith("usage:") || "for tests" in p || p.startsWith("test root") -> m(
                "Couldn't finish", "OneOS asked root something it doesn't take. Check again; if it stays, open Session logs.",
                OneiosFix.CHECK_AGAIN, OneiosPart.OTHER,
            )
            "preflight gave no answer" in p -> m(
                "The last check gave no answer", "Check again. If it stays, open Session logs and look at the switch log.",
                OneiosFix.CHECK_AGAIN, OneiosPart.OTHER,
            )
            p == "stopped" -> m(
                "Stopped", "Nothing set up before was changed. Start again whenever you like.",
                again, part, Level.WARN,
            )

            // The app itself, or its root script on the way to root.
            "not the pinned one" in p || "not the pinned ones" in p -> m(
                "This copy of OneOS is damaged", "Reinstall OneOS, then open iOS 27 again.", OneiosFix.NONE, OneiosPart.OTHER,
            )
            "root script did not arrive intact" in p -> m(
                "The root script didn't arrive", "OneOS's root script reached root damaged. Check again; if it stays, reinstall OneOS.",
                OneiosFix.CHECK_AGAIN, OneiosPart.OTHER,
            )
            "root script is not in the stage" in p -> m(
                "OneOS's root script changed", "Checking again puts this version's root script back.", OneiosFix.CHECK_AGAIN, OneiosPart.OTHER,
            )

            // The phone and root (the preflight's first checks).
            "galaxy s24 ultra" in p -> m(
                "iOS 27 isn't for this phone", "It runs on the Galaxy S24 Ultra (SM-S928) only.", OneiosFix.NONE, OneiosPart.PHONE,
            )
            "not running as root" in p || "su could not be started" in p || p == "root did not answer in time" || p == "no answer from root" ||
                p == "stopped before it finished" || p.startsWith("exit ") -> m(
                "Allow root access", "Open your root app and allow OneOS, then check again.", OneiosFix.CHECK_AGAIN, OneiosPart.PHONE,
            )
            "no sha256sum" in p -> m(
                "Your phone is missing a tool", "OneOS needs sha256sum to check the files. Update your root app, then check again.",
                OneiosFix.CHECK_AGAIN, OneiosPart.PHONE,
            )
            // The preflight's own busybox line names the paths it looked at, after the runtime and image
            // checks; root's (before the preflight could run) does not.
            "busybox" in p || "resetprop" in p || "lacks the applets" in p || Regex(" lacks [a-z]+$").containsMatchIn(p) -> m(
                "Your root app is missing a tool", "OneOS needs a tool your root app doesn't have. Update KernelSU, Magisk or APatch.",
                OneiosFix.CHECK_AGAIN, if ("(/data/adb" in p || "resetprop" in p || "lacks" in p) OneiosPart.SWITCH else OneiosPart.PHONE,
            )

            // Not set up yet: the next step, not a fault.
            "oneios is not set up on this phone" in p || "no oneios runtime is staged" in p -> m(
                "Get the OneiOS runtime", "It holds xnuhost, the program that runs iOS. Download it from OneiOS's releases, or use your own file.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME, Level.INFO,
            )
            "no ios image set is staged" in p -> m(
                "Import your iOS image set", "Build it from Apple's firmware with OneiOS's scripts, then choose its .tar.zst file.",
                OneiosFix.IMPORT_IMAGE, OneiosPart.IMAGE, Level.INFO,
            )
            ("oneios_switch.sh" in p || "oneios_return.sh" in p) && ("missing" in p || "not staged" in p || "not root's" in p) -> m(
                "OneOS's switch files are missing", "Getting the runtime again puts them back on the phone.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )

            // The runtime.
            "session abi" in p -> m(
                "This runtime doesn't fit this OneOS",
                "It speaks another session ABI than this OneOS (${OneiosSystem.SESSION_ABI}). Get a matching runtime, or update OneOS.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )
            "placeholder" in p -> m(
                "This runtime can't start iOS", "It has a stand-in instead of xnuhost. Get a OneiOS release that has xnuhost.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )
            "needs oneos" in p && "or newer" in p -> m(
                "Update OneOS first", "This runtime needs a newer OneOS. Update the app, then get the runtime again.",
                OneiosFix.NONE, OneiosPart.RUNTIME,
            )
            "boots format" in p -> m(
                "Image set and runtime don't match", "Build the image set again for this runtime, or get a runtime that boots it.",
                OneiosFix.IMPORT_IMAGE, OneiosPart.IMAGE,
            )
            listCheck == "runtime" || "the staged runtime is not root's" in p -> m(
                "The runtime changed on this phone", "A file of it no longer matches what root checked when it was set up. Get the runtime again.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )
            listCheck == "image" || "the staged image set is not root's" in p || "image set has no format number" in p -> m(
                "The image set changed on this phone", "A file of it no longer matches what root checked when it was set up. Import it again.",
                OneiosFix.IMPORT_IMAGE, OneiosPart.IMAGE,
            )

            // A session that is open, or did not end.
            "ios session is running" in p || "ios session is already running" in p || "session of this boot is still open" in p -> m(
                "An iOS session is still open", "Go back to One UI first. If Back to One UI does nothing, restart your phone.",
                OneiosFix.BACK_TO_ONE_UI, OneiosPart.SWITCH,
            )
            "never returned" in p || "restart the phone" in p || "framework is not running" in p || "surfaceflinger is not running" in p -> m(
                "Restart your phone first", "An earlier session or return didn't finish. Restart your phone, then check again.",
                OneiosFix.NONE, OneiosPart.SWITCH,
            )
            // After the session checks: "xnuhost of an earlier session is still running" is a restart, not the runtime.
            "xnuhost" in p -> m(
                "This runtime can't start iOS", "Its xnuhost is missing, or not a program for this phone. Get the runtime again.",
                OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )
            "mount namespace" in p -> m(
                "OneOS can't reach One UI", "Root runs apart from One UI's own space. Restart your phone, then check again.",
                OneiosFix.NONE, OneiosPart.SWITCH,
            )
            "has not finished starting" in p -> m(
                "One UI is still starting", "Wait a minute after the phone starts, then check again.", OneiosFix.CHECK_AGAIN, OneiosPart.SWITCH, Level.WARN,
            )

            // The way back and the phone's state (the preflight's last checks).
            "getevent" in p || "volume up key" in p || "volume down key" in p || "no ps:" in p -> m(
                "OneOS can't read the volume keys", "You need them to come back to One UI. Restart your phone, then check again.",
                OneiosFix.NONE, OneiosPart.SWITCH,
            )
            "battery" in p && "not readable" in p -> m(
                "OneOS can't read the battery", "Restart your phone, then check again.", OneiosFix.NONE, OneiosPart.SWITCH,
            )
            "too warm" in p -> m(
                "Your phone is too warm",
                (WARM.find(p)?.groupValues?.get(1)?.let { "The battery is at $it °C. " } ?: "") + "Let it cool down, then check again.",
                OneiosFix.NONE, OneiosPart.SWITCH, Level.WARN,
            )
            "battery at" in p -> m(
                "Charge your phone",
                (BATTERY_AT.find(p)?.groupValues?.get(1)?.let { "The battery is at $it%. " } ?: "") + "Charge it to 30% or plug it in, then check again.",
                OneiosFix.NONE, OneiosPart.SWITCH, Level.WARN,
            )
            "free on /data" in p -> m(
                "Free up space", "iOS needs 2 GB free for its data. Free up space in One UI, then check again.", OneiosFix.NONE, OneiosPart.SWITCH,
            )
            "not enough free space" in p -> m(
                "Not enough space for the $label", "Free up space in One UI, then try again. What was set up before is unchanged.", again, part,
            )
            "wake_lock" in p -> m(
                "This phone can't stay awake for iOS", "Its kernel has no wakelock for a session, so it can't run iOS.", OneiosFix.NONE, OneiosPart.SWITCH,
            )
            "experimental tick" in p || "tick the box" in p -> m(
                "Tick both boxes first", "Read how to get back to One UI, tick both boxes, then switch.", OneiosFix.NONE, OneiosPart.SWITCH, Level.WARN,
            )
            // The stage itself: a link, another owner, not a folder.
            " is a link" in p || " is a symlink" in p || "is not a folder" in p || "is missing or not root's" in p || "is not root's or is writable by others" in p ||
                "is mounted in the stage" in p -> m(
                if ("mounted" in p) "Restart your phone first" else "The iOS folder isn't safe to use",
                if ("mounted" in p) "Something is still mounted in the iOS folder. Restart your phone, then check again."
                else "Something changed it outside OneOS. Remove the iOS files, then set iOS up again.",
                if ("mounted" in p) OneiosFix.NONE else OneiosFix.REMOVE, OneiosPart.OTHER,
            )

            // The download (the runtime only).
            "no connection to github" in p -> m(
                "No connection", "Connect to the internet, then download again.", OneiosFix.DOWNLOAD_RUNTIME, OneiosPart.RUNTIME, Level.WARN,
            )
            "has not published a release" in p -> m(
                "No runtime to download yet", "OneiOS has no release yet. If you built a runtime yourself, choose its file.",
                OneiosFix.IMPORT_RUNTIME, OneiosPart.RUNTIME, Level.WARN,
            )
            "has no release named" in p || "is not a release tag" in p -> m(
                "No release with that name", "Check the tag, or leave it empty for the latest release.", OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME, Level.WARN,
            )
            "runtime package" in p || "release answer" in p || "is not a file of" in p || ("release" in p && ".sha256" in p && "has no" in p) -> m(
                "This release has no runtime", "Choose another release, or use the runtime file you have.", OneiosFix.GET_RUNTIME, OneiosPart.RUNTIME,
            )
            "github answered" in p || "could not be downloaded" in p || "download stopped" in p || "larger than its release says" in p ||
                "answer from github" in p || "does not hold its sha-256" in p -> m(
                "The download didn't finish", "Download it again. What was set up before is unchanged.", OneiosFix.DOWNLOAD_RUNTIME, OneiosPart.RUNTIME, Level.WARN,
            )

            // The import: the file, and root's receive and finish.
            // Before the manifest's own name below: "manifest.json was not received" is an import that stopped.
            "files were received" in p || "was not received" in p || "begin first" in p || "was already received" in p || "were received" in p -> m(
                "The import didn't finish", "Root didn't get every file. Try again; what was set up before is unchanged.", again, part,
            )
            "bytes arrived" in p -> m(
                "The copy didn't finish", "Not all of a file reached root. Try again; what was set up before is unchanged.", again, part,
            )
            "is too large" in p -> m(
                "A file of it is too large", "One file of the $label is over 16 GB. Build it again with smaller files.", OneiosFix.NONE, part,
            )
            "did not arrive intact" in p || "does not match its sha-256" in p || "damaged or incomplete" in p || "was not read to its end" in p ||
                "is in the file twice" in p || " is outside " in p || Regex(" is [0-9]+ bytes, ").containsMatchIn(p) || Regex("^[^ ]+ is not in ").containsMatchIn(p) -> m(
                "The $label is damaged", "It may not have finished copying or downloading. Get it again; nothing set up before changed.", again, part,
            )
            "reads format" in p -> m(
                "OneOS can't read this $label", "It is of a newer format. Update OneOS, or build it again for this version.", OneiosFix.NONE, part,
            )
            "not a .tar.zst" in p || "is not a oneios runtime" in p || "is not a ios image set" in p || "it is not a " in p ||
                p.startsWith("runtime.json") || p.startsWith("manifest.json") -> m(
                if (kind == OneiosKind.IMAGE) "This isn't an iOS image set" else "This isn't a OneiOS runtime",
                if (kind == OneiosKind.IMAGE) "Choose the .tar.zst image set you built with OneiOS's scripts."
                else "Choose a oneios-runtime-…-arm64.tar.zst file.",
                if (kind == OneiosKind.IMAGE) OneiosFix.IMPORT_IMAGE else OneiosFix.IMPORT_RUNTIME, part,
            )
            "cannot be opened" in p || "ioexception" in p -> m(
                "Couldn't read the file", "Choose the file again.",
                if (kind == OneiosKind.IMAGE) OneiosFix.IMPORT_IMAGE else OneiosFix.IMPORT_RUNTIME, part,
            )
            p.startsWith("failed:") -> m(
                "Root couldn't write the files", "Check that the phone has free space, then try again.", again, part,
            )
            else -> m(
                "Couldn't finish", "Something didn't check out. Check again; if it stays, open Session logs.", OneiosFix.CHECK_AGAIN, OneiosPart.OTHER,
            )
        }
    }
}

/**
 * What the app itself checked when it staged a package (`receive` and `finish` answered OK for every
 * file): root's `status` names the runtime's version but not its size, so the screens keep this
 * beside it, and show it only while root's version (and build) is still this one.
 */
data class OneiosStaged(
    val kind: OneiosKind,
    val version: String,
    val build: String?,
    val files: Int,
    val bytes: Long,
    val atMs: Long,
) {
    fun encode(): String = listOf(kind.word, version, build ?: "-", files.toString(), bytes.toString(), atMs.toString()).joinToString(" ")

    /** It describes what root reports as staged now. */
    fun matches(version: String?, build: String? = null): Boolean =
        version == this.version && (kind == OneiosKind.RUNTIME || build == null || build == "unknown" || build == this.build)

    companion object {
        private val WORD = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")

        fun of(manifest: OneiosManifest, atMs: Long): OneiosStaged =
            OneiosStaged(manifest.kind, manifest.version, manifest.build, manifest.files.size, manifest.bytes, atMs)

        /** [encode]'s text again; null for anything else. */
        fun decode(text: String?): OneiosStaged? {
            val w = text?.trim()?.split(' ') ?: return null
            if (w.size != 6) return null
            val kind = OneiosKind.entries.firstOrNull { it.word == w[0] } ?: return null
            if (!WORD.matches(w[1]) || (w[2] != "-" && !WORD.matches(w[2]))) return null
            val files = w[3].toIntOrNull()?.takeIf { it >= 0 } ?: return null
            val bytes = w[4].toLongOrNull()?.takeIf { it >= 0 } ?: return null
            val at = w[5].toLongOrNull()?.takeIf { it >= 0 } ?: return null
            return OneiosStaged(kind, w[1], w[2].takeIf { it != "-" }, files, bytes, at)
        }
    }
}
