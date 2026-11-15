package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.content.res.AppCompatResources
import androidx.appcompat.widget.SeslProgressBar
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.session.OneiosJob
import dev.oneuiproject.oneui.widget.CardItemView

/**
 * Set up iOS 27 (docs/oneios.md, "In the app"): the Android systems' Setting up screen
 * (activity_setup_progress, setup_progress_screen, the same step rows, rings and footer) for the iOS
 * system's steps ([OneiosFlow]): check this phone, get the OneiOS runtime, import the iOS image set,
 * iOS's data, the last check before the switch. The title says what to do now, the footer's main
 * button does it (one action), the steps say what is done and with which versions and checks, and the
 * line under them what comes next. A download or an import shows its bytes here; Stop ends it.
 * Once root's preflight passes, Continue opens iOS 27's page (OneiosActivity), where the switch is.
 */
class OneiosSetupActivity : EdgeToEdgeActivity() {
    private lateinit var picker: OneiosPicker
    private var unsubscribe: (() -> Unit)? = null
    private var stepRows: List<Pair<OneiosFlow.Step, CardItemView>> = emptyList()
    private var stopping = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        picker = OneiosPicker(this, savedInstanceState)
        setContentView(R.layout.activity_setup_progress)
        layoutInflater.inflate(R.layout.setup_progress_screen, findViewById<FrameLayout>(R.id.fragment_container), true)
        findViewById<View>(R.id.setup_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.setup_toolbar).apply {
            setNavigationIcon(dev.oneuiproject.oneui.R.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
        }
        findViewById<NestedScrollView>(R.id.setup_scroll).apply {
            isNestedScrollingEnabled = false
            clipToPadding = false
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(getColor(R.color.oneos_page_background))
            seslSetFadingEdgeWindowBottomAlignment(false)
            seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        }
        findViewById<OsArtworkView>(R.id.setup_artwork).bindArtwork(R.drawable.os_oneios)
        val steps = findViewById<LinearLayout>(R.id.setup_steps)
        Cards.round(steps)
        stepRows = OneiosFlow.Step.entries.map { step ->
            step to (Cards.row(steps, R.drawable.ic_oneos_step_pending, OneiosActions.stepTitle(this, step)) as CardItemView).apply {
                isClickable = false
                isFocusable = false
            }
        }
        if (!resources.getBoolean(R.bool.home_two_pane)) findViewById<View>(R.id.setup_title).visibility = View.GONE
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        picker.save(outState)
    }

    override fun onStart() {
        super.onStart()
        unsubscribe = OneiosJob.observe { bind(it) }
    }

    override fun onResume() {
        super.onResume()
        if (!OneiosJob.state.busy) OneiosJob.refresh(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun bind(s: OneiosJob.State) {
        if (s.copying) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (!s.busy) stopping = false
        val flow = s.flow
        val job = s.job
        val problem = flow.problem?.takeIf { !it.isNextStep }

        // What to do now: the title (the step's action, or what stops it), the footer's main button.
        val title = when {
            job != null -> OneiosActions.runningTitle(this, job)
            flow.next == OneiosFlow.Next.NOT_THIS_PHONE -> getString(R.string.oneios_not_this_phone_title)
            flow.next == OneiosFlow.Next.SWITCH -> getString(R.string.setup_done_title, getString(R.string.oneios_short))
            problem != null -> problem.title
            flow.next == OneiosFlow.Next.GET_RUNTIME -> getString(R.string.oneios_step_runtime)
            flow.next == OneiosFlow.Next.IMPORT_IMAGE -> getString(R.string.oneios_step_image)
            else -> getString(R.string.oneios_setup_title)
        }
        val titleView = findViewById<TextView>(R.id.setup_title)
        if (titleView.text.toString() != title) titleView.text = title
        if (!resources.getBoolean(R.bool.home_two_pane)) findViewById<androidx.appcompat.widget.Toolbar>(R.id.setup_toolbar).title = title

        // What is next: the step after this one, or what happens after the switch.
        val subtitle = when {
            s.copying -> getString(R.string.setup_subtitle)
            flow.next == OneiosFlow.Next.SWITCH -> getString(R.string.oneios_setup_ready_next)
            flow.next == OneiosFlow.Next.NOT_THIS_PHONE || flow.current == null -> ""
            flow.then != null -> getString(R.string.oneios_setup_then, OneiosActions.stepTitle(this, flow.then!!))
            else -> getString(R.string.oneios_setup_then_switch)
        }
        findViewById<TextView>(R.id.setup_subtitle).apply {
            text = subtitle
            visibility = if (subtitle.isEmpty()) View.GONE else View.VISIBLE
        }

        // The hero: what runs, how far, and the time left (as "Installing · 42% · About 8 min left").
        val percent = stepWisePercent(s, flow)
        findViewById<SeslProgressBar>(R.id.setup_linear_progress).apply {
            isIndeterminate = false
            progress = percent
        }
        val doneSteps = flow.rows.count { it.mark == OneiosFlow.Mark.DONE }
        findViewById<TextView>(R.id.setup_artwork_state).text = when {
            s.copying -> listOf(
                // A download stages what it downloaded: from the first file sent to root on, it imports.
                getString(if (job == OneiosFlow.Job.DOWNLOAD_RUNTIME && s.file == null) R.string.oneios_downloading else R.string.oneios_importing),
                getString(R.string.setup_percent, if (s.total > 0) (s.done * 100 / s.total).toInt().coerceIn(0, 100) else 0),
                s.etaSeconds?.let { if (it < 60) getString(R.string.setup_eta_soon) else getString(R.string.setup_eta_minutes, (it + 59) / 60) }
                    ?: getString(R.string.setup_eta_estimating),
            ).joinToString(" · ")
            flow.next == OneiosFlow.Next.SWITCH -> getString(R.string.setup_ring_done)
            problem != null && job == null -> getString(R.string.setup_ring_failed)
            else -> getString(R.string.oneios_steps_done, doneSteps, flow.rows.size)
        }

        // The steps: what is done (with its version and check), what runs, what waits.
        for ((step, row) in stepRows) {
            val r = flow.row(step)
            val summary = when {
                r.mark == OneiosFlow.Mark.RUNNING && s.copying -> listOfNotNull(s.file ?: s.message, s.progressLine).joinToString("\n")
                r.mark == OneiosFlow.Mark.RUNNING -> r.line ?: s.message
                r.mark == OneiosFlow.Mark.NEXT -> OneiosActions.stepAbout(this, step)
                else -> r.line
            }
            row.summary = summary
            row.icon = when (r.mark) {
                OneiosFlow.Mark.RUNNING -> StepRingDrawable(this, if (s.copying && s.total > 0) (s.done.toFloat() / s.total).coerceIn(0f, 1f) else null)
                OneiosFlow.Mark.DONE -> AppCompatResources.getDrawable(this, R.drawable.ic_setup_complete)
                OneiosFlow.Mark.FAILED -> AppCompatResources.getDrawable(this, R.drawable.oneos_badge_warn)
                OneiosFlow.Mark.NEXT -> AppCompatResources.getDrawable(this, R.drawable.ic_oneos_step_current)
                OneiosFlow.Mark.PENDING -> AppCompatResources.getDrawable(this, R.drawable.ic_oneos_step_pending)
            }
            row.contentDescription = OneiosActions.stepTitle(this, step) + ", " + getString(
                when (r.mark) {
                    OneiosFlow.Mark.DONE -> R.string.setup_state_done
                    OneiosFlow.Mark.FAILED -> R.string.setup_state_failed
                    OneiosFlow.Mark.RUNNING, OneiosFlow.Mark.NEXT -> R.string.setup_state_current
                    OneiosFlow.Mark.PENDING -> R.string.setup_state_pending
                },
            ) + summary?.let { ", $it" }.orEmpty()
        }

        // A refusal: the script's own words under the steps, as Setting up's "What it said".
        val slot = findViewById<LinearLayout>(R.id.setup_details_slot)
        slot.removeAllViews()
        slot.visibility = if (problem != null && job == null) View.VISIBLE else View.GONE
        if (problem != null && job == null) {
            val card = Cards.section(slot, null, rows = true, gapAbove = true)
            Cards.row(card, 0, getString(R.string.setup_details_result), problem.detail.ifBlank { problem.line })
        }
        bindFooter(s, flow)
    }

    /** Every step an equal share of the bar; a copy that runs fills its own step to its bytes. */
    private fun stepWisePercent(s: OneiosJob.State, flow: OneiosFlow.View): Int {
        var done = 0f
        for (r in flow.rows) {
            done += when (r.mark) {
                OneiosFlow.Mark.DONE -> 1f
                OneiosFlow.Mark.RUNNING -> if (s.copying && s.total > 0) (s.done.toFloat() / s.total).coerceIn(0f, 1f) else 0f
                else -> 0f
            }
        }
        return (done * 100 / flow.rows.size).toInt().coerceIn(0, 100)
    }

    /** Stop while a copy runs; else the one action of now (Continue once it is ready), and Close. */
    private fun bindFooter(s: OneiosJob.State, flow: OneiosFlow.View) {
        val primary = findViewById<Button>(R.id.setup_primary) ?: return
        val secondary = findViewById<Button>(R.id.setup_secondary) ?: return
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
        when {
            s.copying -> {
                show(primary, null)
                show(secondary, getString(if (stopping) R.string.setup_stopping else R.string.oneios_stop_setup), enabled = !stopping) {
                    // Asked first, as Setting up does: nothing staged before is lost either way.
                    AlertDialog.Builder(this).setTitle(getString(R.string.setup_stop_title, getString(R.string.oneios_short)))
                        .setMessage(R.string.oneios_stop_summary)
                        .setPositiveButton(R.string.setup_stop) { _, _ ->
                            stopping = true
                            OneiosJob.cancel()
                            bind(OneiosJob.state)
                        }
                        .setNegativeButton(R.string.setup_keep_going, null).show()
                }
            }
            s.busy -> {
                show(primary, null)
                show(secondary, getString(R.string.setup_close)) { finish() }
            }
            flow.next == OneiosFlow.Next.SWITCH || flow.next == OneiosFlow.Next.BACK_TO_ONE_UI -> {
                // The switch (and the way back from an open session) is on iOS 27's page, as Boot is on a system's page.
                show(primary, getString(R.string.oneios_continue)) { openPage() }
                show(secondary, getString(R.string.setup_close)) { finish() }
            }
            else -> {
                show(primary, OneiosActions.label(this, flow.next)) { OneiosActions.run(this, flow.next, picker) }
                show(secondary, getString(R.string.setup_close)) { finish() }
            }
        }
        val lp = secondary.layoutParams as? ViewGroup.MarginLayoutParams ?: return
        val top = if (primary.visibility == View.VISIBLE) (8 * resources.displayMetrics.density).toInt() else 0
        if (lp.topMargin != top) {
            lp.topMargin = top
            secondary.layoutParams = lp
        }
    }

    private fun openPage() {
        startActivity(OneiosActivity.intent(this).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        finish()
    }

    companion object {
        fun intent(ctx: Context): Intent = Intent(ctx, OneiosSetupActivity::class.java)
    }
}
