package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.root.RootScript

/**
 * Remove OneOS data (0.4.25, Advanced; owner: "remove the folders it creates
 * ... clean stages, or whole OneOS folders"). Root `remove` deletes every old
 * copy, the stage with the other system's apps and accounts, the session's log
 * capture and its helper files, after checking all of them first: it refuses,
 * having changed nothing, while a session is running, one never returned, or
 * anything of one is still mounted or bridged. The app then deletes its own log
 * bundles and the last session's record and checks the phone again, so Home
 * starts from nothing set up. OneOS stays installed (Android's settings remove
 * the app), and downloaded system files stay where they were saved.
 */
object RemoveJob : BackgroundJob<RemoveJob.State>(State(), "oneos-remove") {
    enum class Phase { IDLE, REMOVING, DONE, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        /** The result line (what was freed), or why root refused. */
        val message: String? = null,
    ) {
        val busy: Boolean get() = phase == Phase.REMOVING
    }

    private fun othersBusy() =
        StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy || OldStagesJob.state.busy

    /** Whether [start] can run now (no other job uses root). */
    fun canStart(): Boolean = !state.busy && !othersBusy()

    fun start(ctx: Context) {
        if (!canStart()) return
        val app = ctx.applicationContext
        update(State(Phase.REMOVING))
        executor.execute {
            val r = runCatching { RootVerbs.run(app, RootScript.Verb.REMOVE, emptyList(), silenceMs = 10 * 60_000L) }
            val reply = r.getOrNull()
            if (reply?.ok == true) {
                // "purged <name> <KiB>": each copy, and the stage once renamed to one.
                val kib = reply.reply.results.filter { it.startsWith("purged ") }
                    .sumOf { it.substringAfterLast(' ').toLongOrNull() ?: 0L }
                LogJob.logsDir(app).deleteRecursively()
                SessionPrefs.forgetLaunch(app)
                update(State(Phase.DONE, "OneOS data removed: ${OldStagesJob.gib(kib)} freed."))
            } else {
                val why = reply?.problem ?: r.exceptionOrNull()?.let { it.message ?: it.javaClass.simpleName } ?: "no answer from root"
                update(State(Phase.FAILED, "Nothing was removed: $why"))
            }
            StageCheck.start(app, StageCheck.Mode.FULL)
        }
    }
}
