package com.fahadali.oneos.ui

import android.content.res.ColorStateList
import android.graphics.Typeface
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Setting up (SettingUp.dc.html; Home's "Show progress", and every setup a
 * fix action starts): the ring with percent and time left from
 * [PrepareJob.State], "Setting up {system}", the three user steps
 * ([PrepareJob.UserStep]) with the current one's detail, the "keep OneOS
 * open" note, Stop (as before: [PrepareJob.cancel], no confirm), the screen
 * kept on while it runs, then the result with its plain message's own fix
 * button. The nine technical steps, the job's message and what was moved
 * aside are behind Details. The technical Prepare page stays in Advanced.
 */
class SetupProgressActivity : ToolbarActivity() {
    // The bar shows the title only once the hero has scrolled away (setBarTitle).
    override val screenTitle: CharSequence get() = ""

    override val layoutRes: Int get() = R.layout.activity_setup_progress

    override fun createFragment(): Fragment = SetupProgressFragment()

    private var unsubscribe: (() -> Unit)? = null

    fun setBarTitle(text: CharSequence) {
        toolbarLayout.setTitle(text)
    }

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
}

class SetupProgressFragment : Fragment() {
    private enum class StepState { DONE, CURRENT, PENDING, STOPPED, FAILED }

    private var unsubscribe: (() -> Unit)? = null
    private var expanded = false
    private var stopping = false
    private var barTitle: CharSequence = ""
    private var barTitleShown = false
    private var stepRows: List<View> = emptyList()
    private var titleColors: ColorStateList? = null
    private var detailsRow: View? = null
    /** The set-aside copy the old copies were listed for (once per screen). */
    private var listedFor: String? = null
    private var techList: LinearLayout? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.setup_progress_screen, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        expanded = savedInstanceState?.getBoolean(KEY_EXPANDED) ?: true
        val inflater = LayoutInflater.from(view.context)

        // The inner screen: one centred column of at most 600dp, its footer button too.
        val density = resources.displayMetrics.density
        val extra = ((resources.configuration.screenWidthDp - MAX_COLUMN_DP) / 2).coerceAtLeast(0)
        if (extra > 0 && !resources.getBoolean(R.bool.home_two_pane)) {
            val column = view.findViewById<LinearLayout>(R.id.setup_column)
            val side = column.paddingStart + (extra * density).toInt()
            column.setPaddingRelative(side, column.paddingTop, side, column.paddingBottom)
            activity?.findViewById<View>(R.id.setup_footer)?.let { f ->
                val fs = f.paddingStart + (extra * density).toInt()
                f.setPaddingRelative(fs, f.paddingTop, fs, f.paddingBottom)
            }
        }

        val steps = view.findViewById<LinearLayout>(R.id.setup_steps)
        stepRows = PrepareJob.UserStep.entries.map {
            val row = inflater.inflate(R.layout.setup_step, steps, false)
            steps.addView(row)
            row
        }
        titleColors = stepRows.firstOrNull()?.findViewById<TextView>(R.id.setup_step_title)?.textColors

        val slot = view.findViewById<LinearLayout>(R.id.setup_details_slot)
        val card = Cards.section(slot, title = null, rows = true, gapAbove = false)
        detailsRow = Cards.row(card, OuiIcons.drawable.ic_oui_info_outline, getString(R.string.setup_details), getString(R.string.setup_details_summary)) {
            expanded = !expanded
            bind(PrepareJob.state)
        }
        val list = LinearLayout(view.context)
        list.orientation = LinearLayout.VERTICAL
        card.addView(list, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        techList = list

        val heroTitle = view.findViewById<TextView>(R.id.setup_title)
        view.findViewById<NestedScrollView>(R.id.setup_scroll).setOnScrollChangeListener(
            NestedScrollView.OnScrollChangeListener { _, _, scrollY, _, _ ->
                val show = scrollY > heroTitle.bottom
                if (show != barTitleShown) {
                    barTitleShown = show
                    (activity as? SetupProgressActivity)?.setBarTitle(if (show) barTitle else "")
                }
            },
        )
    }

    override fun onStart() {
        super.onStart()
        val prepare = PrepareJob.observe { bind(it) }
        // Delete the old copy (0.4.11) runs in OldStagesJob.
        val old = OldStagesJob.observe { bind(PrepareJob.state) }
        unsubscribe = { prepare(); old() }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean(KEY_EXPANDED, expanded)
    }

    private fun bind(s: PrepareJob.State) {
        val root = view ?: return
        val ctx = root.context
        val phase = s.phase
        if (phase != PrepareJob.Phase.RUNNING) stopping = false
        val idle = phase == PrepareJob.Phase.IDLE

        // The system: the job's, else (its first seconds) the picked download's.
        val profile = StageCheck.state.result?.facts?.let { Profiles.resolve(it).profile }
        val image = s.image ?: FixActions.pickedImage(ctx, profile)
        val system = image?.let { Images.systemName(it, profile) }

        root.findViewById<OsArtworkView>(R.id.setup_artwork).bind(image)
        root.findViewById<androidx.appcompat.widget.SeslProgressBar>(R.id.setup_linear_progress).apply {
            isIndeterminate = s.busy && s.percent == null
            progress = if (phase == PrepareJob.Phase.DONE) 100 else s.percent ?: 0
        }
        // The ring.
        val percent = if (phase == PrepareJob.Phase.DONE) 100 else s.percent ?: 0
        val ring = root.findViewById<SetupRingView>(R.id.setup_ring)
        ring.setArcColor(
            ctx.getColor(
                when (phase) {
                    PrepareJob.Phase.STOPPED -> R.color.oneos_warn_text
                    PrepareJob.Phase.FAILED -> R.color.oneos_block_text
                    else -> R.color.oneos_primary_text
                },
            ),
        )
        ring.setPercent(percent)
        root.findViewById<TextView>(R.id.setup_percent).text = getString(R.string.setup_percent, percent)
        val under = when (phase) {
            PrepareJob.Phase.RUNNING -> eta(s.etaSeconds)
            PrepareJob.Phase.DONE -> getString(R.string.setup_ring_done)
            PrepareJob.Phase.STOPPED -> getString(R.string.setup_ring_stopped)
            PrepareJob.Phase.FAILED -> getString(R.string.setup_ring_failed)
            PrepareJob.Phase.IDLE -> ""
        }
        root.findViewById<TextView>(R.id.setup_eta).text = under
        val ringBox = root.findViewById<View>(R.id.setup_ring_box)
        ringBox.visibility = View.GONE
        ringBox.contentDescription = getString(R.string.setup_ring_desc, percent, under)

        // The title and its line (the result's plain message once it stops).
        val title: String
        val subtitle: String
        when (phase) {
            PrepareJob.Phase.IDLE -> {
                title = getString(R.string.setup_idle_title)
                subtitle = getString(R.string.setup_idle_subtitle)
            }
            PrepareJob.Phase.RUNNING -> {
                title = system?.let { getString(R.string.setup_title, it) } ?: getString(R.string.setup_label)
                subtitle = getString(R.string.setup_subtitle)
            }
            PrepareJob.Phase.DONE -> {
                title = system?.let { getString(R.string.setup_done_title, it) } ?: getString(R.string.setup_ring_done)
                subtitle = getString(R.string.setup_done_subtitle)
            }
            PrepareJob.Phase.STOPPED, PrepareJob.Phase.FAILED -> {
                title = s.plain?.title ?: getString(R.string.setup_failed_title)
                subtitle = s.plain?.line.orEmpty()
            }
        }
        val titleView = root.findViewById<TextView>(R.id.setup_title)
        // Set only on a change: it is a polite live region.
        if (titleView.text.toString() != title) titleView.text = title
        val subtitleView = root.findViewById<TextView>(R.id.setup_subtitle)
        subtitleView.text = subtitle
        subtitleView.visibility = if (subtitle.isEmpty()) View.GONE else View.VISIBLE
        barTitle = title
        if (barTitleShown) (activity as? SetupProgressActivity)?.setBarTitle(title)

        // The three steps.
        root.findViewById<View>(R.id.setup_steps).visibility = if (idle) View.GONE else View.VISIBLE
        val noDownload = s.plan?.let { !it.needsDownload } ?: (SessionPrefs.source(ctx) == SessionPrefs.Source.ON_PHONE)
        PrepareJob.UserStep.entries.zip(stepRows).forEach { (u, row) -> bindStep(row, u, s, stepState(u, s), system, image, noDownload) }

        root.findViewById<View>(R.id.setup_keep_open).visibility = if (phase == PrepareJob.Phase.RUNNING) View.VISIBLE else View.GONE
        root.findViewById<View>(R.id.setup_details_slot).visibility = if (idle) View.GONE else View.VISIBLE
        bindDetails(s)
        bindFooter(s)
    }

    private fun stepState(u: PrepareJob.UserStep, s: PrepareJob.State): StepState {
        val current = s.userStep
        return when {
            s.phase == PrepareJob.Phase.DONE -> StepState.DONE
            s.phase == PrepareJob.Phase.IDLE || current == null -> StepState.PENDING
            u.ordinal < current.ordinal -> StepState.DONE
            u.ordinal > current.ordinal -> StepState.PENDING
            s.phase == PrepareJob.Phase.RUNNING -> StepState.CURRENT
            s.phase == PrepareJob.Phase.STOPPED -> StepState.STOPPED
            else -> StepState.FAILED
        }
    }

    private fun bindStep(
        row: View,
        u: PrepareJob.UserStep,
        s: PrepareJob.State,
        state: StepState,
        system: String?,
        image: ImageRef?,
        noDownload: Boolean,
    ) {
        val ctx = row.context
        val title = when (u) {
            PrepareJob.UserStep.CHECK_DOWNLOAD -> getString(if (noDownload) R.string.setup_step_check_phone else R.string.setup_step_check)
            PrepareJob.UserStep.INSTALL -> system?.let { getString(R.string.setup_step_install, it) } ?: getString(R.string.setup_step_install_generic)
            PrepareJob.UserStep.FINISH -> getString(R.string.setup_step_finish)
        }
        val pending = getString(
            when (u) {
                PrepareJob.UserStep.CHECK_DOWNLOAD -> if (noDownload) R.string.setup_step_check_phone_pending else R.string.setup_step_check_pending
                PrepareJob.UserStep.INSTALL -> R.string.setup_step_install_pending
                PrepareJob.UserStep.FINISH -> R.string.setup_step_finish_pending
            },
        )
        val done = getString(
            when (u) {
                PrepareJob.UserStep.CHECK_DOWNLOAD -> if (noDownload) R.string.setup_step_check_phone_done else R.string.setup_step_check_done
                PrepareJob.UserStep.INSTALL -> R.string.setup_step_install_done
                PrepareJob.UserStep.FINISH -> R.string.setup_step_finish_done
            },
        )
        val detail = when (state) {
            StepState.DONE -> done
            StepState.PENDING -> pending
            StepState.CURRENT -> currentDetail(u, s, image) ?: pending
            StepState.STOPPED -> getString(R.string.setup_step_stopped)
            StepState.FAILED -> getString(R.string.setup_step_failed)
        }
        row.findViewById<ImageView>(R.id.setup_step_icon).setImageResource(
            when (state) {
                StepState.DONE -> R.drawable.oneos_badge_ok
                StepState.CURRENT -> R.drawable.ic_oneos_step_current
                StepState.PENDING -> R.drawable.ic_oneos_step_pending
                StepState.STOPPED -> R.drawable.oneos_badge_warn
                StepState.FAILED -> R.drawable.oneos_badge_block
            },
        )
        val titleView = row.findViewById<TextView>(R.id.setup_step_title)
        titleView.text = title
        titleView.setTypeface(null, if (state == StepState.CURRENT) Typeface.BOLD else Typeface.NORMAL)
        if (state == StepState.PENDING) {
            titleView.setTextColor(ctx.getColor(R.color.oneos_text_body))
        } else {
            titleColors?.let { titleView.setTextColor(it) }
        }
        row.findViewById<TextView>(R.id.setup_step_detail).text = detail
        val stateWord = getString(
            when (state) {
                StepState.DONE -> R.string.setup_state_done
                StepState.CURRENT -> R.string.setup_state_current
                StepState.PENDING -> R.string.setup_state_pending
                StepState.STOPPED -> R.string.setup_state_stopped
                StepState.FAILED -> R.string.setup_state_failed
            },
        )
        row.contentDescription = getString(R.string.setup_step_desc, title, stateWord, detail)
    }

    /** The live line of the step in progress ("1.2 GB of 2.5 GB"); null = its fixed line. */
    private fun currentDetail(u: PrepareJob.UserStep, s: PrepareJob.State, image: ImageRef?): String? = when (u) {
        // Hashing the download: bytes read of the download's size.
        PrepareJob.UserStep.CHECK_DOWNLOAD ->
            if (s.step == PrepareJob.Step.HASH && s.bytesDone > 0 && image != null) {
                getString(R.string.setup_step_bytes, Units.bytes(s.bytesDone.coerceAtMost(image.gzBytes)), Units.bytes(image.gzBytes))
            } else {
                null
            }
        // Unpacking: the job's own "2.0 GB of 4.7 GB" (or "Making sure it installed correctly…").
        PrepareJob.UserStep.INSTALL -> if (s.step == PrepareJob.Step.IMAGE) s.detail else null
        PrepareJob.UserStep.FINISH -> null
    }

    /** Details: the nine technical steps (as the Prepare page), the job's message, the check that stopped it, what was moved aside. */
    private fun bindDetails(s: PrepareJob.State) {
        val row = detailsRow ?: return
        val list = techList ?: return
        row.stateDescription = getString(if (expanded) R.string.setup_expanded else R.string.setup_collapsed)
        Cards.setRowEnd(row, if (expanded) OuiIcons.drawable.ic_oui_keyboard_arrow_up else OuiIcons.drawable.ic_oui_keyboard_arrow_down)
        list.removeAllViews()
        list.visibility = if (expanded) View.VISIBLE else View.GONE
        if (!expanded) return

        fun untinted(r: View) {
            // Status drawables carry their own colours; oneos_row tints line icons.
            r.findViewById<ImageView>(R.id.oneos_row_icon).imageTintList = null
        }
        for (step in PrepareJob.Step.entries) {
            val icon = when {
                s.phase == PrepareJob.Phase.DONE || step in s.done -> R.drawable.oneos_badge_ok
                step == s.step && s.busy -> R.drawable.ic_oneos_step_current
                step == s.step && s.phase == PrepareJob.Phase.STOPPED -> R.drawable.oneos_badge_warn
                step == s.step && s.phase == PrepareJob.Phase.FAILED -> R.drawable.oneos_badge_block
                else -> R.drawable.ic_oneos_step_pending
            }
            untinted(Cards.row(list, icon, step.label, if (step == s.step) s.detail else null))
        }
        s.message?.let { Cards.row(list, 0, getString(R.string.setup_details_result), it) }
        s.finding?.let { f -> untinted(Cards.row(list, Cards.badge(f.level), f.title, f.detail.ifEmpty { null })) }
        s.infos.takeIf { it.isNotEmpty() }?.let { Cards.row(list, 0, getString(R.string.setup_details_moved), it.joinToString("\n")) }
    }

    /** Stop while it runs; then Done, or the plain message's fix and Close. */
    private fun bindFooter(s: PrepareJob.State) {
        val a = activity as? SetupProgressActivity ?: return
        val primary = a.findViewById<Button>(R.id.setup_primary) ?: return
        val secondary = a.findViewById<Button>(R.id.setup_secondary) ?: return

        fun show(b: Button, text: CharSequence?, enabled: Boolean = true, onClick: () -> Unit = {}) {
            if (text == null) {
                b.visibility = View.GONE
                b.setOnClickListener(null)
                return
            }
            b.visibility = View.VISIBLE
            b.text = text
            b.isEnabled = enabled
            b.setOnClickListener { onClick() }
        }

        when (s.phase) {
            PrepareJob.Phase.RUNNING -> {
                show(primary, null)
                show(secondary, getString(if (stopping) R.string.setup_stopping else R.string.setup_stop), enabled = !stopping) {
                    // As before: stops after the current file, no confirm (nothing is lost; set up again later).
                    stopping = true
                    PrepareJob.cancel()
                    bind(PrepareJob.state)
                }
            }
            PrepareJob.Phase.DONE -> {
                show(primary, getString(R.string.setup_done_button)) { SystemsNav.home(a) }
                // 0.4.11: a fresh setup kept the system before as an old copy; delete it from here.
                val aside = asideCopy(s)
                val old = OldStagesJob.state
                // Its size for the question: list the old copies once (read only).
                if (aside != null && listedFor != aside && !old.busy && old.stages?.none { it.name == aside } != false) {
                    listedFor = aside
                    OldStagesJob.refresh(a)
                }
                when {
                    aside == null -> show(secondary, null)
                    old.deletedNames?.contains(aside) == true ->
                        show(secondary, getString(R.string.setup_old_deleted, Units.bytes((old.freedKib ?: 0) * 1024)), enabled = false)
                    old.phase == OldStagesJob.Phase.DELETING -> show(secondary, getString(R.string.setup_old_deleting), enabled = false)
                    old.deletedNames != null && old.deleteFailed -> show(secondary, getString(R.string.setup_old_not_deleted), enabled = false)
                    else -> show(secondary, getString(R.string.setup_delete_old), enabled = !old.busy) { confirmDeleteOld(aside) }
                }
            }
            PrepareJob.Phase.STOPPED, PrepareJob.Phase.FAILED -> {
                val fix = s.plain?.takeIf { it.action != FixAction.NONE && it.action != FixAction.ACKNOWLEDGE && it.actionLabel != null }
                show(primary, fix?.actionLabel) { if (fix != null) FixActions.run(a, fix.action, s.image) }
                show(secondary, getString(R.string.setup_close)) { SystemsNav.home(a) }
            }
            PrepareJob.Phase.IDLE -> {
                show(primary, null)
                show(secondary, getString(R.string.setup_close)) { SystemsNav.home(a) }
            }
        }
        val lp = secondary.layoutParams as? ViewGroup.MarginLayoutParams ?: return
        val top = if (primary.visibility == View.VISIBLE) (8 * resources.displayMetrics.density).toInt() else 0
        if (lp.topMargin != top) {
            lp.topMargin = top
            secondary.layoutParams = lp
        }
    }

    /** The copy this setup set aside (root's "aside <path>" result), as Free up space names it. */
    private fun asideCopy(s: PrepareJob.State): String? =
        s.infos.lastOrNull { it.startsWith("aside ") }?.substringAfter("aside ")?.trim()?.substringAfterLast('/')
            ?.takeIf { it.startsWith("oneos.old-") }

    private fun confirmDeleteOld(name: String) {
        val ctx = requireContext()
        // The size, when Free up space has listed it.
        val size = OldStagesJob.state.stages?.firstOrNull { it.name == name }?.let { Units.bytes(it.kib * 1024) }
            ?: getString(R.string.setup_old_size_unknown)
        AlertDialog.Builder(ctx)
            .setTitle(R.string.setup_delete_old_title)
            .setMessage(getString(R.string.setup_delete_old_message, size))
            .setPositiveButton(R.string.space_delete_run) { _, _ -> OldStagesJob.deleteAll(ctx, setOf(name)) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun eta(seconds: Int?): String = when {
        seconds == null -> getString(R.string.setup_eta_estimating)
        seconds < 60 -> getString(R.string.setup_eta_soon)
        else -> getString(R.string.setup_eta_minutes, (seconds + 59) / 60)
    }

    private companion object {
        const val KEY_EXPANDED = "details_expanded"
        const val MAX_COLUMN_DP = 600
    }
}
