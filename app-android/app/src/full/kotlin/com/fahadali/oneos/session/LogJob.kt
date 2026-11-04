package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.model.ProbeStatus
import com.fahadali.oneos.core.model.Redactor
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.core.root.LogBundle
import com.fahadali.oneos.core.root.LogBundleInput
import com.fahadali.oneos.core.root.LogRules
import com.fahadali.oneos.core.root.LogStats
import com.fahadali.oneos.core.root.RedactingOutputStream
import com.fahadali.oneos.core.root.ReturnOutcome
import com.fahadali.oneos.core.root.ReturnOutcomes
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.StageStatus
import com.fahadali.oneos.core.root.SuProbe
import com.fahadali.oneos.probe.ProbeSession
import com.fahadali.oneos.ui.FindingsActivity
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.OutputStream
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

/**
 * Last session (AA19, AA20): Collect logs runs the read-only list
 * assets/logs/collect.list as root. Every line is redacted as it arrives
 * (LogRules' drop tags, Redactor's masks, the saved Wi-Fi names learned first
 * and kept in memory only) before it reaches the app's cache; recordings and
 * screenshots are never taken. Then `oneos-logs-<session>.zip` is built in
 * cache/logs/ for Share or Save. Restore One UI's settings runs the root
 * script's `recover` after a session that never returned.
 */
object LogJob : BackgroundJob<LogJob.State>(State(), "oneos-logs") {
    enum class Phase { IDLE, RUNNING, DONE, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        val detail: String? = null,
        val message: String? = null,
        val outcome: ReturnOutcome? = null,
        val zip: File? = null,
        val status: StageStatus? = null,
        val recovered: String? = null,
        /** Started by itself after a return (Readiness), not from Last session. */
        val auto: Boolean = false,
        /** The session these logs are of. */
        val sessionId: String? = null,
        /** [recover] runs (Restore One UI's settings), not a collection. */
        val recovering: Boolean = false,
        /** The last [recover] did not restore (its reason is [message]); Last session says so in the restore card. */
        val restoreFailed: Boolean = false,
    ) {
        val busy: Boolean get() = phase == Phase.RUNNING
    }

    private val collect = ReadOnlyRun(ReadOnlyRun.COLLECT_LIST, "log-lists")

    fun logsDir(ctx: Context) = FindingsActivity.logsDir(ctx)

    fun latestZip(ctx: Context): File? =
        logsDir(ctx).listFiles { f -> f.isFile && f.name.startsWith("oneos-logs-") && f.name.endsWith(".zip") }?.maxByOrNull { it.lastModified() }

    /** [auto]: Readiness started it after a return (no dialog: read-only, redacted, kept on the phone until shared). */
    fun start(ctx: Context, auto: Boolean = false) {
        if (state.busy || StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy) return
        val app = ctx.applicationContext
        update(State(Phase.RUNNING, "Checking root…", auto = auto, sessionId = SessionPrefs.lastLaunch(app)?.sessionId))
        executor.execute {
            runCatching { run(app) }.exceptionOrNull()?.let { e ->
                update(state.copy(phase = Phase.FAILED, detail = null, message = e.message ?: e.javaClass.simpleName))
            }
        }
    }

    fun recover(ctx: Context) {
        if (state.busy) return
        val app = ctx.applicationContext
        update(state.copy(phase = Phase.RUNNING, detail = "Restoring One UI's settings…", recovering = true, restoreFailed = false))
        executor.execute {
            val r = runCatching {
                val su = SuProbe.runId()
                check(su.state == SuState.GRANTED) { ProbeSession.suText(app, su) }
                RootVerbs.run(app, RootScript.Verb.RECOVER, emptyList(), silenceMs = 5 * 60_000L)
            }
            val reply = r.getOrNull()
            val status = runCatching { StageCheck.readStatus(app) }.getOrNull()
            status?.let(::refreshCheck)
            update(
                state.copy(
                    phase = if (reply?.ok == true) Phase.DONE else Phase.FAILED,
                    detail = null,
                    recovering = false,
                    restoreFailed = reply?.ok != true,
                    status = status ?: state.status,
                    recovered = reply?.reply?.ok,
                    message = when {
                        reply == null -> r.exceptionOrNull()?.message
                        reply.ok -> "One UI's settings: ${reply.reply.ok?.removePrefix("recover ")}"
                        else -> "Could not restore: ${reply.problem}"
                    },
                ),
            )
        }
    }

    /** The stage read again after a restore or a collection: Home and Switch go by it (the rest of the last check stays). */
    private fun refreshCheck(status: StageStatus) {
        StageCheck.state.result?.let { StageCheck.publish(it.copy(status = status)) }
    }

    private fun run(app: Context) {
        val su = SuProbe.runId()
        check(su.state == SuState.GRANTED) { ProbeSession.suText(app, su) }
        val launch = SessionPrefs.lastLaunch(app)
        val sid = launch?.sessionId ?: "unknown"
        val root = logsDir(app).apply { mkdirs() }
        val name = LogBundle.name(sid)
        // (0.4.42) Only the newest bundle is kept: every earlier one (its zip and its unpacked
        // folder, 200-300 MB each on the owner's Fold) goes before collecting. The newest keeps its
        // folder: Send and the log preview read report.json and the checklist from it.
        root.listFiles { f -> f.name.startsWith("oneos-logs-") && f.name != name && f.name != "$name.zip" }
            ?.forEach { it.deleteRecursively() }
        val folder = File(root, name).apply {
            deleteRecursively()
            mkdirs()
        }
        File(root, "$name.zip").delete()
        val redactor = Redactor.forBundle()
        val stats = LogStats()
        val salt = RedactingOutputStream.newFileSalt()
        val base = folder.canonicalPath + File.separator
        var learned = 0
        val sink: (String) -> OutputStream = { path ->
            when {
                // The names to remove: learned when the entry ends, before any log
                // is read, and never written anywhere.
                path.startsWith("memory/") -> object : ByteArrayOutputStream() {
                    override fun close() {
                        val t = toString(Charsets.UTF_8.name())
                        reset()
                        when (path) {
                            "memory/ssids.txt" -> learned = LogBundle.learn(redactor, t, null)
                            "memory/input_devices.txt" -> LogBundle.learn(redactor, null, t)
                        }
                    }
                }
                // Never kept, whatever a list prints (recordings, screenshots).
                LogRules.neverCollected(path) -> object : OutputStream() {
                    override fun write(b: Int) = Unit

                    override fun write(b: ByteArray, off: Int, len: Int) = Unit
                }
                else -> {
                    val f = File(folder, path)
                    check(f.canonicalPath.startsWith(base)) { "output outside the folder: $path" }
                    f.parentFile?.mkdirs()
                    RedactingOutputStream(f.outputStream().buffered(1 shl 16), path, redactor, stats, salt)
                }
            }
        }
        val b = collect.bundled(app)
        var done = 0
        val out = collect.run(
            app, sink,
            onStarted = { id -> update(state.copy(detail = "Collecting ${done + 1} of ${b.commands.size}: $id (personal data is removed as it arrives)")) },
            onFinished = { done++ },
        )
        fun text(prefix: String, suffix: String): String? = folder.walkTopDown()
            .firstOrNull { it.isFile && it.relativeTo(folder).invariantSeparatorsPath.let { p -> p.startsWith(prefix) && p.endsWith(suffix) } }
            ?.readText()
        val bootReason = text("boot/", "reason.txt")?.lineSequence()?.firstOrNull { it.startsWith("sys.boot.reason=") }?.removePrefix("sys.boot.reason=")
        val outcome = ReturnOutcomes.parse(
            text("stage/", "_auto_return.log"),
            text("stage/", "_takeover_app.log"),
            bootReason,
        )
        val incomplete = out.stream.results.filter { it.status != ProbeStatus.OK && it.status != ProbeStatus.NOT_PRESENT }.map { "${it.id} ${it.status.label}" }
        val zip = LogBundle.build(
            LogBundleInput(
                app = ProbeSession.appInfo(app),
                sessionId = sid,
                generatedAt = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX")),
                profileId = launch?.profileId,
                imageId = launch?.imageId,
                tableSha256 = text("stage/", "current.json")?.let { Regex("\"table\": \"([0-9a-f]{64})\"").find(it)?.groupValues?.get(1) },
                dryRun = launch?.dryRun == true,
                outcome = outcome,
                listSha256 = b.listSha256,
                runnerSha256 = b.runnerSha256,
                incomplete = incomplete + listOfNotNull(if (out.stopped) "the collection stopped early" else null),
                learnedNames = learned,
            ),
            folder, redactor, stats,
        )
        if (launch != null) SessionPrefs.setLogsCollected(app, launch.sessionId, outcome.kind.name, outcome.afterSeconds)
        update(state.copy(detail = "Reading the stage…"))
        val status = runCatching { StageCheck.readStatus(app) }.getOrNull()
        status?.let(::refreshCheck)
        update(
            State(
                Phase.DONE, outcome = outcome, zip = zip, status = status, auto = state.auto, sessionId = sid,
                message = "${redactor.log.total} personal values removed, ${stats.droppedLines} log lines of personal tags dropped.",
            ),
        )
    }
}
