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

    /**
     * ALL: Advanced > Remove OneOS data. SYSTEM and DATA (0.5.09, the system card's menu): root
     * `remove-system` deletes only the system set up now with its apps and data, `reset-data` only its
     * apps, accounts and settings (the next start is a first start). Old copies, logs and downloaded
     * system files stay in both.
     */
    enum class Kind(val verb: RootScript.Verb) { ALL(RootScript.Verb.REMOVE), SYSTEM(RootScript.Verb.REMOVE_SYSTEM), DATA(RootScript.Verb.RESET_DATA) }

    data class State(
        val phase: Phase = Phase.IDLE,
        /** The result line (what was freed), or why root refused. */
        val message: String? = null,
        /** Which removal ran last: everything, one system, or one system's data. */
        val kind: Kind = Kind.ALL,
        /** What root is doing now, in plain words (null before its first step). */
        val step: String? = null,
        /** `elapsedRealtime` the run started at. */
        val startedAt: Long = 0,
    ) {
        val busy: Boolean get() = phase == Phase.REMOVING
    }

    private fun othersBusy() =
        StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy || OldStagesJob.state.busy

    /** Whether [start] can run now (no other job uses root). */
    fun canStart(): Boolean = !state.busy && !othersBusy()

    fun start(ctx: Context) = start(ctx, Kind.ALL)

    /** [name] is the system's name for the result line (SYSTEM, DATA). */
    fun start(ctx: Context, kind: Kind, name: String? = null) {
        if (!canStart()) return
        val app = ctx.applicationContext
        update(State(Phase.REMOVING, kind = kind, step = "Checking it is safe to delete…", startedAt = android.os.SystemClock.elapsedRealtime()))
        executor.execute {
            val r = runCatching { RootVerbs.run(app, kind.verb, emptyList(), silenceMs = 10 * 60_000L) { raw ->
                plainStep(raw)?.let { update(state.copy(step = it)) }
            } }
            val reply = r.getOrNull()
            if (reply?.ok == true) {
                // "purged <name> <KiB>": each copy, and the stage once renamed to one.
                val kib = reply.reply.results.filter { it.startsWith("purged ") }
                    .sumOf { it.substringAfterLast(' ').toLongOrNull() ?: 0L }
                val freed = OldStagesJob.gib(kib)
                val line = when (kind) {
                    Kind.ALL -> {
                        LogJob.logsDir(app).deleteRecursively()
                        SessionPrefs.forgetLaunch(app)
                        "OneOS data removed: $freed freed."
                    }
                    Kind.SYSTEM -> {
                        SessionPrefs.forgetLaunch(app)
                        "${name ?: "The system"} removed: $freed freed."
                    }
                    Kind.DATA -> "${name ?: "The system"} starts fresh next time: $freed freed."
                }
                update(State(Phase.DONE, line, kind))
            } else {
                val why = reply?.problem ?: r.exceptionOrNull()?.let { it.message ?: it.javaClass.simpleName } ?: "no answer from root"
                update(State(Phase.FAILED, "Nothing was removed: $why", kind))
            }
            StageCheck.start(app, StageCheck.Mode.FULL)
        }
    }

    /** Root's `@@STEP` lines (aside, rename, move, delete) in plain words. */
    fun plainStep(raw: String): String? = when {
        raw.startsWith("aside") || raw.startsWith("rename") || raw.startsWith("move") -> "Moving it out of the way…"
        raw.startsWith("delete") -> "Deleting files… a big system takes a minute or two."
        else -> null
    }
}
