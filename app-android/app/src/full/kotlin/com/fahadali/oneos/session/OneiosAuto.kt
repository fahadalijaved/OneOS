package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.root.OneiosSteps

/**
 * Updates by themselves (the owner, 2026-11-25 & 2026-11-28: "auto update the kernel and runtime when an update is
 * there, so users don't get confused"; docs/oneios.md, "UI (2026-11-25)"). While iOS 27's page is open and nothing
 * else runs, the page calls [tick]; [OneiosSteps.auto] decides, in this order: put in a kernel Update the kernel built
 * (root's finish kernel); stage a newer release's runtime (Get the runtime's own download); build the kernel when the
 * image's is not the staged runtime's (Update the kernel's own flow); look for a newer release via [UpdateCheck] (at
 * most once an hour, shared with the app APK check). Each start is the same job a tap starts, shown on its step with
 * its progress and Cancel. Each is tried once per app run: a failure stays on its step with its reason, and the user's
 * tap tries again. Nothing starts during an iOS session.
 */
object OneiosAuto {
    private val tried = java.util.Collections.synchronizedSet(HashSet<String>())

    /** The newest release's runtime version from the last look (kept across runs); null before the first answer. */
    fun latest(ctx: Context): String? = UpdateCheck.latestRuntime(ctx)

    /** On the main thread, from the page's render: starts at most one thing. */
    fun tick(ctx: Context) {
        val app = ctx.applicationContext
        val idle = OneiosJob.canStart() && OneiosToolJob.canStart()
        // Nothing starts while anything runs: no work at all then (the page calls this with each progress line).
        if (!idle) return
        val input = com.fahadali.oneos.ui.OneiosStepRow.input(ctx)
        val latest = latest(app)
        val what = OneiosSteps.auto(OneiosSteps.AutoInput(input, idle, latest, checkDue = true, tried.toSet()))
        if (what == OneiosSteps.Auto.NONE) return
        if (what == OneiosSteps.Auto.CHECK_RUNTIME) {
            // UpdateCheck itself enforces the 1-hour rate limit and 10-minute retry backoff.
            UpdateCheck.run(app)
            return
        }
        tried += OneiosSteps.autoKey(what, input, latest)
        when (what) {
            OneiosSteps.Auto.ACTIVATE -> input.tool.builtKc?.let { OneiosJob.activateKernel(app, it) }
            OneiosSteps.Auto.UPDATE_RUNTIME -> OneiosJob.downloadRuntime(app, null)
            OneiosSteps.Auto.UPDATE_KERNEL -> OneiosToolJob.run(app, OneiosToolJob.Flow.KERNEL)
            OneiosSteps.Auto.CHECK_RUNTIME, OneiosSteps.Auto.NONE -> Unit
        }
    }
}
