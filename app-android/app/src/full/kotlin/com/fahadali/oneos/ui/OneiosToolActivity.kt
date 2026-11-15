package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OneiosToolJob
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * One flow of OneiOS's Rust tools on this phone ([OneiosToolJob]; docs/oneios.md, "oneios-tool in the app"):
 * Make iOS image, Check every file, the CPU, the session's log, iOS's own log. What it shows is what the tool
 * sent, nothing worked out here: the steps with their marks (done, running, next, waiting, failed), what runs
 * now with its progress and the time left, the space a request needs and has, a heat pause, the tool's output
 * lines and rows, and at the end its result or its reason (with its code). **Stop** asks the tool to stop; it
 * removes what it wrote itself (its README). The layout is the session logs' (a toolbar over a list of cards).
 */
class OneiosToolActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_logs)
        val toolbar = findViewById<ToolbarLayout>(R.id.oneios_logs_toolbar)
        toolbar.setTitle(title(OneiosToolJob.state.last))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_logs_scroll)
        applyEdgeToEdgeInsets(toolbar) { bottom -> scroll.setPadding(0, 0, 0, bottom) }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0; fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
    }

    override fun onStart() {
        super.onStart()
        // Rebuild the rows only when a step, the end, the progress line or the output changes.
        unsubscribe = OneiosToolJob.observeBy({ s ->
            listOf(s.flow, s.request, s.starting, s.stopping, s.problem, s.results.size, s.view.steps, s.view.end, s.view.progressLine, s.view.paused, s.view.lines.size, s.view.rows.size)
        }) { render() }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun title(flow: OneiosToolJob.Flow?): String = getString(
        when (flow) {
            OneiosToolJob.Flow.MAKE_IMAGE, null -> R.string.oneios_make_image
            OneiosToolJob.Flow.SUMS -> R.string.oneios_tool_sums
            OneiosToolJob.Flow.CPU -> R.string.oneios_tool_cpu
            OneiosToolJob.Flow.LOG -> R.string.oneios_tool_log
            OneiosToolJob.Flow.IOSLOG_BOOTS -> R.string.oneios_tool_ioslog_boots
            OneiosToolJob.Flow.IOSLOG_SHOW -> R.string.oneios_tool_ioslog_show
        },
    )

    private fun mark(state: OneiosTool.StepState): String = getString(
        when (state) {
            OneiosTool.StepState.DONE -> R.string.oneios_tool_mark_done
            OneiosTool.StepState.RUNNING -> R.string.oneios_tool_mark_running
            OneiosTool.StepState.NEXT -> R.string.oneios_tool_mark_next
            OneiosTool.StepState.PENDING -> R.string.oneios_tool_mark_pending
            OneiosTool.StepState.CANCELLED -> R.string.oneios_tool_mark_skipped
            OneiosTool.StepState.FAILED -> R.string.oneios_tool_mark_failed
            OneiosTool.StepState.REFUSED -> R.string.oneios_tool_mark_refused
        },
    )

    private fun render() {
        val s = OneiosToolJob.state
        findViewById<ToolbarLayout>(R.id.oneios_logs_toolbar).setTitle(title(s.last))
        // The screen stays on while the tool works, as during an import.
        if (s.busy) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val list = findViewById<LinearLayout>(R.id.oneios_logs_list)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_logs_scroll)
        val at = scroll.scrollY
        list.removeAllViews()
        val v = s.view

        // What runs now, what is next, the time left, the space, a heat pause; or how it ended and why.
        val now = PrebootCards.section(list, gap = false)
        val running = v.steps.firstOrNull { it.state == OneiosTool.StepState.RUNNING }
        val end = v.end
        when {
            s.starting -> PrebootCards.row(now, getString(R.string.oneios_tool_starting), getString(R.string.oneios_tool_starting_line))
            s.problem != null -> PrebootCards.row(now, getString(R.string.oneios_tool_not_started), s.problem)
            end != null && end != OneiosToolFlow.End.OK -> PrebootCards.row(now, endTitle(end), listOfNotNull(v.code, v.text).joinToString(": "))
            s.busy -> PrebootCards.row(now, running?.text ?: running?.id ?: getString(R.string.oneios_tool_working), v.paused ?: v.progressLine)
            end == OneiosToolFlow.End.OK -> PrebootCards.row(now, endTitle(end), s.results.lastOrNull() ?: v.text)
            else -> PrebootCards.row(now, getString(R.string.oneios_tool_idle))
        }
        if (s.busy) v.next?.let { PrebootCards.row(now, getString(R.string.oneios_tool_next), it.text ?: it.id) }
        v.spaceNeed?.let { need ->
            val free = v.spaceFree?.let { getString(R.string.oneios_tool_space_free, Units.bytes(it)) }
            PrebootCards.row(now, getString(R.string.oneios_tool_space), listOfNotNull(Units.bytes(need), free).joinToString(" · "))
        }
        s.toolVersion?.let { PrebootCards.row(now, getString(R.string.oneios_tool_version), it) }

        if (v.steps.isNotEmpty()) {
            val steps = PrebootCards.section(list, getString(R.string.oneios_tool_steps))
            for (st in v.steps) PrebootCards.row(steps, st.text ?: st.id, mark(st.state))
        }
        if (s.results.isNotEmpty()) {
            val done = PrebootCards.section(list, getString(R.string.oneios_tool_end_done))
            for (r in s.results) PrebootCards.row(done, r)
        }
        val rows = v.rows.takeLast(OUTPUT_ROWS).map { r -> r.filterKeys { it != "ev" && it != "id" }.entries.joinToString(" ") { "${it.key}=${it.value}" } }
        val out = v.lines.takeLast(OUTPUT_ROWS) + rows
        if (out.isNotEmpty()) {
            // The last lines; a longer output goes to a file of the stage (a request's `out`, the tool's README).
            PrebootCards.row(PrebootCards.section(list, getString(R.string.oneios_tool_output)), out.joinToString("\n"))
        }

        val actions = PrebootCards.section(list)
        if (s.busy) {
            PrebootCards.row(actions, getString(if (s.stopping) R.string.oneios_tool_stopping else R.string.oneios_tool_stop), enabled = !s.stopping) { OneiosToolJob.cancel() }
        } else {
            val again = s.last ?: OneiosToolJob.Flow.MAKE_IMAGE
            PrebootCards.row(actions, getString(R.string.oneios_tool_run_again), enabled = OneiosToolJob.canStart()) { OneiosToolJob.run(this, again) }
        }
        scroll.post { scroll.scrollTo(0, at) }
    }

    private fun endTitle(end: OneiosToolFlow.End): String = getString(
        when (end) {
            OneiosToolFlow.End.OK -> R.string.oneios_tool_end_done
            OneiosToolFlow.End.REFUSED -> R.string.oneios_tool_end_refused
            OneiosToolFlow.End.FAILED -> R.string.oneios_tool_end_failed
            OneiosToolFlow.End.CANCELLED -> R.string.oneios_tool_end_cancelled
            OneiosToolFlow.End.LOST -> R.string.oneios_tool_end_lost
        },
    )

    companion object {
        private const val OUTPUT_ROWS = 60

        fun intent(ctx: Context): Intent = Intent(ctx, OneiosToolActivity::class.java)

        /** Starts [flow] (unless a flow runs) and opens this screen. */
        fun start(ctx: Context, flow: OneiosToolJob.Flow) {
            if (!OneiosToolJob.state.busy) OneiosToolJob.run(ctx, flow)
            ctx.startActivity(intent(ctx))
        }
    }
}
