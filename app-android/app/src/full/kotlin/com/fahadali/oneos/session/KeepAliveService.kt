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
import android.os.PowerManager
import android.os.SystemClock
import com.fahadali.oneos.R

/**
 * Keeps a long job of the app alive while it runs: setting up an Android system
 * ([PrepareService], 0.4.41) and importing a OneiOS package ([OneiosService]).
 * A job in the app process dies with its task, and an app that is not on the
 * screen is frozen: while the job is busy this foreground service holds the
 * process, and its notification shows the step and its progress; it stops
 * itself when the job ends.
 */
abstract class KeepAliveService : Service() {
    /** What the notification shows; [key] changing (a new step) updates it at once. */
    data class Show(val busy: Boolean, val key: Any?, val title: String, val text: String, val fraction: Float?)

    protected abstract val notificationId: Int

    /** Calls the listener now and on every change of the job (main thread); returns the unsubscribe call. */
    protected abstract fun observe(listener: (Show) -> Unit): () -> Unit

    /** The screen a tap on the notification opens. */
    protected abstract fun screen(): Intent

    /**
     * Also keep the CPU awake while busy, so the job goes on with the screen off. Only while busy, and
     * never longer than [WAKE_MAX_MS].
     */
    protected open val keepCpuAwake: Boolean = false

    private var unsubscribe: (() -> Unit)? = null
    private var lastNotifyMs = 0L
    private var lastKey: Any? = null
    private var wake: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        channel(this)
        var first: Show? = null
        observe { first = it }.invoke()
        runCatching { startForeground(notificationId, notification(first!!), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC) }
            .onFailure { stopSelf(); return START_NOT_STICKY }
        if (keepCpuAwake && wake == null) {
            wake = runCatching {
                getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "oneos:job").apply {
                    setReferenceCounted(false)
                    acquire(WAKE_MAX_MS)
                }
            }.getOrNull()
        }
        if (unsubscribe == null) {
            unsubscribe = observe { s ->
                if (!s.busy) {
                    end()
                    return@observe
                }
                // At most once a second, and at every new step: Android drops faster updates.
                val now = SystemClock.elapsedRealtime()
                if (s.key != lastKey || now - lastNotifyMs >= 1000) {
                    lastKey = s.key
                    lastNotifyMs = now
                    getSystemService(NotificationManager::class.java).notify(notificationId, notification(s))
                }
            }
        }
        return START_NOT_STICKY
    }

    private fun end() {
        release()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun release() {
        runCatching { wake?.takeIf { it.isHeld }?.release() }
        wake = null
    }

    /**
     * Android 15+ gives a dataSync foreground service 6 hours a day; past that it calls this and,
     * unless the service stops, ends the app (0.4.42 review). The job goes on without the service.
     */
    override fun onTimeout(startId: Int, fgsType: Int) = end()

    @Deprecated("Deprecated in Java")
    override fun onTimeout(startId: Int) = end()

    override fun onDestroy() {
        unsubscribe?.invoke()
        unsubscribe = null
        release()
        super.onDestroy()
    }

    private fun notification(s: Show): Notification {
        val open = PendingIntent.getActivity(
            this, notificationId, screen().addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_oneos_mark)
            .setContentTitle(s.title)
            .setContentText(s.text)
            .setProgress(1000, ((s.fraction ?: 0f) * 1000).toInt(), s.fraction == null)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .build()
    }

    companion object {
        private const val CHANNEL = "oneos-setup"
        private const val WAKE_MAX_MS = 2 * 60 * 60_000L

        private fun channel(ctx: Context) {
            val nm = ctx.getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL, ctx.getString(R.string.setup_notification_channel), NotificationManager.IMPORTANCE_LOW),
                )
            }
        }

        /** Started with the job (from the screen the user tapped); the job runs without it if Android refuses. */
        fun start(ctx: Context, service: Class<out KeepAliveService>) {
            runCatching { ctx.applicationContext.startForegroundService(Intent(ctx.applicationContext, service)) }
        }
    }
}
