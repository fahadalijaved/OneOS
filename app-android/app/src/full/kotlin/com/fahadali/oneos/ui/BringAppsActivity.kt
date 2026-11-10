package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.text.format.DateUtils
import android.view.View
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.BringApps
import com.fahadali.oneos.core.model.BringApps.Change
import com.fahadali.oneos.core.model.BringApps.CopyState
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.session.BringAppsJob
import com.fahadali.oneos.session.BringAppsJob.Phase
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Bring apps (on each system's page, next to Root, 0.4.75, owner: "a way to select our 3rd party apps we
 * want to bring over with us to guest OS with its data ... so we dont have to
 * keep logging in"). Three cards: how it works (naming the system set up now),
 * the user apps One UI has with a box to tick each, and the actions.
 *
 * Build 104 (owner: "apps list should have select all button too, and apps
 * whose data or app itself has been updated should be reminded to toggle
 * again ... so newer data is picked"): the list starts with Select all; a
 * brought app's row says what became of it in the system (copied and waiting,
 * installed, not installed) and whether One UI's app or data is newer than
 * the copy, and a line above the list ticks the newer ones in one tap. The
 * ticked apps are copied when the system is booted ([BringAppsJob.beforeLaunch]);
 * Bring now ([BringAppsJob.collect]) does it right away. Then Remove brought
 * apps ([BringAppsJob.clear]), what the stage holds, and Details (each copy,
 * what was skipped, what root said and the system's own install log).
 *
 * Build 109 (owner: "if 2 apps are already present and selected, when i
 * select a 3rd one why it starts to add the previous 2 again too ... it should
 * ask me if i want to recheck data of old apps"): Bring now counts only the
 * ticked apps the system does not have yet, and asks before one it has
 * already is brought again ([BringApps.split], [BringAppsFragment.confirmBring]).
 *
 * Bring is off until [StageCheck] says this page's system is set up, and
 * while its root script is another build's (then: update the system first).
 * One way: One UI's data is only read, the guest never writes back to it.
 */
class BringAppsActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.bring_title)

    override fun createFragment(): Fragment = BringAppsFragment().apply {
        arguments = Bundle().apply { putString(EXTRA_IMAGE, intent.getStringExtra(EXTRA_IMAGE)) }
    }

    companion object {
        const val EXTRA_IMAGE = "image"

        fun intent(ctx: Context, image: ImageRef): Intent =
            Intent(ctx, BringAppsActivity::class.java).putExtra(EXTRA_IMAGE, image.id)
    }
}

class BringAppsFragment : CardsFragment() {
    private val subs = mutableListOf<() -> Unit>()

    /** Read the apps again on a fresh visit (a new install since); a rotation keeps the list and the last result. */
    private var loadOnStart = false

    /** This start already asked root what the stage holds (the page or its stage changed). */
    private var asked = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        loadOnStart = savedInstanceState == null
    }

    override fun onStart() {
        super.onStart()
        asked = false
        syncStage()
        subs += BringAppsJob.observe { redraw() }
        subs += StageCheck.observe { syncStage(); redraw() }
        // The same page again: what became of the copies, and what is newer on One UI, is read again.
        if (!asked) BringAppsJob.refresh(requireContext())
        val st = BringAppsJob.state
        if (!st.busy && (loadOnStart || st.candidates == null)) BringAppsJob.load(requireContext())
        loadOnStart = false
        if (StageCheck.state.result == null && !StageCheck.state.busy) {
            StageCheck.start(requireContext(), StageCheck.Mode.STAGE_ONLY)
        }
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val st = BringAppsJob.state
        val stage = StageCheck.state
        val status = stage.result?.status?.takeIf { it.ours }
        // Another system is set up now than the one whose page opened this screen.
        val other = status != null && !onThisPage(status.marker?.imageId)
        val prepared = status != null && !other
        val system = systemName()
        val candidates = st.candidates
        val ticked = st.selected.size
        // The job's brought apps are this page's stage's (not another page's, kept while a bring runs).
        val synced = prepared && st.stageKey != null && st.stageKey == BringAppsJob.stageKey(status?.marker)
        // What became of each copy in this page's stage, once root was asked.
        val copies = if (synced) st.copies.orEmpty().associateBy { it.pkg } else emptyMap()
        // The stage's root script is another build's: nothing can be brought until the system is updated.
        val stale = synced && st.stale
        // The ticked apps: the ones to copy, and the ones the system has already (asked about first).
        val split = BringApps.split(st.selected, if (synced) st.copies else null, if (synced) st.brought else emptySet())

        // How it works: what Bring copies, where to, and that it is one way.
        val about = Cards.section(column, getString(R.string.bring_card_about))
        CardRows.text(about, getString(R.string.bring_about_body, system))
        CardRows.text(about, getString(R.string.bring_about_one_way, system), R.style.OneOS_Text_Caption)

        // The apps on One UI, a box each. The header counts the ticks.
        val apps = Cards.section(
            column, getString(R.string.bring_card_apps),
            trailing = if (ticked > 0) resources.getQuantityString(R.plurals.bring_ticked_n, ticked, ticked) else null,
            trailingLevel = Level.INFO, rows = true,
        )
        when {
            candidates == null && st.phase == Phase.LOADING ->
                CardRows.tint(Cards.row(apps, OuiIcons.drawable.ic_oui_refresh, getString(R.string.bring_loading), null), Level.INFO)
            candidates == null -> {
                CardRows.status(apps, Level.WARN, getString(R.string.bring_not_read), st.message)
                if (!st.busy) Cards.row(apps, OuiIcons.drawable.ic_oui_refresh, getString(R.string.bring_look_again), null) { BringAppsJob.load(ctx) }
            }
            candidates.isEmpty() ->
                CardRows.status(apps, Level.INFO, getString(R.string.bring_none), getString(R.string.bring_none_summary, system))
            else -> {
                // Brought and installed there, and One UI's app or data changed since: one tap ticks them.
                val newer = candidates.filter { c -> c.pkg !in st.selected && copies[c.pkg]?.let { it.state == CopyState.INSTALLED && it.newer } == true }
                if (newer.isNotEmpty()) {
                    val tickThem: ((View) -> Unit)? = if (st.busy) null else { _ -> BringAppsJob.tick(ctx, newer.map { it.pkg }) }
                    CardRows.status(
                        apps, Level.INFO,
                        resources.getQuantityString(R.plurals.bring_newer_n, newer.size, newer.size),
                        getString(R.string.bring_newer_summary, system), tickThem,
                    )
                }
                CardRows.tick(
                    apps, getString(R.string.bring_select_all),
                    resources.getQuantityString(R.plurals.bring_select_all_n, candidates.size, candidates.size),
                    checked = ticked == candidates.size,
                    enabled = !st.busy,
                ) { on -> BringAppsJob.setAll(ctx, on) }
                for (c in candidates) {
                    CardRows.tick(
                        apps, c.label,
                        rowSummary(c, copies[c.pkg], c.pkg in st.selected, system),
                        checked = c.pkg in st.selected,
                        enabled = !st.busy,
                    ) { on -> BringAppsJob.toggle(ctx, c.pkg, on) }
                }
            }
        }

        // Bring now, Remove, what the stage holds, Details.
        val actions = Cards.section(column, title = null, rows = true)
        when {
            prepared -> Unit
            stage.busy -> CardRows.tint(Cards.row(actions, OuiIcons.drawable.ic_oui_refresh, getString(R.string.bring_stage_checking), null), Level.INFO)
            stage.result == null -> {
                CardRows.status(actions, Level.WARN, getString(R.string.bring_stage_not_read), getString(R.string.bring_stage_not_read_summary))
                Cards.row(actions, OuiIcons.drawable.ic_oui_refresh, getString(R.string.bring_stage_check_again), null) {
                    StageCheck.start(ctx, StageCheck.Mode.STAGE_ONLY)
                }
            }
            other -> CardRows.status(
                actions, Level.WARN, getString(R.string.bring_other_system, system),
                getString(R.string.bring_other_system_summary, Images.systemName(status?.marker?.imageId?.let { Images.byId(it) }), system),
            )
            else -> CardRows.status(actions, Level.WARN, getString(R.string.bring_no_stage), getString(R.string.bring_no_stage_summary))
        }
        if (stale) {
            CardRows.status(actions, Level.WARN, getString(R.string.bring_update_first, system), getString(R.string.bring_update_first_summary, system))
        }
        when {
            st.phase == Phase.COLLECTING -> {
                val n = if (st.working > 0) st.working else ticked
                CardRows.tint(
                    Cards.row(
                        actions, OuiIcons.drawable.ic_oui_download,
                        resources.getQuantityString(R.plurals.bring_working_n, n, n),
                        st.current?.let { getString(R.string.bring_working_at, label(it)) } ?: getString(R.string.bring_working_summary, system),
                    ),
                    Level.INFO,
                )
            }
            ticked == 0 -> CardRows.row(
                actions, OuiIcons.drawable.ic_oui_download,
                getString(R.string.bring_do_none), getString(R.string.bring_do_none_summary, system),
                enabled = false,
            )
            else -> {
                val fresh = split.fresh.size
                val there = split.there.size
                CardRows.row(
                    actions, OuiIcons.drawable.ic_oui_download,
                    if (fresh > 0) resources.getQuantityString(R.plurals.bring_do_n, fresh, fresh)
                    else resources.getQuantityString(R.plurals.bring_again_n, there, there),
                    when {
                        there == 0 -> getString(R.string.bring_do_summary, system)
                        fresh == 0 -> getString(R.string.bring_again_summary, system)
                        else -> resources.getQuantityString(R.plurals.bring_do_there_summary, there, there, system)
                    },
                    enabled = prepared && !stale && !st.busy && candidates != null,
                ) { confirmBring(split, system) }
            }
        }
        if (st.phase == Phase.CLEARING) {
            CardRows.tint(Cards.row(actions, OuiIcons.drawable.ic_oui_delete_outline, getString(R.string.bring_removing), null), Level.INFO)
        } else if (synced && st.brought.isNotEmpty()) {
            CardRows.row(
                actions, OuiIcons.drawable.ic_oui_delete_outline,
                getString(R.string.bring_remove), getString(R.string.bring_remove_summary, system),
                enabled = !stale && !st.busy,
            ) { confirmClear(system) }
        }

        // The last action's result; on a fresh visit, what the stage holds and what became of it.
        val message = st.message
        val list = copies.values.sortedBy { label(it.pkg).lowercase() }
        when {
            st.busy -> Unit
            message != null && st.failed ->
                CardRows.status(actions, Level.WARN, message, null)
            message != null && st.phase == Phase.DONE -> CardRows.status(
                actions, Level.OK, message,
                when {
                    st.brought.isEmpty() -> null
                    st.skipped.isNotEmpty() -> getString(R.string.bring_done_skipped)
                    else -> getString(R.string.bring_done_summary, system)
                },
            )
            list.isNotEmpty() -> {
                val installed = list.count { it.state == CopyState.INSTALLED }
                val waiting = list.count { it.state == CopyState.WAITING }
                val failed = list.count { it.state == CopyState.FAILED }
                CardRows.status(
                    actions,
                    when {
                        failed > 0 -> Level.WARN
                        waiting > 0 -> Level.INFO
                        else -> Level.OK
                    },
                    listOfNotNull(
                        if (installed > 0) getString(R.string.bring_count_installed, installed, system) else null,
                        if (waiting > 0) getString(R.string.bring_count_waiting, waiting) else null,
                        if (failed > 0) getString(R.string.bring_count_failed, failed) else null,
                    ).joinToString(" · "),
                    when {
                        failed > 0 -> getString(R.string.bring_count_failed_summary, system)
                        waiting > 0 -> getString(R.string.bring_count_waiting_summary, system)
                        else -> null
                    },
                )
            }
            synced && st.brought.isNotEmpty() -> CardRows.status(
                actions, Level.INFO,
                resources.getQuantityString(R.plurals.bring_brought_n, st.brought.size, st.brought.size),
                getString(R.string.bring_count_waiting_summary, system),
            )
        }

        // Details: what the guest does, each copy and what became of it, what was skipped, what root and the guest said.
        details(actions, getString(R.string.bring_details_summary, system)) { card ->
            CardRows.text(card, getString(R.string.bring_details_how, system), R.style.OneOS_Text_Caption, inList = true)
            when {
                list.isNotEmpty() -> {
                    CardRows.text(card, getString(R.string.bring_details_brought), R.style.OneOS_Text_Caption_Strong, inList = true)
                    for (c in list) Cards.row(card, 0, label(c.pkg), copyLines(c, system))
                }
                synced && st.brought.isNotEmpty() -> {
                    CardRows.text(card, getString(R.string.bring_details_brought), R.style.OneOS_Text_Caption_Strong, inList = true)
                    for (pkg in st.brought.sorted()) Cards.row(card, 0, label(pkg), pkg)
                }
                else -> CardRows.text(card, getString(R.string.bring_details_none), R.style.OneOS_Text_Caption_Strong, inList = true)
            }
            if (st.skipped.isNotEmpty()) {
                CardRows.text(card, getString(R.string.bring_details_skipped), R.style.OneOS_Text_Caption, inList = true)
                for (pkg in st.skipped.sorted()) Cards.row(card, 0, label(pkg), pkg)
            }
            if (st.notes.isNotEmpty()) Cards.row(card, 0, getString(R.string.bring_details_said), st.notes.joinToString("\n"))
            if (synced && st.log.isNotEmpty()) Cards.row(card, 0, getString(R.string.bring_details_log, system), st.log.joinToString("\n"))
            message?.let { Cards.row(card, 0, getString(R.string.setup_details_result), it) }
        }
    }

    /** An app's line in the list: its version and package, or what became of its copy in the system. */
    private fun rowSummary(c: BringAppsJob.Candidate, copy: BringApps.Copy?, ticked: Boolean, system: String): String = when {
        copy == null -> if (c.version.isBlank()) c.pkg else getString(R.string.bring_app_summary, c.version, c.pkg)
        ticked && copy.state == CopyState.INSTALLED -> getString(R.string.bring_row_again, system)
        ticked -> getString(R.string.bring_row_ticked, system)
        copy.state == CopyState.WAITING -> getString(R.string.bring_row_waiting, system)
        copy.state == CopyState.FAILED -> getString(R.string.bring_row_failed, system)
        copy.change == Change.APP -> getString(R.string.bring_row_newer_app, system)
        copy.change == Change.DATA -> getString(R.string.bring_row_newer_data, system)
        copy.stamp > 0 -> getString(R.string.bring_row_installed_on, system, date(copy.stamp))
        else -> getString(R.string.bring_row_installed, system)
    }

    /** A copy in Details: the package, what became of it, and what One UI has that it does not. */
    private fun copyLines(c: BringApps.Copy, system: String): String = listOfNotNull(
        c.pkg,
        when (c.state) {
            CopyState.WAITING ->
                if (c.stamp > 0) getString(R.string.bring_state_waiting_on, date(c.stamp)) else getString(R.string.bring_state_waiting)
            CopyState.INSTALLED ->
                if (c.stamp > 0) getString(R.string.bring_state_installed_on, system, date(c.stamp)) else getString(R.string.bring_state_installed, system)
            CopyState.FAILED -> getString(R.string.bring_state_failed, system, c.why ?: getString(R.string.bring_state_no_reason))
        },
        when (c.change) {
            Change.SAME -> null
            Change.DATA -> getString(R.string.bring_change_data)
            Change.APP -> getString(R.string.bring_change_app)
            Change.GONE -> getString(R.string.bring_change_gone)
        },
    ).joinToString("\n")

    /** "10 Nov, 07:40": when a copy was made (epoch seconds). */
    private fun date(epoch: Long): String = DateUtils.formatDateTime(
        requireContext(), epoch * 1000,
        DateUtils.FORMAT_SHOW_DATE or DateUtils.FORMAT_SHOW_TIME or DateUtils.FORMAT_ABBREV_MONTH or DateUtils.FORMAT_NO_YEAR,
    )

    /** The system whose page opened this screen; null from anywhere else (then: the one set up now). */
    private fun pageImage(): ImageRef? = arguments?.getString(BringAppsActivity.EXTRA_IMAGE)?.let { Images.byId(it) }

    private fun onThisPage(imageId: String?): Boolean = pageImage()?.let { it.id == imageId } ?: true

    /** The ticks shown are this page's system's; the brought set is the one of the stage set up now, when that is this page's system. */
    private fun syncStage() {
        val status = StageCheck.state.result?.status
        val page = pageImage()?.id
        if (status == null) {
            // Not read yet: keep what is shown, unless that is another system's.
            if (page != null && BringAppsJob.state.imageId != page) BringAppsJob.page(requireContext(), page, null)
            return
        }
        val marker = status.marker?.takeIf { status.ours && onThisPage(it.imageId) }
        if (BringAppsJob.page(requireContext(), page ?: status.marker?.takeIf { status.ours }?.imageId, marker)) asked = true
    }

    /** "Pixel 11 Fold": this page's system, else the one set up now, or "the other system" while none is known. */
    private fun systemName(): String {
        pageImage()?.let { return Images.systemName(it) }
        val status = StageCheck.state.result?.status?.takeIf { it.ours }
        return Images.systemName(status?.marker?.imageId?.let { Images.byId(it) })
    }

    /** The app's name as One UI shows it, or the package when it is gone. */
    private fun label(pkg: String): String =
        BringAppsJob.state.candidates?.firstOrNull { it.pkg == pkg }?.label ?: pkg

    /**
     * Bring now. Only new apps ticked: one question, as before. Apps the system
     * has already among them: the new ones are brought either way, and the
     * owner says whether the others are brought again (their data there is
     * replaced) or left as they are, which also takes their ticks off. Only
     * apps it has already: bringing them again is the whole question.
     */
    private fun confirmBring(split: BringApps.Ticked, system: String) {
        val ctx = requireContext()
        val fresh = split.fresh.size
        val there = split.there.size
        val dialog = AlertDialog.Builder(ctx).setNegativeButton(android.R.string.cancel, null)
        when {
            there == 0 -> dialog
                .setTitle(getString(R.string.bring_confirm_title, system))
                .setMessage(resources.getQuantityString(R.plurals.bring_confirm_body, fresh, fresh, system))
                .setPositiveButton(R.string.bring_confirm_do) { _, _ -> BringAppsJob.collect(ctx) }
            fresh == 0 -> dialog
                .setTitle(resources.getQuantityString(R.plurals.bring_again_title, there, there))
                .setMessage(resources.getQuantityString(R.plurals.bring_again_body, there, there, system))
                .setPositiveButton(R.string.bring_again_do) { _, _ -> BringAppsJob.collect(ctx) }
            else -> dialog
                .setTitle(getString(R.string.bring_confirm_title, system))
                .setMessage(
                    resources.getQuantityString(R.plurals.bring_confirm_body, fresh, fresh, system) + "\n\n" +
                        resources.getQuantityString(R.plurals.bring_confirm_there, there, there, system),
                )
                .setPositiveButton(R.string.bring_confirm_new) { _, _ -> BringAppsJob.collect(ctx, split.fresh) }
                .setNeutralButton(getString(R.string.bring_confirm_all, fresh + there)) { _, _ -> BringAppsJob.collect(ctx) }
        }
        dialog.show()
    }

    private fun confirmClear(system: String) {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.bring_remove_title)
            .setMessage(getString(R.string.bring_remove_confirm, system))
            .setPositiveButton(R.string.bring_remove_do) { _, _ -> BringAppsJob.clear(requireContext()) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }
}
