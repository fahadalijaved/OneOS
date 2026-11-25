package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.model.OneiosReleases
import com.fahadali.oneos.core.root.OneiosSteps
import java.net.HttpURLConnection
import java.net.URL

/**
 * Updates by themselves (the owner, 2026-11-25: "auto update the kernel and runtime when an update is there, so users
 * don't get confused"; docs/oneios.md, "UI (2026-11-25)"). While iOS 27's page is open and nothing else runs, the page
 * calls [tick]; [OneiosSteps.auto] decides, in this order: put in a kernel Update the kernel built (root's finish
 * kernel); stage a newer release's runtime (Get the runtime's own download); build the kernel when the image's is not
 * the staged runtime's (Update the kernel's own flow); look for a newer release, at most every 6 hours. Each start is
 * the same job a tap starts, shown on its step with its progress and Cancel. Each is tried once per app run: a failure
 * stays on its step with its reason, and the user's tap tries again. Nothing starts during an iOS session.
 */
object OneiosAuto {
    private const val PREFS = "oneios_auto"
    private const val KEY_CHECKED = "checked_at"
    private const val KEY_LATEST = "latest"

    /** After a look that got no answer (offline, GitHub refused), the next one in 10 minutes, not 6 hours. */
    private const val RETRY_MS = 10L * 60 * 1000

    @Volatile private var checking = false
    @Volatile private var nextCheckAt = 0L
    private val tried = java.util.Collections.synchronizedSet(HashSet<String>())

    /** The newest release's runtime version from the last look (kept across runs); null before the first answer. */
    fun latest(ctx: Context): String? = prefs(ctx).getString(KEY_LATEST, null)

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** On the main thread, from the page's render: starts at most one thing. */
    fun tick(ctx: Context) {
        val app = ctx.applicationContext
        val idle = OneiosJob.canStart() && OneiosToolJob.canStart()
        // Nothing starts while anything runs: no work at all then (the page calls this with each progress line).
        if (!idle) return
        val input = com.fahadali.oneos.ui.OneiosStepRow.input(ctx)
        val now = System.currentTimeMillis()
        val due = !checking && now >= nextCheckAt && now - prefs(app).getLong(KEY_CHECKED, 0) >= OneiosSteps.CHECK_EVERY_MS
        val latest = latest(app)
        val what = OneiosSteps.auto(OneiosSteps.AutoInput(input, idle, latest, due, tried.toSet()))
        if (what == OneiosSteps.Auto.NONE) return
        tried += OneiosSteps.autoKey(what, input, latest)
        when (what) {
            OneiosSteps.Auto.ACTIVATE -> input.tool.builtKc?.let { OneiosJob.activateKernel(app, it) }
            OneiosSteps.Auto.UPDATE_RUNTIME -> OneiosJob.downloadRuntime(app, null)
            OneiosSteps.Auto.UPDATE_KERNEL -> OneiosToolJob.run(app, OneiosToolJob.Flow.KERNEL)
            OneiosSteps.Auto.CHECK_RUNTIME -> check(app)
            OneiosSteps.Auto.NONE -> Unit
        }
    }

    /** The latest release's runtime version from GitHub's API (one small request on a thread of its own). */
    private fun check(app: Context) {
        checking = true
        Thread({
            val version = runCatching { latestVersion() }.getOrNull()
            val now = System.currentTimeMillis()
            if (version != null) {
                prefs(app).edit().putLong(KEY_CHECKED, now).putString(KEY_LATEST, version).apply()
            } else {
                nextCheckAt = now + RETRY_MS
            }
            checking = false
            // The page hears of it with the next state change; nudge it now when something is to do.
            if (version != null) android.os.Handler(android.os.Looper.getMainLooper()).post { OneiosJob.nudge() }
        }, "oneos-oneios-auto").start()
    }

    private fun latestVersion(): String? {
        val c = URL(OneiosReleases.apiUrl(null)).openConnection() as HttpURLConnection
        return try {
            c.connectTimeout = 15_000
            c.readTimeout = 15_000
            c.setRequestProperty("Accept", "application/vnd.github+json")
            c.setRequestProperty("User-Agent", "OneOS")
            if (c.responseCode != 200) return null
            val text = c.inputStream.use { it.readBytes().take(1 shl 20).toByteArray().toString(Charsets.UTF_8) }
            OneiosReleases.parse(text).getOrNull()?.version
        } finally {
            c.disconnect()
        }
    }
}
