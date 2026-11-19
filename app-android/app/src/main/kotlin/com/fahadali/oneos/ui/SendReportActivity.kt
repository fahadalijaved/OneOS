package com.fahadali.oneos.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputFilter
import android.text.InputType
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.preference.Preference
import androidx.preference.PreferenceCategory
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SwitchPreferenceCompat
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.CheckItem
import com.fahadali.oneos.core.model.Checklist
import com.fahadali.oneos.core.model.FormFactor
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.ReportLogs
import com.fahadali.oneos.core.model.ReportRecord
import com.fahadali.oneos.core.model.ReportReply
import com.fahadali.oneos.core.model.Reports
import com.fahadali.oneos.core.model.StartAnswer
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.LogTrim
import com.fahadali.oneos.probe.ProbeSession
import com.fahadali.oneos.report.ReportSender
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.security.SecureRandom
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.Executors

/**
 * Send to the OneOS team (0.4.29, both editions): a session's log bundle with
 * the user's checklist (did it start, what worked, what had problems, a note,
 * an optional Telegram name), or OneOS Probe's findings, straight to the report
 * service ([ReportSender]). The logs are the same redacted bundle Share sends;
 * by default a session sends the short log ([LogTrim]: the switch's first
 * minutes and the 2 before the end), the whole one when a problem is ticked or
 * the user asks. Share and Save stay where they were: if sending fails, this
 * screen says so and opens them. The phone, the system and how the session
 * ended come from the bundle's own report.json.
 */
class SendReportActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.send_title)

    /** A log bundle (files/logs) or findings zip (cache/findings): nothing else is sent from here. */
    val zip: File? by lazy {
        intent.getStringExtra(EXTRA_ZIP)?.let(::File)?.takeIf { f ->
            val dir = f.parentFile?.canonicalPath
            f.isFile && f.name.endsWith(".zip") &&
                (dir == FindingsActivity.logsDir(this).canonicalPath || dir == ProbeSession.findingsDir(this).canonicalPath)
        }
    }

    override fun createFragment(): Fragment = SendReportFragment()

    companion object {
        const val EXTRA_ZIP = "com.fahadali.oneos.extra.REPORT_ZIP"

        fun intent(ctx: Context, zip: File): Intent = Intent(ctx, SendReportActivity::class.java).putExtra(EXTRA_ZIP, zip.path)

        /** The report code a bundle was sent with (Last session shows it). */
        fun sentCode(ctx: Context, zip: File): String? = prefs(ctx).getString(zip.name.removeSuffix(".zip"), null)

        internal fun prefs(ctx: Context) = ctx.getSharedPreferences("reports_sent", Context.MODE_PRIVATE)

        /** The reporter's last valid Telegram username (in reports_sent; the sent codes there are keyed by zip name). */
        internal const val CONTACT_KEY = "contact_telegram"

        /** 0.5.16 (owner): the Telegram sign-in's pass and @username (in reports_sent). */
        internal const val PASS_KEY = "tg_pass"
        internal const val USERNAME_KEY = "tg_username"

        internal fun remember(ctx: Context, zip: File, code: String) {
            prefs(ctx).edit().putString(zip.name.removeSuffix(".zip"), code).apply()
        }
    }
}

class SendReportFragment : PreferenceFragmentCompat() {
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    /** What the bundle says about itself. */
    private data class Facts(
        val session: Boolean,
        val sessionId: String?,
        val profile: PhoneProfile?,
        val image: ImageRef?,
        val imageId: String?,
        val outcomeKind: String?,
        val afterSeconds: Int?,
        /** The OneOS the session ran on, which can be older than this app (0.4.32). */
        val sessionAppVersion: String? = null,
        val sessionAppCode: Int? = null,
        /** The day the session's bundle was written, from its generatedAt. */
        val sessionDate: String? = null,
        /** The session ran with Full session logs off (ONEOS_FULL_LOGS=0 in the bundle's stage/session.env). */
        val fullLogsOff: Boolean = false,
    )

    private lateinit var facts: Facts
    private var checklist = Checklist()

    /** Null: whole log only when a problem is ticked; set when the user chose. */
    private var fullChoice: Boolean? = null
    private var attach = true
    private var sending = false
    private var sentCode: String? = null
    private var failure: String? = null
    private var progress: String? = null

    /** The answers came from How's it going? in the other system (0.4.30). */
    private var fromGuest = false

    // 0.5.16 (owner): reports only from group members. Sign-in state; the pass itself is in prefs.
    private var signingIn = false
    private var claimCode: String? = null
    private var signinUrl: String? = null
    private var claimTries = 0
    private var claimErrors = 0
    private var claimBusy = false
    private var signinNote: String? = null
    private var notMember = false
    private val poll = Runnable { pollClaim() }

    private val pass: String? get() = SendReportActivity.prefs(requireContext()).getString(SendReportActivity.PASS_KEY, null)?.takeIf { it.isNotEmpty() }
    private val username: String? get() = SendReportActivity.prefs(requireContext()).getString(SendReportActivity.USERNAME_KEY, null)?.takeIf { it.isNotEmpty() }

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        val host = requireActivity() as SendReportActivity
        val zip = host.zip
        preferenceScreen = preferenceManager.createPreferenceScreen(preferenceManager.context)
        if (zip == null) {
            category("").row(getString(R.string.send_unavailable), null)
            return
        }
        facts = readFacts(zip)
        sentCode = SendReportActivity.sentCode(requireContext(), zip)
        // The plain cases from how it ended; the rest the user says.
        checklist = checklist.copy(
            start = when (facts.outcomeKind) {
                "BLACK_SCREEN" -> StartAnswer.BLACK
                "BOOT_TIMEOUT" -> StartAnswer.LOGO
                else -> null
            },
        )
        // How's it going? (0.4.30): what the user ticked in the other system, when it is this session's.
        if (facts.session) {
            guestAnswers(zip)?.let { g ->
                checklist = checklist.copy(start = StartAnswer.HOME, works = g.works - g.problems, problems = g.problems, note = g.note)
                fromGuest = true
            }
        }
        redraw()
    }

    override fun onResume() {
        super.onResume()
        if (claimCode != null) schedulePoll()
    }

    override fun onPause() {
        main.removeCallbacks(poll)
        super.onPause()
    }

    override fun onDestroy() {
        main.removeCallbacks(poll)
        io.shutdown()
        super.onDestroy()
    }

    private fun readFacts(zip: File): Facts {
        val json = runCatching { JSONObject(File(ProbeSession.folderOf(zip), "report.json").readText()) }.getOrNull()
        val session = json?.optString("schema")?.startsWith("oneos.logbundle") == true
        return if (session) {
            val profile = json!!.optString("profile").takeIf { it.isNotEmpty() && it != "null" }?.let { Profiles.byId(it) }
            val imageId = json.optString("image").takeIf { it.isNotEmpty() && it != "null" }
            val outcome = json.optJSONObject("outcome")
            Facts(
                session = true,
                sessionId = json.optString("sessionId").takeIf { it.isNotEmpty() },
                profile = profile,
                image = imageId?.let { Images.byId(it) },
                imageId = imageId,
                outcomeKind = outcome?.optString("kind")?.takeIf { it.isNotEmpty() },
                afterSeconds = outcome?.takeIf { it.has("afterSeconds") && !it.isNull("afterSeconds") }?.optInt("afterSeconds"),
                sessionAppVersion = json.optJSONObject("app")?.optString("version")?.takeIf { it.isNotEmpty() },
                sessionAppCode = json.optJSONObject("app")?.optInt("versionCode")?.takeIf { it > 0 },
                sessionDate = json.optString("generatedAt").takeIf { it.length >= 10 }?.take(10),
                // 0.5.17: Record full logs from now in the guest app leaves stage/full_logs_mid.log: logs from then on.
                fullLogsOff = runCatching {
                    val stage = File(ProbeSession.folderOf(zip), "stage")
                    File(stage, "session.env").readLines().contains("ONEOS_FULL_LOGS=0") && !File(stage, "full_logs_mid.log").isFile
                }.getOrDefault(false),
            )
        } else {
            val device = json?.optJSONObject("device")
            val profile = Profiles.resolve(
                device?.optString("model") ?: Build.MODEL,
                device?.optString("device") ?: Build.DEVICE,
                device?.optString("soc") ?: Build.SOC_MODEL,
            ).profile
            Facts(false, null, profile, null, null, null, null)
        }
    }

    private val full: Boolean get() = facts.session && (fullChoice ?: checklist.wantsFullLogs)

    /**
     * The guest OneOS app's How's it going? in the bundle (logs.guest copies it as
     * guest/…oneos_checklist.json), when it was saved in this session: not before the
     * session's start in stage/current.json (guest_prepare.sh also deletes it at each switch).
     */
    private fun guestAnswers(zip: File): Checklist? {
        val folder = ProbeSession.folderOf(zip)
        val f = File(folder, "guest").listFiles { x -> x.isFile && x.name.endsWith("oneos_checklist.json") }?.firstOrNull() ?: return null
        val json = runCatching { JSONObject(f.readText()) }.getOrNull() ?: return null
        val started = runCatching { JSONObject(File(folder, "stage/current.json").readText()).optLong("epoch") }.getOrNull() ?: 0L
        if (started > 0 && json.optLong("updatedAt") < started) return null
        val items = json.optJSONObject("items") ?: return null
        val works = mutableSetOf<CheckItem>()
        val problems = mutableSetOf<CheckItem>()
        for (k in items.keys()) {
            val item = CheckItem.byId(k) ?: continue
            when (items.optString(k)) {
                "works" -> works += item
                "problem" -> problems += item
            }
        }
        val note = Reports.cleanText(json.optString("note"), Reports.NOTE_MAX)
        if (works.isEmpty() && problems.isEmpty() && note.isEmpty()) return null
        return Checklist(works = works, problems = problems, note = note)
    }

    private fun redraw() {
        val zip = (requireActivity() as SendReportActivity).zip ?: return
        preferenceScreen.removeAll()
        val ctx = requireContext()
        val form: FormFactor? = facts.profile?.form
        val items = CheckItem.forForm(form)

        // Which report this is.
        val about = category(getString(if (facts.session) R.string.send_cat_session else R.string.send_cat_probe))
        // 0.4.32: say which session this is, not just its id. Send sends the session
        // the phone has stored, and a tester sent one twelve releases old without
        // knowing (Z Fold7, 2026-10-30), so the date, the system and the OneOS it
        // ran on are on the screen, and an older one says so in as many words.
        val ran = facts.sessionAppVersion
        val stale = facts.session && ran != null &&
            ran.substringBefore('-') != com.fahadali.oneos.BuildConfig.VERSION_NAME.substringBefore('-')
        about.row(
            listOfNotNull(facts.profile?.label ?: Build.MODEL, facts.image?.let { imageLabel(it) }).joinToString(" · "),
            when {
                !facts.session -> getString(R.string.send_probe_summary)
                ran == null -> getString(R.string.send_session_summary, facts.sessionId ?: "?")
                else -> getString(
                    R.string.send_session_summary_full,
                    facts.sessionDate ?: "?", ran, facts.sessionId ?: "?",
                )
            },
        )
        if (ran != null && stale) {
            about.row(getString(R.string.send_session_old_title), getString(R.string.send_session_old_summary, ran, com.fahadali.oneos.BuildConfig.VERSION_NAME))
        }

        if (facts.session && facts.fullLogsOff) {
            about.row(getString(R.string.send_full_logs_off_title), getString(R.string.send_full_logs_off_summary))
        }

        if (facts.session) {
            val how = category(getString(R.string.send_cat_how))
            if (fromGuest) how.row(getString(R.string.send_from_guest), getString(R.string.send_from_guest_summary))
            how.row(getString(R.string.send_start_title), checklist.start?.label ?: getString(R.string.send_choose), enabled = !sending) {
                val starts = StartAnswer.entries
                AlertDialog.Builder(ctx)
                    .setTitle(R.string.send_start_title)
                    .setSingleChoiceItems(starts.map { it.label }.toTypedArray(), starts.indexOf(checklist.start)) { d, i ->
                        checklist = checklist.copy(start = starts[i])
                        d.dismiss()
                        redraw()
                    }
                    .show()
            }
            how.row(getString(R.string.send_works_title), names(checklist.works, items), enabled = !sending) {
                pick(R.string.send_works_title, items, checklist.works) { checklist = checklist.copy(works = it, problems = checklist.problems - it) }
            }
            how.row(getString(R.string.send_problems_title), names(checklist.problems, items), enabled = !sending) {
                pick(R.string.send_problems_title, items, checklist.problems) { checklist = checklist.copy(problems = it, works = checklist.works - it) }
            }
        }
        val more = category(getString(R.string.send_cat_more))
        more.row(getString(R.string.send_note_title), checklist.note.ifEmpty { getString(R.string.send_note_hint) }, enabled = !sending) {
            text(R.string.send_note_title, checklist.note, Reports.NOTE_MAX, multiLine = true) { checklist = checklist.copy(note = it) }
        }
        // Required since 0.5.10 (owner: "make giving contact in the report compulsory, with proper telegram
        // username"); the last good one is filled in again for the next report.
        if (checklist.contact.isEmpty()) savedContact(ctx)?.let { checklist = checklist.copy(contact = it) }
        val contactSummary = when {
            checklist.contact.isEmpty() -> getString(R.string.send_contact_hint)
            Reports.telegramUsername(checklist.contact) == null -> getString(R.string.send_contact_invalid, checklist.contact)
            else -> checklist.contact
        }
        more.row(getString(R.string.send_contact_title), contactSummary, enabled = !sending) { askContact() }

        // Who sends (0.5.16, owner: reports only from group members).
        telegramRows(category(getString(R.string.send_cat_telegram)))

        // What is sent.
        val what = category(getString(R.string.send_cat_what))
        val attachRow = SwitchPreferenceCompat(ctx).apply {
            title = getString(if (facts.session) R.string.send_attach_logs else R.string.send_attach_findings)
            summary = when {
                !facts.session -> getString(R.string.send_attach_findings_summary, Units.bytes(zip.length()))
                full -> getString(R.string.send_full_summary, Units.bytes(zip.length()))
                else -> getString(R.string.send_short_summary)
            }
            isChecked = attach
            isPersistent = false
            isIconSpaceReserved = false
            isEnabled = !sending
            setOnPreferenceChangeListener { _, v -> attach = v as Boolean; main.post { redraw() }; true }
        }
        what.addPreference(attachRow)
        if (facts.session && attach) {
            what.addPreference(SwitchPreferenceCompat(ctx).apply {
                title = getString(R.string.send_full_title)
                summary = getString(if (checklist.wantsFullLogs && fullChoice == null) R.string.send_full_auto else R.string.send_full_hint)
                isChecked = full
                isPersistent = false
                isIconSpaceReserved = false
                isEnabled = !sending
                setOnPreferenceChangeListener { _, v -> fullChoice = v as Boolean; main.post { redraw() }; true }
            })
        }
        what.row(getString(R.string.send_privacy_title), getString(R.string.send_privacy_summary))

        // Send, and how it went.
        val send = category("")
        when {
            sending -> send.row(getString(R.string.send_sending), progress)
            sentCode != null && failure == null -> {
                send.row(getString(R.string.send_done_title), getString(R.string.send_done_summary, sentCode)) {
                    ctx.getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText("OneOS report", sentCode))
                    Toast.makeText(ctx, R.string.send_copied, Toast.LENGTH_SHORT).show()
                }
                send.row(getString(R.string.send_again), null) { sentCode = null; redraw() }
            }
            else -> {
                failure?.let { send.row(getString(R.string.send_failed_title), it) }
                send.row(getString(R.string.send_button), getString(R.string.send_button_summary)) { send(zip) }
                if (failure != null) {
                    send.row(getString(R.string.send_share_instead), getString(R.string.send_share_instead_summary)) { shareInstead(zip) }
                }
            }
        }
    }

    private fun telegramRows(cat: PreferenceCategory) {
        // 0.5.24: no sign-in; the user posts the report from their own Telegram into OneOSReports.
        cat.row(getString(R.string.send_tg_reports_join_title), getString(R.string.send_tg_reports_join_summary), enabled = !sending) {
            openLink(ReportSender.REPORTS_INVITE)
        }
    }

    private fun openLink(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(requireContext(), R.string.send_tg_no_app, Toast.LENGTH_LONG).show()
        }
    }

    private fun startSignIn() {
        signingIn = true
        signinNote = null
        redraw()
        io.execute {
            val result = runCatching { ReportSender.signin() }
            main.post {
                signingIn = false
                if (!isAdded) return@post
                result.onSuccess { (code, url) ->
                    claimCode = code
                    signinUrl = url
                    claimTries = 0
                    claimErrors = 0
                    openLink(url)
                    if (isResumed) schedulePoll()
                }.onFailure { e -> signinNote = e.message ?: e.javaClass.simpleName }
                redraw()
            }
        }
    }

    /** Every 3 s while the screen is in front, 60 times (3 minutes); a pause does not use them up. */
    private fun schedulePoll() {
        main.removeCallbacks(poll)
        main.postDelayed(poll, 3_000L)
    }

    private fun pollClaim() {
        val code = claimCode ?: return
        if (claimBusy || !isAdded) return
        if (claimTries >= 60) return endSignIn(getString(R.string.send_tg_expired))
        claimTries++
        claimBusy = true
        io.execute {
            val result = runCatching { ReportSender.claim(code) }
            main.post {
                claimBusy = false
                if (!isAdded || claimCode != code) return@post
                result.onSuccess { claim ->
                    claimErrors = 0
                    when (claim) {
                        ReportReply.Claim.Waiting -> if (isResumed) schedulePoll()
                        ReportReply.Claim.Expired -> endSignIn(getString(R.string.send_tg_expired))
                        is ReportReply.Claim.Done -> {
                            SendReportActivity.prefs(requireContext()).edit()
                                .putString(SendReportActivity.PASS_KEY, claim.pass)
                                .putString(SendReportActivity.USERNAME_KEY, claim.username ?: "")
                                .apply()
                            notMember = !claim.member
                            endSignIn(null)
                        }
                    }
                }.onFailure { e ->
                    // A dropped connection is tried again twice; a refusal or a 5xx is shown.
                    if (e !is ReportSender.Failed && ++claimErrors < 3) {
                        if (isResumed) schedulePoll()
                    } else {
                        endSignIn(e.message ?: e.javaClass.simpleName)
                    }
                }
            }
        }
    }

    private fun endSignIn(note: String?) {
        main.removeCallbacks(poll)
        claimCode = null
        signinUrl = null
        signinNote = note
        if (isAdded) redraw()
    }

    private fun imageLabel(i: ImageRef): String = if (i.name.contains(i.shortName)) i.name else "${i.name} (${i.shortName})"

    private fun names(set: Set<CheckItem>, items: List<CheckItem>): String =
        items.filter { it in set }.joinToString(", ") { it.label }.ifEmpty { getString(R.string.send_none_ticked) }

    private fun pick(title: Int, items: List<CheckItem>, current: Set<CheckItem>, done: (Set<CheckItem>) -> Unit) {
        val checked = items.map { it in current }.toBooleanArray()
        AlertDialog.Builder(requireContext())
            .setTitle(title)
            .setMultiChoiceItems(items.map { it.label }.toTypedArray(), checked) { _, i, on -> checked[i] = on }
            .setPositiveButton(android.R.string.ok) { _, _ ->
                done(items.filterIndexed { i, _ -> checked[i] }.toSet())
                redraw()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun text(title: Int, current: String, max: Int, multiLine: Boolean, done: (String) -> Unit) {
        val ctx = requireContext()
        val edit = EditText(ctx).apply {
            setText(current)
            filters = arrayOf(InputFilter.LengthFilter(max))
            inputType = InputType.TYPE_CLASS_TEXT or (if (multiLine) InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES else 0)
            if (multiLine) minLines = 3
        }
        val box = FrameLayout(ctx).apply {
            val pad = (24 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad / 2, pad, 0)
            addView(edit)
        }
        AlertDialog.Builder(ctx)
            .setTitle(title)
            .setView(box)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                done(Reports.cleanText(edit.text.toString(), max))
                redraw()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun askContact() =
        text(R.string.send_contact_title, checklist.contact, Reports.CONTACT_MAX, multiLine = false) { raw ->
            val user = Reports.telegramUsername(raw)
            checklist = checklist.copy(contact = user ?: raw)
            if (user != null) SendReportActivity.prefs(requireContext()).edit().putString(SendReportActivity.CONTACT_KEY, user).apply()
            else if (raw.isNotBlank()) Toast.makeText(requireContext(), getString(R.string.send_contact_invalid, raw), Toast.LENGTH_LONG).show()
        }

    private fun savedContact(ctx: Context): String? = SendReportActivity.prefs(ctx).getString(SendReportActivity.CONTACT_KEY, null)?.let(Reports::telegramUsername)

    private fun send(zip: File) {
        if (facts.session && checklist.start == null) {
            Toast.makeText(requireContext(), R.string.send_need_start, Toast.LENGTH_SHORT).show()
            return
        }
        val app = requireContext().applicationContext
        sending = true
        failure = null
        progress = getString(R.string.send_preparing)
        redraw()
        val f = facts
        val c = checklist.cleaned()
        val wantFull = full
        val withLogs = attach
        io.execute {
            val result = runCatching {
                // The short log is made in the cache from the bundle itself (not next
                // to it: Last session shows the newest zip in files/logs), and deleted after.
                val shortDir = File(app.cacheDir, "report-short").apply { deleteRecursively(); mkdirs() }
                val file = when {
                    !withLogs -> null
                    !f.session || wantFull -> zip
                    else -> File(shortDir, zip.name.removeSuffix(".zip") + "-short.zip").takeIf { LogTrim.shorten(zip, it) } ?: zip
                }
                check(file == null || file.length() <= Reports.MAX_ZIP_BYTES) { app.getString(R.string.send_too_big, Units.bytes(file!!.length())) }
                val rnd = ByteArray(4).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
                val record = ReportRecord(
                    reportId = Reports.reportId(f.sessionId ?: zip.name.removeSuffix(".zip"), rnd),
                    createdAt = OffsetDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME).take(25),
                    app = ProbeSession.appInfo(app),
                    series = com.fahadali.oneos.BuildConfig.VERSION_NAME.substringAfterLast('-', "").takeIf { it in setOf("fold", "s26", "s25") }.orEmpty(),
                    model = Build.MODEL.take(40),
                    device = Build.DEVICE.lowercase().take(48),
                    profileId = f.profile?.id,
                    phoneLabel = f.profile?.label,
                    imageId = f.imageId,
                    imageName = f.image?.let { imageLabel(it) },
                    sessionId = f.sessionId,
                    sessionAppVersion = f.sessionAppVersion,
                    sessionAppCode = f.sessionAppCode,
                    sessionDate = f.sessionDate,
                    outcomeKind = f.outcomeKind,
                    afterSeconds = f.afterSeconds,
                    checklist = if (f.session) c else Checklist(note = c.note, contact = c.contact),
                    form = f.profile?.form,
                    logs = file?.let { ReportLogs(if (f.session) "session" else "probe", it.name, full = f.session && it == zip, bytes = it.length(), sha256 = sha256(it)) },
                )
                // 0.5.24: one zip for Telegram, the bundle's own files plus the record (reports/tgbot.py reads it).
                val out = File(File(app.cacheDir, "findings").apply { mkdirs() }, "oneos-report-${record.reportId}.zip")
                try {
                    java.util.zip.ZipOutputStream(out.outputStream().buffered()).use { zo ->
                        if (file != null) java.util.zip.ZipFile(file).use { zf ->
                            for (e in zf.entries()) {
                                if (e.isDirectory || e.name == "oneos-report.json") continue
                                zo.putNextEntry(java.util.zip.ZipEntry(e.name))
                                zf.getInputStream(e).use { it.copyTo(zo) }
                                zo.closeEntry()
                            }
                        }
                        zo.putNextEntry(java.util.zip.ZipEntry("oneos-report.json"))
                        zo.write(record.toJson().toByteArray(Charsets.UTF_8))
                        zo.closeEntry()
                    }
                } finally {
                    shortDir.deleteRecursively()
                }
                Triple(record.reportId, out, caption(record))
            }
            main.post {
                sending = false
                result.onSuccess { (code, out, text) ->
                    if (isAdded && postToTelegram(out, text)) {
                        sentCode = code
                        SendReportActivity.remember(app, zip, code)
                    }
                }.onFailure { e ->
                    failure = e.message ?: e.javaClass.simpleName
                    when (e) {
                        // 0.5.16: sign in again (the pass is no longer good), or join the group and retry.
                        is ReportSender.NeedsSignIn -> {
                            SendReportActivity.prefs(app).edit().remove(SendReportActivity.PASS_KEY).remove(SendReportActivity.USERNAME_KEY).apply()
                            notMember = false
                        }
                        is ReportSender.NotMember -> { notMember = true; failure = null }
                    }
                }
                if (isAdded) redraw()
            }
        }
    }

    /** The caption Telegram shows under the file (the full answers are in the zip's oneos-report.json). */
    private fun caption(r: ReportRecord): String = buildString {
        append("OneOS report ").append(r.reportId)
        r.phoneLabel?.let { append("\n📱 ").append(it) }
        r.imageName?.let { append("\n💿 ").append(it) }
        r.checklist?.start?.let { append("\n🚀 ").append(it.label) }
    }

    /** Share [out] to Telegram (a Telegram app directly when one is installed, else the share sheet). */
    private fun postToTelegram(out: File, text: String): Boolean {
        val ctx = requireContext()
        val uri = androidx.core.content.FileProvider.getUriForFile(ctx, "${com.fahadali.oneos.BuildConfig.APPLICATION_ID}.findings", out)
        fun intent() = Intent(Intent.ACTION_SEND).setType("application/zip").putExtra(Intent.EXTRA_STREAM, uri)
            .putExtra(Intent.EXTRA_TEXT, text).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            .also { it.clipData = ClipData.newRawUri(out.name, uri) }
        for (pkg in ReportSender.TELEGRAM_PACKAGES) {
            try {
                startActivity(intent().setPackage(pkg))
                return true
            } catch (_: ActivityNotFoundException) {
            }
        }
        return try {
            startActivity(Intent.createChooser(intent(), getString(R.string.send_button)))
            true
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(ctx, R.string.send_tg_no_app, Toast.LENGTH_LONG).show()
            false
        }
    }

    private fun sha256(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        f.inputStream().use { input ->
            val buf = ByteArray(1 shl 16)
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    /** The findings screen of this zip, with Share and Save. */
    private fun shareInstead(zip: File) {
        val ctx = requireContext()
        val i = Intent(ctx, FindingsActivity::class.java)
        if (zip.parentFile?.canonicalPath == FindingsActivity.logsDir(ctx).canonicalPath) i.putExtra(FindingsActivity.EXTRA_ZIP, zip.path)
        startActivity(i)
    }

    private fun category(title: String): PreferenceCategory {
        val c = PreferenceCategory(preferenceManager.context)
        c.title = title
        c.isIconSpaceReserved = false
        preferenceScreen.addPreference(c)
        return c
    }

    private fun PreferenceCategory.row(title: CharSequence, summary: CharSequence?, enabled: Boolean = true, onClick: (() -> Unit)? = null): Preference {
        val p = Preference(context)
        p.title = title
        p.summary = summary
        p.isIconSpaceReserved = false
        p.isEnabled = enabled
        if (onClick == null) {
            p.isSelectable = false
        } else {
            p.setOnPreferenceClickListener { onClick(); true }
        }
        addPreference(p)
        return p
    }
}
