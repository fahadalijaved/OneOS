package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosCheck
import com.fahadali.oneos.core.model.OneiosCheckOutcome
import com.fahadali.oneos.core.model.OneiosCheckResult
import com.fahadali.oneos.core.model.OneiosChecks
import com.fahadali.oneos.core.root.OneiosRoot
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.core.root.RootReply
import com.fahadali.oneos.core.root.RootShell
import java.io.File

/**
 * The hardware checks of the iOS 27 (OneiOS) system (docs/oneios.md, "Hardware
 * checks"): each is one `check <id>` of `oneios_root.sh`, which runs a tool of
 * the staged runtime beside One UI under a time limit of root's own. Nothing
 * here starts a session.
 *
 * The app keeps a limit of its own a little past root's. When that ends the
 * root command, or the owner stops it, `uncheck <id>` runs the put-back step
 * again (the tool and its helpers ended, the backlight and the light sensor as
 * they were).
 */
object OneiosChecksJob : BackgroundJob<OneiosChecksJob.State>(State(), "oneos-oneios-checks") {
    data class Row(
        val result: OneiosCheckResult? = null,
        val output: List<String> = emptyList(),
        /** The picture a camera check wrote, copied into the app's cache. */
        val picture: File? = null,
    )

    data class State(
        /** Reading what is staged. */
        val checking: Boolean = false,
        /** The check that runs now. */
        val running: String? = null,
        /** The checks still to run after it. */
        val queued: List<String> = emptyList(),
        val rows: Map<String, Row> = emptyMap(),
        /** What root last reported; null until the first read. */
        val status: OneiosStatus? = null,
        /** Why nothing could be read or run (no root, an open session). */
        val problem: String? = null,
        /** The running check's latest output line as root passes it on (once a second), and how many came so far. */
        val liveLine: String? = null,
        val liveLines: Int = 0,
        /** When the running check started ([android.os.SystemClock.elapsedRealtime]); 0 when none runs. */
        val startedAt: Long = 0,
    ) {
        val busy: Boolean get() = checking || running != null
    }

    @Volatile private var cancelled = false

    @Volatile private var shell: RootShell? = null

    private class Answer(val reply: RootReply, val lines: List<String>, val end: RootShell.End) {
        val ok: Boolean get() = end.exitCode == 0 && reply.ok != null && end.error == null
    }

    private fun root(app: Context, verb: OneiosRoot.Verb, args: List<String>, limitMs: Long, onLine: ((String, Int) -> Unit)? = null): Answer {
        val command = OneiosRoot.launcher(verb, args, BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES)
        val input = if (verb.stdin == OneiosRoot.Stdin.SCRIPT) {
            val script = OneiosJob.rootScript(app)
            RootShell.Feed { it.write(script) }
        } else null
        val sh = RootShell(command)
        shell = sh
        val reply = RootReply()
        val lines = ArrayList<String>()
        val end = try {
            sh.run(input, { line ->
                reply.accept(line)
                if (!line.startsWith("@@") && lines.size < MAX_LINES) {
                    lines += line.take(MAX_LINE)
                    if (line.startsWith("| ")) onLine?.invoke(line, lines.size)
                }
            }, { limitMs }, limitMs)
        } finally {
            shell = null
        }
        return Answer(reply, lines, end)
    }

    fun canStart(): Boolean = !state.busy && OneiosJob.canStart() && !OneiosToolJob.state.busy

    /** Stops the running check (its put-back step still runs) and leaves the rest. */
    fun cancel() {
        cancelled = true
        shell?.cancel()
    }

    /** Read only: which runtime is staged, whether a session is open. */
    fun refresh(ctx: Context) {
        if (!canStart()) return
        val app = ctx.applicationContext
        update(state.copy(checking = true, problem = null))
        executor.execute {
            val (status, problem) = readStatus(app)
            update(state.copy(checking = false, status = status ?: state.status, problem = problem))
        }
    }

    private fun readStatus(app: Context): Pair<OneiosStatus?, String?> = try {
        val a = root(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000)
        if (a.ok) OneiosStatus.parse(a.reply.results) to null
        else null to (a.end.error ?: a.reply.problem(a.end.exitCode) ?: "no answer from root")
    } catch (e: Exception) {
        null to (e.message ?: e.javaClass.simpleName)
    }

    /**
     * Runs [ids] in order. [skip] names the ones whose condition is not met
     * (Bluetooth on, adaptive brightness on) with the reason: they are marked
     * skipped and not run.
     */
    fun run(ctx: Context, ids: List<String>, skip: Map<String, String> = emptyMap()) {
        val checks = ids.mapNotNull(OneiosChecks::byId)
        if (checks.isEmpty() || !canStart()) return
        val app = ctx.applicationContext
        cancelled = false
        update(state.copy(running = checks.first().id, queued = checks.drop(1).map { it.id }, problem = null,
            rows = state.rows - checks.map { it.id }.toSet()))
        executor.execute {
            // The staged script is this build's after a status (which may install it), and the runtime is known.
            val (status, problem) = readStatus(app)
            if (status == null || status.runtime == null || status.sessionOpen) {
                val why = problem ?: if (status?.sessionOpen == true) "An iOS session is open: the checks only run beside One UI." else "No OneiOS runtime is staged."
                update(state.copy(running = null, queued = emptyList(), status = status ?: state.status, problem = why))
                return@execute
            }
            update(state.copy(status = status))
            for ((i, check) in checks.withIndex()) {
                val rest = checks.drop(i + 1).map { it.id }
                update(state.copy(running = check.id, queued = rest, liveLine = null, liveLines = 0, startedAt = android.os.SystemClock.elapsedRealtime()))
                val row = when {
                    cancelled -> Row(OneiosChecks.skipped("Not run: stopped"))
                    skip[check.id] != null -> Row(OneiosChecks.skipped(skip.getValue(check.id)))
                    else -> one(app, check)
                }
                update(state.copy(rows = state.rows + (check.id to row)))
            }
            update(state.copy(running = null, queued = emptyList(), liveLine = null, liveLines = 0, startedAt = 0))
        }
    }

    private fun one(app: Context, check: OneiosCheck): Row {
        // Root ends the tool at the check's limit, then 2 s to SIGKILL and its put-back step; this is the backstop.
        val limitMs = (check.limitSeconds + 20) * 1000L
        val a = try {
            // The tool's lines as root passes them on: the screen shows the latest, at most twice a second.
            var shown = 0L
            root(app, OneiosRoot.Verb.CHECK, listOf(check.id), limitMs) { line, n ->
                val now = android.os.SystemClock.elapsedRealtime()
                if (now - shown >= 500) {
                    shown = now
                    update(state.copy(liveLine = line.removePrefix("| ").trim().take(200).ifEmpty { null } ?: state.liveLine, liveLines = n))
                }
            }
        } catch (e: Exception) {
            return Row(OneiosCheckResult(OneiosCheckOutcome.FAIL, e.message ?: e.javaClass.simpleName))
        }
        val run = if (a.ok) OneiosChecks.parseRun(check.id, a.reply.results, a.lines) else null
        val output = run?.output ?: a.lines.map { it.removePrefix("| ") }
        if (run == null) {
            // Root's command ended without a result: stopped here, killed by the backstop, or refused.
            val refused = a.reply.refused
            if (refused == null) putBack(app, check)
            val result = when {
                refused != null -> OneiosChecks.skipped(refused)
                a.end.cancelled || cancelled -> OneiosChecks.skipped("Stopped by you; what the tool changed was put back")
                a.end.killed -> OneiosCheckResult(OneiosCheckOutcome.FAIL, "Root did not answer within ${limitMs / 1000} s; the tool was ended and what it changed was put back")
                else -> OneiosCheckResult(OneiosCheckOutcome.FAIL, a.end.error ?: a.reply.problem(a.end.exitCode) ?: "no answer from root")
            }
            return Row(result, output)
        }
        val result = OneiosChecks.classify(check, run)
        val picture = if (check.picture && result.outcome == OneiosCheckOutcome.PASS) runCatching { picture(app, check) }.getOrNull() else null
        return Row(result, output + a.reply.infos, picture)
    }

    private fun putBack(app: Context, check: OneiosCheck) {
        runCatching {
            // Not this run's shell: a stop must not end the put-back step too.
            val was = cancelled
            cancelled = false
            root(app, OneiosRoot.Verb.UNCHECK, listOf(check.id), 30_000)
            cancelled = was
        }
    }

    /** The PNG of a camera check: base64 from root, checked by size, SHA-256 and its first bytes. */
    private fun picture(app: Context, check: OneiosCheck): File? {
        val a = root(app, OneiosRoot.Verb.CHECKFILE, listOf(check.id), 60_000)
        if (!a.ok) return null
        val w = a.reply.results.firstOrNull { it.startsWith("file ${check.id} ") }?.split(' ') ?: return null
        val text = a.lines.filter { it.startsWith("| ") }.joinToString("") { it.removePrefix("| ").trim() }
        val bytes = android.util.Base64.decode(text, android.util.Base64.DEFAULT)
        if (bytes.size.toString() != w.getOrNull(2) || Hashes.sha256(bytes) != w.getOrNull(3)) return null
        val png = byteArrayOf(0x89.toByte(), 'P'.code.toByte(), 'N'.code.toByte(), 'G'.code.toByte())
        if (bytes.size < 8 || !bytes.copyOfRange(0, 4).contentEquals(png)) return null
        val dir = File(app.cacheDir, "oneios-checks").apply { mkdirs() }
        return File(dir, "${check.id}.png").also { it.writeBytes(bytes) }
    }

    /** Every check's log in one text. */
    fun report(header: List<String>): String {
        val s = state
        return OneiosChecks.report(header, OneiosChecks.ALL.map { c -> Triple(c, s.rows[c.id]?.result, s.rows[c.id]?.output.orEmpty()) })
    }

    // A picture in base64 is the longest answer: 8 MiB in 76-character lines.
    private const val MAX_LINES = 160_000
    private const val MAX_LINE = 2000
}
