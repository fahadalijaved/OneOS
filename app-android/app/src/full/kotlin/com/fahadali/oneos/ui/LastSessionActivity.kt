package com.fahadali.oneos.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.root.OutcomeKind
import com.fahadali.oneos.report.ReportSender
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.SessionPrefs
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Last session (build 2, AA19; the redesign's card look): first how it went
 * in plain words (the outcome, when, the time in {system} and how you came
 * back), then the logs (Collect logs: read-only as root, redacted as it
 * arrives, never recordings or screenshots; the bundle to view and share),
 * then Restore One UI's settings after a session that never returned. The
 * session id, the technical outcome and the log counts are under Details.
 */
class LastSessionActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.last_title)

    override fun createFragment(): Fragment = LastSessionFragment()
}

/**
 * Restore One UI's settings (Last session and Advanced): offered when the
 * stage says the last session never returned, or (not read yet) after any
 * restart since a session: `recover` restores nothing when it returned
 * normally. The confirm is the same wherever it is asked.
 */
internal object SessionRestore {
    /** Not read yet, and the phone restarted since a session (not a test run). */
    fun maybe(ctx: Context): Boolean {
        val launch = SessionPrefs.lastLaunch(ctx)
        return LogJob.state.status == null && launch != null && !launch.dryRun && launch.rebootedSince()
    }

    fun offered(ctx: Context): Boolean = LogJob.state.status?.unfinishedSession == true || maybe(ctx)

    fun confirm(a: Activity) {
        AlertDialog.Builder(a)
            .setTitle(R.string.last_restore_title)
            .setMessage(R.string.last_restore_dialog_message)
            .setPositiveButton(R.string.last_restore_run) { _, _ -> LogJob.recover(a) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }
}

class LastSessionFragment : CardsFragment() {
    private var unsubscribe: (() -> Unit)? = null

    /** "What is collected" is open. */
    private var privacyOpen = false

    override fun onStart() {
        super.onStart()
        unsubscribe = LogJob.observe { redraw() }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val launch = SessionPrefs.lastLaunch(ctx)
        val job = LogJob.state
        val image = launch?.imageId?.let { Images.byId(it) }
        val system = Images.systemName(image)
        // How it ended: the logs read now, else what the last read kept.
        val outcome = job.outcome?.kind ?: launch?.outcome?.let { o -> OutcomeKind.entries.firstOrNull { it.name == o } }
        val afterSeconds = job.outcome?.afterSeconds ?: launch?.afterSeconds
        val test = launch?.dryRun == true || outcome == OutcomeKind.DRY_RUN

        // How it went.
        val title = when {
            launch == null -> getString(R.string.last_none)
            outcome != null -> outcome.title(system).let { if (it.endsWith('.')) it.dropLast(1) else it }
            test -> getString(R.string.last_dry)
            launch.rebootedSince() -> getString(R.string.last_time_in, system)
            else -> getString(R.string.last_switched_to, system)
        }
        val summary = Cards.section(column, title, launch?.let { CardRows.dateTime(ctx, it.wallMs) }, Level.INFO)
        when {
            launch == null -> CardRows.text(summary, getString(R.string.last_none_line))
            outcome != null && !test -> {
                val minutes = afterSeconds?.takeIf { it > 0 }?.let { (it + 59) / 60 }
                val tiles = buildList<Pair<CharSequence, CharSequence>> {
                    if (minutes != null) add(getString(R.string.home_minutes, minutes) to getString(R.string.home_welcome_in, system))
                    // The title says how you came back already, except for these.
                    if (!titleSaysHow(outcome)) add(getString(howCameBack(outcome)) to getString(R.string.home_welcome_how))
                }
                if (tiles.isNotEmpty()) CardRows.stats(summary, tiles)
            }
            outcome != null -> CardRows.text(summary, getString(R.string.last_test_line, system))
            launch.rebootedSince() -> CardRows.text(summary, getString(R.string.last_rebooted_summary))
            else -> CardRows.text(summary, getString(R.string.last_not_rebooted_summary))
        }

        // Logs.
        val logs = Cards.section(column, getString(R.string.last_cat_logs), rows = true)
        val zip = job.zip ?: LogJob.latestZip(ctx)
        when {
            job.busy && !job.recovering ->
                CardRows.tint(Cards.row(logs, OuiIcons.drawable.ic_oui_refresh, getString(R.string.last_collecting), getString(R.string.last_collecting_summary)), Level.INFO)
            else -> CardRows.row(
                logs, OuiIcons.drawable.ic_oui_file_type_txt,
                getString(if (zip == null) R.string.last_collect_title else R.string.last_collect_again),
                getString(R.string.last_collect_summary),
                enabled = !job.busy,
            ) { confirmCollect() }
        }
        if (!job.busy && job.phase == LogJob.Phase.FAILED && !job.restoreFailed) {
            CardRows.status(logs, Level.WARN, getString(R.string.last_collect_failed), getString(R.string.last_collect_failed_line))
        } else if (!job.busy && job.phase == LogJob.Phase.DONE && job.zip != null && job.recovered == null) {
            CardRows.status(logs, Level.OK, getString(R.string.last_collected), getString(R.string.last_collected_summary))
        }
        if (zip != null && !job.busy) {
            // 0.4.29: the checklist and the logs straight to the team; Share and Save stay under View.
            if (ReportSender.available) {
                val code = SendReportActivity.sentCode(ctx, zip)
                Cards.row(
                    logs, OuiIcons.drawable.ic_oui_send, getString(R.string.send_title),
                    if (code != null) getString(R.string.last_send_sent, code) else getString(R.string.last_send_summary),
                ) { startActivity(SendReportActivity.intent(ctx, zip)) }
            }
            Cards.row(logs, OuiIcons.drawable.ic_oui_share, getString(R.string.last_view_title), getString(R.string.last_view_summary)) {
                startActivity(Intent(ctx, FindingsActivity::class.java).putExtra(FindingsActivity.EXTRA_ZIP, zip.path))
            }
        }
        val privacy = Cards.row(logs, OuiIcons.drawable.ic_oui_privacy, getString(R.string.last_privacy_title), null) {
            privacyOpen = !privacyOpen
            redraw()
        }
        CardRows.expandable(privacy, privacyOpen)
        if (privacyOpen) CardRows.text(logs, getString(R.string.last_privacy_summary), R.style.OneOS_Text_Caption, inList = true)

        // One UI's settings: a session that never returned (force restart); they come back from its snapshot.
        val maybe = SessionRestore.maybe(ctx)
        val unfinished = job.status?.unfinishedSession == true || maybe
        if (job.busy && job.recovering) {
            val fix = Cards.section(column, getString(R.string.last_cat_restore), rows = true)
            CardRows.tint(Cards.row(fix, OuiIcons.drawable.ic_oui_restart, getString(R.string.home_restoring), null), Level.INFO)
        } else if (!job.busy && (unfinished || job.recovered != null || job.restoreFailed)) {
            val fix = Cards.section(column, getString(R.string.last_cat_restore), rows = true)
            if (job.recovered != null) CardRows.status(fix, Level.OK, getString(R.string.last_restored), null)
            if (job.restoreFailed) CardRows.status(fix, Level.WARN, getString(R.string.last_restore_failed), getString(R.string.last_restore_failed_line))
            if (unfinished) {
                Cards.row(
                    fix, OuiIcons.drawable.ic_oui_restart, getString(R.string.last_restore_title),
                    getString(if (maybe) R.string.last_restore_maybe else R.string.last_restore_summary),
                ) { activity?.let { SessionRestore.confirm(it) } }
            }
        }

        // "Done with this session" hides Last session; never offered while a
        // session is still unfinished, or the friend could orphan the only way
        // to restore One UI's settings (Restore, above).
        if (launch != null && !job.busy && !unfinished) {
            val done = Cards.section(column, title = null, rows = true)
            Cards.row(done, OuiIcons.drawable.ic_oui_checkbox_checked_outline, getString(R.string.last_forget_title), getString(R.string.last_forget_summary)) {
                SessionPrefs.forgetLaunch(ctx)
                activity?.finish()
            }
        }

        // Details: the session's ids, the technical outcome, what the collection said.
        val more = Cards.section(column, title = null, rows = true)
        details(more, getString(R.string.last_details_summary)) { card ->
            if (launch != null) {
                Cards.row(card, 0, getString(R.string.last_id, launch.sessionId), CardRows.dateTime(ctx, launch.wallMs))
                val phone = Profiles.byId(launch.profileId)?.label ?: launch.profileId
                Cards.row(card, 0, getString(R.string.last_details_image, image?.shortName ?: launch.imageId), phone)
            }
            job.outcome?.let { o -> Cards.row(card, 0, o.title, o.detail(system)) }
            // What the collection is reading now ("Collecting 3 of 12: …"), to see where it hangs.
            job.detail?.takeIf { job.busy }?.let { Cards.row(card, 0, it, null) }
            job.message?.let { Cards.row(card, 0, getString(R.string.setup_details_result), it) }
            job.recovered?.let { Cards.row(card, 0, getString(R.string.last_restored), it) }
            zip?.let { Cards.row(card, 0, it.name, null) }
        }
    }

    /** The outcome's title already says how you came back (the tile would say it twice). */
    private fun titleSaysHow(o: OutcomeKind): Boolean = when (o) {
        OutcomeKind.SESSION_LIMIT, OutcomeKind.PREPARE_FAILED -> false
        else -> true
    }

    /** The same words as Welcome back's "how you came back" tile. */
    private fun howCameBack(o: OutcomeKind): Int = when (o) {
        OutcomeKind.USER_RETURN -> R.string.home_how_keys
        OutcomeKind.APP_RETURN -> R.string.home_how_app
        OutcomeKind.GUEST_REBOOT, OutcomeKind.GUEST_DEAD, OutcomeKind.BLACK_SCREEN, OutcomeKind.SESSION_LIMIT, OutcomeKind.BOOT_TIMEOUT ->
            R.string.home_how_auto
        OutcomeKind.HARD_RESET -> R.string.home_how_restart
        OutcomeKind.GUEST_SHUTDOWN -> R.string.home_how_off
        OutcomeKind.PREPARE_FAILED, OutcomeKind.REFUSED -> R.string.home_how_none
        OutcomeKind.DRY_RUN -> R.string.home_how_test
        OutcomeKind.UNKNOWN -> R.string.home_how_other
    }

    private fun confirmCollect() {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.last_collect_dialog_title)
            .setMessage(R.string.last_collect_dialog_message)
            .setPositiveButton(R.string.last_collect_run) { _, _ -> LogJob.start(requireContext()) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }
}
