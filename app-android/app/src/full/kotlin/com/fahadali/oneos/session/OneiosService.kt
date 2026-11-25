package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.ui.OneiosActivity
import com.fahadali.oneos.ui.OneiosToolActivity

/**
 * Keeps a OneiOS download, import or oneios-tool flow alive while it runs, as [PrepareService] does for
 * setup ([KeepAliveService]): 0.4.76 ran the import as a plain job of the app, which Android freezes a few
 * seconds after the screen turns off or the app leaves the screen, and root then waited for bytes
 * that did not come. It also keeps the CPU awake, only while the work runs. A flow of [OneiosToolJob]
 * (Make iOS image, the stage's hashes, the logs, the CPU) ends when this service stops.
 */
class OneiosService : KeepAliveService() {
    override val notificationId = 4102
    override val keepCpuAwake = true

    override fun observe(listener: (Show) -> Unit): () -> Unit {
        fun show() {
            val t = OneiosToolJob.state
            // Make iOS image's runtime download: OneiosJob's bytes, under the flow's name.
            if (t.busy && t.makePhase == com.fahadali.oneos.core.root.OneiosMakeImage.Phase.RUNTIME) {
                val j = OneiosJob.state
                listener(
                    Show(
                        busy = true,
                        key = t.flow to j.message,
                        title = getString(R.string.oneios_title),
                        text = listOfNotNull(t.makePhase.words, j.progressLine).joinToString(" · "),
                        fraction = if (j.total > 0) (j.done.toDouble() / j.total).toFloat().coerceIn(0f, 1f) else null,
                    ),
                )
                return
            }
            if (t.busy) {
                val v = t.view
                val step = v.steps.firstOrNull { it.state == OneiosTool.StepState.RUNNING }
                listener(
                    Show(
                        busy = true,
                        key = Triple(t.flow, step?.id, t.makePhase),
                        title = getString(R.string.oneios_title),
                        text = listOfNotNull(step?.text ?: step?.id ?: t.makePhase?.words ?: getString(R.string.oneios_tool_starting), v.netWaiting ?: (if (v.held || t.pausedByUser) getString(R.string.oneios_tool_paused) else null) ?: v.paused ?: v.progressLine).joinToString(" · "),
                        fraction = v.total?.takeIf { it > 0 }?.let { total -> ((v.done ?: 0).toDouble() / total).toFloat().coerceIn(0f, 1f) },
                    ),
                )
                return
            }
            val s = OneiosJob.state
            listener(
                Show(
                    busy = s.copying,
                    key = s.message to s.file,
                    title = getString(R.string.oneios_title),
                    text = listOfNotNull(s.file ?: s.message, s.progressLine).joinToString(" · "),
                    fraction = if (s.total > 0) (s.done.toDouble() / s.total).toFloat().coerceIn(0f, 1f) else null,
                ),
            )
        }
        val a = OneiosJob.observe { show() }
        val b = OneiosToolJob.observe { show() }
        return { a(); b() }
    }

    // Set up iOS 27 shows the download or import with its bytes; a tool flow has its own screen.
    override fun screen() = if (OneiosToolJob.state.busy) OneiosToolActivity.intent(this) else OneiosActivity.intent(this)

    override fun onDestroy() {
        OneiosToolJob.serviceStopped()
        super.onDestroy()
    }

    companion object {
        fun start(ctx: Context) = start(ctx, OneiosService::class.java)
    }
}
