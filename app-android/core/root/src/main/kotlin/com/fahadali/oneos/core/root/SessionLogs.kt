package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.AppInfo
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Json
import com.fahadali.oneos.core.model.RedactionKind
import com.fahadali.oneos.core.model.Redactor
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.OutputStream
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * What the log bundle keeps and drops (docs/app/compat-safety-logs.md
 * section 3.3), on top of [Redactor]: logcat lines of tags that are mostly
 * personal data are dropped whole, file names under shared storage are
 * masked, and screen recordings and screenshots never get in.
 */
object LogRules {
    /** Tags whose lines are dropped (exact). A fix pack may add tags later, never remove these. */
    val DROP_TAGS: Set<String> = setOf(
        "SmsProvider", "TP/SmsProvider", "TP/MmsSmsProvider", "MmsSmsProvider", "GsmInboundSmsHandler",
        "ContactsProvider", "ContactInfoHelper", "Ts43PhoneNumberController", "PhoneNumberOfflineGeocoder",
        "wpa_supplicant", "WiFiPerception", "LocationManagerService", "GnssLocationProvider",
    )

    /** `SIPMSG*`. */
    val DROP_TAG_PREFIXES: List<String> = listOf("SIPMSG")

    /** `*GetUpcomingContactsUseCase`. */
    val DROP_TAG_SUFFIXES: List<String> = listOf("GetUpcomingContactsUseCase")

    /** `*Geofence*`. */
    val DROP_TAG_PARTS: List<String> = listOf("Geofence")

    /** `logcat -v threadtime`: `MM-DD HH:MM:SS.mmm  PID  TID L TAG: message`. */
    private val THREADTIME = Regex("""^\d\d-\d\d \d\d:\d\d:\d\d\.\d+\s+\d+\s+\d+\s+[VDIWEFAS]\s+(.*?)\s*: """)

    /** Media that never goes into a bundle, whatever a list prints. */
    private val NEVER = Regex("""(?i).*\.(mp4|webm|3gp|mkv|png|jpe?g|webp|gif|heic)$""")

    fun tag(line: String): String? = THREADTIME.find(line)?.groupValues?.get(1)

    fun drop(line: String): Boolean {
        val t = tag(line) ?: return false
        return t in DROP_TAGS || DROP_TAG_PREFIXES.any { t.startsWith(it) } ||
            DROP_TAG_SUFFIXES.any { t.endsWith(it) } || DROP_TAG_PARTS.any { t.contains(it) }
    }

    /** A screen recording or a screenshot (by name): never collected. */
    fun neverCollected(name: String): Boolean = NEVER.matches(name)

    /**
     * Network names from `grep -o 'name="...ssid">...'` lines of the Wi-Fi
     * config stores (the logs.ssids entry): XML entities decoded, quotes
     * removed, empty and `<unknown ssid>` dropped.
     */
    fun ssids(grepOutput: String): List<String> = grepOutput.lineSequence()
        .mapNotNull { l ->
            val i = l.indexOf('>')
            if (i < 0) null else l.substring(i + 1)
        }
        .map { xmlText(it).trim() }
        .map { if (it.length >= 2 && it.startsWith('"') && it.endsWith('"')) it.substring(1, it.length - 1) else it }
        .filter { it.isNotBlank() && it != "<unknown ssid>" }
        .distinct()
        .toList()

    private fun xmlText(s: String): String =
        s.replace("&quot;", "\"").replace("&apos;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    /** Text every [USER_FILE] match holds. */
    val USER_ROOTS = listOf("/storage/emulated/", "/sdcard", "/data/media/")

    /**
     * A file under shared storage (a name with an extension): the folders
     * stay, the file name is masked.
     */
    val USER_FILE = Regex("""/(?:storage/emulated/\d+|sdcard|data/media/\d+)(?:/[^\s"'/]+)*/([^\s"'/]+\.[^\s"'/.]+)""")
}

/** Counts of what the log redaction did, beyond [Redactor]'s own log. */
class LogStats {
    var droppedLines = 0L
    val droppedByTag = sortedMapOf<String, Long>()
    var maskedFiles = 0L
    var lines = 0L
    var cutLines = 0L
}

/**
 * Redacts a text stream line by line as it arrives (never a whole 20 MB file
 * in memory): drops [LogRules.drop] lines, runs every other line through
 * [Redactor.redactText] and masks shared-storage file names. Lines over
 * [MAX_LINE] bytes are cut there.
 */
class RedactingOutputStream(
    private val out: OutputStream,
    private val file: String,
    private val redactor: Redactor,
    private val stats: LogStats,
    private val fileSalt: ByteArray,
) : OutputStream() {
    private val line = ByteArrayOutputStream(1024)
    private var closed = false

    override fun write(b: Int) {
        if (b == '\n'.code) emit() else {
            line.write(b)
            if (line.size() >= MAX_LINE) {
                stats.cutLines++
                emit()
            }
        }
    }

    override fun write(b: ByteArray, off: Int, len: Int) {
        var start = off
        val end = off + len
        for (i in off until end) {
            if (b[i] == '\n'.code.toByte()) {
                line.write(b, start, i - start)
                emit()
                start = i + 1
            } else if (line.size() + (i - start) >= MAX_LINE) {
                line.write(b, start, i - start)
                stats.cutLines++
                emit()
                start = i
            }
        }
        if (start < end) line.write(b, start, end - start)
    }

    private fun emit() {
        val text = line.toString(Charsets.UTF_8.name()).trimEnd('\r')
        line.reset()
        stats.lines++
        if (LogRules.drop(text)) {
            stats.droppedLines++
            LogRules.tag(text)?.let { stats.droppedByTag[it] = (stats.droppedByTag[it] ?: 0) + 1 }
            return
        }
        var s = redactor.redactText(text, file)
        // The literal text USER_FILE needs first: most lines name no user file.
        if (LogRules.USER_ROOTS.none { s.contains(it) }) {
            out.write(s.toByteArray(Charsets.UTF_8))
            out.write('\n'.code)
            return
        }
        s = LogRules.USER_FILE.replace(s) { m ->
            val name = m.groupValues[1]
            if (name.startsWith("<")) {
                m.value
            } else {
                stats.maskedFiles++
                m.value.substring(0, m.value.length - name.length) + fileToken(name)
            }
        }
        out.write(s.toByteArray(Charsets.UTF_8))
        out.write('\n'.code)
    }

    private fun fileToken(name: String): String {
        val md = MessageDigest.getInstance("SHA-256")
        md.update(fileSalt)
        md.update(name.toByteArray(Charsets.UTF_8))
        return "<file:${Hashes.hex(md.digest()).take(6)}>"
    }

    override fun flush() = out.flush()

    override fun close() {
        if (closed) return
        closed = true
        if (line.size() > 0) emit()
        out.close()
    }

    companion object {
        const val MAX_LINE = 64 * 1024

        fun newFileSalt(): ByteArray = ByteArray(16).also { SecureRandom().nextBytes(it) }
    }
}

/**
 * How the last session ended (docs/app/compat-safety-logs.md section 3.2).
 * [label] is the technical one (the log bundle's summary); [title] is what
 * Home and Last session say, with the system's name.
 */
enum class OutcomeKind(val label: String) {
    USER_RETURN("Returned with Volume Up+Down"),
    /** Back to One UI in the other system's OneOS app or its Quick Settings tile (`app:app`, `app:tile`). */
    APP_RETURN("Returned with Back to One UI"),
    GUEST_REBOOT("The other system asked to restart"),
    GUEST_SHUTDOWN("The other system asked to power off"),
    GUEST_DEAD("The other system stopped"),
    BLACK_SCREEN("The other system showed a black screen"),
    SESSION_LIMIT("Session time limit reached"),
    BOOT_TIMEOUT("The other system did not finish starting"),
    PREPARE_FAILED("The switch stopped while setting up"),
    REFUSED("The switch refused to start"),
    DRY_RUN("Test run finished"),
    HARD_RESET("The phone restarted without the return"),
    UNKNOWN("Not known"),
    ;

    /** The user came back on purpose, or a test run ended as planned. */
    val good: Boolean get() = this == USER_RETURN || this == APP_RETURN || this == DRY_RUN

    /** How it ended, in plain words, for [system] (`{system}`, e.g. "Pixel 11 Fold"). */
    fun title(system: String): String {
        val sys = com.fahadali.oneos.core.model.Sentence.start(system)
        return when (this) {
            USER_RETURN -> "You came back with the volume keys"
            APP_RETURN -> "You came back with Back to One UI"
            GUEST_REBOOT -> "$sys restarted, so OneOS brought you back"
            GUEST_SHUTDOWN -> "$sys turned the phone off"
            GUEST_DEAD -> "$sys stopped working. OneOS brought you back."
            BLACK_SCREEN -> "$sys's screen stayed black. OneOS brought you back."
            SESSION_LIMIT -> "The session time limit was reached"
            BOOT_TIMEOUT -> "$sys didn't finish starting. OneOS brought you back."
            PREPARE_FAILED -> "The switch stopped before $system started"
            REFUSED -> "The switch didn't start. Nothing changed."
            DRY_RUN -> "Test run finished: $system can start"
            HARD_RESET -> "Your phone was force-restarted"
            UNKNOWN -> "We couldn't tell how the session ended"
        }
    }
}

data class ReturnOutcome(
    val kind: OutcomeKind,
    /** Seconds into the session, when the line says. */
    val afterSeconds: Int?,
    /** The log line it was read from. */
    val line: String?,
    val bootReason: String?,
) {
    val title: String get() = kind.label

    val detail: String get() = detail(Images.OTHER_SYSTEM)

    /** The technical detail (Last session, the bundle's summary), naming [system]. */
    fun detail(system: String): String {
        val sys = com.fahadali.oneos.core.model.Sentence.start(system)
        return when (kind) {
            OutcomeKind.USER_RETURN -> "You held Volume Up+Down${after()}; OneOS returned to One UI."
            OutcomeKind.APP_RETURN -> "You tapped Back to One UI in $system${after()}; OneOS returned to One UI."
            OutcomeKind.GUEST_REBOOT -> "$sys asked for a restart${after()} (Restart in its power menu, or a crash); OneOS returned to One UI."
            OutcomeKind.GUEST_SHUTDOWN -> "$sys asked to power off${after()} (power menu, low battery or heat); the phone powered off."
            OutcomeKind.GUEST_DEAD -> "$sys's system stopped${after()}; OneOS returned to One UI by itself."
            OutcomeKind.BLACK_SCREEN -> "The screen stayed black${after()}; OneOS returned to One UI by itself."
            OutcomeKind.SESSION_LIMIT -> "The session reached its time limit${after()}."
            OutcomeKind.BOOT_TIMEOUT -> "$sys was still not started${after()}; OneOS returned to One UI by itself."
            OutcomeKind.PREPARE_FAILED -> "The switch stopped before $system started and returned to One UI."
            OutcomeKind.REFUSED -> "A check of the switch refused before anything changed; One UI kept running."
            OutcomeKind.DRY_RUN -> "Everything was set up and checked, then OneOS returned to One UI without starting $system."
            OutcomeKind.HARD_RESET -> "No return was logged and the phone booted for another reason (${bootReason ?: "unknown"}): a force restart or a crash."
            OutcomeKind.UNKNOWN -> "The logs do not say how the session ended."
        } + (line?.let { "\n$it" } ?: "")
    }

    private fun after(): String = afterSeconds?.let { " after ${it / 60} min ${it % 60} s" } ?: ""
}

object ReturnOutcomes {
    private const val PREPARE_FAILED = "guest_prepare.sh failed"
    private const val PREPARE_FAILED_0_3_6 = "master_prepare.sh failed"
    private val GUEST_REQ = Regex("""guest requested '([^']*)' after (\d+)s, returning to One UI""")
    private val DEAD = Regex("""guest zygote/system_server gone for \d+s after (\d+)s""")
    private val BLACK = Regex("""black screen after (\d+)s""")
    private val LIMIT = Regex("""session limit (\d+)s reached""")
    private val NOT_BOOTED = Regex("""guest still not booted after (\d+)s""")
    private const val KEYS = "Volume Up + Volume Down held 3 s"
    private const val SESSION_HEADER = "=== OneOS session "
    private const val LAUNCH_HEADER = "=== OneOS app launch "

    /** The part of an appended log after its last [header] line (all of it when there is none). */
    fun lastBlock(text: String, header: String): List<String> {
        val lines = text.lines()
        val i = lines.indexOfLast { it.startsWith(header) }
        return if (i < 0) lines else lines.drop(i)
    }

    /**
     * [autoReturn]: `$STAGE/auto_return.log` (the watcher and the return,
     * every session appended, one header per session); [takeoverApp]:
     * `$STAGE/takeover_app.log` (the switch, one launch header per launch);
     * [bootReason]: `sys.boot.reason` after the return.
     */
    fun parse(autoReturn: String?, takeoverApp: String?, bootReason: String?): ReturnOutcome {
        val reason = bootReason?.trim()?.takeIf { it.isNotEmpty() }
        val launch = takeoverApp?.let { lastBlock(it, LAUNCH_HEADER) }.orEmpty()
        launch.firstOrNull { it.contains("PREFLIGHT REFUSED:") }?.let { return ReturnOutcome(OutcomeKind.REFUSED, null, it.trim(), reason) }
        launch.firstOrNull { it.startsWith("ONEOS_PREPARE_ONLY=1:") }?.let { return ReturnOutcome(OutcomeKind.DRY_RUN, null, it.trim(), reason) }
        // guest_prepare.sh was master_prepare.sh up to 0.3.6: a log of such a session still reads the same.
        launch.firstOrNull { it.contains(PREPARE_FAILED) || it.contains(PREPARE_FAILED_0_3_6) || it.contains("Aborting and returning to One UI") || it.startsWith("ERROR: One UI's persist") }
            ?.let { return ReturnOutcome(OutcomeKind.PREPARE_FAILED, null, it.trim(), reason) }

        val ret = autoReturn?.let { lastBlock(it, SESSION_HEADER) }.orEmpty()
        for (l in ret.asReversed()) {
            GUEST_REQ.find(l)?.let { m ->
                val req = m.groupValues[1]
                val t = m.groupValues[2].toIntOrNull()
                val kind = when {
                    req.startsWith("keys") -> OutcomeKind.USER_RETURN
                    // The guest's OneOS app (Back to One UI): app:app or app:tile.
                    req.startsWith("app:") -> OutcomeKind.APP_RETURN
                    req.startsWith("shutdown") -> OutcomeKind.GUEST_SHUTDOWN
                    else -> OutcomeKind.GUEST_REBOOT
                }
                return ReturnOutcome(kind, t, l.trim(), reason)
            }
            DEAD.find(l)?.let { return ReturnOutcome(OutcomeKind.GUEST_DEAD, it.groupValues[1].toIntOrNull(), l.trim(), reason) }
            BLACK.find(l)?.let { return ReturnOutcome(OutcomeKind.BLACK_SCREEN, it.groupValues[1].toIntOrNull(), l.trim(), reason) }
            LIMIT.find(l)?.let { return ReturnOutcome(OutcomeKind.SESSION_LIMIT, it.groupValues[1].toIntOrNull(), l.trim(), reason) }
            NOT_BOOTED.find(l)?.let { return ReturnOutcome(OutcomeKind.BOOT_TIMEOUT, it.groupValues[1].toIntOrNull(), l.trim(), reason) }
            if (l.contains(KEYS)) return ReturnOutcome(OutcomeKind.USER_RETURN, null, l.trim(), reason)
        }
        return when {
            reason?.startsWith("shutdown,oneos-guest-shutdown") == true -> ReturnOutcome(OutcomeKind.GUEST_SHUTDOWN, null, null, reason)
            reason != null && !reason.contains("oneos") -> ReturnOutcome(OutcomeKind.HARD_RESET, null, null, reason)
            else -> ReturnOutcome(OutcomeKind.UNKNOWN, null, null, reason)
        }
    }
}

/** What the log bundle records besides the files. */
data class LogBundleInput(
    val app: AppInfo,
    val sessionId: String,
    val generatedAt: String,
    val profileId: String?,
    val imageId: String?,
    val tableSha256: String?,
    val dryRun: Boolean,
    val outcome: ReturnOutcome,
    val listSha256: String,
    val runnerSha256: String,
    /** Entries that did not finish (id: status). */
    val incomplete: List<String>,
    val learnedNames: Int,
)

/**
 * `oneos-logs-<session>.zip` (schema `oneos.logbundle/1`,
 * docs/app/compat-safety-logs.md section 3.4) from a folder the collection
 * already wrote redacted: report.json, summary.txt and redaction.txt are
 * added, then everything is zipped next to the folder.
 */
object LogBundle {
    const val SCHEMA = "oneos.logbundle/1"
    const val REPORT = "report.json"
    const val SUMMARY = "summary.txt"
    const val REDACTION = "redaction.txt"

    fun name(sessionId: String): String = "oneos-logs-${sessionId.filter { it.isLetterOrDigit() || it == '-' }.take(40)}"

    fun build(input: LogBundleInput, folder: File, redactor: Redactor, stats: LogStats): File {
        val files = folder.walkTopDown().filter { it.isFile }
            .map { it.relativeTo(folder).invariantSeparatorsPath }
            .filter { it != REPORT && it != SUMMARY && it != REDACTION }
            .sorted().toList()
        val summary = buildString {
            append("OneOS session logs ${input.sessionId}\n")
            append("App ${input.app.versionName} (${input.app.versionCode}), profile ${input.profileId ?: "unknown"}, image ${input.imageId ?: "unknown"}")
            append(if (input.dryRun) ", dry run\n" else "\n")
            append("Outcome: ${input.outcome.title}\n${input.outcome.detail(Images.systemName(input.imageId?.let { Images.byId(it) }))}\n")
            append("Boot reason: ${input.outcome.bootReason ?: "unknown"}\n")
            if (input.incomplete.isNotEmpty()) append("Not collected: ${input.incomplete.joinToString(", ")}\n")
            append("Files: ${files.size}; lines ${stats.lines}, dropped ${stats.droppedLines}, personal values removed ${redactor.log.total}, file names masked ${stats.maskedFiles}\n")
        }
        File(folder, SUMMARY).writeText(summary)
        File(folder, REDACTION).writeText(
            redactor.log.render() + "\nLog lines dropped whole (personal tags): ${stats.droppedLines}\n" +
                stats.droppedByTag.entries.joinToString("") { "  ${it.key}: ${it.value}\n" } +
                "Shared-storage file names masked: ${stats.maskedFiles}\nLines cut at ${RedactingOutputStream.MAX_LINE} bytes: ${stats.cutLines}\n" +
                "Saved Wi-Fi network names learned to remove: ${input.learnedNames} (not stored)\n",
        )
        val report = linkedMapOf<String, Any?>(
            "schema" to SCHEMA,
            "sessionId" to input.sessionId,
            "generatedAt" to input.generatedAt,
            "app" to linkedMapOf("id" to input.app.id, "version" to input.app.versionName, "versionCode" to input.app.versionCode),
            "profile" to input.profileId,
            "image" to input.imageId,
            "installdTableSha256" to input.tableSha256,
            "dryRun" to input.dryRun,
            "outcome" to linkedMapOf(
                "kind" to input.outcome.kind.name,
                "afterSeconds" to input.outcome.afterSeconds,
                "line" to input.outcome.line,
            ),
            "bootReason" to input.outcome.bootReason,
            "collect" to linkedMapOf(
                "listSha256" to input.listSha256,
                "runnerSha256" to input.runnerSha256,
                "incomplete" to input.incomplete,
            ),
            "redaction" to linkedMapOf(
                "rules" to Redactor.RULES,
                "droppedLines" to stats.droppedLines,
                "droppedTags" to stats.droppedByTag.size,
                "maskedFiles" to stats.maskedFiles,
                "masked" to redactor.log.counts().entries.associate { it.key.token to it.value },
            ),
            "files" to files.map { rel ->
                val f = File(folder, rel)
                linkedMapOf("path" to rel, "bytes" to f.length(), "sha256" to Hashes.sha256(f))
            },
        )
        File(folder, REPORT).writeText(Json.write(report))
        val zip = File(folder.parentFile, "${folder.name}.zip")
        zip.delete()
        ZipOutputStream(zip.outputStream().buffered(1 shl 16)).use { z ->
            for (rel in listOf(SUMMARY, REPORT, REDACTION) + files) {
                z.putNextEntry(ZipEntry("${folder.name}/$rel"))
                File(folder, rel).inputStream().use { it.copyTo(z) }
                z.closeEntry()
            }
        }
        return zip
    }

    /**
     * Learns the names the redaction must remove before any file is read:
     * saved Wi-Fi network names and Bluetooth device names. They are never
     * written anywhere. Returns the number of network names.
     */
    fun learn(redactor: Redactor, ssidGrep: String?, inputDevices: String?): Int {
        val names = ssidGrep?.let { LogRules.ssids(it) }.orEmpty()
        redactor.learnNames(RedactionKind.SSID, names)
        inputDevices?.let(redactor::learnBluetoothInputNames)
        return names.size
    }
}
