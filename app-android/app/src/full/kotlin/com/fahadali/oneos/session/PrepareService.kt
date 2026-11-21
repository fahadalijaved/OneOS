package com.fahadali.oneos.session

import android.content.Context
import android.content.Intent
import com.fahadali.oneos.R
import com.fahadali.oneos.ui.SetupProgressActivity

/**
 * Keeps setup alive while it runs (0.4.41). The 0.4.41 download was killed half way when the app was
 * swiped away ("Killing ... remove task" on the owner's Fold): a job in the app process dies with
 * its task. While [PrepareJob] is busy this foreground service ([KeepAliveService]) holds the process, and its
 * notification shows the step and its progress; it stops itself when the job ends.
 */
class PrepareService : KeepAliveService() {
    override val notificationId = 4101

    override fun observe(listener: (Show) -> Unit): () -> Unit = PrepareJob.observe { s ->
        listener(
            Show(
                busy = s.busy,
                key = s.step,
                title = s.image?.let { getString(R.string.setup_notification_title, it.shortName) } ?: getString(R.string.setup_label),
                text = listOfNotNull(s.step?.label, s.detail).joinToString(" · "),
                fraction = s.stepFraction,
            ),
        )
    }

    override fun screen() = Intent(this, SetupProgressActivity::class.java)

    companion object {
        /** Started with the job (from the screen the user tapped); the job runs without it if Android refuses. */
        fun start(ctx: Context) = start(ctx, PrepareService::class.java)
    }
}
