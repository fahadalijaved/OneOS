package com.fahadali.oneos.session

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.AppUpdate
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.SuProbe
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * OneOS updates itself (0.4.41; owner: "include apk updater in OneOS rather than
 * shipping APK over and over ... all of them have root"). [check] reads the
 * latest GitHub release's update.json (at most every few hours, or when asked);
 * [install] downloads the APK it names into `files/oneos-update/OneOS.apk`,
 * checks its size and SHA-256, that it is this app (package name), signed with
 * the certificate this copy is signed with and a higher versionCode, and root
 * `selfupdate` installs it: the app closes and opens again as the new version.
 * The package set files are downloaded by Prepare (SetDownloader), so the APK
 * is small and an update does not download any system's files again.
 *
 * Without root (0.4.45; owner: a phone whose root was off after a restart got
 * "The update didn't install" on every try) Android's own installer installs
 * the same checked APK and asks the user to confirm ([Phase.CONFIRM]);
 * setting up and switching still need root.
 */
object AppUpdater : BackgroundJob<AppUpdater.State>(State(), "oneos-update") {
    enum class Phase { IDLE, CHECKING, CURRENT, AVAILABLE, DOWNLOADING, INSTALLING, CONFIRM, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        val update: AppUpdate? = null,
        val percent: Int = 0,
        val message: String? = null,
    ) {
        val busy: Boolean get() = phase == Phase.CHECKING || phase == Phase.DOWNLOADING || phase == Phase.INSTALLING
    }

    private const val PREFS = "oneos-update"
    private const val APK = "OneOS.apk"
    private const val ROOT_PROBE_MS = 15_000L
    private const val NO_ROOT = "Root is off, so Android's installer installs the update: confirm it there. " +
        "Setting up and switching still need root."
    private const val CHECK_EVERY_MS = 6 * 3600_000L

    @Volatile private var cancelled = false

    /** Android installer's confirmation for the update handed to it without root ([Phase.CONFIRM]). */
    @Volatile private var confirmIntent: Intent? = null

    /**
     * The team's test channel (Debug settings): update.json from the owner's Drive instead of GitHub, on
     * while a test channel code is stored (0.4.56: [AppUpdate.testUrl]; the 0.4.41-0.4.55 switch is gone).
     */
    fun testCode(ctx: Context): String? =
        ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("test_code", null)
            ?.takeIf { AppUpdate.testUrl(it) != null }

    fun testChannel(ctx: Context): Boolean = testCode(ctx) != null

    /** Stores [code] (empty: test channel off); false when it is no test channel code. */
    fun setTestCode(ctx: Context, code: String): Boolean {
        val c = code.trim()
        if (c.isNotEmpty() && AppUpdate.testUrl(c) == null) return false
        ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString("test_code", c.ifEmpty { null }).remove("test_channel").apply()
        if (!state.busy) update(State())
        check(ctx, force = true)
        return true
    }

    fun dir(ctx: Context): File = File(ctx.applicationContext.filesDir, "oneos-update").apply { mkdirs() }

    private fun othersBusy() =
        StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy ||
            OldStagesJob.state.busy || RemoveJob.state.busy

    /** Reads update.json unless it was read in the last hours ([force]: now). */
    fun check(ctx: Context, force: Boolean = false) {
        if (state.busy) return
        val app = ctx.applicationContext
        val prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (!force && state.phase != Phase.IDLE && now - prefs.getLong("checked", 0) < CHECK_EVERY_MS) return
        update(state.copy(phase = Phase.CHECKING, message = null))
        executor.execute {
            val testUrl = AppUpdate.testUrl(testCode(app))
            val test = testUrl != null
            val r = runCatching { AppUpdate.parse(fetchText(testUrl ?: AppUpdate.URL), test).getOrThrow() }
            prefs.edit().putLong("checked", now).apply()
            val u = r.getOrNull()
            update(
                when {
                    u == null -> State(Phase.FAILED, message = "Could not check for an update: ${r.exceptionOrNull()?.message ?: "no answer"}")
                    u.newerThan(BuildConfig.VERSION_CODE) -> State(Phase.AVAILABLE, u)
                    else -> State(Phase.CURRENT, u)
                },
            )
            // The APK an earlier update installed stayed in files/oneos-update (0.4.44): only the
            // update on offer is kept (its part, to resume, or its download, checked again before use).
            val keep = u?.takeIf { it.newerThan(BuildConfig.VERSION_CODE) }?.let { setOf("OneOS-${it.versionCode}.part", APK) }.orEmpty()
            dir(app).listFiles()?.filter { it.name !in keep }?.forEach { it.delete() }
        }
    }

    fun canInstall(): Boolean =
        state.phase == Phase.AVAILABLE || ((state.phase == Phase.FAILED || state.phase == Phase.CONFIRM) && state.update != null)

    /** Android installer's confirmation again (the user left it); a new install when there is none. */
    fun confirm(ctx: Context) {
        val i = confirmIntent
        if (state.phase == Phase.CONFIRM && i != null && runCatching { ctx.startActivity(i) }.isSuccess) return
        install(ctx)
    }

    /** Downloads, checks and installs [State.update]; the app is replaced and reopened. */
    fun install(ctx: Context) {
        val u = state.update ?: return
        if (state.busy || !u.newerThan(BuildConfig.VERSION_CODE)) return
        if (othersBusy()) {
            update(State(Phase.FAILED, u, message = "OneOS is busy: update when the setup or check has finished."))
            return
        }
        val app = ctx.applicationContext
        cancelled = false
        update(State(Phase.DOWNLOADING, u))
        executor.execute {
            val r = runCatching {
                val apk = File(dir(app), APK)
                val part = File(dir(app), "OneOS-${u.versionCode}.part")
                // The download an earlier try checked is used again (0.4.45): Try again downloaded it each time.
                val have = apk.length() == u.bytes && runCatching { SetDownloader.verify(apk, u.bytes, u.sha256, "OneOS ${u.versionName}") }.isSuccess
                if (!have) {
                    dir(app).listFiles()?.filter { it != part }?.forEach { it.delete() }
                    if (part.length() > u.bytes) part.delete()
                    SetDownloader.download(part, u.apk, u.bytes, "OneOS ${u.versionName}", { cancelled }) { done ->
                        val pct = (done * 100 / u.bytes).toInt()
                        if (pct != state.percent) update(State(Phase.DOWNLOADING, u, pct))
                    }
                    SetDownloader.verify(part, u.bytes, u.sha256, "OneOS ${u.versionName}")
                    if (!part.renameTo(apk)) throw IOException("could not keep the update")
                }
                apk.setReadable(true, false)
                checkApk(app, apk, u)
                update(State(Phase.INSTALLING, u, 100))
                val su = SuProbe.runId(ROOT_PROBE_MS)
                if (su.state == SuState.GRANTED && su.uid == 0) {
                    val reply = RootVerbs.run(app, RootScript.Verb.SELFUPDATE, listOf(u.bytes.toString(), u.sha256, u.versionCode.toString()), silenceMs = 5 * 60_000L)
                    // On success the install closes this app before the reply ends; still here means it did not install.
                    if (!reply.ok) throw IOException(reply.problem ?: "root did not install it")
                    false
                } else {
                    installWithAndroid(app, apk)
                    true
                }
            }
            when {
                r.isFailure -> update(State(Phase.FAILED, u, message = "The update was not installed: ${r.exceptionOrNull()?.message ?: "unknown error"}"))
                // Android's installer may have answered already ([onInstallerResult]).
                r.getOrNull() == true -> if (state.phase == Phase.INSTALLING) update(State(Phase.CONFIRM, u, 100, NO_ROOT))
                else -> update(State(Phase.INSTALLING, u, 100, "Installed: OneOS opens again as ${u.versionName}."))
            }
        }
    }

    /**
     * The checked APK to Android's installer, for a phone without root: the same app, the same
     * certificate, a newer build, so Android updates it in place once the user confirms (and, the
     * first time, allows OneOS to install apps). [ResultReceiver] gets the answer.
     */
    private fun installWithAndroid(app: Context, apk: File) {
        confirmIntent = null
        val installer = app.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(app.packageName)
            setSize(apk.length())
            setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
        }
        val id = installer.createSession(params)
        try {
            installer.openSession(id).use { s ->
                s.openWrite(APK, 0, apk.length()).use { out ->
                    apk.inputStream().use { it.copyTo(out) }
                    s.fsync(out)
                }
                val result = Intent(app, ResultReceiver::class.java).setPackage(app.packageName)
                val pending = PendingIntent.getBroadcast(app, id, result, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)
                s.commit(pending.intentSender)
            }
        } catch (e: Exception) {
            runCatching { installer.abandonSession(id) }
            throw IOException("Android's installer refused it: ${e.message ?: e.javaClass.simpleName}")
        }
    }

    /** Android installer's answers for [installWithAndroid]. */
    class ResultReceiver : BroadcastReceiver() {
        override fun onReceive(ctx: Context, intent: Intent) = AppUpdater.onInstallerResult(ctx, intent)
    }

    private fun onInstallerResult(ctx: Context, intent: Intent) {
        val u = state.update
        when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirm = (
                    if (android.os.Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                    else @Suppress("DEPRECATION") intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                    ) ?: return
                confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                confirmIntent = confirm
                update(State(Phase.CONFIRM, u, 100, NO_ROOT))
                // Opens while OneOS is in front; else the Update line opens it ([confirm]).
                runCatching { ctx.startActivity(confirm) }
            }
            PackageInstaller.STATUS_SUCCESS -> update(State(Phase.INSTALLING, u, 100, "Installed: open OneOS again."))
            PackageInstaller.STATUS_FAILURE_ABORTED -> {
                confirmIntent = null
                update(State(Phase.FAILED, u, message = "The update was not installed: you cancelled it in Android's installer."))
            }
            else -> {
                confirmIntent = null
                val why = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "status $status"
                update(State(Phase.FAILED, u, message = "The update was not installed: Android's installer said $why."))
            }
        }
    }

    fun cancel() {
        cancelled = true
    }

    /** This app, signed with this copy's certificate, and newer than it. */
    private fun checkApk(ctx: Context, apk: File, u: AppUpdate) {
        val pm = ctx.packageManager
        val flags = PackageManager.GET_SIGNING_CERTIFICATES
        val info = pm.getPackageArchiveInfo(apk.path, flags) ?: throw IOException("the download is not an app")
        if (info.packageName != ctx.packageName) throw IOException("the download is ${info.packageName}, not OneOS")
        if (info.longVersionCode != u.versionCode.toLong()) throw IOException("the download is build ${info.longVersionCode}, update.json says ${u.versionCode}")
        if (info.longVersionCode <= BuildConfig.VERSION_CODE) throw IOException("the download is not newer than this OneOS")
        val mine = pm.getPackageInfo(ctx.packageName, flags).signingInfo?.apkContentsSigners?.toSet().orEmpty()
        val theirs = info.signingInfo?.apkContentsSigners?.toSet().orEmpty()
        if (mine.isEmpty() || mine != theirs) {
            throw IOException("the download is signed with another key than this OneOS (a test build? install the release by hand)")
        }
    }

    private fun fetchText(url: String): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 20_000
        c.readTimeout = 20_000
        c.instanceFollowRedirects = true
        try {
            if (c.responseCode != HttpURLConnection.HTTP_OK) throw IOException("HTTP ${c.responseCode}")
            return c.inputStream.use { it.readNBytes(4097) }.toString(Charsets.UTF_8)
        } finally {
            c.disconnect()
        }
    }
}
