package com.fahadali.oneos.ui

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.content.res.AppCompatResources
import androidx.appcompat.widget.SeslProgressBar
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.root.OneiosSteps
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosToolJob

/**
 * The iOS screens' shared pieces of the redesign (docs/oneios.md, "UI (2026-11-25)"): one checklist row
 * (oneios_step.xml) bound from a step of [OneiosSteps], its state icon, and the steps' input read from the app's jobs.
 */
internal object OneiosStepRow {
    /** A row of [card]; [onTap] when the row can be pressed (its step's action), [onCancel] and [onLog] for its buttons. */
    fun add(card: LinearLayout, step: OneiosSteps.Step, title: CharSequence, onTap: (() -> Unit)?, onCancel: (() -> Unit)?, onLog: (() -> Unit)?): View {
        val v = LayoutInflater.from(card.context).inflate(R.layout.oneios_step, card, false)
        if (card.childCount > 1) divider(card)
        card.addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        bind(v, step, title, onTap, onCancel, onLog)
        return v
    }

    fun bind(v: View, step: OneiosSteps.Step, title: CharSequence, onTap: (() -> Unit)?, onCancel: (() -> Unit)?, onLog: (() -> Unit)?) =
        bindParts(v, step.state, title, step.line, step.progress, step.reason, if (step.cancel != null) onCancel else null, if (step.log != null) onLog else null, onTap)

    /** A row of the checklist's look for anything with a state (an oneios-tool flow and its steps). */
    fun addParts(
        card: LinearLayout, state: OneiosSteps.State, title: CharSequence, line: String? = null, progress: OneiosSteps.Progress? = null,
        reason: String? = null, onCancel: (() -> Unit)? = null, onLog: (() -> Unit)? = null, onTap: (() -> Unit)? = null,
    ): View {
        val v = LayoutInflater.from(card.context).inflate(R.layout.oneios_step, card, false)
        if (card.childCount > 1) divider(card)
        card.addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        bindParts(v, state, title, line, progress, reason, onCancel, onLog, onTap)
        return v
    }

    fun bindParts(
        v: View, state: OneiosSteps.State, title: CharSequence, lineText: String?, p: OneiosSteps.Progress?, reasonText: String?,
        onCancel: (() -> Unit)?, onLog: (() -> Unit)?, onTap: (() -> Unit)?,
    ) {
        val step = Parts(state, lineText, p, reasonText)
        val ctx = v.context
        v.findViewById<TextView>(R.id.oneios_step_title).text = title
        val line = v.findViewById<TextView>(R.id.oneios_step_line)
        line.text = step.line
        line.visibility = if (step.line.isNullOrBlank()) View.GONE else View.VISIBLE
        v.findViewById<ImageView>(R.id.oneios_step_icon).setImageDrawable(icon(ctx, step.state, step.progress?.fraction))
        // Waiting for an earlier step: dimmed, as a list row that cannot be pressed yet.
        v.alpha = if (step.state == OneiosSteps.State.WAITING) 0.55f else 1f

        val running = v.findViewById<View>(R.id.oneios_step_running)
        running.visibility = if (step.state == OneiosSteps.State.RUNNING && p != null) View.VISIBLE else View.GONE
        if (p != null) {
            v.findViewById<TextView>(R.id.oneios_step_phase).text = p.phase
            v.findViewById<SeslProgressBar>(R.id.oneios_step_bar).apply {
                val f = p.fraction
                isIndeterminate = f == null
                if (f != null) progress = (f * 1000).toInt().coerceIn(0, 1000)
            }
            val amount = v.findViewById<TextView>(R.id.oneios_step_amount)
            amount.text = listOfNotNull(p.percent?.let { "$it%" }?.takeIf { p.amount?.contains("%") != true }, p.amount).joinToString(" · ")
            amount.visibility = if (amount.text.isNullOrEmpty()) View.GONE else View.VISIBLE
        }
        v.findViewById<Button>(R.id.oneios_step_cancel).apply {
            visibility = if (onCancel != null && step.state == OneiosSteps.State.RUNNING) View.VISIBLE else View.GONE
            setOnClickListener { onCancel?.invoke() }
        }

        val failed = v.findViewById<View>(R.id.oneios_step_failed)
        failed.visibility = if (step.state == OneiosSteps.State.FAILED && (step.reason != null || onLog != null)) View.VISIBLE else View.GONE
        v.findViewById<TextView>(R.id.oneios_step_reason).apply {
            text = step.reason
            visibility = if (step.reason.isNullOrBlank()) View.GONE else View.VISIBLE
        }
        v.findViewById<Button>(R.id.oneios_step_log).apply {
            visibility = if (onLog != null) View.VISIBLE else View.GONE
            setOnClickListener { onLog?.invoke() }
        }

        val chevron = v.findViewById<ImageView>(R.id.oneios_step_chevron)
        if (onTap != null) {
            v.isClickable = true
            v.isFocusable = true
            v.setOnClickListener { onTap() }
            chevron.setImageResource(dev.oneuiproject.oneui.R.drawable.ic_oui_keyboard_arrow_right)
            chevron.visibility = View.VISIBLE
        } else {
            v.setOnClickListener(null)
            v.isClickable = false
            v.isFocusable = false
            chevron.visibility = View.GONE
        }
        v.contentDescription = listOfNotNull(
            title, ctx.getString(stateWord(step.state)), step.line, p?.takeIf { step.state == OneiosSteps.State.RUNNING }?.let { listOfNotNull(it.phase, it.amount).joinToString(", ") }, step.reason,
        ).joinToString(", ")
    }

    private class Parts(val state: OneiosSteps.State, val line: String?, val progress: OneiosSteps.Progress?, val reason: String?)

    fun stateWord(s: OneiosSteps.State): Int = when (s) {
        OneiosSteps.State.DONE -> R.string.oneios_step_state_done
        OneiosSteps.State.TODO -> R.string.oneios_step_state_todo
        OneiosSteps.State.WAITING -> R.string.oneios_step_state_waiting
        OneiosSteps.State.RUNNING -> R.string.oneios_step_state_running
        OneiosSteps.State.FAILED -> R.string.oneios_step_state_failed
    }

    fun icon(ctx: Context, s: OneiosSteps.State, fraction: Float?) = when (s) {
        OneiosSteps.State.RUNNING -> StepRingDrawable(ctx, fraction)
        OneiosSteps.State.DONE -> AppCompatResources.getDrawable(ctx, R.drawable.ic_setup_complete)
        OneiosSteps.State.FAILED -> AppCompatResources.getDrawable(ctx, R.drawable.oneos_badge_warn)
        OneiosSteps.State.TODO -> AppCompatResources.getDrawable(ctx, R.drawable.ic_oneos_step_current)
        OneiosSteps.State.WAITING -> AppCompatResources.getDrawable(ctx, R.drawable.ic_oneos_step_pending)
    }

    /** A tool step's state as the checklist's ([OneiosToolActivity]'s steps use the same icons). */
    fun of(s: OneiosTool.StepState): OneiosSteps.State = when (s) {
        OneiosTool.StepState.DONE -> OneiosSteps.State.DONE
        OneiosTool.StepState.RUNNING -> OneiosSteps.State.RUNNING
        OneiosTool.StepState.NEXT -> OneiosSteps.State.TODO
        OneiosTool.StepState.PENDING, OneiosTool.StepState.CANCELLED -> OneiosSteps.State.WAITING
        OneiosTool.StepState.FAILED, OneiosTool.StepState.REFUSED -> OneiosSteps.State.FAILED
    }

    private fun divider(card: LinearLayout) {
        val d = View(card.context)
        d.setBackgroundColor(card.context.getColor(R.color.oneios_check_divider))
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 1)
        lp.marginStart = PrebootCards.dp(card, 62)
        lp.marginEnd = PrebootCards.dp(card, 20)
        card.addView(d, lp)
    }

    /** The checklist's input, from what the app's jobs hold now. */
    fun input(ctx: Context): OneiosSteps.Input {
        val j = OneiosJob.state
        val t = OneiosToolJob.state
        fun kind(f: OneiosToolJob.Flow?) = when (f) {
            null -> null
            OneiosToolJob.Flow.MAKE_IMAGE -> OneiosSteps.ToolFlow.MAKE_IMAGE
            OneiosToolJob.Flow.KERNEL -> OneiosSteps.ToolFlow.KERNEL
            else -> OneiosSteps.ToolFlow.OTHER
        }
        val v = t.view
        val held = when {
            v.netWaiting != null -> v.netWaiting
            t.noNetwork -> ctx.getString(R.string.oneios_tool_no_network)
            v.held || t.pausedByUser -> ctx.getString(R.string.oneios_tool_paused)
            else -> v.paused
        }
        val phase = t.kernelPhase?.words ?: t.makePhase?.words
        // Make iOS image's runtime download is OneiosJob's: its file and bytes are the step's.
        val runtimeDownload = t.makePhase == com.fahadali.oneos.core.root.OneiosMakeImage.Phase.RUNTIME && j.copying
        val failure = t.plain ?: t.problem?.let { com.fahadali.oneos.core.model.OneiosMessage(ctx.getString(R.string.oneios_tool_not_started), it, com.fahadali.oneos.core.model.OneiosFix.NONE, com.fahadali.oneos.core.model.OneiosPart.OTHER) }
            ?: v.end?.takeIf { it != com.fahadali.oneos.core.model.OneiosToolFlow.End.OK }?.let { end ->
                com.fahadali.oneos.core.model.OneiosMessage(OneiosToolActivity.endTitle(ctx, end), listOfNotNull(v.code, v.text).joinToString(": "), com.fahadali.oneos.core.model.OneiosFix.NONE, com.fahadali.oneos.core.model.OneiosPart.OTHER)
            }
        val tool = OneiosSteps.Tool(
            running = kind(t.flow),
            last = kind(t.last),
            view = if (runtimeDownload) com.fahadali.oneos.core.model.OneiosToolFlow(done = j.done, total = j.total) else v,
            phase = if (runtimeDownload) listOfNotNull(phase, j.file).joinToString(" · ") else phase,
            starting = t.starting,
            stopping = t.stopping,
            held = held,
            failure = if (t.busy) null else failure,
            builtKc = t.builtKc?.takeIf { it.matches(Regex("^[0-9a-f]{64}$")) },
        )
        // While Make iOS image downloads its runtime, OneiosJob's own job is that flow's, not Get the runtime's.
        val job = OneiosSteps.Job(
            running = j.job.takeUnless { runtimeDownload },
            message = j.message,
            done = j.done,
            total = j.total,
            file = j.file,
            progressLine = j.progressLine,
            last = j.last,
            failure = j.failure,
        )
        val st = j.status
        val expected = st?.let { s ->
            val build = s.image?.build?.let { com.fahadali.oneos.core.model.OneiosImageChoice.kernelBuildOf(it) } ?: com.fahadali.oneos.core.model.OneiosImageChoice.IOS_27.build
            OneiosJob.stagedKernel(ctx, s, build)?.buildId
        }
        return OneiosSteps.Input(j.flow, st, job, tool, expected)
    }
}
