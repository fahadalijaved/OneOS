package com.fahadali.oneos.session

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.fahadali.oneos.core.model.OneiosAppRelease
import com.fahadali.oneos.core.model.OneiosAppReleases
import com.fahadali.oneos.core.model.OneiosReleases
import com.fahadali.oneos.core.model.OneiosUpdates
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * The one look for updates (the owner, 2026-11-28: "updates should be checked automatically: the runtime, the kernel
 * and the app itself"; docs/oneios.md, "Updates"). One request to GitHub's API for OneiOS's latest release answers
 * both: its runtime version ([OneiosAuto.latest]) and its OneOS APK ([OneiosAppReleases], handed to [AppUpdater]).
 * Asked at app start and whenever the main screen or iOS 27's page is shown, at most once an hour
 * ([OneiosUpdates.CHECK_EVERY_MS]; 10 minutes after a look that got no answer): no loop, no background timer.
 * Whether the kernel is due is the phone's own state (the image's kernel.kc against the staged runtime's kernel),
 * read by the screens, not from GitHub.
 */
object UpdateCheck {
    private const val PREFS = "oneios_auto"
    private const val KEY_CHECKED = "checked_at"
    private const val KEY_LATEST = "latest"

    @Volatile private var running = false
    @Volatile private var nextTryAt = 0L

    /** The newest release's OneOS APK from the last answered look in this run; null before it or when it had none. */
    @Volatile var app: OneiosAppRelease? = null
        private set

    private val listeners = java.util.concurrent.CopyOnWriteArrayList<() -> Unit>()

    /** Called on the main thread after each answered look; returns the call that stops listening. */
    fun observe(l: () -> Unit): () -> Unit {
        listeners += l
        return { listeners -= l }
    }

    fun latestRuntime(ctx: Context): String? = prefs(ctx).getString(KEY_LATEST, null)

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** Looks now when due ([force]: now, as Check for updates); one small request on a thread of its own. */
    fun run(ctx: Context, force: Boolean = false) {
        val app = ctx.applicationContext
        val now = System.currentTimeMillis()
        // (A start of the app always looks once: the APK on offer is not kept across runs.)
        val due = OneiosUpdates.checkDue(now, if (lookedThisRun) prefs(app).getLong(KEY_CHECKED, 0) else 0, nextTryAt, force)
        if (running || !due) return
        running = true
        AppUpdater.markChecking(app, force)
        Thread({
            val r = runCatching { fetch() }
            val at = System.currentTimeMillis()
            r.onSuccess { (runtime, apk) ->
                lookedThisRun = true
                prefs(app).edit().putLong(KEY_CHECKED, at).apply { if (runtime != null) putString(KEY_LATEST, runtime) }.apply()
                this.app = apk
                AppUpdater.offer(app, apk)
            }.onFailure {
                nextTryAt = at + OneiosUpdates.RETRY_MS
                AppUpdater.offerFailed("Could not check for an update: ${it.message ?: it.javaClass.simpleName}")
            }
            running = false
            Handler(Looper.getMainLooper()).post {
                listeners.forEach { it() }
                OneiosJob.nudge()
            }
        }, "oneos-update-check").start()
    }

    @Volatile private var lookedThisRun = false

    /** The latest release: its runtime version (null: none in it) and its OneOS APK (null: none, or no versionCode in its notes). */
    private fun fetch(): Pair<String?, OneiosAppRelease?> {
        val text = get(OneiosReleases.apiUrl(null), 1 shl 20)
        val runtime = OneiosReleases.parse(text).getOrNull()?.version
        return runtime to OneiosAppReleases.parse(text)
    }

    /** The SHA-256 in an APK's `.sha256` asset (one `sha256sum` line). */
    fun sha256Of(release: OneiosAppRelease): String =
        OneiosReleases.parseSha256(get(release.sha256Url, 4096), release.assetName)
            ?: throw IOException("${release.assetName}.sha256 holds no SHA-256 of ${release.assetName}")

    private fun get(url: String, max: Int): String {
        val c = URL(url).openConnection() as HttpURLConnection
        try {
            c.connectTimeout = 15_000
            c.readTimeout = 15_000
            c.instanceFollowRedirects = true
            c.setRequestProperty("Accept", "application/vnd.github+json")
            c.setRequestProperty("User-Agent", "OneOS")
            if (c.responseCode != HttpURLConnection.HTTP_OK) throw IOException("GitHub answered HTTP ${c.responseCode}")
            return c.inputStream.use { it.readNBytes(max) }.toString(Charsets.UTF_8)
        } finally {
            c.disconnect()
        }
    }
}
