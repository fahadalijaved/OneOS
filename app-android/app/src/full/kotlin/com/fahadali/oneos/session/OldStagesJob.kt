package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.root.OldStage
import com.fahadali.oneos.core.root.OldStages
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.SuProbe
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.probe.ProbeSession

/**
 * Old stages (0.3.5): lists the stages `begin aside` left behind (root
 * `old-list`, read only) and deletes one the user confirmed (root `purge`,
 * which checks again that nothing is mounted, bridged or running there), or
 * (0.4.10) uses one again (root `restore`: the stage set up now moves aside
 * and is kept, after the same checks on both). 0.4.11: [deleteAll] deletes
 * every old copy not in use (or the named ones) in one go, one `purge` each,
 * for Free up space's Delete all and setup's Delete the old copy.
 */
object OldStagesJob : BackgroundJob<OldStagesJob.State>(State(), "oneos-old-stages") {
    enum class Phase { IDLE, LISTING, DELETING, RESTORING, DONE, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        val stages: List<OldStage>? = null,
        val deleting: String? = null,
        /** The copy being restored, while root runs. */
        val restoring: String? = null,
        /** The last [restore] put a copy back (the system it holds is set up now). */
        val restored: Boolean = false,
        /** The last [restore] did not happen (its reason is [message]). */
        val restoreFailed: Boolean = false,
        /** `elapsedRealtime` the last [restore] put a copy back at (Quick switch waits for a stage check after it); 0 otherwise. */
        val restoredAt: Long = 0,
        val message: String? = null,
        /** What the last delete freed (KiB), for Free up space's result line; null otherwise. */
        val freedKib: Long? = null,
        /** The last [delete] did not delete (its reason is [message]); a failed list leaves it false. */
        val deleteFailed: Boolean = false,
        /** [deleteAll] running: the copy it is on (1-based) and how many it deletes. */
        val batch: Pair<Int, Int>? = null,
        /** What the last [deleteAll] deleted; null after any other run. */
        val deletedNames: List<String>? = null,
    ) {
        val busy: Boolean get() = phase == Phase.LISTING || phase == Phase.DELETING || phase == Phase.RESTORING
    }

    private fun othersBusy() = StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy

    fun refresh(ctx: Context) {
        if (state.busy || othersBusy()) return
        val app = ctx.applicationContext
        update(state.copy(phase = Phase.LISTING, message = null, freedKib = null, deleteFailed = false, restored = false, restoreFailed = false, deletedNames = null))
        executor.execute {
            val r = runCatching { list(app) }
            update(
                r.fold(
                    { state.copy(phase = Phase.DONE, stages = it) },
                    { state.copy(phase = Phase.FAILED, message = it.message ?: it.javaClass.simpleName) },
                ),
            )
        }
    }

    fun delete(ctx: Context, stage: OldStage) {
        if (state.busy || othersBusy()) return
        val app = ctx.applicationContext
        update(state.copy(phase = Phase.DELETING, deleting = stage.name, message = null, freedKib = null, deleteFailed = false, restored = false, restoreFailed = false, deletedNames = null))
        executor.execute {
            val r = runCatching {
                su(app)
                RootVerbs.run(app, RootScript.Verb.PURGE, listOf(stage.name), silenceMs = 10 * 60_000L)
            }
            val reply = r.getOrNull()
            val freed = if (reply?.ok == true) OldStages.freedKib(reply.reply.results, stage.name) ?: stage.kib else null
            val msg = when {
                reply == null -> r.exceptionOrNull()?.message
                reply.ok -> "Deleted ${stage.name}: ${gib(freed ?: stage.kib)} freed."
                else -> "Not deleted: ${reply.problem}"
            }
            val after = runCatching { list(app) }.getOrNull()
            update(
                state.copy(
                    phase = if (reply?.ok == true) Phase.DONE else Phase.FAILED, deleting = null, stages = after ?: state.stages,
                    message = msg, freedKib = freed, deleteFailed = reply?.ok != true,
                ),
            )
            if (reply?.ok == true) StageCheck.start(app, StageCheck.Mode.STAGE_ONLY)
        }
    }

    /**
     * Deletes every old copy root lists that is not in use, or only those in
     * [only] (setup's copy it just set aside), one root `purge` each, which
     * checks each one again. Stops at the first refusal; what was deleted by
     * then stays deleted ([State.deletedNames], [State.freedKib]).
     */
    fun deleteAll(ctx: Context, only: Set<String>? = null) {
        if (state.busy || othersBusy()) return
        val app = ctx.applicationContext
        update(state.copy(phase = Phase.DELETING, deleting = null, batch = null, message = null, freedKib = null, deleteFailed = false, restored = false, restoreFailed = false, deletedNames = null))
        executor.execute {
            val deleted = mutableListOf<String>()
            var freed = 0L
            var problem: String? = null
            runCatching {
                val todo = list(app).filter { !it.busy && (only == null || it.name in only) }
                todo.forEachIndexed { i, stage ->
                    if (problem != null) return@forEachIndexed
                    update(state.copy(deleting = stage.name, batch = (i + 1) to todo.size))
                    val reply = RootVerbs.run(app, RootScript.Verb.PURGE, listOf(stage.name), silenceMs = 10 * 60_000L)
                    if (reply.ok) {
                        deleted += stage.name
                        freed += OldStages.freedKib(reply.reply.results, stage.name) ?: stage.kib
                    } else {
                        problem = "Not deleted: ${stage.name}: ${reply.problem}"
                    }
                }
            }.onFailure { problem = it.message ?: it.javaClass.simpleName }
            val after = runCatching { list(app) }.getOrNull()
            val msg = problem ?: "Deleted ${deleted.size} old ${if (deleted.size == 1) "copy" else "copies"}: ${gib(freed)} freed."
            update(
                state.copy(
                    phase = if (problem == null) Phase.DONE else Phase.FAILED, deleting = null, batch = null, stages = after ?: state.stages,
                    message = msg, freedKib = freed, deleteFailed = problem != null, deletedNames = deleted.toList(),
                ),
            )
            // Home's space tile and old-copy count come from the stage check.
            StageCheck.start(app, StageCheck.Mode.STAGE_ONLY)
        }
    }

    /**
     * Uses [stage] again: root `restore` sets the stage up now aside (kept as
     * another old copy) and puts this one back; then Home's stage check runs,
     * so Home shows that system and asks for Update now when its files are older.
     */
    fun restore(ctx: Context, stage: OldStage) {
        if (state.busy || othersBusy()) return
        val app = ctx.applicationContext
        update(state.copy(phase = Phase.RESTORING, restoring = stage.name, message = null, freedKib = null, deleteFailed = false, restored = false, restoreFailed = false, deletedNames = null))
        executor.execute {
            val r = runCatching {
                su(app)
                RootVerbs.run(app, RootScript.Verb.RESTORE, listOf(stage.name), silenceMs = 5 * 60_000L)
            }
            val reply = r.getOrNull()
            val aside = if (reply?.ok == true) OldStages.setAsideBy(reply.reply.results, stage.name) else null
            val msg = when {
                reply == null -> r.exceptionOrNull()?.message
                reply.ok -> "Restored ${stage.name}" + (aside?.let { "; the stage set up before is kept as $it" } ?: "") + "."
                else -> "Not restored: ${reply.problem}"
            }
            val after = runCatching { list(app) }.getOrNull()
            update(
                state.copy(
                    phase = if (reply?.ok == true) Phase.DONE else Phase.FAILED, restoring = null, stages = after ?: state.stages,
                    message = msg, restored = reply?.ok == true, restoreFailed = reply?.ok != true,
                    restoredAt = if (reply?.ok == true) android.os.SystemClock.elapsedRealtime() else 0,
                ),
            )
            if (reply?.ok == true) StageCheck.start(app, StageCheck.Mode.STAGE_ONLY)
        }
    }

    private fun su(app: Context) {
        val s = SuProbe.runId()
        check(s.state == SuState.GRANTED) { ProbeSession.suText(app, s) }
    }

    private fun list(app: Context): List<OldStage> {
        su(app)
        val reply = RootVerbs.run(app, RootScript.Verb.OLD_LIST, emptyList(), silenceMs = 5 * 60_000L)
        check(reply.ok) { "Could not list old stages: ${reply.problem}" }
        return OldStages.parse(reply.reply.results)
    }

    fun gib(kib: Long): String = String.format(java.util.Locale.ROOT, "%.1f GB", kib / 1_048_576.0)
}
