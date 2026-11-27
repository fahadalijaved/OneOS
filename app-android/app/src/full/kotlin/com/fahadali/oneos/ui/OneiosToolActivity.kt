package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OneiosMakeImage
import com.fahadali.oneos.core.root.OneiosSteps
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosToolJob
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * One flow of OneiOS's Rust tools on this phone ([OneiosToolJob]; docs/oneios.md, "oneios-tool in the app" and "UI
 * (2026-11-25)"): Make iOS image, Update the kernel, Check every file, the CPU, the session's log, iOS's own log. The
 * flow's details, as the tool sent them: what runs now as the checklist's row (the phase in words, a real bar from
 * the tool's `progress`, the bytes, rate and time left: [OneiosSteps.toolProgress]), the space a request needs and
 * has, a pause; the tool's steps with the checklist's state icons; the failure in one line with the tool's code; its
 * last output lines. One button at the bottom: Cancel while it runs (asked first for the long flows; the tool removes
 * what it wrote itself), else Activate, Continue, Resume or Run again; Pause, Resume, Run again and Forget are in the
 * overflow menu.
 */
class OneiosToolActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null
    private var menuKey: Any? = null
    private lateinit var toolbar: ToolbarLayout
    private lateinit var primaryColors: ColorStateList
    private val ticker = android.os.Handler(android.os.Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            if (isDestroyed || !OneiosToolJob.state.busy) return
            render()
            ticker.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_screen)
        askNotifications(this, savedInstanceState)
        toolbar = findViewById(R.id.oneios_toolbar)
        OneiosScreens.setUp(this, toolbar, title(OneiosToolJob.state.last ?: OneiosToolJob.interrupted(this)))
        applyEdgeToEdgeInsets(toolbar)
        primaryColors = findViewById<Button>(R.id.oneios_primary).textColors
    }

    override fun onStart() {
        super.onStart()
        // Rebuild the rows only when a step, the end, the progress line or the output changes.
        val tool = OneiosToolJob.observeBy({ s ->
            listOf(s.flow, s.request, s.starting, s.stopping, s.problem, s.results.size, s.view.steps, s.view.end, s.view.progressLine, s.view.percent,
                s.view.paused, s.view.held, s.view.netWaiting, s.view.note, s.pausedByUser, s.noNetwork, s.canPause, s.view.lines.size, s.view.rows.size,
                s.kernelPhase, s.plain, s.builtKc, s.makePhase, s.stepDetail, s.stepFraction)
        }) { render() }
        // Make iOS image's runtime download is OneiosJob's: its file and bytes (four times a second at most).
        val runtime = OneiosJob.observeBy({ j ->
            // Also whether root's job can start: Activate is offered only then.
            listOf(j.busy, if (OneiosToolJob.state.makePhase == OneiosMakeImage.Phase.RUNTIME) listOf(j.message, j.file, j.progressLine) else null)
        }) { render() }
        unsubscribe = { tool(); runtime() }
    }

    override fun onStop() {
        ticker.removeCallbacks(tick)
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun title(flow: OneiosToolJob.Flow?): String {
        // Make iOS image names the build it makes when the phone offers more than one ("Make iOS 27.2.1 (24B156)").
        if (flow == OneiosToolJob.Flow.MAKE_IMAGE || flow == null) {
            val build = (if (OneiosToolJob.state.last == OneiosToolJob.Flow.MAKE_IMAGE) OneiosToolJob.state.makeBuild else null)
                ?: OneiosToolJob.interruptedBuild(this)
            val choices = OneiosJob.imageChoices()
            if (choices.size > 1) {
                choices.firstOrNull { it.build == build }?.let { return getString(R.string.oneios_make_image_of, "${it.version} (${it.build})") }
            }
        }
        return getString(
            when (flow) {
                OneiosToolJob.Flow.MAKE_IMAGE, null -> R.string.oneios_make_image
                OneiosToolJob.Flow.SUMS -> R.string.oneios_tool_sums
                OneiosToolJob.Flow.CPU -> R.string.oneios_tool_cpu
                OneiosToolJob.Flow.LOG -> R.string.oneios_tool_log
                OneiosToolJob.Flow.IOSLOG_BOOTS -> R.string.oneios_tool_ioslog_boots
                OneiosToolJob.Flow.IOSLOG_SHOW -> R.string.oneios_tool_ioslog_show
                OneiosToolJob.Flow.KERNEL -> R.string.oneios_kernel_update
            },
        )
    }

    private fun render() {
        if (isDestroyed) return
        val s = OneiosToolJob.state
        toolbar.setTitle(title(s.last ?: OneiosToolJob.interrupted(this)))
        // The screen stays on while the tool works, as during an import.
        ticker.removeCallbacks(tick)
        if (s.busy) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            ticker.postDelayed(tick, 1000)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        val list = findViewById<LinearLayout>(R.id.oneios_column)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_scroll)
        val at = scroll.scrollY
        list.removeAllViews()
        val v = s.view

        // What runs now with its progress, or how it ended and why: the checklist's row.
        val now = PrebootCards.section(list, gap = false)
        val running = v.steps.firstOrNull { it.state == OneiosTool.StepState.RUNNING }
        val end = v.end
        val phase = s.kernelPhase?.words ?: s.makePhase?.words
        val held = when {
            v.netWaiting != null -> v.netWaiting
            s.noNetwork -> getString(R.string.oneios_tool_no_network)
            v.held || s.pausedByUser -> getString(R.string.oneios_tool_paused)
            else -> v.paused
        }
        var subtitle: String? = null
        when {
            s.starting -> OneiosStepRow.addParts(now, OneiosSteps.State.RUNNING, getString(R.string.oneios_tool_starting),
                progress = OneiosSteps.toolProgress(v, starting = true, detail = s.stepDetail, elapsedSeconds = s.elapsedSeconds()),
                line = getString(R.string.oneios_tool_starting_line))
            s.problem != null -> OneiosStepRow.addParts(now, OneiosSteps.State.FAILED, getString(R.string.oneios_tool_not_started), reason = s.problem)
            // Update the kernel's and Make iOS image's stop in plain words; the tool's own words are below (Not done).
            !s.busy && s.plain != null -> OneiosStepRow.addParts(now, OneiosSteps.State.FAILED, s.plain.title, reason = s.plain.line,
                line = listOfNotNull(v.code, v.text).joinToString(": ").ifEmpty { null })
            end != null && end != OneiosToolFlow.End.OK -> OneiosStepRow.addParts(now, OneiosSteps.State.FAILED, endTitle(this, end),
                reason = listOfNotNull(v.code, v.text).joinToString(": ").ifEmpty { null })
            s.busy -> {
                // Make iOS image's own runtime download: OneiosJob's file and bytes.
                val p = if (s.makePhase == OneiosMakeImage.Phase.RUNTIME) OneiosJob.state.let { j ->
                    OneiosSteps.Progress(
                        if (j.total > 0) (j.done.toFloat() / j.total).coerceIn(0f, 1f) else null,
                        listOfNotNull(phase, j.file ?: j.message).joinToString(" · "),
                        listOfNotNull(j.progressLine, s.elapsedSeconds()?.let(OneiosSteps::elapsedWords)).joinToString(" · ").ifEmpty { null },
                    )
                } else OneiosSteps.toolProgress(v, phase, held, stopping = s.stopping, detail = s.stepDetail, detailFraction = s.stepFraction, elapsedSeconds = s.elapsedSeconds())
                subtitle = p.percent?.let { "$it%" }
                OneiosStepRow.addParts(now, OneiosSteps.State.RUNNING, phase ?: running?.text ?: running?.id ?: getString(R.string.oneios_tool_working), progress = p)
            }
            end == OneiosToolFlow.End.OK -> OneiosStepRow.addParts(now, OneiosSteps.State.DONE, endTitle(this, end), line = s.results.lastOrNull() ?: v.text)
            else -> OneiosStepRow.addParts(now, OneiosSteps.State.WAITING, getString(R.string.oneios_tool_idle))
        }
        toolbar.expandedSubtitle = subtitle ?: when {
            s.busy -> getString(R.string.oneios_step_state_running)
            end == OneiosToolFlow.End.OK -> endTitle(this, end)
            end != null -> endTitle(this, end)
            else -> ""
        }
        // A pause or resume the tool could not do (not-pausable, not-paused): its words. The room it needs and has.
        if (s.busy) v.note?.let { PrebootCards.row(now, getString(R.string.oneios_tool_note), it) }
        v.spaceNeed?.let { need ->
            val free = v.spaceFree?.let { getString(R.string.oneios_tool_space_free, Units.bytes(it)) }
            PrebootCards.row(now, getString(R.string.oneios_tool_space), listOfNotNull(Units.bytes(need), free).joinToString(" · "))
        }

        if (v.steps.isNotEmpty()) {
            val steps = PrebootCards.section(list, getString(R.string.oneios_tool_steps))
            for (st in v.steps) OneiosStepRow.addParts(steps, OneiosStepRow.of(st.state), st.text ?: st.id)
        }
        if (s.refusals.isNotEmpty()) {
            // Why the flow stopped, in the tool's (or root's) own words with its code: the detail of the plain words above.
            val no = PrebootCards.section(list, getString(R.string.oneios_tool_not_yet))
            for (r in s.refusals) PrebootCards.row(no, r)
        }
        if (s.results.isNotEmpty()) {
            val done = PrebootCards.section(list, getString(R.string.oneios_tool_end_done))
            for (r in s.results) PrebootCards.row(done, r)
        }
        val rows = v.rows.takeLast(OUTPUT_ROWS).map { r -> r.filterKeys { it != "ev" && it != "id" }.entries.joinToString(" ") { "${it.key}=${it.value}" } }
        val out = v.lines.takeLast(OUTPUT_ROWS) + rows
        if (out.isNotEmpty()) {
            // The last lines; a longer output goes to a file of the stage (a request's `out`, the tool's README).
            val card = PrebootCards.section(list, getString(R.string.oneios_tool_output))
            CardRows.text(card, out.joinToString("\n"), inList = true).apply {
                typeface = android.graphics.Typeface.MONOSPACE
                textSize = 12f
                setTextIsSelectable(true)
            }
        }
        s.toolVersion?.let { CardRows.text(PrebootCards.section(list), getString(R.string.oneios_tool_version) + ": " + it, inList = true) }
        bindPrimary(s)
        // The menu (Pause, Resume, Forget, Run again) changes with these only, not with each progress event.
        val menuKey = listOf(s.busy, s.canPause, s.pausedByUser, s.stopping, s.starting, OneiosToolJob.interrupted(this), s.builtKc, s.view.end)
        if (menuKey != this.menuKey) {
            this.menuKey = menuKey
            invalidateOptionsMenu()
        }
        scroll.post { scroll.scrollTo(0, at) }
    }

    /** One button: Cancel while it runs; then the flow's next thing (Activate, Continue), Resume, or Run again. */
    private fun bindPrimary(s: OneiosToolJob.State) {
        val b = findViewById<Button>(R.id.oneios_primary)
        findViewById<View>(R.id.oneios_primary_spinner).visibility = View.GONE
        b.setTextColor(primaryColors)
        fun set(text: CharSequence, enabled: Boolean = true, go: () -> Unit) {
            b.text = text
            b.isEnabled = enabled
            b.setOnClickListener { go() }
        }
        val interrupted = OneiosToolJob.interrupted(this)
        val again = s.last ?: OneiosToolJob.Flow.MAKE_IMAGE
        val kcSha = s.builtKc?.takeIf { it.matches(Regex("^[0-9a-f]{64}$")) }
        when {
            s.busy -> set(getString(if (s.stopping) R.string.oneios_tool_stopping else R.string.oneios_step_cancel), enabled = !s.stopping) { cancel(s) }
            interrupted != null -> set(getString(R.string.oneios_tool_interrupted, title(interrupted)), enabled = OneiosToolJob.canStart()) {
                // The app was ended while this flow ran: started again, the tool goes on from what it kept.
                OneiosToolJob.run(this, interrupted)
            }
            again == OneiosToolJob.Flow.KERNEL && kcSha != null -> set(getString(R.string.oneios_kernel_activate), enabled = OneiosJob.canStart()) {
                // The phone built kernel.kc and the audit passed: activate it (checks first, fallback kept), then back
                // on the iOS page, where the activation runs as the Activate step. Offered only when root's job can
                // start (OneiosJob.canStart); the built kernel stays until root put it in (OneiosToolJob.kernelActivated).
                OneiosJob.activateKernel(this, kcSha)
                startActivity(OneiosActivity.intent(this).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
            }
            again == OneiosToolJob.Flow.MAKE_IMAGE && s.view.end == OneiosToolFlow.End.OK && s.plain == null && s.problem == null ->
                // The set is staged: the switch is on iOS 27's page (its last check first).
                set(getString(R.string.oneios_continue)) { startActivity(OneiosActivity.intent(this).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)) }
            else -> set(getString(R.string.oneios_tool_run_again), enabled = OneiosToolJob.canStart()) { runAgain(again) }
        }
        b.contentDescription = b.text
    }

    private fun runAgain(flow: OneiosToolJob.Flow) {
        // Make iOS image says its download and room again first.
        if (flow == OneiosToolJob.Flow.MAKE_IMAGE) OneiosActions.makeImage(this) else OneiosToolJob.run(this, flow)
    }

    /** Cancel: asked first for the long flows (Make iOS image, Update the kernel), at once for the quick ones. */
    private fun cancel(s: OneiosToolJob.State) {
        val flow = s.flow ?: return
        if (flow != OneiosToolJob.Flow.MAKE_IMAGE && flow != OneiosToolJob.Flow.KERNEL) return OneiosToolJob.cancel()
        AlertDialog.Builder(this).setTitle(getString(R.string.oneios_step_cancel_title, title(flow))).setMessage(R.string.oneios_step_cancel_tool)
            .setNegativeButton(R.string.oneios_step_keep_going, null)
            .setPositiveButton(R.string.oneios_step_cancel) { _, _ -> OneiosToolJob.cancel() }.show()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        val s = OneiosToolJob.state
        val interrupted = OneiosToolJob.interrupted(this)
        fun item(id: Int, title: CharSequence, enabled: Boolean = true) = menu.add(Menu.NONE, id, Menu.NONE, title).apply {
            setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER)
            isEnabled = enabled
        }
        if (s.busy && s.canPause && !s.stopping) {
            // Pause and Resume when this tool takes them (its hello); the tool holds the request and keeps its parts.
            if (s.pausedByUser) item(M_RESUME, getString(R.string.oneios_tool_resume)) else item(M_PAUSE, getString(R.string.oneios_tool_pause), enabled = !s.starting)
        }
        if (!s.busy && interrupted != null) item(M_FORGET, getString(R.string.oneios_tool_forget))
        if (!s.busy && (interrupted != null || s.builtKc != null || s.view.end == OneiosToolFlow.End.OK)) {
            item(M_AGAIN, getString(R.string.oneios_tool_run_again), enabled = OneiosToolJob.canStart())
        }
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            M_PAUSE -> OneiosToolJob.pauseByUser()
            M_RESUME -> OneiosToolJob.resumeByUser()
            M_FORGET -> {
                OneiosToolJob.forget(this)
                render()
            }
            M_AGAIN -> runAgain(OneiosToolJob.state.last ?: OneiosToolJob.interrupted(this) ?: OneiosToolJob.Flow.MAKE_IMAGE)
            else -> return super.onOptionsItemSelected(item)
        }
        return true
    }

    companion object {
        private const val OUTPUT_ROWS = 60
        private const val M_PAUSE = 1
        private const val M_RESUME = 2
        private const val M_FORGET = 3
        private const val M_AGAIN = 4

        fun intent(ctx: Context): Intent = Intent(ctx, OneiosToolActivity::class.java)

        fun endTitle(ctx: Context, end: OneiosToolFlow.End): String = ctx.getString(
            when (end) {
                OneiosToolFlow.End.OK -> R.string.oneios_tool_end_done
                OneiosToolFlow.End.REFUSED -> R.string.oneios_tool_end_refused
                OneiosToolFlow.End.FAILED -> R.string.oneios_tool_end_failed
                OneiosToolFlow.End.CANCELLED -> R.string.oneios_tool_end_cancelled
                OneiosToolFlow.End.LOST -> R.string.oneios_tool_end_lost
            },
        )

        /**
         * OneiosService's notification (the running step) needs this on Android 13+; asked once where an iOS
         * download, import or tool flow is shown, as Setting up asks it. The work runs either way, without the
         * notification if refused.
         */
        fun askNotifications(a: android.app.Activity, saved: Bundle?) {
            if (saved == null && android.os.Build.VERSION.SDK_INT >= 33 &&
                a.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED
            ) {
                a.requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 42)
            }
        }

        /** Starts [flow] (unless a flow runs) and opens this screen; [build]: Make iOS image's pick ([OneiosToolJob.run]). */
        fun start(ctx: Context, flow: OneiosToolJob.Flow, build: String? = null) {
            if (!OneiosToolJob.state.busy) OneiosToolJob.run(ctx, flow, build)
            ctx.startActivity(intent(ctx))
        }
    }
}
