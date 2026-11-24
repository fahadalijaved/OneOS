package com.fahadali.oneos.core.model

import java.io.EOFException
import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest
import java.util.Locale

/**
 * The iOS 27 (OneiOS) system (docs/oneios.md): not an Android guest, so it is
 * not an [ImageRef]. Three things differ:
 *  - its runtime (xnuhost, the program that runs iOS on One UI's kernel) is a
 *    package from OneiOS's GitHub releases ([OneiosReleases]);
 *  - its image set is built by the user from Apple's firmware with OneiOS's
 *    scripts and imported from a file, never downloaded ([OneiosKind.IMAGE]);
 *  - its session is `oneios_switch.sh` / `oneios_return.sh`, in its own stage.
 * Both the runtime package and the image set are a `.tar.zst` with a manifest
 * of sizes and SHA-256s ([OneiosManifests], [OneiosPackage]).
 */
object OneiosSystem {
    const val ID = "oneios-ios27"

    /** The system's name on its card and in every text about it. */
    const val NAME = "iOS 27 (OneiOS)"
    const val SHORT_NAME = "iOS 27"

    /**
     * The name of what the staged image set starts: "iOS 16.5" for the A56's 20F66 set, the whole version of an iOS 27
     * set ("iOS 27.0.1", "iOS 27.2.1": two builds can be staged, OneOS 2026-11-25), [SHORT_NAME] when no set is
     * staged. The page title, the Switch button and the switching line use it: on the A56 they all said "iOS 27" over
     * an iOS 16.5 set (OneiOS issue 73, 2026-11-24).
     */
    fun shortName(imageVersion: String?): String {
        val v = imageVersion?.trim()?.takeIf { it.isNotEmpty() } ?: return SHORT_NAME
        if (!Regex("^[0-9]{1,3}(\\.[0-9]{1,3}){0,3}$").matches(v)) return SHORT_NAME
        return if (isIos27(v)) "iOS " + v.split('.').take(3).joinToString(".") else "iOS " + v.split('.').take(2).joinToString(".")
    }

    /** The set is iOS 27 (or none is staged): the iOS 27 artwork shows over it. */
    fun isIos27(imageVersion: String?): Boolean =
        imageVersion?.trim()?.takeIf { it.isNotEmpty() }?.substringBefore('.')?.let { it == "27" } ?: true

    /** [shortName] with "(OneiOS)", as [NAME]. */
    fun name(imageVersion: String?): String = "${shortName(imageVersion)} (OneiOS)"

    const val BLURB = "Apple's iOS 27 on this phone's own kernel, run by OneiOS's xnuhost. " +
        "You build the image yourself from Apple's firmware; OneOS never downloads it."

    /** Root's stage for it: separate from the Android guests' ([Images.STAGE_NAME]'s folder). */
    const val STAGE = "/data/local/tmp/oneios"

    /** The session contract between the session scripts and xnuhost (OneiOS's oneos/interface.md). */
    const val SESSION_ABI = 1

    /** The manifest `format` of both a runtime package and an image set this build reads. */
    const val FORMAT = 1

    /**
     * The phones that get the iOS card in Systems and the iOS page's setup steps: the Galaxy S24 Ultra, and the
     * Galaxy A56 (SM-A566, a56x, s5e8855; OneiOS issue 73), which makes and starts iOS 16.5 (20F66), not iOS 27
     * ([OneiosImageChoice.of]). The A56 path has not run on an A56 yet (untested on hardware).
     */
    val PROFILE_IDS: Set<String> = setOf(Profiles.ID_S_ULTRA_8650, Profiles.ID_A56)

    /**
     * The phone it is mainly tested and working on: the Galaxy S24 Ultra (SM-S928, e3q, SM8650); every other phone,
     * the A56 of [PROFILE_IDS] too, is warned, not refused (the owner, 2026-11-16) by [gate]. Every S24 Ultra model
     * number is this profile: the owner's SM-S928B, the US SM-S928U and U1, the Canadian SM-S928W (its stock firmware
     * has the US bootloader and vendor model: [CustomRomRule] takes it), the Korean SM-S928N and the Chinese SM-S9280
     * (OneiosTest).
     */
    val TESTED_PROFILE_IDS: Set<String> = setOf(Profiles.ID_S_ULTRA_8650)

    const val R_NOT_THIS_PHONE = "oneios-not-this-phone"
    const val R_EXPERIMENTAL = "oneios-experimental"
    const val GATE_ID = "gate-oneios"

    /** The not-this-phone warning's tick (OneiosSwitchConfirm's box; the owner's 2026-11-16 decision). */
    const val NOT_THIS_PHONE_ACK = "I understand that iOS 27 (OneiOS) is mainly tested and working on the Galaxy S24 Ultra 5G " +
        "(SM-S928B); on this phone it may be unstable, miss pieces, or not come back to One UI, and that One UI stops while it runs."

    /**
     * What is known of a phone the warning names, by profile id: facts another fork measured on it (OneiOS
     * docs/s26.md). Still a WARN, never a refusal (the owner's 2026-11-16 rule; YMGPwcca/OneOS refuses the S26 Ultra,
     * this fork does not: docs/oneios.md, "Scope").
     */
    val NOT_THIS_PHONE_NOTES: Map<String, String> = mapOf(
        Profiles.ID_S_ULTRA_8850 to "On the Galaxy S26 Ultra iOS ran only in another fork's root-only test, never through " +
            "this switch; its watchdog hand-off and the return to One UI in place are not verified there. A return that " +
            "fails restarts the phone into One UI.",
        Profiles.ID_A56 to "On the Galaxy A56 this app makes and starts iOS 16.5 (20F66), not iOS 27. iOS 16.5 reached " +
            "the lock screen there only in another fork (Musicalista/OneiOS-A56), and touch did not work there; this " +
            "app's A56 path has not run on an A56 yet. A return that fails restarts the phone into One UI.",
    )

    /** What the experimental tick says. */
    const val ACK = "I understand that iOS 27 (OneiOS) is experimental, has never been tested on a phone like this one, " +
        "and that One UI stops while it runs. Volume Up + Volume Down for 3 seconds brings One UI back."

    /**
     * The session modes (docs/oneios.md, "Android takeover"; OneiOS's oneos/interface.md 4a): [MODE_HOSTED], the session
     * as it always was, and [MODE_TAKEOVER], the opt-in Android takeover. Root's switch verb takes the mode as its third
     * word; the switch also reads `session-mode=` from the image's xnuhost.conf.
     */
    const val MODE_HOSTED = "hosted"
    const val MODE_TAKEOVER = "takeover"

    /**
     * The phones whose profile offers the Android takeover's toggle: the Galaxy S24 Ultra (the owner's) and the Galaxy
     * S26 Ultra (where YMGPwcca/OneOS's Framework-takeover experiment it comes from ran). The same two rows of OneiOS's
     * host table allow `session-mode=takeover`; the switch asks xnuhost (`--host-info`) before it stops anything.
     */
    val TAKEOVER_PROFILE_IDS: Set<String> = setOf(Profiles.ID_S_ULTRA_8650, Profiles.ID_S_ULTRA_8850)

    /** The toggle's title and its warning, on the Switch sheet. */
    const val TAKEOVER_TITLE = "Android takeover (faster, experimental)"
    const val TAKEOVER_WARNING = "iOS gets this phone's touchscreen for itself (One UI cannot read it until the session " +
        "ends), the switch stops Android services no iOS bridge uses (the camera service, media extractor and metrics, " +
        "the TV tuner, perfmond, wificond) so iOS gets their memory, and it caps the CPUs' top speed only when the " +
        "battery gets hot (50 C and up; at 55 C it returns to One UI). Everything it " +
        "changes is put back when One UI comes back. The way back is the same: Volume Up + Volume Down for 3 seconds " +
        "returns to One UI in place; only when the return in place cannot put One UI back does the phone restart into " +
        "One UI. Not tried on a phone yet."

    /** Whether the Switch sheet offers the Android takeover's toggle on this phone. */
    fun takeoverOfferedOn(profile: PhoneProfile?): Boolean = profile != null && profile.enabled && profile.id in TAKEOVER_PROFILE_IDS

    /** Root's switch verb's arguments: the versionCode, the tick, and the mode only for the takeover (hosted: two words, as before). */
    fun switchArgs(versionCode: Int, takeover: Boolean): List<String> =
        listOf(versionCode.toString(), "1") + if (takeover) listOf(MODE_TAKEOVER) else emptyList()

    fun offeredOn(profile: PhoneProfile?): Boolean = profile != null && profile.enabled && profile.id in PROFILE_IDS

    /** The phone itself, by the three ids a profile matches on. */
    fun offeredOn(model: String, device: String, soc: String, profiles: List<PhoneProfile> = Profiles.BUILT_IN): Boolean =
        offeredOn(Profiles.resolve(model, device, soc, profiles).profile)

    /** The phone it is mainly tested on ([TESTED_PROFILE_IDS]): false means the not-this-phone warning and its tick. */
    fun testedOn(profile: PhoneProfile?): Boolean = profile != null && profile.enabled && profile.id in TESTED_PROFILE_IDS

    /**
     * The system-kind gate. On the Galaxy S24 Ultra: a WARN the user has to tick
     * ([ACK]) before every switch, as for an untested profile, and OK once [ticked]. On any other
     * phone, the Galaxy A56 included (the owner, 2026-11-16: they may try it): a WARN that says what to expect,
     * with what is known of it ([NOT_THIS_PHONE_NOTES]), until [notThisPhoneTicked] ([NOT_THIS_PHONE_ACK] on the
     * confirm screen), then OK.
     */
    fun gate(profile: PhoneProfile?, ticked: Boolean, notThisPhoneTicked: Boolean = false): Finding = when {
        !testedOn(profile) && !notThisPhoneTicked -> Finding(
            GATE_ID, Level.WARN, "$NAME is mainly for the Galaxy S24 Ultra",
            "$NAME is mainly tested and working on the Galaxy S24 Ultra 5G (SM-S928B)" +
                (profile?.let { "; this phone is the ${it.label}" } ?: "; this phone is unknown") +
                ": on it the code may be unstable, miss pieces, or not come back to One UI." +
                (profile?.let { NOT_THIS_PHONE_NOTES[it.id] }?.let { " $it" } ?: ""),
            R_NOT_THIS_PHONE,
        )
        !testedOn(profile) -> Finding(GATE_ID, Level.OK, "$NAME: not the phone it is mainly tested on, acknowledged")
        !ticked -> Finding(GATE_ID, Level.WARN, "$NAME is experimental", ACK, R_EXPERIMENTAL)
        else -> Finding(GATE_ID, Level.OK, "$NAME: experimental, acknowledged")
    }
}

/** The two things OneOS stages for iOS; [word] is root's name for it, [manifestName] the file at its top. */
enum class OneiosKind(val word: String, val manifestName: String, val label: String) {
    RUNTIME("runtime", "runtime.json", "OneiOS runtime"),
    IMAGE("image", "manifest.json", "iOS image set"),
}

/** One file a manifest lists. [mode] is `0644` or `0755`. */
data class OneiosFile(val path: String, val size: Long, val sha256: String, val mode: String = "0644")

/** The kernel a runtime package carries (`runtime.json`'s `kernel`): our own XNU the phone pairs with Apple's kernelcache. Null when the runtime has none. */
data class OneiosKernel(
    /** `kernel/xnu.macho` in the package (what runs is `runtime.json`'s `xnuhost`-sibling path; this build reads this one). */
    val path: String,
    /** `xnu-<xnu version>-<profile>-<first 12 hex of the series hash>` (`oneios-tool kernel build-record`). */
    val buildId: String,
    val sha256: String,
    /** `xnu-12377.121.6`. */
    val xnu: String,
    /** `ios-27.0.1-24A446`. */
    val profile: String,
    /** `kernel/xnu.macho.build.json` in the package. */
    val record: String,
    /** `runtime.json`'s `kernels[]` entry: the Apple build it pairs ("24A446", "24B156"); null for `kernel` itself. */
    val build: String? = null,
)

/**
 * A checked `runtime.json` or `manifest.json`. [files] never names the manifest
 * itself. The runtime's own fields are null for an image set and the other way round.
 */
data class OneiosManifest(
    val kind: OneiosKind,
    val format: Int,
    val version: String,
    val files: List<OneiosFile>,
    /** Runtime: the session contract it speaks, the path of xnuhost, the image formats it boots. */
    val sessionAbi: Int? = null,
    val xnuhost: String? = null,
    val imageFormats: List<Int> = emptyList(),
    /** Runtime: its xnuhost is OneiOS's stand-in that only says "not built yet" (`"placeholder": true`): it stages, and the switch refuses it. */
    val placeholder: Boolean = false,
    /** Runtime: the lowest version of this fork that can run it (`min_oneos_fork`); null = any. */
    val minOneosFork: String? = null,
    /** Runtime: the kernel it carries ([OneiosKernel]); null = `runtime.json` has no `kernel` (nothing to rebuild from). */
    val kernel: OneiosKernel? = null,
    /**
     * Runtime: one kernel per Apple build it pairs (`runtime.json`'s `kernels`, OneiOS 2026-11-25: 24A446 at
     * `kernel/xnu.macho`, as [kernel], and 24B156 at `kernel/24B156/xnu.macho`); empty for a runtime before it.
     */
    val kernels: List<OneiosKernel> = emptyList(),
    /** Image set: Apple's build ("24A..."), the device it is of ("iPhone18,2"), "iOS". */
    val build: String? = null,
    val device: String? = null,
    val os: String? = null,
) {
    val bytes: Long get() = files.sumOf { it.size }
    fun file(path: String): OneiosFile? = files.firstOrNull { it.path == path }

    /**
     * Runtime: its kernel for a set whose kexts are [kernelBuild]'s ([OneiosImageChoice.kernelBuildOf]): [kernel] for
     * 24A446, exactly as before (a runtime without `kernels` too); the `kernels[]` entry of that build for another
     * one, null when it has none (a runtime too old for that build: "get the latest OneiOS runtime").
     */
    fun kernelFor(kernelBuild: String): OneiosKernel? =
        if (kernelBuild == OneiosImageChoice.IOS_27.build) kernel else kernels.firstOrNull { it.build == kernelBuild }
}

/** What was really there for one path: what the app read, or what root wrote. */
data class OneiosSeen(val path: String, val size: Long, val sha256: String)

object OneiosManifests {
    /** A manifest is small: a list of files. */
    const val MAX_MANIFEST_BYTES = 4 * 1024 * 1024

    /** One file of a package: root's `receive` takes at most this. */
    const val MAX_FILE_BYTES = 16L * 1024 * 1024 * 1024
    const val MAX_FILES = 4096

    private val SEGMENT = Regex("^[A-Za-z0-9_][A-Za-z0-9._+-]*$")
    private val HEX64 = Regex("^[0-9a-f]{64}$")
    private val WORD = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")

    /** A relative path of plain segments (what root's `receive` accepts). */
    fun validPath(path: String): Boolean =
        path.length in 1..200 && !path.contains("..") && path.split('/').all { SEGMENT.matches(it) }

    /**
     * The manifest [text] says, or why it is not one. Unknown keys are ignored
     * (the image builder may add its own); everything this app acts on is checked.
     */
    fun parse(kind: OneiosKind, text: String): Result<OneiosManifest> = runCatching {
        val name = kind.manifestName
        if (text.length > MAX_MANIFEST_BYTES) error("$name is too long")
        val root = JsonRead.parse(text) as? Map<*, *> ?: error("$name is not a JSON object")
        fun int(key: String): Int? = when (val v = root[key]) {
            null -> null
            is Long -> if (v in 0..Int.MAX_VALUE.toLong()) v.toInt() else error("$name: $key is out of range")
            else -> error("$name: $key is not a whole number")
        }
        fun word(key: String, required: Boolean): String? = when (val v = root[key]) {
            null -> if (required) error("$name has no $key") else null
            is String -> if (WORD.matches(v)) v else error("$name: $key '${v.take(40)}' is not a plain word")
            else -> error("$name: $key is not a string")
        }
        val format = int("format") ?: error("$name has no format")
        if (format != OneiosSystem.FORMAT) {
            error("$name is format $format; this version of OneOS reads format ${OneiosSystem.FORMAT}" +
                if (format > OneiosSystem.FORMAT) " (update OneOS)" else "")
        }
        val version = word("version", required = true)!!
        val want = if (kind == OneiosKind.RUNTIME) "oneios-runtime" else "oneios-image"
        root["name"]?.let { if (it != want) error("$name is a '${it.toString().take(40)}', not a $want") }
        val list = root["files"] as? List<*> ?: error("$name has no files list")
        if (list.isEmpty()) error("$name lists no files")
        if (list.size > MAX_FILES) error("$name lists ${list.size} files (at most $MAX_FILES)")
        val seen = HashSet<String>()
        val files = list.mapIndexed { i, item ->
            val o = item as? Map<*, *> ?: error("$name: files[$i] is not an object")
            val path = o["path"] as? String ?: error("$name: files[$i] has no path")
            if (!validPath(path)) error("$name: '${path.take(80)}' is not a plain relative path")
            if (path == name) error("$name lists itself")
            if (!seen.add(path)) error("$name lists $path twice")
            // A file where another entry needs a folder ("a" and "a/b").
            val size = o["size"] as? Long ?: error("$name: $path has no size")
            if (size !in 0..MAX_FILE_BYTES) error("$name: $path has size $size")
            val sha = (o["sha256"] as? String)?.lowercase(Locale.ROOT) ?: error("$name: $path has no sha256")
            if (!HEX64.matches(sha)) error("$name: $path has a malformed sha256")
            val mode = when (val m = o["mode"]) {
                null -> "0644"
                "0644", "0755" -> m as String
                else -> error("$name: $path has mode '$m' (0644 or 0755)")
            }
            OneiosFile(path, size, sha, mode)
        }
        for (f in files) {
            var dir = f.path.substringBeforeLast('/', "")
            while (dir.isNotEmpty()) {
                if (dir in seen) error("$name: $dir is both a file and a folder")
                dir = dir.substringBeforeLast('/', "")
            }
        }
        when (kind) {
            OneiosKind.RUNTIME -> {
                val abi = int("session_abi") ?: error("$name has no session_abi")
                val x = root["xnuhost"] as? String ?: error("$name names no xnuhost: this runtime cannot start iOS yet")
                val xf = files.firstOrNull { it.path == x } ?: error("$name: xnuhost '$x' is not one of its files")
                if (xf.mode != "0755") error("$name: xnuhost $x is not mode 0755")
                val arch = root["arch"]
                if (arch != null && arch != "arm64") error("$name: arch '$arch' is not arm64")
                val formats = (root["image_formats"] as? List<*> ?: error("$name has no image_formats")).map {
                    (it as? Long)?.takeIf { v -> v in 0..9999 }?.toInt() ?: error("$name: image_formats holds '$it'")
                }
                if (formats.isEmpty()) error("$name: image_formats is empty")
                val placeholder = when (val v = root["placeholder"]) {
                    null -> false
                    is Boolean -> v
                    else -> error("$name: placeholder is not true or false")
                }
                OneiosManifest(
                    kind, format, version, files, sessionAbi = abi, xnuhost = x, imageFormats = formats.distinct(),
                    placeholder = placeholder, minOneosFork = word("min_oneos_fork", required = false),
                    kernel = kernelOf(root, name), kernels = kernelsOf(root, name),
                )
            }
            OneiosKind.IMAGE -> OneiosManifest(
                kind, format, version, files,
                build = word("build", required = false),
                device = (root["device"] as? String)?.take(40),
                os = (root["os"] as? String)?.take(40),
            )
        }
    }

    /**
     * Verifies what was found ([seen]) against [manifest]: every listed file
     * present once with its size and SHA-256, and nothing else. Empty = verified.
     */
    fun verify(manifest: OneiosManifest, seen: List<OneiosSeen>): List<String> {
        val problems = mutableListOf<String>()
        val byPath = HashMap<String, OneiosSeen>()
        for (s in seen) {
            if (s.path == manifest.kind.manifestName) continue
            if (byPath.put(s.path, s) != null) problems += "${s.path} is there twice"
            val want = manifest.file(s.path)
            when {
                want == null -> problems += "${s.path} is not in ${manifest.kind.manifestName}"
                want.size != s.size -> problems += "${s.path} is ${s.size} bytes, ${manifest.kind.manifestName} says ${want.size}"
                want.sha256 != s.sha256.lowercase(Locale.ROOT) ->
                    problems += "${s.path} does not match its SHA-256 (${s.sha256.take(12)}..., expected ${want.sha256.take(12)}...)"
            }
        }
        for (f in manifest.files) if (f.path !in byPath) problems += "${f.path} is missing"
        return problems
    }

    /**
     * "0.4.74" against a runtime's `min_oneos_fork`: [have] is at least [need], number by number
     * (a suffix such as "-s25" is not counted). A version that does not parse is not enough.
     */
    fun versionAtLeast(have: String, need: String): Boolean {
        fun parts(v: String): List<Int>? = v.substringBefore('-').split('.').map { it.toIntOrNull() ?: return null }
        val h = parts(have) ?: return false
        val n = parts(need) ?: return false
        for (i in 0 until maxOf(h.size, n.size)) {
            val a = h.getOrElse(i) { 0 }
            val b = n.getOrElse(i) { 0 }
            if (a != b) return a > b
        }
        return true
    }

    /**
     * `runtime.json`'s `kernel` object, or null when it has none. Unknown keys
     * are ignored (the packer may add its own); everything a kernel update acts
     * on is checked. A present but malformed object refuses the manifest: a
     * kernel the app cannot name must never be staged as updatable.
     */
    private fun kernelOf(root: Map<*, *>, name: String): OneiosKernel? =
        root["kernel"]?.let { kernelObject(it, name, "kernel", build = false) }

    /**
     * `runtime.json`'s `kernels` array (OneiOS 2026-11-25): one object per Apple build, each shaped like `kernel`
     * plus its `build` ("24A446", "24B156"), each build once. Empty when there is none (every runtime before it);
     * malformed refuses the manifest, as a malformed `kernel` does.
     */
    private fun kernelsOf(root: Map<*, *>, name: String): List<OneiosKernel> {
        val list = root["kernels"] ?: return emptyList()
        list as? List<*> ?: error("$name: kernels is not a list")
        if (list.size > 16) error("$name: kernels holds ${list.size} kernels (at most 16)")
        val got = list.mapIndexed { i, o -> kernelObject(o, name, "kernels[$i]", build = true) }
        got.groupBy { it.build }.filterValues { it.size > 1 }.keys.firstOrNull()?.let { error("$name: kernels names $it twice") }
        return got
    }

    private val BUILD = Regex("^[0-9A-Z]{3,20}$")

    private fun kernelObject(v: Any?, name: String, what: String, build: Boolean): OneiosKernel {
        val o = v as? Map<*, *> ?: error("$name: $what is not an object")
        fun text(key: String, max: Int = 120): String {
            val s = o[key] as? String ?: error("$name: $what has no $key")
            if (s.length !in 1..max || s.any { it !in 'A'..'Z' && it !in 'a'..'z' && it !in '0'..'9' && it !in "._-/+" }) {
                error("$name: $what $key '${s.take(40)}' is not plain")
            }
            return s
        }
        return OneiosKernel(
            path = text("path").also { if (!validPath(it)) error("$name: $what path '$it' is not a plain relative path") },
            buildId = text("build_id"),
            sha256 = text("sha256", 64).lowercase(Locale.ROOT).also { if (!HEX64.matches(it)) error("$name: $what sha256 is malformed") },
            xnu = text("xnu"),
            profile = text("profile"),
            record = text("record").also { if (!validPath(it)) error("$name: $what record '$it' is not a plain relative path") },
            build = if (build) text("build", 20).also { if (!BUILD.matches(it)) error("$name: $what build '$it' is not an Apple build") } else null,
        )
    }

    /**
     * Whether the staged pair can start a session, as `oneios_switch.sh` decides it
     * again as root: the runtime speaks this build's session ABI and boots the
     * image set's format. null = yes; else the one line why not.
     */
    fun pairProblem(runtime: OneiosManifest?, image: OneiosManifest?): String? = when {
        runtime == null -> "No OneiOS runtime is staged: xnuhost, the program that runs iOS, comes with it."
        runtime.sessionAbi != OneiosSystem.SESSION_ABI ->
            "The runtime ${runtime.version} speaks session ABI ${runtime.sessionAbi}, this OneOS speaks ${OneiosSystem.SESSION_ABI}."
        runtime.placeholder -> "The runtime ${runtime.version} carries a placeholder instead of xnuhost: OneiOS has not built xnuhost yet."
        image == null -> "No iOS image set is staged: import the one you built with OneiOS's scripts."
        image.format !in runtime.imageFormats ->
            "The image set is format ${image.format}; the runtime ${runtime.version} boots format(s) ${runtime.imageFormats.joinToString(", ")}."
        else -> null
    }

    /**
     * Whether a phone-built kernel.kc may be activated for the staged image
     * set (docs/oneios.md, "Kernel updates"): the app's fail-fast check with a
     * plain message. null = yes. Root's `finish kernel` checks the rest itself,
     * where both sides live independently: the collection's build record names
     * the xnu and the kernelcache it was paired from, against the staged
     * runtime's list and the staged kernelcache. What has no versioned surface
     * in OneiOS's oneos/interface.md is not checked anywhere: the switch's
     * command line is fixed (no per-kernel boot-args or tunables exist) and
     * the bridges ship inside the runtime, so a kernel from the staged
     * runtime's xnu needs no config change; a new runtime carries its own
     * session ABI, image formats and `min_oneos_fork`, which [pairProblem] and
     * the staging checks already enforce.
     */
    fun kernelProblem(
        /** Apple's build of the staged image set (`manifest.json`'s `build`), e.g. "24A446"; null = none staged. */
        imageBuild: String?,
        /** The prelink inputs the app carries for the set's kernel build (`kb/kb.json`, `kb-24B156/kb.json`): the Apple build they pair. */
        kb: OneiosKb,
        /** SHA-256 of the staged `kb/kernelcache.macho` (or `kb-<BUILD>/`'s, root's `kbset` line); null = not staged. */
        kernelcacheSha256: String?,
        /** The staged runtime carries a kernel for that build (`kernel`, or its `kernels[]` entry). */
        runtimeHasKernel: Boolean,
    ): String? = updateProblem(imageBuild, kb, runtimeHasKernel) ?: when {
        kernelcacheSha256 == null -> "Apple's kernelcache is not staged: run Update the kernel, which downloads it from Apple."
        !kernelcacheSha256.equals(kb.kernelcacheSha256, ignoreCase = true) ->
            "The staged kernelcache is not the ${kb.build} one the profile pins: run Update the kernel, which downloads it from Apple."
        else -> null
    }

    /**
     * Whether Update the kernel may start ([kernelProblem] without the kernelcache: the update downloads it from
     * Apple itself). null = yes. [kb] is the app's pairing files of the staged set's kernel build
     * ([OneiosImageChoice.kernelBuildOf]: `kb/` for 24A446 and the A56's 20F66, `kb-24B156/` for iOS 27.2.1);
     * [runtimeHasKernel]: the staged runtime carries a kernel for that build (`kernel` for 24A446, its `kernels[]`
     * entry for another one).
     */
    fun updateProblem(imageBuild: String?, kb: OneiosKb, runtimeHasKernel: Boolean): String? = when {
        imageBuild == null -> "No iOS image set is staged: import the one you built with OneiOS's scripts."
        OneiosImageChoice.kernelBuildOf(imageBuild) != kb.build ->
            "The prelink inputs pair Apple's build ${kb.build}, but the staged image set is $imageBuild: a kernel built from them must never boot it."
        !runtimeHasKernel && kb.build == OneiosImageChoice.IOS_27.build ->
            "The staged runtime carries no kernel (its runtime.json has no kernel): update the runtime first."
        !runtimeHasKernel -> noBuildKernel(imageBuild)
        else -> null
    }

    /**
     * A staged runtime with no kernel for a set of [imageBuild] (one before `runtime.json`'s `kernels`, or one whose
     * `kernels` has no entry of it), in the words the app has for a runtime too old for something.
     */
    fun noBuildKernel(imageBuild: String): String {
        val name = OneiosImageChoice.ofBuild(imageBuild)?.title ?: imageBuild
        return "The staged OneiOS runtime has no kernel for $name (its runtime.json has no kernels entry for it): get the latest OneiOS runtime."
    }

    /** The staged runtime's kernel build id against a release's: null when nothing newer is offered, else the one line what it carries. */
    fun kernelUpdate(stagedBuildId: String?, latest: OneiosKernel?): String? = when {
        latest == null -> "The release's runtime carries no kernel: there is nothing to rebuild from."
        stagedBuildId == null -> "The release's runtime carries kernel ${latest.buildId} (${latest.xnu}): stage that runtime, then rebuild the kernel on this phone."
        stagedBuildId == latest.buildId -> null
        else -> "The release's runtime carries kernel ${latest.buildId} (${latest.xnu}); the staged one is $stagedBuildId."
    }
}

/**
 * The prelink inputs the app carries for a phone-built kernel, of one Apple build (`assets/kb/kb.json` for 24A446,
 * `assets/kb-24B156/kb.json` for iOS 27.2.1: [OneiosImageChoice.kbDirOf]): what they pair and their hashes.
 */
data class OneiosKb(
    val build: String,
    val device: String,
    val kernelcacheSha256: String,
    val files: Map<String, String>,
) {
    /** The files `kbinput` gets, in the order it gets them: every file kb.json lists, sorted by name. */
    val names: List<String> get() = files.keys.sorted()

    companion object {
        /** The input files the stage needs, in the order `serve prelink` takes shape from them. */
        val INPUTS: List<String> = listOf(
            "kernelcache.macho", "profile.toml", "reviewed.json", "pairs.json", "stubs.json",
            "lead.json", "user.json",
        )

        /**
         * The pairing files' format (`kb.json`'s `kb`): 2 since 2026-11-22, the matcher folder `match/` with its
         * reviewed fixtures alone (1 also had XnuPrelink's three Python sources, for the matcher signature of
         * runtimes up to 0.1.13). A tool reads the format its `hello`'s `kb` names (absent: 1).
         */
        const val FORMAT = 2

        /** What `kb/kb.json` (24A446) pins (everything but the Apple kernelcache, which the kernel update downloads from Apple). */
        val PINNED: List<String> = (INPUTS - "kernelcache.macho") + "match/fixtures/fileset-23F84-symbols.json" +
            "match/fixtures/fileset-24A446-symbols.json" + "match/fixtures/fileset-26C5035r-symbols.json"

        /**
         * What every build's kb.json pins at least: the six inputs beside the kernelcache; the matcher's fixtures
         * are each build's own (at least one), 24A446's exactly [PINNED].
         */
        val CORE: List<String> = INPUTS - "kernelcache.macho"
        private val HEX64 = Regex("^[0-9a-f]{64}$")

        fun parse(text: String): Result<OneiosKb> = runCatching {
            val root = JsonRead.parse(text) as? Map<*, *> ?: error("kb.json is not a JSON object")
            if (root["kb"] != FORMAT.toLong()) error("kb.json has no kb $FORMAT")
            val build = root["build"] as? String ?: error("kb.json has no build")
            if (!Regex("^[0-9A-Z]{3,20}$").matches(build)) error("kb.json build '$build' is not plain")
            val device = root["device"] as? String ?: error("kb.json has no device")
            if (device.length !in 1..40) error("kb.json device is not plain")
            val pin = (root["kernelcache_sha256"] as? String)?.lowercase(java.util.Locale.ROOT)
                ?: error("kb.json has no kernelcache_sha256")
            if (!HEX64.matches(pin)) error("kb.json kernelcache_sha256 is malformed")
            val files = root["files"] as? Map<*, *> ?: error("kb.json has no files")
            if (files.isEmpty()) error("kb.json lists no files")
            val got = files.entries.associate { (k, v) ->
                val name = k as? String ?: error("kb.json names a file that is not a string")
                if (!OneiosManifests.validPath(name)) error("kb.json file '$name' is not a plain relative path")
                if (name == "kernelcache.macho" || !OneiosKbFiles.allowed(name)) error("kb.json file '$name' is not one root's kbinput takes")
                val sha = (v as? String)?.lowercase(java.util.Locale.ROOT) ?: error("kb.json file '$name' has no SHA-256")
                if (!HEX64.matches(sha)) error("kb.json file '$name' has a malformed SHA-256")
                name to sha
            }
            for (need in if (build == OneiosImageChoice.IOS_27.build) PINNED else CORE) {
                if (need !in got) error("kb.json lists no $need (the phone's prelink needs it)")
            }
            if (got.keys.none { it.startsWith("match/") }) error("kb.json lists no matcher file (match/)")
            OneiosKb(build, device, pin, got)
        }
    }
}

/**
 * The kernel-build input files `kbinput` takes (assets/kb/, the root script's allowlist); a test matches them with
 * kb.json. [NAMES] is 24A446's set; another build's kb (`kb-24B156`) may name other matcher fixtures ([allowed]).
 */
object OneiosKbFiles {
    val NAMES: Set<String> = setOf(
        "kernelcache.macho", "profile.toml", "reviewed.json", "pairs.json", "stubs.json",
        "lead.json", "user.json", "match/fixtures/fileset-23F84-symbols.json",
        "match/fixtures/fileset-24A446-symbols.json", "match/fixtures/fileset-26C5035r-symbols.json",
    )

    /** Root's `kb_name`: the seven inputs, or a matcher fixture `match/fixtures/fileset-<id>-symbols.json` (id: 1 to 20 letters and digits). */
    private val FIXTURE = Regex("^match/fixtures/fileset-[0-9A-Za-z]{1,20}-symbols\\.json$")

    fun allowed(name: String): Boolean = name in OneiosKb.INPUTS || FIXTURE.matches(name)
}
/** The runtime package of one OneiOS release: the asset to download and the file holding its SHA-256. */
data class OneiosRelease(
    val tag: String,
    val version: String,
    val assetName: String,
    val assetUrl: String,
    val assetBytes: Long,
    val sha256Url: String,
)

/**
 * OneiOS's releases (github.com/akshaynexus/OneiOS): they carry only OneiOS's
 * own code. The runtime is the asset `oneios-runtime-<version>-arm64.tar.zst`
 * with `<that name>.sha256` beside it. The latest release, or a pinned tag.
 */
object OneiosReleases {
    const val REPO = "akshaynexus/OneiOS"
    const val PAGE_URL = "https://github.com/$REPO/releases"
    const val LATEST_API = "https://api.github.com/repos/$REPO/releases/latest"
    private const val DOWNLOAD_PREFIX = "https://github.com/$REPO/releases/download/"

    /** Larger than any runtime package (xnuhost, the stub, the host drivers' user side). */
    const val MAX_ASSET_BYTES = 512L * 1024 * 1024

    val ASSET = Regex("^oneios-runtime-([0-9A-Za-z][0-9A-Za-z._-]{0,39})-arm64\\.tar\\.zst$")
    private val TAG = Regex("^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$")
    private val HEX64 = Regex("^[0-9a-f]{64}$")

    fun validTag(tag: String): Boolean = TAG.matches(tag) && !tag.contains("..")

    /** The API address of the release to read: [tag]'s, or the latest when null or blank. */
    fun apiUrl(tag: String?): String {
        val t = tag?.trim().orEmpty()
        if (t.isEmpty()) return LATEST_API
        require(validTag(t)) { "'$t' is not a release tag" }
        return "https://api.github.com/repos/$REPO/releases/tags/$t"
    }

    /** What to say when GitHub answers 404 for [tag] (null: the latest). */
    fun noRelease(tag: String?): String =
        if (tag.isNullOrBlank()) "OneiOS has not published a release yet, so there is no runtime to download. " +
            "If you built one yourself, use \"I have the file\"."
        else "OneiOS has no release named $tag."

    /**
     * The runtime package in GitHub's release JSON [text], or why there is none.
     * Only assets of this repository's own releases are taken.
     */
    fun parse(text: String): Result<OneiosRelease> = runCatching {
        val root = JsonRead.parse(text) as? Map<*, *> ?: error("the release answer is not a JSON object")
        val tag = root["tag_name"] as? String ?: error("the release answer names no tag")
        if (!validTag(tag)) error("release tag '${tag.take(40)}'")
        val assets = (root["assets"] as? List<*>).orEmpty().mapNotNull { it as? Map<*, *> }
        fun url(a: Map<*, *>): String? = (a["browser_download_url"] as? String)?.takeIf { it.startsWith(DOWNLOAD_PREFIX) }
        val candidates = assets.filter { a -> (a["name"] as? String)?.let(ASSET::matches) == true }
        if (candidates.isEmpty()) error("release $tag has no runtime package (oneios-runtime-<version>-arm64.tar.zst)")
        if (candidates.size > 1) error("release $tag has ${candidates.size} runtime packages")
        val a = candidates.single()
        val name = a["name"] as String
        val bytes = a["size"] as? Long ?: error("$name has no size")
        if (bytes !in 1..MAX_ASSET_BYTES) error("$name is $bytes bytes")
        val assetUrl = url(a) ?: error("$name is not a file of $REPO's releases")
        val sha = assets.firstOrNull { it["name"] == "$name.sha256" } ?: error("release $tag has no $name.sha256")
        val shaUrl = url(sha) ?: error("$name.sha256 is not a file of $REPO's releases")
        OneiosRelease(tag, ASSET.matchEntire(name)!!.groupValues[1], name, assetUrl, bytes, shaUrl)
    }

    /**
     * The SHA-256 in a `.sha256` file: one `sha256sum` line (`<hex>  <name>`), or
     * the bare hash. A line naming another file than [assetName] is not it.
     */
    fun parseSha256(text: String, assetName: String): String? {
        val lines = text.lineSequence().map { it.trim() }.filter { it.isNotEmpty() && !it.startsWith("#") }.toList()
        if (lines.size != 1) return null
        val parts = lines[0].split(Regex("\\s+"))
        val hex = parts[0].lowercase(Locale.ROOT)
        if (!HEX64.matches(hex)) return null
        return when (parts.size) {
            1 -> hex
            2 -> hex.takeIf { parts[1].removePrefix("*").substringAfterLast('/') == assetName }
            else -> null
        }
    }
}

/**
 * A strict reader for the small JSON files this app is handed (a manifest,
 * GitHub's release answer): objects as `Map<String, Any?>` (a key twice is an
 * error), arrays as `List<Any?>`, strings, whole numbers as `Long`, others as
 * `Double`, `true`/`false`/`null`. No serialization library in :core:model.
 */
object JsonRead {
    private const val MAX_DEPTH = 32

    fun parse(text: String): Any? {
        val p = Parser(text)
        p.ws()
        val v = p.value(0)
        p.ws()
        if (p.i != text.length) p.fail("text after the value")
        return v
    }

    private class Parser(val s: String) {
        var i = 0

        fun fail(what: String): Nothing = throw IllegalArgumentException("JSON: $what at ${i.coerceAtMost(s.length)}")

        fun ws() {
            while (i < s.length && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++
        }

        fun value(depth: Int): Any? {
            if (depth > MAX_DEPTH) fail("nested too deep")
            if (i >= s.length) fail("unexpected end")
            return when (val c = s[i]) {
                '{' -> obj(depth)
                '[' -> arr(depth)
                '"' -> str()
                't' -> lit("true", true)
                'f' -> lit("false", false)
                'n' -> lit("null", null)
                else -> if (c == '-' || c in '0'..'9') num() else fail("unexpected '$c'")
            }
        }

        private fun lit(word: String, v: Any?): Any? {
            if (!s.startsWith(word, i)) fail("unexpected text")
            i += word.length
            return v
        }

        private fun obj(depth: Int): Map<String, Any?> {
            val out = LinkedHashMap<String, Any?>()
            i++
            ws()
            if (i < s.length && s[i] == '}') { i++; return out }
            while (true) {
                ws()
                if (i >= s.length || s[i] != '"') fail("expected a key")
                val k = str()
                ws()
                if (i >= s.length || s[i] != ':') fail("expected ':'")
                i++
                ws()
                if (out.containsKey(k)) fail("key '$k' twice")
                out[k] = value(depth + 1)
                ws()
                if (i >= s.length) fail("unexpected end")
                when (s[i++]) {
                    ',' -> continue
                    '}' -> return out
                    else -> { i--; fail("expected ',' or '}'") }
                }
            }
        }

        private fun arr(depth: Int): List<Any?> {
            val out = ArrayList<Any?>()
            i++
            ws()
            if (i < s.length && s[i] == ']') { i++; return out }
            while (true) {
                ws()
                out += value(depth + 1)
                ws()
                if (i >= s.length) fail("unexpected end")
                when (s[i++]) {
                    ',' -> continue
                    ']' -> return out
                    else -> { i--; fail("expected ',' or ']'") }
                }
            }
        }

        private fun str(): String {
            val out = StringBuilder()
            i++
            while (true) {
                if (i >= s.length) fail("unterminated string")
                val c = s[i++]
                when {
                    c == '"' -> return out.toString()
                    c == '\\' -> {
                        if (i >= s.length) fail("unterminated escape")
                        when (val e = s[i++]) {
                            '"', '\\', '/' -> out.append(e)
                            'n' -> out.append('\n')
                            'r' -> out.append('\r')
                            't' -> out.append('\t')
                            'b' -> out.append('\b')
                            'f' -> out.append('\u000c')
                            'u' -> {
                                if (i + 4 > s.length) fail("short \\u escape")
                                val code = s.substring(i, i + 4).toIntOrNull(16) ?: fail("bad \\u escape")
                                out.append(code.toChar())
                                i += 4
                            }
                            else -> { i--; fail("bad escape") }
                        }
                    }
                    c < ' ' -> { i--; fail("control character in a string") }
                    else -> out.append(c)
                }
            }
        }

        private fun num(): Any {
            val start = i
            if (s[i] == '-') i++
            while (i < s.length && s[i] in '0'..'9') i++
            var whole = true
            if (i < s.length && s[i] == '.') {
                whole = false
                i++
                while (i < s.length && s[i] in '0'..'9') i++
            }
            if (i < s.length && (s[i] == 'e' || s[i] == 'E')) {
                whole = false
                i++
                if (i < s.length && (s[i] == '+' || s[i] == '-')) i++
                while (i < s.length && s[i] in '0'..'9') i++
            }
            val t = s.substring(start, i)
            return if (whole) t.toLongOrNull() ?: run { i = start; fail("number out of range") }
            else t.toDoubleOrNull() ?: run { i = start; fail("bad number") }
        }
    }
}

/**
 * A streaming tar reader for the two packages (ustar, with pax `x`/`g` headers
 * and GNU long names): regular files and folders only. A link, a device or any
 * other member is an error, never skipped.
 */
class TarReader(private val input: InputStream) {
    class Entry(val name: String, val size: Long, val directory: Boolean)

    private var remaining = 0L
    private var padding = 0L

    /** The next member, or null at the end of the archive. Skips what is left of the one before. */
    fun next(): Entry? {
        skipFully(remaining + padding)
        remaining = 0
        padding = 0
        var longName: String? = null
        var paxPath: String? = null
        var paxSize: Long? = null
        while (true) {
            val h = ByteArray(512)
            if (!readBlock(h)) return null
            if (h.all { it.toInt() == 0 }) return null
            checksum(h)
            val size = number(h, 124, 12)
            val type = h[156].toInt().toChar()
            val pad = (512 - size % 512) % 512
            when (type) {
                'x', 'g', 'L' -> {
                    if (size > 1024 * 1024) throw IOException("tar: an extended header of $size bytes")
                    val body = ByteArray(size.toInt())
                    readFully(body)
                    skipFully(pad)
                    when (type) {
                        'L' -> longName = body.toString(Charsets.UTF_8).trimEnd('\u0000')
                        'x' -> for ((k, v) in pax(body)) {
                            if (k == "path") paxPath = v
                            if (k == "size") paxSize = v.toLongOrNull() ?: throw IOException("tar: pax size '$v'")
                        }
                    }
                }
                '0', '\u0000', '5' -> {
                    val prefix = text(h, 345, 155)
                    val base = text(h, 0, 100)
                    val name = paxPath ?: longName ?: if (prefix.isEmpty()) base else "$prefix/$base"
                    val dir = type == '5' || name.endsWith("/")
                    val real = if (dir) 0L else paxSize ?: size
                    remaining = real
                    padding = (512 - real % 512) % 512
                    return Entry(name.removePrefix("./").trimEnd('/'), real, dir)
                }
                else -> throw IOException("tar: '${text(h, 0, 100).take(80)}' is a link or a special file (type '$type'); only files and folders are allowed")
            }
        }
    }

    /** The current member's bytes: ends after its size. Read it before [next], or it is skipped. */
    fun data(): InputStream = object : InputStream() {
        override fun read(): Int {
            val b = ByteArray(1)
            return if (read(b, 0, 1) < 0) -1 else b[0].toInt() and 0xff
        }

        override fun read(b: ByteArray, off: Int, len: Int): Int {
            if (remaining <= 0) return -1
            val n = input.read(b, off, minOf(len.toLong(), remaining).toInt())
            if (n < 0) throw EOFException("tar: the archive ends inside a file")
            remaining -= n
            return n
        }
    }

    private fun pax(body: ByteArray): List<Pair<String, String>> {
        val out = mutableListOf<Pair<String, String>>()
        var i = 0
        while (i < body.size) {
            var j = i
            while (j < body.size && body[j] != ' '.code.toByte()) j++
            val len = String(body, i, j - i, Charsets.US_ASCII).toIntOrNull() ?: throw IOException("tar: malformed pax header")
            if (len <= j - i + 1 || i + len > body.size) throw IOException("tar: malformed pax header")
            val rec = String(body, j + 1, len - (j - i) - 2, Charsets.UTF_8)
            val eq = rec.indexOf('=')
            if (eq > 0) out += rec.substring(0, eq) to rec.substring(eq + 1)
            i += len
        }
        return out
    }

    private fun checksum(h: ByteArray) {
        val want = number(h, 148, 8)
        var sum = 0L
        for (i in 0 until 512) sum += if (i in 148..155) 32 else (h[i].toInt() and 0xff)
        if (sum != want) throw IOException("tar: bad header checksum (not a tar archive, or damaged)")
    }

    private fun text(h: ByteArray, off: Int, len: Int): String {
        var end = off
        while (end < off + len && h[end].toInt() != 0) end++
        return String(h, off, end - off, Charsets.UTF_8)
    }

    /** Octal, or GNU's base-256 for sizes over 8 GiB. */
    private fun number(h: ByteArray, off: Int, len: Int): Long {
        if (h[off].toInt() and 0x80 != 0) {
            var v = 0L
            for (i in off + 1 until off + len) {
                if (v > (Long.MAX_VALUE shr 8)) throw IOException("tar: number too large")
                v = (v shl 8) or (h[i].toLong() and 0xff)
            }
            return v
        }
        val t = text(h, off, len).trim()
        if (t.isEmpty()) return 0
        return t.toLongOrNull(8) ?: throw IOException("tar: malformed number '$t'")
    }

    private fun readBlock(b: ByteArray): Boolean {
        var n = 0
        while (n < b.size) {
            val k = input.read(b, n, b.size - n)
            if (k < 0) {
                if (n == 0) return false
                throw EOFException("tar: the archive ends inside a header")
            }
            n += k
        }
        return true
    }

    private fun readFully(b: ByteArray) {
        var n = 0
        while (n < b.size) {
            val k = input.read(b, n, b.size - n)
            if (k < 0) throw EOFException("tar: the archive ends inside a header")
            n += k
        }
    }

    private fun skipFully(count: Long) {
        var left = count
        val buf = ByteArray(1 shl 16)
        while (left > 0) {
            val k = input.read(buf, 0, minOf(left, buf.size.toLong()).toInt())
            if (k < 0) throw EOFException("tar: the archive ends inside a file")
            left -= k
        }
    }
}

/**
 * Reads a runtime package or an image set (the tar inside the `.tar.zst`; the
 * caller decompresses):
 *  1. the manifest, at the top or under one top folder: [manifestFirst] when it
 *     is the archive's first file (OneiOS packs both packages so), and the
 *     same reader then goes on, one pass; otherwise [readManifest], which finds
 *     it anywhere, and a second pass over the file;
 *  2. [unpack]: hands every listed file to the sink while hashing it, and
 *     refuses anything the manifest does not list, a wrong size, a wrong
 *     SHA-256 and a missing file.
 * Root checks each file's size and SHA-256 again as it writes it.
 */
object OneiosPackage {
    class Problem(message: String) : IOException(message)

    /** Where the manifest was found: [prefix] is "" or "<top folder>/". */
    data class Found(val prefix: String, val text: String)

    fun interface Sink {
        /** Must read [data] to its end; [file] is the manifest's entry for it. */
        fun file(file: OneiosFile, data: InputStream)
    }

    /**
     * Like [Sink], for a reader that hashes on its own (or leaves it to root):
     * returns the SHA-256 of what it read, or null when it did not hash, and then
     * root's check of the file is the only one.
     */
    fun interface Copier {
        fun file(file: OneiosFile, data: InputStream): String?
    }

    private fun manifestOf(reader: TarReader, e: TarReader.Entry, kind: OneiosKind): Found? {
        val parts = e.name.split('/')
        if (parts.last() != kind.manifestName || parts.size > 2) return null
        if (e.size > OneiosManifests.MAX_MANIFEST_BYTES) throw Problem("${kind.manifestName} is too long")
        val text = reader.data().readBytes().toString(Charsets.UTF_8)
        return Found(if (parts.size == 2) parts[0] + "/" else "", text)
    }

    fun readManifest(tar: InputStream, kind: OneiosKind): Found = readManifest(TarReader(tar), kind)

    /** The manifest wherever it is from where [reader] stands; the reader stops behind it. */
    fun readManifest(reader: TarReader, kind: OneiosKind): Found {
        while (true) {
            val e = reader.next() ?: throw Problem("no ${kind.manifestName} in this file: it is not a ${kind.label}")
            if (e.directory) continue
            return manifestOf(reader, e, kind) ?: continue
        }
    }

    /**
     * The manifest when it is the archive's first file, as OneiOS packs both
     * packages: [reader] then stands behind it and [unpack] goes on from there,
     * so the archive is read (and decompressed) once. Null when another file
     * comes first: read the archive again with [readManifest].
     */
    fun manifestFirst(reader: TarReader, kind: OneiosKind): Found? {
        while (true) {
            val e = reader.next() ?: throw Problem("no ${kind.manifestName} in this file: it is not a ${kind.label}")
            if (e.directory) continue
            return manifestOf(reader, e, kind)
        }
    }

    /** Returns what was unpacked (every listed file, verified). [progress] gets the bytes of files done so far. */
    fun unpack(
        tar: InputStream,
        manifest: OneiosManifest,
        prefix: String,
        sink: Sink,
        progress: (Long) -> Unit = {},
    ): List<OneiosSeen> = unpack(TarReader(tar), manifest, prefix, Copier { f, data ->
        val md = MessageDigest.getInstance("SHA-256")
        sink.file(f, object : InputStream() {
            override fun read(): Int {
                val b = ByteArray(1)
                return if (read(b, 0, 1) < 0) -1 else b[0].toInt() and 0xff
            }

            override fun read(b: ByteArray, off: Int, len: Int): Int {
                val n = data.read(b, off, len)
                if (n > 0) md.update(b, off, n)
                return n
            }
        })
        Hashes.hex(md.digest())
    }, progress)

    /**
     * The same from where [reader] stands (behind the manifest of a single
     * pass, or at the start). Each listed member goes to [copier], which has to
     * read it to its end; a member the manifest does not list, one listed twice,
     * a wrong size, a wrong SHA-256 (when [copier] hashed) and a missing file
     * end it. The reader refuses links and devices by itself.
     */
    fun unpack(
        reader: TarReader,
        manifest: OneiosManifest,
        prefix: String,
        copier: Copier,
        progress: (Long) -> Unit = {},
    ): List<OneiosSeen> {
        val name = manifest.kind.manifestName
        val seen = ArrayList<OneiosSeen>()
        val done = HashSet<String>()
        var bytes = 0L
        while (true) {
            val e = reader.next() ?: break
            if (!e.name.startsWith(prefix) && e.name + "/" != prefix) {
                throw Problem("${e.name.take(80)} is outside ${prefix.trimEnd('/')}")
            }
            if (e.directory) continue
            val path = e.name.removePrefix(prefix)
            if (path == name) continue
            val want = manifest.file(path) ?: throw Problem("$path is not in $name")
            if (!done.add(path)) throw Problem("$path is in the file twice")
            if (e.size != want.size) throw Problem("$path is ${e.size} bytes, $name says ${want.size}")
            val raw = reader.data()
            val base = bytes
            var read = 0L
            val counting = object : InputStream() {
                override fun read(): Int {
                    val b = ByteArray(1)
                    return if (read(b, 0, 1) < 0) -1 else b[0].toInt() and 0xff
                }

                override fun read(b: ByteArray, off: Int, len: Int): Int {
                    val n = raw.read(b, off, len)
                    if (n > 0) {
                        read += n
                        progress(base + read)
                    }
                    return n
                }
            }
            val sha = copier.file(want, counting)
            if (read != want.size) throw Problem("$path was not read to its end")
            if (sha != null && sha != want.sha256) {
                throw Problem("$path does not match its SHA-256 (${sha.take(12)}..., expected ${want.sha256.take(12)}...)")
            }
            seen += OneiosSeen(path, read, sha ?: want.sha256)
            bytes += read
        }
        val problems = OneiosManifests.verify(manifest, seen)
        if (problems.isNotEmpty()) throw Problem(problems.first() + if (problems.size > 1) " (and ${problems.size - 1} more)" else "")
        return seen
    }
}
