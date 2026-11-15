package com.fahadali.oneos.session

import android.content.Context
import android.content.Intent
import com.fahadali.oneos.R
import com.fahadali.oneos.ui.OneiosSetupActivity

/**
 * Keeps a OneiOS download or import alive while it runs, as [PrepareService] does for setup
 * ([KeepAliveService]): 0.4.76 ran the import as a plain job of the app, which Android freezes a few
 * seconds after the screen turns off or the app leaves the screen, and root then waited for bytes
 * that did not come. It also keeps the CPU awake, only while the copy runs.
 */
class OneiosService : KeepAliveService() {
    override val notificationId = 4102
    override val keepCpuAwake = true

    override fun observe(listener: (Show) -> Unit): () -> Unit = OneiosJob.observe { s ->
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

    // Set up iOS 27 shows the download or import with its bytes.
    override fun screen() = OneiosSetupActivity.intent(this)

    companion object {
        fun start(ctx: Context) = start(ctx, OneiosService::class.java)
    }
}
