package com.fahadali.oneos.core.model

/**
 * Send to the OneOS team (0.4.29): a report goes from the app straight to the
 * team's report service (reports/worker.js) instead of through Telegram and
 * the owner. A report is a small record (schema `oneos.report/1`: the phone,
 * the app, the system, how the session ended and the user's checklist) and,
 * when the user leaves it ticked, the log bundle or probe findings zip, sent
 * in parts of at most [PART_BYTES] (the service keeps each part as one Workers
 * KV value, 25 MiB at most). Nothing is sent without the user's tap; the logs
 * are the same redacted bundle Share sends. The checklist answers (never the
 * note or the contact) are what docs/compatibility.md counts per app version,
 * phone and system.
 */
object Reports {
    const val SCHEMA = "oneos.report/1"

    /** One part of the zip per request: under the 25 MiB a Workers KV value holds. */
    const val PART_BYTES = 20 * 1024 * 1024

    /** The largest zip the service takes (the biggest session bundle so far was 27 MB). */
    const val MAX_ZIP_BYTES = 64L * 1024 * 1024

    const val NOTE_MAX = 500
    const val CONTACT_MAX = 64

    /** Parts for a zip of [bytes] (0 for no zip). */
    fun parts(bytes: Long): Int = if (bytes <= 0) 0 else ((bytes + PART_BYTES - 1) / PART_BYTES).toInt()

    /** A report id: the session's (or the findings') id and a random suffix, so one session can be sent again. */
    fun reportId(baseId: String, suffix: String): String {
        val base = baseId.lowercase().filter { it in '0'..'9' || it in 'a'..'z' }.take(32).ifEmpty { "report" }
        val tail = suffix.lowercase().filter { it in '0'..'9' || it in 'a'..'f' }.take(8)
        require(tail.length >= 4) { "suffix needs at least 4 hex digits" }
        return "$base-$tail"
    }

    /** What the service accepts as a report id (reports/worker.js checks the same). */
    val ID_PATTERN = Regex("^[a-z0-9]{1,32}-[0-9a-f]{4,8}$")

    /** Free text as sent: no control characters, one space for runs of blanks, at most [max] characters. */
    fun cleanText(s: String, max: Int): String =
        s.replace(Regex("[\\p{Cntrl}&&[^\\n]]"), " ")
            .lines().joinToString("\n") { it.replace(Regex("\\s+"), " ").trim() }
            .replace(Regex("\\n{3,}"), "\n\n")
            .trim().take(max).trim()
}

/** Did the other system start (the first checklist question). */
enum class StartAnswer(val id: String, val label: String) {
    HOME("home", "Reached the home screen"),
    LOGO("logo", "Stuck on the boot logo"),
    BLACK("black", "Black screen"),
    BACK("back", "Came back to One UI or restarted by itself"),
    ;

    val started: Boolean get() = this == HOME

    companion object {
        fun byId(id: String?): StartAnswer? = entries.firstOrNull { it.id == id }
    }
}

/** What the user checks in the other system ([foldOnly]: asked on the Z Folds only). */
enum class CheckItem(val id: String, val label: String, val foldOnly: Boolean = false) {
    SCREEN("screen", "Screen and touch"),
    WIFI("wifi", "Wi-Fi"),
    DATA("data", "Mobile data"),
    CALLS("calls", "Calls"),
    SMS("sms", "SMS"),
    BLUETOOTH("bluetooth", "Bluetooth"),
    SOUND("sound", "Sound"),
    CAMERA("camera", "Camera"),
    GOOGLE("google", "Google sign-in and Play Store"),
    LOCATION("location", "Location"),
    BACK_TO_ONE_UI("back", "Back to One UI"),
    HEAT("heat", "Heat and battery"),
    FOLD("fold", "Both screens, folding and unfolding", foldOnly = true),
    ;

    companion object {
        fun byId(id: String?): CheckItem? = entries.firstOrNull { it.id == id }

        /** The items asked on a phone of [form]. */
        fun forForm(form: FormFactor?): List<CheckItem> = entries.filter { !it.foldOnly || form == FormFactor.FOLD }
    }
}

enum class CheckAnswer(val id: String, val label: String) {
    WORKS("works", "Works"),
    PROBLEM("problem", "Problem"),
    NOT_TRIED("not_tried", "Didn't try"),
}

/**
 * The user's answers. An item in neither [works] nor [problems] was not
 * tried; one in both counts as a problem. [note] and [contact] (an optional
 * Telegram name) are free text, cleaned and cut by [cleaned].
 */
data class Checklist(
    val start: StartAnswer? = null,
    val works: Set<CheckItem> = emptySet(),
    val problems: Set<CheckItem> = emptySet(),
    val note: String = "",
    val contact: String = "",
) {
    fun answer(item: CheckItem): CheckAnswer = when (item) {
        in problems -> CheckAnswer.PROBLEM
        in works -> CheckAnswer.WORKS
        else -> CheckAnswer.NOT_TRIED
    }

    /** A problem was ticked: the whole session's log is sent (when it was tried is unknown), not the short one. */
    val wantsFullLogs: Boolean get() = problems.isNotEmpty()

    fun cleaned(): Checklist = copy(
        works = works - problems,
        note = Reports.cleanText(note, Reports.NOTE_MAX),
        contact = Reports.cleanText(contact, Reports.CONTACT_MAX).replace("\n", " "),
    )

    /** The record's "checklist" object: every item asked on [form] with its answer. */
    fun toMap(form: FormFactor?): Map<String, Any?> = linkedMapOf(
        "start" to start?.id,
        "items" to CheckItem.forForm(form).associateTo(linkedMapOf()) { it.id to answer(it).id },
    )
}

/** The zip a report carries. */
data class ReportLogs(
    /** `session` (a log bundle) or `probe` (OneOS Probe findings). */
    val kind: String,
    val name: String,
    /** The whole session's log, not the short one ([LogTrim] in :core:root). */
    val full: Boolean,
    val bytes: Long,
    val sha256: String,
) {
    val parts: Int get() = Reports.parts(bytes)
}

/** The record the service keeps and the team reads (schema [Reports.SCHEMA]). */
data class ReportRecord(
    val reportId: String,
    val createdAt: String,
    val app: AppInfo,
    /** The series APK (fold, s26, s25), or empty for the all-in-one build. */
    val series: String,
    val model: String,
    val device: String,
    val profileId: String?,
    /** The profile's name ("Galaxy S25 Ultra"): docs/compatibility.md's rows. */
    val phoneLabel: String?,
    val imageId: String?,
    /** The system's name ("Infinity-X 4.1"). */
    val imageName: String?,
    val sessionId: String?,
    /**
     * The OneOS the session itself ran on, and when it ran. Send sends the session
     * the phone has stored, which can be older than the app sending it (a Z Fold7
     * report of 2026-10-30 came from 0.4.31 with a 0.4.19 session), so [app] alone
     * says nothing about which build a result is evidence for. Null for a probe
     * report and for a bundle too old to record its own app.
     */
    val sessionAppVersion: String? = null,
    val sessionAppCode: Int? = null,
    /** When the session's log bundle was written (its `generatedAt`, date only). */
    val sessionDate: String? = null,
    val outcomeKind: String?,
    val afterSeconds: Int?,
    val checklist: Checklist?,
    val form: FormFactor?,
    val logs: ReportLogs?,
) {
    fun toJson(): String = Json.write(toMap())

    fun toMap(): Map<String, Any?> {
        val c = checklist?.cleaned()
        return linkedMapOf(
            "schema" to Reports.SCHEMA,
            "reportId" to reportId,
            "createdAt" to createdAt,
            "app" to linkedMapOf("id" to app.id, "version" to app.versionName, "versionCode" to app.versionCode, "series" to series),
            "phone" to linkedMapOf("model" to model, "device" to device, "profile" to profileId, "label" to phoneLabel),
            "image" to imageId,
            "imageName" to imageName,
            "sessionId" to sessionId,
            "sessionApp" to sessionAppVersion?.let {
                linkedMapOf("version" to it, "versionCode" to sessionAppCode, "date" to sessionDate)
            },
            "outcome" to outcomeKind?.let { linkedMapOf("kind" to it, "afterSeconds" to afterSeconds) },
            "checklist" to c?.toMap(form),
            "note" to c?.note?.ifEmpty { null },
            "contact" to c?.contact?.ifEmpty { null },
            "logs" to logs?.let {
                linkedMapOf("kind" to it.kind, "name" to it.name, "full" to it.full, "bytes" to it.bytes, "sha256" to it.sha256, "parts" to it.parts)
            },
        )
    }
}
