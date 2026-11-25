package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.OneiosConf
import com.fahadali.oneos.core.root.OneiosRoot
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.core.root.RootReply
import com.fahadali.oneos.core.root.RootShell

/**
 * xnuhost's switches on this phone (docs/oneios.md, "UI (2026-11-25)"): root's `conf` verb, which runs the staged
 * runtime's oneios-tool on root's copy of the staged image's overlay/userland/xnuhost.conf and puts a changed file
 * in with the image's lists ([OneiosConf]). Reads (the catalog and the file, a check) run beside anything; a write
 * waits for no other iOS job ([canWrite]: never while a download, an import, a switch or an oneios-tool flow runs),
 * and OneiosJob waits for a write the same way. Every answer reads the file again, so the screens show what root has.
 */
object OneiosConfJob : BackgroundJob<OneiosConfJob.State>(State(), "oneos-oneios-conf") {
    data class State(
        val loading: Boolean = false,
        val writing: Boolean = false,
        /** The staged tool reads the file (`@@RESULT conf tool`); false: a runtime older than `conf`, the plain file. */
        val tool: Boolean = false,
        val loaded: Boolean = false,
        val catalog: OneiosConf.Catalog? = null,
        /** The runtime has no catalog (older than v0.1.31, or its tool has no `switches`). */
        val noCatalog: Boolean = false,
        val show: OneiosConf.Show? = null,
        /** Why the last call did not work, in root's or the app's words; null when it did. */
        val problem: String? = null,
        /** The tool's answer to the last check or write (its errors at their lines). */
        val answer: OneiosConf.Answer? = null,
        /** The last operation (load, set, write, ...) and whether it went in. */
        val lastOp: String? = null,
        val lastOk: Boolean = false,
        /** Counts writes that went in, so a screen can say Saved once. */
        val saves: Int = 0,
    ) {
        val busy: Boolean get() = loading || writing
        val groups: List<OneiosConf.Group>
            get() = catalog?.let { c -> show?.let { OneiosConf.groups(c, it) } }.orEmpty()
    }

    @Volatile private var shell: RootShell? = null

    /** Nothing else of the iOS system runs that a write could race (OneiosJob's copy, switch, kernel; a tool flow). */
    fun canWrite(): Boolean = !state.busy && !OneiosJob.state.busy && !OneiosToolJob.state.busy

    fun load(ctx: Context) = run(ctx, "load", "", write = false)

    /** Changes from the Switches screen: the sets in one call, the unsets in another. */
    fun change(ctx: Context, changes: List<OneiosConf.Change>) {
        val puts = changes.filterIsInstance<OneiosConf.Change.Put>()
        val unsets = changes.filterIsInstance<OneiosConf.Change.Unset>()
        if (puts.isEmpty() && unsets.isEmpty()) return
        if (!canWrite()) return
        val app = ctx.applicationContext
        update(state.copy(writing = true, problem = null, answer = null))
        executor.execute {
            var ok = true
            if (puts.isNotEmpty()) ok = call(app, "set", OneiosConf.stdin(puts))
            if (ok && unsets.isNotEmpty()) call(app, "unset", OneiosConf.stdin(unsets))
            update(state.copy(writing = false))
        }
    }

    fun write(ctx: Context, text: String, force: Boolean) = run(ctx, if (force) "write-force" else "write", text, write = true)

    fun check(ctx: Context, text: String) = run(ctx, "check", text, write = false)

    fun restore(ctx: Context) = run(ctx, "restore", "", write = true)

    fun cancel() {
        shell?.cancel()
    }

    private fun run(ctx: Context, op: String, stdin: String, write: Boolean) {
        if (state.busy || (write && !canWrite())) return
        val app = ctx.applicationContext
        update(if (write) state.copy(writing = true, problem = null, answer = null) else state.copy(loading = true, problem = null, answer = if (op == "check") null else state.answer))
        executor.execute {
            call(app, op, stdin)
            update(state.copy(loading = false, writing = false))
        }
    }

    /** One `conf <op>` as root; the state takes what came back. True when root answered OK. */
    private fun call(app: Context, op: String, stdin: String): Boolean {
        val bytes = stdin.toByteArray(Charsets.UTF_8)
        if (bytes.size > OneiosConf.MAX_TEXT_BYTES) {
            update(state.copy(problem = "The text is over ${OneiosConf.MAX_TEXT_BYTES / 1024} KiB.", lastOp = op, lastOk = false))
            return false
        }
        val first = try {
            root(app, op, bytes)
        } catch (e: Exception) {
            update(state.copy(problem = e.message ?: e.javaClass.simpleName, lastOp = op, lastOk = false))
            return false
        }
        // A stage holding another build's root script: one status puts this build's there (as the session logs do).
        val a = if (!first.ok && first.reply.refused?.contains("not in the stage") == true) {
            val st = root(app, OneiosRoot.Verb.STATUS, emptyList(), ByteArray(0), 180_000)
            if (st.ok && OneiosStatus.parse(st.reply.results).staged) root(app, op, bytes) else first
        } else first
        val r = OneiosConf.Reply.parse(a.lines)
        val show = r.show
        update(
            state.copy(
                loaded = state.loaded || show != null,
                tool = if (show != null) r.tool else state.tool,
                catalog = if (op == "load") r.catalog else state.catalog,
                noCatalog = if (op == "load") r.noCatalog || r.catalog == null else state.noCatalog,
                show = show ?: state.show,
                answer = r.answer ?: if (op == "load" || op == "show") state.answer else null,
                problem = if (a.ok) null else a.problem,
                lastOp = op,
                lastOk = a.ok,
                saves = state.saves + if (a.ok && op != "load" && op != "show" && op != "check") 1 else 0,
            ),
        )
        return a.ok
    }

    private class Answer(val reply: RootReply, val lines: List<String>, val end: RootShell.End) {
        val ok: Boolean get() = end.exitCode == 0 && reply.ok != null && end.error == null
        val problem: String get() = end.error ?: reply.problem(end.exitCode) ?: "no answer from root"
    }

    private fun root(app: Context, op: String, stdin: ByteArray): Answer = root(app, OneiosRoot.Verb.CONF, listOf(op), stdin, LIMIT_MS)

    private fun root(app: Context, verb: OneiosRoot.Verb, args: List<String>, stdin: ByteArray, limitMs: Long): Answer {
        val command = OneiosRoot.launcher(verb, args, BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES)
        val input = when (verb.stdin) {
            OneiosRoot.Stdin.SCRIPT -> OneiosJob.rootScript(app).let { s -> RootShell.Feed { it.write(s) } }
            OneiosRoot.Stdin.DATA -> RootShell.Feed { it.write(stdin) }
            OneiosRoot.Stdin.NONE -> null
        }
        val sh = RootShell(command)
        shell = sh
        val reply = RootReply()
        val lines = ArrayList<String>()
        val end = try {
            sh.run(input, { line ->
                reply.accept(line)
                if (lines.size < MAX_LINES) lines += if (line.length > MAX_LINE) line.substring(0, MAX_LINE) else line
            }, { limitMs }, limitMs)
        } finally {
            shell = null
        }
        return Answer(reply, lines, end)
    }

    private const val LIMIT_MS = 60_000L
    private const val MAX_LINES = 20_000
    private const val MAX_LINE = 262_144
}
