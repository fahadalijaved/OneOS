package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import android.provider.DocumentsContract
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.ImageIdentifier
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.SpaceRule
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.GuestData
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootScript.BeginMode
import com.fahadali.oneos.core.root.StageKind
import com.fahadali.oneos.core.root.StageStatus
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck
import java.util.concurrent.Executors
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Repair or start fresh (Advanced; the old Prepare page in the card look): the checks
 * (read-only, as root, behind a confirm), what happens to what is set up now
 * (Keep its apps and data, or keep it as an old copy and start fresh), then
 * Start setup behind its confirm. The job and root check everything again
 * before anything is written; once it starts, Setting up shows its progress.
 * From For the OneOS team it is "Setup details": the same page with Details
 * open (every finding, the stage folder as root read it, the nine steps with
 * Stop, the job's message, Next: All checks and Test run), and the steps
 * stay on this page.
 */
class PrepareActivity : ToolbarActivity() {
    private val team: Boolean get() = intent.getBooleanExtra(EXTRA_TEAM, false)

    override val screenTitle: CharSequence get() = getString(if (team) R.string.prepare_title_team else R.string.prepare_title)

    override fun createFragment(): Fragment = PrepareFragment()

    private var unsubscribe: (() -> Unit)? = null

    override fun onStart() {
        super.onStart()
        unsubscribe = PrepareJob.observe { s ->
            if (s.busy) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    companion object {
        /** Opened from For the OneOS team: titled "Setup details", Details open, the steps on this page. */
        const val EXTRA_TEAM = "com.fahadali.oneos.extra.TEAM"
    }
}

class PrepareFragment : CardsFragment() {
    private val subs = mutableListOf<() -> Unit>()
    private var mode: BeginMode? = null
    private val io = Executors.newSingleThreadExecutor()

    private val team: Boolean get() = activity?.intent?.getBooleanExtra(PrepareActivity.EXTRA_TEAM, false) == true

    override val detailsOpenAtStart: Boolean get() = team

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mode = savedInstanceState?.getString(KEY_MODE)?.let { m -> BeginMode.entries.firstOrNull { it.name == m } }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        mode?.let { outState.putString(KEY_MODE, it.name) }
    }

    override fun onStart() {
        super.onStart()
        subs += StageCheck.observe { redraw() }
        subs += PrepareJob.observe { redraw() }
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
    }

    override fun onDestroy() {
        io.shutdownNow()
        super.onDestroy()
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val job = PrepareJob.state
        val check = StageCheck.state
        val r = check.result
        val source = SessionPrefs.source(ctx)

        // What it does, in two lines.
        val intro = Cards.section(column, title = null)
        CardRows.text(intro, getString(R.string.prepare_intro))
        CardRows.text(intro, getString(R.string.prepare_intro_safe), R.style.OneOS_Text_Caption)

        // Checks: read-only, as root.
        val checks = Cards.section(column, getString(R.string.prepare_cat_checks), rows = true)
        if (check.busy) {
            CardRows.tint(
                Cards.row(checks, OuiIcons.drawable.ic_oui_refresh, (if (team) check.step else null) ?: getString(R.string.prepare_checking), null),
                Level.INFO,
            )
        } else {
            CardRows.row(
                checks, OuiIcons.drawable.ic_oui_refresh,
                getString(if (r == null) R.string.prepare_check_title else R.string.prepare_check_again),
                getString(if (check.message != null) R.string.prepare_check_failed else R.string.prepare_check_summary),
                enabled = !job.busy,
            ) { if (!job.busy) confirmCheck() }
        }
        val st = r?.status
        val stale = r != null && r.ageMs > StageCheck.FRESH_MS
        var blocked = true
        var report: GateReport? = null
        var modes: List<BeginMode> = emptyList()
        if (r != null && st != null) {
            modes = st.beginModes(null)
            if (mode !in modes) mode = modes.firstOrNull()
            if (r.installd == null) {
                // The cached check was stage-only (e.g. Use a downloaded file > Look for it), so the
                // installd table was never derived. Ask for a full check instead of
                // evaluating the installd gate as a BLOCK (as SwitchFragment does).
                CardRows.status(checks, Level.BLOCK, getString(R.string.prepare_need_full), null)
                blocked = true
            } else {
                fun gates() = StageCheck.gates(
                    ctx, r, GatePhase.PREPARE, SessionPrefs.picked(ctx)?.check, source == SessionPrefs.Source.ON_PHONE,
                    if (mode == BeginMode.KEEP) st.rawSize ?: 0 else 0,
                )
                var rep = gates()
                // The identified image decides whether the guest data may be kept (it stays with the image that made it).
                modes = st.beginModes(rep.image?.id)
                if (mode !in modes) {
                    mode = modes.firstOrNull()
                    rep = gates()
                }
                report = rep
                // A download not hashed yet does not stop it: setup checks the download itself
                // first, and the same identity gate then refuses anything but the verified image.
                blocked = rep.gates.any {
                    it.level == Level.BLOCK && !(it.id == SwitchGates.ID_IMAGE && it.finding.reason == ImageIdentifier.R_NOT_CHECKED)
                }
                // What stops it besides the gates (shown below): the system on this phone is reused only
                // when setup keeps it; something that is not a folder has to go first.
                val onPhoneNeedsKeep = source == SessionPrefs.Source.ON_PHONE && mode != BeginMode.KEEP
                if (onPhoneNeedsKeep || modes.isEmpty()) blocked = true
                // In plain words: what stops or warns, each once; every finding is under Details.
                // "Everything is in place" only when nothing stops it and the check is fresh.
                val problems = rep.report.sorted.filter { it.level == Level.BLOCK || it.level == Level.WARN }
                if (problems.isEmpty() && !blocked && !stale) CardRows.status(checks, Level.OK, getString(R.string.prepare_checks_ok), null)
                for (f in problems) {
                    val m = Plain.of(f, rep, r.facts)
                    val level = if (f.id == SwitchGates.ID_IMAGE && f.reason == ImageIdentifier.R_NOT_CHECKED) Level.INFO else f.level
                    CardRows.status(checks, level, m.title, m.line)
                }
                if (onPhoneNeedsKeep) {
                    CardRows.status(checks, Level.BLOCK, getString(R.string.prepare_on_phone_needs_keep), null)
                }
            }

            // What is set up now, and what setup does with it.
            val stage = Cards.section(column, getString(R.string.prepare_cat_stage), rows = true)
            Cards.row(stage, OuiIcons.drawable.ic_oui_folder_outline, stageTitle(st), null)
            if (modes.isEmpty()) {
                CardRows.status(stage, Level.BLOCK, getString(R.string.prepare_stage_not_folder), null)
                blocked = true
            }
            if (modes.size > 1) {
                for (m in modes) {
                    CardRows.tick(stage, modeTitle(m), modeSummary(m, st, report?.image), mode == m, enabled = !job.busy) { on ->
                        if (on) mode = m
                        redraw()
                    }
                }
            } else {
                modes.firstOrNull()?.let { Cards.row(stage, 0, modeTitle(it), modeSummary(it, st, report?.image)) }
            }
        }

        // Start setup.
        val run = Cards.section(column, getString(R.string.prepare_cat_run), rows = true)
        // The image the checks identified (the picked file, or the one already on this phone) and its set.
        val image = report?.image
        val set = report?.set
        val canRun = !job.busy && !check.busy && r != null && !stale && !blocked && mode != null
        // The system set up now when setup would write another one (the remembered download is a different
        // system): said above the button and in the confirm, never only in the small print (11-10).
        val replaced = st?.takeIf { it.ours }?.marker?.imageId?.let { Images.byId(it) }
            ?.takeIf { image != null && it.id != image.id && source != SessionPrefs.Source.ON_PHONE }
        if (replaced != null && image != null && !job.busy) {
            CardRows.status(
                run, Level.WARN,
                getString(R.string.prepare_other_system_title, image.name, replaced.name),
                getString(R.string.prepare_other_system_summary, image.name, replaced.name),
            )
        }
        if (job.busy && !team) {
            // The progress is on Setting up (Stop is there too).
            CardRows.tint(
                Cards.row(run, OuiIcons.drawable.ic_oui_refresh, getString(R.string.prepare_running_title, job.percent ?: 0), getString(R.string.prepare_running)) {
                    startActivity(Intent(ctx, SetupProgressActivity::class.java))
                },
                Level.INFO,
            )
        } else {
            val needs = if (image != null) Units.bytes(SpaceRule.toStage(image, set)) else getString(R.string.prepare_needs_unknown)
            CardRows.row(
                run, OuiIcons.drawable.ic_oui_download,
                if (image != null) getString(R.string.prepare_run_title_system, image.name) else getString(R.string.prepare_run_title),
                when {
                    job.busy -> getString(R.string.prepare_running)
                    r == null -> getString(R.string.prepare_run_check_first)
                    stale -> getString(R.string.prepare_run_stale)
                    blocked -> getString(R.string.prepare_run_blocked)
                    else -> getString(R.string.prepare_run_summary, needs)
                },
                enabled = canRun || job.busy,
            ) { if (canRun) confirmPrepare(mode!!, source, image, replaced) }
        }
        // How the last setup ended (its plain message; Setting up has the rest).
        if (!job.busy && job.phase != PrepareJob.Phase.IDLE) {
            val done = job.phase == PrepareJob.Phase.DONE
            val system = Images.systemName(job.image ?: image, report?.profile)
            val title = if (done) getString(R.string.setup_done_title, system) else job.plain?.title ?: getString(R.string.setup_failed_title)
            val line = if (done) getString(R.string.setup_done_subtitle) else job.plain?.line
            CardRows.status(run, if (done) Level.OK else job.plain?.level ?: Level.WARN, title, line) {
                startActivity(Intent(ctx, SetupProgressActivity::class.java))
            }
            if (done && team) {
                Cards.row(run, OuiIcons.drawable.ic_oui_labs_outline, getString(R.string.switch_title), getString(R.string.prepare_next_summary)) {
                    startActivity(Intent(ctx, SwitchActivity::class.java))
                }
            }
            val picked = SessionPrefs.picked(ctx)
            if (done && source == SessionPrefs.Source.GZ && picked != null) {
                Cards.row(run, OuiIcons.drawable.ic_oui_delete_outline, getString(R.string.prepare_delete_gz_title), getString(R.string.prepare_delete_gz_summary, picked.name ?: "")) {
                    confirmDeleteGz()
                }
            }
        }

        // Details: every finding, the stage as root read it, and (OneOS team) the nine steps.
        val more = Cards.section(column, title = null, rows = true)
        details(more, getString(R.string.prepare_details_summary)) { card ->
            CardRows.text(card, getString(R.string.prepare_what_summary), R.style.OneOS_Text_Caption, inList = true)
            CardRows.text(card, getString(R.string.prepare_safe_summary), R.style.OneOS_Text_Caption, inList = true)
            check.step?.takeIf { check.busy }?.let { Cards.row(card, 0, it, null) }
            check.message?.let { Cards.row(card, 0, getString(R.string.setup_details_result), it) }
            report?.report?.sorted?.forEach { CardRows.finding(card, it) }
            if (st != null) Cards.row(card, 0, stageTitle(st), stageSummary(st))
            if (job.phase != PrepareJob.Phase.IDLE) {
                for (s in PrepareJob.Step.entries) {
                    val level = when {
                        s in job.done -> Level.OK
                        s == job.step && job.busy -> Level.INFO
                        s == job.step -> Level.BLOCK
                        else -> null
                    }
                    val detail = if (s == job.step) job.detail else null
                    if (level == null) Cards.row(card, OuiIcons.drawable.ic_oui_checkbox_unchecked, s.label, detail) else CardRows.status(card, level, s.label, detail)
                }
            }
            if (job.busy) {
                Cards.row(card, OuiIcons.drawable.ic_oui_close, getString(R.string.tests_stop_title), getString(R.string.prepare_stop_summary)) { PrepareJob.cancel() }
            }
            job.message?.let { Cards.row(card, 0, getString(if (job.phase == PrepareJob.Phase.DONE) R.string.prepare_done else R.string.prepare_not_done), it) }
            job.infos.takeIf { it.isNotEmpty() }?.let { Cards.row(card, 0, getString(R.string.prepare_moved_title), it.joinToString("\n")) }
        }
    }

    /** What is set up now, in plain words. */
    private fun stageTitle(st: StageStatus): String = when {
        !st.exists -> getString(R.string.prepare_stage_none)
        st.kind != StageKind.FOLDER -> getString(R.string.prepare_stage_odd)
        st.ours -> getString(R.string.prepare_stage_ours, Images.systemName(st.marker?.imageId?.let { Images.byId(it) }))
        st.empty -> getString(R.string.prepare_stage_empty)
        st.partial -> getString(R.string.prepare_stage_partial)
        else -> getString(R.string.prepare_stage_foreign)
    }

    /** The stage as root read it (Details, for the OneOS team). */
    private fun stageSummary(st: StageStatus): String = buildList {
        if (st.exists && st.kind == StageKind.FOLDER) {
            add("Owner uid ${st.ownerUid}, mode ${st.mode}" + if (!st.safe) " (not root's alone: OneOS makes it root's)" else "")
            add(
                when (st.guest) {
                    GuestData.NONE -> "No guest data"
                    GuestData.EMPTY -> "An empty guest data folder"
                    GuestData.OTHER -> "Holds guest data OneOS does not recognise"
                    GuestData.LINEAGEOS -> "Holds an older system's guest data"
                    else -> "Holds guest data of " + (st.guest.family?.let { f -> Images.ALL.firstOrNull { it.family == f }?.name } ?: Images.OTHER_SYSTEM)
                },
            )
            st.rawSize?.let { add("system.raw: ${Units.bytes(it)}") }
            st.marker?.let { add("Marker: ${it.imageId}, set ${it.setId}, app ${it.versionCode}") }
        }
        if (st.oldStages.isNotEmpty()) add("Moved aside before: ${st.oldStages.joinToString { it.substringAfterLast('/') }}")
    }.joinToString("\n").ifEmpty { "Nothing yet in ${RootScript.STAGE}" }

    private fun modeTitle(m: BeginMode): String = getString(
        when (m) {
            BeginMode.NEW -> R.string.prepare_mode_new
            BeginMode.KEEP -> R.string.prepare_mode_keep
            BeginMode.ASIDE -> R.string.prepare_mode_aside
        },
    )

    private fun modeSummary(m: BeginMode, st: StageStatus, image: ImageRef?): String {
        val other = st.otherImageData(image?.id)
        val system = Images.systemName(image)
        return when {
            m == BeginMode.NEW -> getString(R.string.prepare_mode_new_summary, system)
            m == BeginMode.KEEP -> getString(R.string.prepare_mode_keep_summary)
            st.guest == GuestData.LINEAGEOS -> getString(R.string.prepare_mode_aside_older, system)
            other != null && image != null ->
                getString(R.string.prepare_mode_aside_other_image, Images.systemName(Images.byId(other)), image.name)
            image != null && st.guest.otherSystemThan(image) -> getString(R.string.prepare_mode_aside_other_system, system)
            else -> getString(R.string.prepare_mode_aside_summary, system)
        }
    }

    private fun confirmCheck() {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.prepare_check_dialog_title)
            .setMessage(R.string.prepare_check_dialog_message)
            .setPositiveButton(R.string.prepare_check_run) { _, _ -> StageCheck.start(requireContext(), StageCheck.Mode.FULL) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmPrepare(m: BeginMode, source: SessionPrefs.Source, image: ImageRef?, replaced: ImageRef?) {
        val system = Images.systemName(image)
        val what = buildString {
            if (replaced != null && image != null) {
                append(getString(R.string.prepare_dialog_other_system, image.name, replaced.name)).append("\n\n")
            }
            append(getString(R.string.prepare_dialog_message))
            append("\n\n")
            append(modeTitle(m)).append('.')
            append(' ')
            append(
                if (source == SessionPrefs.Source.ON_PHONE) getString(R.string.prepare_dialog_on_phone, system)
                else getString(R.string.prepare_dialog_gz, system),
            )
            if (team) append("\n\n").append(getString(R.string.prepare_dialog_team))
        }
        val stepsHere = team
        AlertDialog.Builder(requireContext())
            .setTitle(if (image != null) getString(R.string.confirm_setup_title, image.name) else getString(R.string.prepare_dialog_title))
            .setMessage(what)
            .setPositiveButton(R.string.confirm_setup_go) { _, _ ->
                val a = activity ?: return@setPositiveButton
                PrepareJob.start(a, PrepareJob.Plan(m, source))
                // As every other setup: Setting up shows it (the OneOS team's page keeps the steps here).
                if (!stepsHere && PrepareJob.state.busy) a.startActivity(Intent(a, SetupProgressActivity::class.java))
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** After a setup, the 5 GB download can go: through the picker's own provider (no storage permission). */
    private fun confirmDeleteGz() {
        val ctx = requireContext().applicationContext
        val picked = SessionPrefs.picked(ctx) ?: return
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.prepare_delete_gz_title)
            .setMessage(getString(R.string.prepare_delete_gz_message, picked.name ?: ""))
            .setPositiveButton(R.string.delete) { _, _ ->
                io.execute {
                    val ok = runCatching { DocumentsContract.deleteDocument(ctx.contentResolver, picked.uri) }.getOrDefault(false)
                    if (ok) SessionPrefs.clearPicked(ctx)
                    activity?.runOnUiThread {
                        Toast.makeText(ctx, if (ok) R.string.prepare_deleted else R.string.prepare_delete_failed, Toast.LENGTH_SHORT).show()
                        redraw()
                    }
                }
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private companion object {
        const val KEY_MODE = "mode"
    }
}
