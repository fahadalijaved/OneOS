package com.fahadali.oneos.session

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.os.SystemClock
import com.fahadali.oneos.R
import com.fahadali.oneos.ui.SetupProgressActivity

/**
 * Keeps setup alive while it runs (0.4.41). The 0.4.41 download was killed half way when the app was
 * swiped away ("Killing ... remove task" on the owner's Fold): a job in the app process dies with
 * its task. While [PrepareJob] is busy this foreground service holds the process, and its
 * notification shows the step and its progress; it stops itself when the job ends.
 */
class PrepareService : Service() {
    private var unsubscribe: (() -> Unit)? = null
    private var lastNotifyMs = 0L
    private var lastStep: PrepareJob.Step? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        channel(this)
        val first = notification(PrepareJob.state)
        runCatching { startForeground(ID, first, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) }
            .onFailure { stopSelf(); return START_NOT_STICKY }
        if (unsubscribe == null) {
            unsubscribe = PrepareJob.observe { s ->
                if (!s.busy) {
                    stopForeground(STOP_FOREGROUND_REMOVE)
                    stopSelf()
                    return@observe
                }
                // At most once a second, and at every new step: Android drops faster updates.
                val now = SystemClock.elapsedRealtime()
                if (s.step != lastStep || now - lastNotifyMs >= 1000) {
                    lastStep = s.step
                    lastNotifyMs = now
                    getSystemService(NotificationManager::class.java).notify(ID, notification(s))
                }
            }
        }
        return START_NOT_STICKY
    }

    /**
     * Android 15+ gives a dataSync foreground service 6 hours a day; past that it calls this and,
     * unless the service stops, ends the app (0.4.42 review). Setup goes on without the service.
     */
    override fun onTimeout(startId: Int, fgsType: Int) {
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    @Deprecated("Deprecated in Java")
    override fun onTimeout(startId: Int) {
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onDestroy()
    }

    private fun notification(s: PrepareJob.State): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, SetupProgressActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val title = s.image?.let { getString(R.string.setup_notification_title, it.shortName) } ?: getString(R.string.setup_label)
        val fraction = s.stepFraction
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_oneos_mark)
            .setContentTitle(title)
            .setContentText(listOfNotNull(s.step?.label, s.detail).joinToString(" · "))
            .setProgress(1000, ((fraction ?: 0f) * 1000).toInt(), fraction == null)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .build()
    }

    companion object {
        private const val CHANNEL = "oneos-setup"
        private const val ID = 4101

        private fun channel(ctx: Context) {
            val nm = ctx.getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL, ctx.getString(R.string.setup_notification_channel), NotificationManager.IMPORTANCE_LOW),
                )
            }
        }

        /** Started with the job (from the screen the user tapped); the job runs without it if Android refuses. */
        fun start(ctx: Context) {
            runCatching { ctx.applicationContext.startForegroundService(Intent(ctx.applicationContext, PrepareService::class.java)) }
        }
    }
}
