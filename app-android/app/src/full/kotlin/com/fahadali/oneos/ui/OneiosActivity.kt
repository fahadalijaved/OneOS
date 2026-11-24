package com.fahadali.oneos.ui

import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.content.res.AppCompatResources
import androidx.appcompat.widget.Toolbar
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosToolJob
import dev.oneuiproject.oneui.R as Icons

/**
 * iOS 27 (OneiOS)'s page (docs/oneios.md, "In the app"), as an Android system's page is
 * (EnvironmentActivity, the same activity_environment layout): the artwork, what runs now (its step and seconds),
 * the setup steps while the runtime or the image set is missing ([stepper]), else the state of the iOS
 * files on this phone as check tiles (the runtime and its check, the image set and its check, iOS's
 * data, the last check before the switch), the one thing that stops the switch in plain words with
 * its fix, the runtime's and the image set's own rows, the last session and its logs, the tools, and
 * one fixed button that does what comes next: Set up iOS 27, a fix, Back to One UI, or Switch to
 * iOS 27, which asks first (OneiosSwitchConfirm) and shows the way back before One UI closes.
 * Everything it does is a job of [OneiosJob], whose root verbs are the ones before the redesign.
 */
class OneiosActivity : EdgeToEdgeActivity() {
    private lateinit var picker: OneiosPicker
    private lateinit var actionTextColors: ColorStateList
    private var unsubscribe: (() -> Unit)? = null
    private var toolUnsubscribe: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        picker = OneiosPicker(this, savedInstanceState)
        setContentView(R.layout.activity_environment)
        actionTextColors = findViewById<Button>(R.id.environment_boot).textColors
        val nativeToolbar = findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)
        if (nativeToolbar != null) {
            applyEdgeToEdgeInsets(nativeToolbar, onNavigationBarInset = {})
            findViewById<View>(R.id.environment_window).setOnApplyWindowInsetsListener { _, insets ->
                val bottom = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout()).bottom
                findViewById<View>(R.id.environment_footer).updateBottomMarginForNavigationBar(0, bottom)
                insets
            }
            nativeToolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
            nativeToolbar.setEdgeInsetHorizontal(0f)
            nativeToolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
                roundedCorners = 0
                fillHorizontalPadding = false
            }
            nativeToolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
            nativeToolbar.setTitle(getString(R.string.oneios_title))
        } else findViewById<View>(R.id.environment_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        toolbar().apply {
            setNavigationIcon(Icons.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
        }
        val scroll = findViewById<NestedScrollView>(R.id.environment_scroll)
        scroll.apply {
            isNestedScrollingEnabled = !resources.getBoolean(R.bool.home_two_pane)
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(getColor(R.color.preboot_page))
            seslSetFadingEdgeWindowBottomAlignment(nativeToolbar != null)
            seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        }
        findViewById<View>(R.id.environment_footer).addOnLayoutChangeListener { footer, _, _, _, _, _, _, _, _ ->
            // As on a system's page: the last row scrolls clear of the fixed button.
            val navigation = if (nativeToolbar != null) (footer.layoutParams as? ViewGroup.MarginLayoutParams)?.bottomMargin ?: 0 else 0
            val clearance = footer.height + navigation + dp(16)
            val fadeHeight = footer.height + navigation + dp(24)
            scroll.seslForceBottomFadingEdgeClamped(fadeHeight)
            scroll.invalidate()
            if (scroll.paddingBottom != clearance) {
                scroll.setPadding(scroll.paddingLeft, scroll.paddingTop, scroll.paddingRight, clearance)
                scroll.seslSetFadingEdgeEnabled(true, dp(24), fadeHeight)
            }
        }
        findViewById<OsArtworkView>(R.id.environment_artwork).bindArtwork(R.drawable.os_oneios)
        findViewById<TextView>(R.id.environment_title).text = getString(R.string.oneios_title)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        picker.save(outState)
    }

    override fun onStart() {
        super.onStart()
        // This page shows no byte count (Set up iOS 27 does): rows are built again only when something else changes.
        unsubscribe = OneiosJob.observeBy({ it.copy(done = 0, total = 0, bytesPerSecond = 0, etaSeconds = null, file = null, message = if (it.copying) null else it.message) }) { render(it) }
        // Update the kernel's rows (kernelUpdateRows): its step, pause and end, not its bytes.
        toolUnsubscribe = OneiosToolJob.observeBy({ s ->
            if (s.last != OneiosToolJob.Flow.KERNEL) null
            else listOf(s.flow, s.starting, s.stopping, s.problem, s.kernelPhase, s.view.current, s.view.held, s.view.paused, s.view.netWaiting,
                s.pausedByUser, s.noNetwork, s.canPause, s.plain, s.builtKc)
        }) { render(OneiosJob.state) }
    }

    override fun onResume() {
        super.onResume()
        // Not again when root answered moments ago (back from the picker, a flow, the logs): OneiosJob.refreshIfStale.
        if (!OneiosJob.state.busy) OneiosJob.refreshIfStale(this)
    }

    override fun onStop() {
        ticker.removeCallbacks(tick)
        unsubscribe?.invoke()
        unsubscribe = null
        toolUnsubscribe?.invoke()
        toolUnsubscribe = null
        super.onStop()
    }

    /** The busy card's line, counted each second while a job runs ([render], [tick]). */
    private var busyRow: dev.oneuiproject.oneui.widget.CardItemView? = null
    private val ticker = android.os.Handler(android.os.Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            val s = OneiosJob.state
            val row = busyRow ?: return
            if ((!s.busy && s.waitingFor == null) || isDestroyed) return
            row.summary = busyLine(s)
            ticker.postDelayed(this, 1000)
        }
    }

    /** "Asking root for access… · 7 s": the step in words, and how long it has run. */
    private fun busyLine(s: OneiosJob.State): String = listOfNotNull(
        if (s.job == null && s.waitingFor != null) getString(R.string.oneios_waiting_line, s.waitingFor) else s.message,
        s.since.takeIf { it > 0 }?.let { getString(R.string.oneios_seconds, ((android.os.SystemClock.elapsedRealtime() - it) / 1000).toInt()) },
    ).joinToString(" · ")

    private fun render(s: OneiosJob.State) {
        if (isDestroyed) return
        val flow = s.flow
        val st = s.status
        val idle = !s.busy
        val column = findViewById<LinearLayout>(R.id.environment_cards)
        column.removeAllViews()

        // What runs now (a system page's busy card), at full size: what it is, the step in words and its seconds (the
        // ticker counts them), Stop for a check; a download or an import has its progress on Set up iOS 27. Before
        // 2026-11-22 this was one small caption, and a check that waited for root showed nothing else.
        busyRow = null
        s.job?.let { job ->
            val busy = PrebootCards.section(column)
            busyRow = PrebootCards.row(busy, OneiosActions.runningTitle(this, job), busyLine(s)) as dev.oneuiproject.oneui.widget.CardItemView
            if (job == OneiosFlow.Job.CHECK) PrebootCards.row(busy, getString(R.string.oneios_stop), getString(R.string.oneios_check_stop_line)) {
                OneiosJob.cancel()
            }
            ticker.removeCallbacks(tick)
            ticker.postDelayed(tick, 1000)
            if (s.copying) PrebootCards.row(busy, getString(R.string.systems_show_progress), chevron = true) {
                startActivity(OneiosSetupActivity.intent(this))
            }
        }
        // A check that waits for another of the app's jobs: which one, and its seconds; it starts by itself after it.
        if (s.job == null) s.waitingFor?.let {
            val busy = PrebootCards.section(column)
            busyRow = PrebootCards.row(busy, getString(R.string.oneios_waiting_title), busyLine(s)) as dev.oneuiproject.oneui.widget.CardItemView
            ticker.removeCallbacks(tick)
            ticker.postDelayed(tick, 1000)
        }

        // While the runtime or the image set is missing: the steps, numbered, with what each needs and the one to do
        // now (tap it). Once both are here: the state of the iOS files on this phone, as a system page's check tiles.
        if (settingUp(s)) stepper(column, s, flow, idle) else tiles(column, s, flow)

        // What to do now, or what stops the switch, in plain words (a system page's "what stops the switch").
        val problem = flow.problem
        when {
            s.offered == false -> PrebootCards.row(PrebootCards.section(column), getString(R.string.oneios_not_this_phone_title), getString(R.string.oneios_not_this_phone))
            // (Only a next step, such as "not set up yet": the steps above say it already.)
            problem != null && s.job == null && !(problem.isNextStep && settingUp(s)) -> {
                val fix = OneiosFlow.Next.of(problem.fix)
                PrebootCards.row(PrebootCards.section(column), problem.title, problem.line, chevron = problem.fix != OneiosFix.NONE, enabled = idle) {
                    OneiosActions.run(this, fix, picker)
                }
            }
            flow.ready && s.job == null -> PrebootCards.row(PrebootCards.section(column), getString(R.string.oneios_ready), getString(R.string.oneios_ready_line))
        }

        // The runtime: what is staged and its check, then where a runtime comes from.
        val runtime = PrebootCards.section(column, getString(R.string.oneios_runtime))
        PrebootCards.row(
            runtime,
            flow.runtimeLine ?: getString(R.string.oneios_runtime_none_title),
            st?.runtime?.let { getString(R.string.oneios_runtime_details, it.xnuhost, it.sessionAbi, OneiosSystem.SESSION_ABI.toString(), it.imageFormats) }
                ?: getString(R.string.oneios_runtime_none),
        )
        PrebootCards.row(runtime, getString(R.string.oneios_runtime_download), getString(R.string.oneios_runtime_download_line), chevron = true, enabled = idle) {
            OneiosActions.download(this, null)
        }
        // The other ways in one row: an older release by its tag, or a runtime file (OneiosActions.askRuntimeOther).
        PrebootCards.row(runtime, getString(R.string.oneios_runtime_other), getString(R.string.oneios_runtime_other_line), chevron = true, enabled = idle) {
            OneiosActions.askRuntimeOther(this, picker)
        }

        // The image set: what is staged and its check; it only ever comes from a file.
        val image = PrebootCards.section(column, getString(R.string.oneios_image))
        PrebootCards.row(
            image,
            flow.imageLine ?: getString(R.string.oneios_image_none_title),
            st?.image?.let { getString(R.string.oneios_image_details, it.format, st?.runtime?.imageFormats ?: "?") }
                ?: getString(R.string.oneios_image_none),
        )
        // Made on this phone from Apple's files (Make iOS image: no PC; it gets a newer runtime first when it needs
        // one), or a set the user already has.
        PrebootCards.row(image, getString(R.string.oneios_make_image), getString(R.string.oneios_make_image_line), chevron = true,
            enabled = idle || OneiosToolJob.state.busy) { OneiosActions.makeImage(this) }
        PrebootCards.row(image, getString(R.string.oneios_image_file), getString(R.string.oneios_image_file_line), chevron = true, enabled = idle) {
            picker.pick(OneiosKind.IMAGE)
        }
        PrebootCards.row(image, getString(R.string.oneios_data), (flow.dataLine ?: getString(R.string.environment_unknown)) + "\n" + getString(R.string.oneios_data_line))

        // The kernel: what the runtime carries, what the image boots, and Update the kernel (docs/oneios.md,
        // "Kernel updates"). A new kernel never means rebuilding the image set, and needs no PC: the phone fetches
        // Apple's kernelcache from Apple itself (once; it stays cached in the stage), pairs the staged xnu with it
        // and activates the collection atomically.
        if (st?.runtime != null) {
            val kernel = PrebootCards.section(column, getString(R.string.oneios_kernel))
            PrebootCards.row(
                kernel,
                kernelTitle(st),
                kernelDetails(st) + OneiosJob.kernelCheckLine(this)?.let { "\n$it" }.orEmpty(),
            )
            if (st.image != null) {
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_check), getString(R.string.oneios_kernel_check_line), chevron = true, enabled = idle) {
                    OneiosJob.checkKernel(this)
                }
                kernelUpdateRows(kernel, st, idle)
                if (st.imageKernel?.hasFallback == true) {
                    PrebootCards.row(kernel, getString(R.string.oneios_kernel_restore), getString(R.string.oneios_kernel_restore_line), chevron = true, enabled = idle) {
                        OneiosActions.confirmRestoreKernel(this)
                    }
                }
                // Optional, with no download: a kernelcache.macho a PC wrote (checked against the same pin).
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_kernelcache), getString(R.string.oneios_kernel_kernelcache_line), chevron = true, enabled = idle) {
                    picker.pickKernelcache()
                }
            }
        }

        // The return: an open session's way back, and how the last one came back.
        val session = PrebootCards.section(column, getString(R.string.last_title))
        if (st?.sessionOpen == true) {
            PrebootCards.row(session, getString(R.string.oneios_back), getString(R.string.oneios_back_line), chevron = true, enabled = idle) {
                OneiosJob.backToOneUi(this)
            }
        }
        val last = OneiosFlow.lastReturn(st)
        PrebootCards.row(
            session,
            last?.title ?: getString(R.string.last_none),
            last?.line ?: getString(R.string.oneios_last_none_line),
        )
        PrebootCards.row(session, getString(R.string.oneios_logs), getString(R.string.oneios_logs_line), chevron = true) {
            startActivity(OneiosLogsActivity.intent(this))
        }

        // Tools: OneiOS's phone checks beside One UI, and oneios-tool's flows (docs/oneios.md, "oneios-tool in the app").
        val tools = PrebootCards.section(column, getString(R.string.oneios_tools))
        PrebootCards.row(tools, getString(R.string.oneios_checks), getString(R.string.oneios_checks_line), chevron = true) {
            startActivity(OneiosChecksActivity.intent(this))
        }
        if (st?.runtime != null) {
            PrebootCards.row(tools, getString(R.string.oneios_tool_sums), getString(R.string.oneios_tool_sums_line), chevron = true,
                enabled = idle || OneiosToolJob.state.busy) { OneiosToolActivity.start(this, OneiosToolJob.Flow.SUMS) }
        }

        if (st?.staged == true) {
            PrebootCards.row(PrebootCards.section(column, getString(R.string.oneios_manage)), getString(R.string.oneios_remove), getString(R.string.oneios_remove_line), chevron = true, enabled = idle) {
                OneiosActions.confirmRemove(this)
            }
        }
        bindAction(s, flow)
    }

    /**
     * The runtime or the image set is not staged yet (and no session is open, and the phone takes the system): the
     * page shows the setup steps ([stepper]) in place of the tiles, so what is missing and what comes next is the
     * first thing on it.
     */
    private fun settingUp(s: OneiosJob.State): Boolean {
        val st = s.status ?: return s.offered != false
        return s.offered != false && !st.sessionOpen && (st.runtime == null || st.image == null)
    }

    /**
     * The setup steps on this page ([OneiosFlow]'s rows, as Set up iOS 27 shows them): numbered, each with its mark
     * (done, now, waiting, failed, running) and its line; the step to do now says what it needs and is the one row
     * that can be tapped, which does it (the same action as the fixed button). A step that failed is tappable too, for
     * its fix.
     */
    private fun stepper(column: LinearLayout, s: OneiosJob.State, flow: OneiosFlow.View, idle: Boolean) {
        val card = PrebootCards.section(column, getString(R.string.oneios_steps_title))
        for ((n, r) in flow.rows.withIndex()) {
            val now = r.mark == OneiosFlow.Mark.NEXT && r.step == flow.current
            val fix = r.mark == OneiosFlow.Mark.FAILED && flow.problem?.fix?.let { it != OneiosFix.NONE } == true
            val summary = when (r.mark) {
                // A check says its step (root's grant, the stage, the last check) as it goes.
                OneiosFlow.Mark.RUNNING -> listOfNotNull(if (s.job == OneiosFlow.Job.CHECK) s.message ?: r.line else r.line ?: s.message, s.progressLine).joinToString("\n")
                OneiosFlow.Mark.NEXT -> OneiosActions.stepAbout(this, r.step) + if (now && idle) "\n" + getString(R.string.oneios_step_tap) else ""
                OneiosFlow.Mark.PENDING -> OneiosActions.stepAbout(this, r.step)
                else -> r.line
            }
            val title = getString(R.string.oneios_step_numbered, n + 1, OneiosActions.stepTitle(this, r.step))
            val tap: ((View) -> Unit)? = when {
                !idle -> null
                now -> { _ -> OneiosActions.run(this, flow.next, picker) }
                fix -> { _ -> OneiosActions.run(this, OneiosFlow.Next.of(flow.problem!!.fix), picker) }
                else -> null
            }
            val row = PrebootCards.row(card, title, summary, chevron = tap != null, onClick = tap) as dev.oneuiproject.oneui.widget.CardItemView
            row.icon = when (r.mark) {
                OneiosFlow.Mark.RUNNING -> StepRingDrawable(this, if (s.copying && s.total > 0) (s.done.toFloat() / s.total).coerceIn(0f, 1f) else null)
                OneiosFlow.Mark.DONE -> AppCompatResources.getDrawable(this, R.drawable.ic_setup_complete)
                OneiosFlow.Mark.FAILED -> AppCompatResources.getDrawable(this, R.drawable.oneos_badge_warn)
                OneiosFlow.Mark.NEXT -> AppCompatResources.getDrawable(this, R.drawable.ic_oneos_step_current)
                OneiosFlow.Mark.PENDING -> AppCompatResources.getDrawable(this, R.drawable.ic_oneos_step_pending)
            }
            if (tap == null) {
                row.isClickable = false
                row.isFocusable = false
            }
            row.contentDescription = title + ", " + getString(
                when (r.mark) {
                    OneiosFlow.Mark.DONE -> R.string.setup_state_done
                    OneiosFlow.Mark.FAILED -> R.string.setup_state_failed
                    OneiosFlow.Mark.RUNNING, OneiosFlow.Mark.NEXT -> R.string.setup_state_current
                    OneiosFlow.Mark.PENDING -> R.string.setup_state_pending
                },
            ) + summary?.let { ", $it" }.orEmpty()
        }
    }

    /** The state of the iOS files on this phone, as a system page's check tiles (once the runtime and the image are here). */
    private fun tiles(column: LinearLayout, s: OneiosJob.State, flow: OneiosFlow.View) {
        val st = s.status
        val checks = PrebootCards.section(column, getString(R.string.oneios_state_title))
    checks.setPadding(dp(10), dp(10), dp(10), dp(10))
    Cards.tileGrid(
        checks,
        listOf(
            Cards.Tile(Icons.drawable.ic_oui_download, getString(R.string.oneios_runtime), tileValue(st?.runtime?.version, flow.runtime, st?.runtime?.placeholder == true), level(flow.runtime)),
            Cards.Tile(Icons.drawable.ic_oui_file_type_zip, getString(R.string.oneios_image), tileValue(st?.image?.let { "iOS ${it.version}" }, flow.image, false), level(flow.image)),
            Cards.Tile(
                Icons.drawable.ic_oui_folder_outline, getString(R.string.oneios_data),
                getString(if (st == null) R.string.environment_unknown else if (OneiosFlow.dataNew(st)) R.string.oneios_data_new else R.string.oneios_data_kept),
                if (st == null) Level.INFO else Level.OK,
            ),
            Cards.Tile(
                Icons.drawable.ic_oui_security_outline, getString(R.string.oneios_last_check),
                getString(
                    when (flow.mark(OneiosFlow.Step.READY)) {
                        OneiosFlow.Mark.DONE -> R.string.oneios_last_check_passed
                        OneiosFlow.Mark.FAILED -> R.string.oneios_last_check_refused
                        OneiosFlow.Mark.RUNNING -> R.string.oneios_checking
                        else -> R.string.oneios_last_check_not_yet
                    },
                ),
                when (flow.mark(OneiosFlow.Step.READY)) {
                    OneiosFlow.Mark.DONE -> Level.OK
                    OneiosFlow.Mark.FAILED -> Level.BLOCK
                    else -> Level.INFO
                },
            ),
        ),
    )
    }

    /** The fixed button: the one thing to do now, with a spinner while a job runs (as a system page's Boot). */
    private fun bindAction(s: OneiosJob.State, flow: OneiosFlow.View) {
        // Only a job that runs spins the button. No status yet and nothing running: Check again (flow.next), never a
        // spinner with no reason (before 2026-11-22 it spun until something else read the status).
        val waiting = s.busy
        findViewById<View>(R.id.environment_action_spinner).visibility = if (waiting) View.VISIBLE else View.GONE
        // The staged set's own iOS: the A56's iOS 16.5 set is not "iOS 27" (issue 73). The artwork says iOS 27, so it
        // shows only over an iOS 27 set (or none yet).
        val version = s.status?.image?.version
        val name = OneiosSystem.name(version)
        findViewById<TextView>(R.id.environment_title)?.text = name
        findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)?.setTitle(name)
        findViewById<View>(R.id.environment_artwork)?.visibility =
            if (OneiosSystem.isIos27(version)) View.VISIBLE else View.GONE
        val next = flow.next
        findViewById<Button>(R.id.environment_boot).apply {
            text = when {
                next == OneiosFlow.Next.NOT_THIS_PHONE -> getString(R.string.catalog_not_available)
                else -> OneiosActions.label(this@OneiosActivity, next) ?: "Switch to ${OneiosSystem.shortName(version)}"
            }
            isEnabled = !waiting && next != OneiosFlow.Next.NOT_THIS_PHONE
            setTextColor(if (waiting) ColorStateList.valueOf(Color.TRANSPARENT) else actionTextColors)
            contentDescription = if (waiting) getString(R.string.oneios_checking) else text
            setOnClickListener {
                val now = OneiosJob.state
                if (now.busy) return@setOnClickListener
                // Not set up yet: the step to do now (Get the runtime, Get the iOS image), the same as its row in the
                // steps above; a download or an import then shows its bytes on Set up iOS 27.
                OneiosActions.run(this@OneiosActivity, now.flow.next, picker)
            }
        }
    }

    /**
     * Update the kernel on this page (docs/oneios.md, "Kernel updates"): while it runs, what runs now (its step, a
     * pause, the wait for a network) with Pause or Resume, Stop, and its own screen for the bytes and the time left;
     * after it, why it stopped in plain words ([OneiosPlain.kernelUpdate]) or Activate for the kernel it built; and
     * the Update button. This page is built again only when the step, a pause or the end changes, never for a byte
     * count ([onStart]).
     */
    private fun kernelUpdateRows(kernel: LinearLayout, st: OneiosStatus, idle: Boolean) {
        val t = OneiosToolJob.state
        val mine = t.last == OneiosToolJob.Flow.KERNEL
        if (mine && t.busy) {
            val v = t.view
            val running = v.steps.firstOrNull { it.state == OneiosTool.StepState.RUNNING }
            val why = when {
                t.stopping -> getString(R.string.oneios_tool_stopping)
                v.netWaiting != null -> v.netWaiting
                t.noNetwork -> getString(R.string.oneios_tool_no_network)
                v.held || t.pausedByUser -> getString(R.string.oneios_tool_paused)
                else -> v.paused
            }
            PrebootCards.row(
                kernel, t.kernelPhase?.words ?: getString(R.string.oneios_tool_starting),
                listOfNotNull(running?.text, why).joinToString(" · ").ifEmpty { getString(R.string.oneios_kernel_update_progress) }, chevron = true,
            ) { startActivity(OneiosToolActivity.intent(this)) }
            if (t.canPause && !t.stopping) {
                if (t.pausedByUser) PrebootCards.row(kernel, getString(R.string.oneios_tool_resume), getString(R.string.oneios_tool_resume_line)) { OneiosToolJob.resumeByUser() }
                else PrebootCards.row(kernel, getString(R.string.oneios_tool_pause), getString(R.string.oneios_tool_pause_line), enabled = !t.starting) { OneiosToolJob.pauseByUser() }
            }
            PrebootCards.row(kernel, getString(if (t.stopping) R.string.oneios_tool_stopping else R.string.oneios_tool_stop), enabled = !t.stopping) { OneiosToolJob.cancel() }
            return
        }
        if (mine) {
            t.problem?.let { PrebootCards.row(kernel, getString(R.string.oneios_tool_not_started), it, chevron = true) { startActivity(OneiosToolActivity.intent(this)) } }
            t.plain?.let { m -> PrebootCards.row(kernel, m.title, m.line, chevron = true) { startActivity(OneiosToolActivity.intent(this)) } }
            t.builtKc?.let { kc ->
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_activate), getString(R.string.oneios_kernel_activate_line), chevron = true, enabled = idle) {
                    OneiosToolJob.kernelActivating()
                    OneiosJob.activateKernel(this, kc)
                }
            }
        }
        PrebootCards.row(
            kernel, getString(R.string.oneios_kernel_update),
            getString(if (st.kb.kernelcacheSha256 != null) R.string.oneios_kernel_update_cached_line else R.string.oneios_kernel_update_line),
            chevron = true, enabled = idle && OneiosToolJob.canStart(),
        ) { OneiosToolActivity.start(this, OneiosToolJob.Flow.KERNEL) }
    }

    private fun kernelTitle(st: OneiosStatus): String =
        st.runtimeKernel?.let { getString(R.string.oneios_kernel_title, it.buildId) } ?: getString(R.string.oneios_kernel_none)

    private fun kernelDetails(st: OneiosStatus): String {
        val runtime = st.runtimeKernel?.let { "${it.buildId} (${it.xnu})" } ?: getString(R.string.oneios_kernel_kc_none)
        val image = st.imageKernel?.let {
            it.buildId + " (" + it.kcSha256.take(12) + "…)" + if (it.hasFallback) " · ${getString(R.string.oneios_kernel_kc_fallback)}" else ""
        } ?: getString(R.string.oneios_kernel_kc_unknown)
        val inputs = (if (st.kb.inputs == 0) getString(R.string.oneios_kernel_inputs_none)
            else getString(R.string.oneios_kernel_inputs, st.kb.inputs)) + " · " +
            getString(if (st.kb.kernelcacheSha256 != null) R.string.oneios_kernel_cache_yes else R.string.oneios_kernel_cache_no)
        return getString(R.string.oneios_kernel_details, runtime, image, inputs)
    }

    private fun tileValue(version: String?, check: OneiosFlow.Check, placeholder: Boolean): String = when {
        version == null -> getString(R.string.oneios_tile_none)
        placeholder -> getString(R.string.oneios_tile_value, version, getString(R.string.oneios_tile_placeholder))
        else -> getString(
            R.string.oneios_tile_value, version,
            getString(
                when (check) {
                    OneiosFlow.Check.PASSED -> R.string.oneios_tile_checked
                    OneiosFlow.Check.FAILED -> R.string.oneios_tile_check_failed
                    else -> R.string.oneios_tile_not_checked
                },
            ),
        )
    }

    private fun level(check: OneiosFlow.Check): Level = when (check) {
        OneiosFlow.Check.PASSED -> Level.OK
        OneiosFlow.Check.FAILED -> Level.BLOCK
        OneiosFlow.Check.NOT_STAGED -> Level.WARN
        OneiosFlow.Check.NOT_CHECKED -> Level.INFO
    }

    private fun toolbar(): Toolbar =
        findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)?.toolbar
            ?: findViewById(R.id.environment_toolbar)

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    companion object {
        fun intent(ctx: android.content.Context): Intent = Intent(ctx, OneiosActivity::class.java)
    }
}
