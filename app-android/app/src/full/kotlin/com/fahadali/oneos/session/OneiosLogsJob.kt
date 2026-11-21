package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.OneiosLogFile
import com.fahadali.oneos.core.model.OneiosLogs
import com.fahadali.oneos.core.root.OneiosRoot
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.core.root.RootReply
import com.fahadali.oneos.core.root.RootShell
import java.io.File
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * The session logs of the iOS 27 (OneiOS) system (docs/oneios.md, "Session
 * logs"): what xnuhost, the switch, the return and the helpers left in the
 * stage, read as root with `oneios_root.sh logs` and `logfile`. Both verbs
 * only read; root writes nothing.
 *
 * A log is read from its end: the last 256 KiB first, then earlier chunks of
 * 1 MiB (each a root command with a time limit of its own) up to 4 MiB by
 * itself, and further on request. Share writes a log, or all of them as one
 * zip, under files/logs/oneios-session, which the app's file provider serves.
 * These files are the logs as they are: Collect logs is the redacted way.
 */
object OneiosLogsJob : BackgroundJob<OneiosLogsJob.State>(State(), "oneos-oneios-logs") {
    /** The log on screen. */
    data class Open(
        val id: String,
        val size: Long = 0,
        /** Byte offset of the first line read; 0 = the whole log is here; -1 = nothing read yet. */
        val start: Long = -1,
        val lines: List<String> = emptyList(),
        val loading: Boolean = false,
        val problem: String? = null,
        /** For an xnuhost log; of what has been read so far. */
        val summary: OneiosLogs.Summary? = null,
    ) {
        val complete: Boolean get() = start == 0L
    }

    /** A file made for Share, to be handed to the chooser once. */
    data class Shared(val file: File, val mime: String, val subject: String, val text: String)

    data class State(
        val listing: Boolean = false,
        /** What root listed; null until the first read. */
        val list: OneiosLogs.Listing? = null,
        /** No stage on this phone: OneiOS was never set up here. */
        val noStage: Boolean = false,
        val problem: String? = null,
        val open: Open? = null,
        /** What a Share is doing now. */
        val exporting: String? = null,
        val shared: Shared? = null,
        val shareProblem: String? = null,
    ) {
        val busy: Boolean get() = listing || exporting != null || open?.loading == true
    }

    @Volatile private var shell: RootShell? = null

    @Volatile private var stopExport = false

    private class Answer(val reply: RootReply, val lines: List<String>, val end: RootShell.End) {
        val ok: Boolean get() = end.exitCode == 0 && reply.ok != null && end.error == null
        val problem: String get() = end.error ?: reply.problem(end.exitCode) ?: "no answer from root"
    }

    private fun root(app: Context, verb: OneiosRoot.Verb, args: List<String>, limitMs: Long): Answer {
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
                if (!line.startsWith("@@") && lines.size < MAX_LINES) lines += if (line.length > MAX_LINE) line.substring(0, MAX_LINE) else line
            }, { limitMs }, limitMs)
        } finally {
            shell = null
        }
        return Answer(reply, lines, end)
    }

    /**
     * A log verb. The launcher runs only this build's root script; a stage that
     * holds an earlier build's (or none) answers "not in the stage", and one
     * `status` puts this build's there when a stage exists. Returns null with
     * [State.noStage] set when there is no stage at all.
     */
    private fun logVerb(app: Context, verb: OneiosRoot.Verb, args: List<String>): Answer? {
        val a = root(app, verb, args, READ_LIMIT_MS)
        if (a.ok || a.reply.refused?.contains("not in the stage") != true) return a
        val st = root(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000)
        if (!st.ok) return st
        if (!OneiosStatus.parse(st.reply.results).staged) return null
        return root(app, verb, args, READ_LIMIT_MS)
    }

    private fun chunk(app: Context, id: String, end: Long, bytes: Int): Pair<OneiosLogs.Chunk?, String?> = try {
        val a = logVerb(app, OneiosRoot.Verb.LOGFILE, listOf(id, end.toString(), bytes.toString()))
        when {
            a == null -> null to "OneiOS is not set up on this phone."
            !a.ok -> null to a.problem
            else -> OneiosLogs.parseChunk(id, a.reply.results, a.lines)?.let { it to null } ?: (null to "root's answer could not be read")
        }
    } catch (e: Exception) {
        null to (e.message ?: e.javaClass.simpleName)
    }

    /** Read only: which logs are in the stage, their sizes, times and last lines. */
    fun refresh(ctx: Context) {
        if (state.listing || state.exporting != null) return
        val app = ctx.applicationContext
        update(state.copy(listing = true, problem = null))
        executor.execute {
            try {
                val a = logVerb(app, OneiosRoot.Verb.LOGS, emptyList())
                update(
                    when {
                        a == null -> state.copy(listing = false, list = OneiosLogs.Listing(false, emptyList()), noStage = true)
                        a.ok -> state.copy(listing = false, list = OneiosLogs.parseList(a.reply.results, a.lines), noStage = false)
                        else -> state.copy(listing = false, problem = a.problem)
                    },
                )
            } catch (e: Exception) {
                update(state.copy(listing = false, problem = e.message ?: e.javaClass.simpleName))
            }
        }
    }

    /** Opens [id]: its end at once, then earlier chunks until 4 MiB are here or the log is whole. */
    fun open(ctx: Context, id: String) {
        if (!OneiosLogs.validId(id)) return
        val app = ctx.applicationContext
        update(state.copy(open = Open(id, loading = true)))
        executor.execute { load(app, id, first = true) }
    }

    /** Reads up to 4 MiB more of the open log, before what is here. */
    fun more(ctx: Context) {
        val o = state.open ?: return
        if (o.loading || o.complete || o.start < 0) return
        val app = ctx.applicationContext
        update(state.copy(open = o.copy(loading = true, problem = null)))
        executor.execute { load(app, o.id, first = false) }
    }

    /** The viewer was left: what was read is dropped. */
    fun close(id: String) {
        executor.execute { if (state.open?.id == id) update(state.copy(open = null)) }
    }

    private fun load(app: Context, id: String, first: Boolean) {
        fun mine(): Open? = state.open?.takeIf { it.id == id }
        var returned: OneiosLogs.ReturnNote? = mine()?.summary?.returned
        val file = state.list?.files?.firstOrNull { it.id == id }
        val session = id == OneiosLogs.SESSION || id.startsWith("xnuhost-")
        if (first && session && file != null) returned = returnNote(app, file)
        var read = 0L
        while (true) {
            val o = mine() ?: return
            if (o.complete || read >= AUTO_BYTES) break
            val (c, problem) = chunk(app, id, if (o.start < 0) 0 else o.start, if (o.start < 0) OneiosLogs.FIRST_CHUNK else OneiosLogs.CHUNK_MAX)
            val now = mine() ?: return
            if (c == null) {
                update(state.copy(open = now.copy(loading = false, problem = problem)))
                return
            }
            read += c.end - c.start
            val lines = if (now.lines.isEmpty()) c.lines else c.lines + now.lines
            // A chunk that brought nothing and is not the start would ask for the same bytes again.
            val start = if (c.end == c.start && !c.first) 0 else c.start
            update(
                state.copy(
                    open = now.copy(
                        size = c.size, start = start, lines = lines, problem = null,
                        summary = if (session) OneiosLogs.summarize(lines, complete = start == 0L, returned = returned) else null,
                    ),
                ),
            )
            if (lines.size >= MAX_SHOWN_LINES) break
        }
        mine()?.let { update(state.copy(open = it.copy(loading = false))) }
    }

    /** What return.log says of the return that ended [file]'s session; its end is enough (the last returns). */
    private fun returnNote(app: Context, file: OneiosLogFile): OneiosLogs.ReturnNote? {
        val list = state.list ?: return null
        if (list.files.none { it.id == "return" }) return null
        val (c, _) = chunk(app, "return", 0, OneiosLogs.FIRST_CHUNK)
        val notes = OneiosLogs.returns(c?.lines ?: return null)
        val at = Instant.ofEpochSecond(file.modified).atZone(ZoneId.systemDefault())
        return OneiosLogs.returnFor(
            notes, at.toLocalDate().toString(), at.toLocalTime().toSecondOfDay(),
            newest = file.id == OneiosLogs.SESSION && !list.sessionOpen,
        )
    }

    // --- Share --------------------------------------------------------------------------

    private fun shareDir(app: Context) = File(File(app.filesDir, "logs"), "oneios-session")

    /** The share was handed to the chooser (or dropped). */
    fun taken() {
        executor.execute { update(state.copy(shared = null, shareProblem = null)) }
    }

    /** Stops a Share that is still reading. */
    fun stopShare() {
        stopExport = true
        shell?.cancel()
    }

    /** One log as a file: the whole log, read again from root, as it is on the phone. */
    fun shareOne(ctx: Context, id: String, header: List<String>) {
        if (state.exporting != null || !OneiosLogs.validId(id)) return
        val app = ctx.applicationContext
        stopExport = false
        update(state.copy(exporting = "Reading ${OneiosLogs.fileName(id)}…", shared = null, shareProblem = null))
        executor.execute {
            val out = runCatching {
                val dir = shareDir(app).apply { deleteRecursively(); mkdirs() }
                val name = if (id == OneiosLogs.SESSION) "xnuhost-session.log" else OneiosLogs.fileName(id)
                val f = File(dir, name)
                val note = whole(app, id, f)
                val text = buildList {
                    addAll(header)
                    add("${OneiosLogs.path(id)}, ${f.length()} bytes" + (note?.let { " ($it)" } ?: ""))
                    if (id == OneiosLogs.SESSION || id.startsWith("xnuhost-")) {
                        add("")
                        addAll(OneiosLogs.summaryLines(summaryOf(app, id, f)))
                    }
                }.joinToString("\n")
                Shared(f, "text/plain", name, text)
            }
            update(state.copy(exporting = null, shared = out.getOrNull(), shareProblem = out.exceptionOrNull()?.let { it.message ?: it.javaClass.simpleName }))
        }
    }

    /** Every listed log in one zip, with a summary.txt that has each session's summary. */
    fun shareAll(ctx: Context, header: List<String>) {
        if (state.exporting != null) return
        val files = state.list?.files.orEmpty()
        if (files.isEmpty()) return
        val app = ctx.applicationContext
        stopExport = false
        update(state.copy(exporting = "Reading the logs…", shared = null, shareProblem = null))
        executor.execute {
            val out = runCatching {
                val dir = shareDir(app).apply { deleteRecursively(); mkdirs() }
                val work = File(dir, "work").apply { mkdirs() }
                val summary = StringBuilder()
                header.forEach { summary.append(it).append('\n') }
                val stamp = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss").format(java.time.LocalDateTime.now())
                val zip = File(dir, "oneios-session-logs-$stamp.zip")
                val time = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
                ZipOutputStream(zip.outputStream().buffered(1 shl 16)).use { z ->
                    for ((i, file) in files.withIndex()) {
                        update(state.copy(exporting = "Reading ${i + 1} of ${files.size}: ${OneiosLogs.path(file.id)}"))
                        val f = File(work, "log")
                        val note = whole(app, file.id, f)
                        summary.append("\n== ${OneiosLogs.path(file.id)}: ${f.length()} bytes, last written ")
                            .append(time.format(Instant.ofEpochSecond(file.modified).atZone(ZoneId.systemDefault())))
                        note?.let { summary.append(" (").append(it).append(')') }
                        summary.append('\n')
                        if (file.session) OneiosLogs.summaryLines(summaryOf(app, file.id, f)).forEach { summary.append(it).append('\n') }
                        z.putNextEntry(ZipEntry(OneiosLogs.path(file.id)))
                        f.inputStream().use { it.copyTo(z, 1 shl 16) }
                        z.closeEntry()
                        f.delete()
                    }
                    z.putNextEntry(ZipEntry("summary.txt"))
                    z.write(summary.toString().toByteArray())
                    z.closeEntry()
                }
                work.deleteRecursively()
                Shared(zip, "application/zip", zip.name, header.joinToString("\n"))
            }
            update(state.copy(exporting = null, shared = out.getOrNull(), shareProblem = out.exceptionOrNull()?.let { it.message ?: it.javaClass.simpleName }))
        }
    }

    private fun summaryOf(app: Context, id: String, f: File): OneiosLogs.Summary {
        val returned = state.list?.files?.firstOrNull { it.id == id }?.let { runCatching { returnNote(app, it) }.getOrNull() }
        return f.bufferedReader().useLines { OneiosLogs.summarize(it.asIterable(), complete = true, returned = returned) }
    }

    /**
     * Reads the whole of [id] into [out]: chunks from the end, each to a part
     * file, then put together in order. A log past 32 MiB keeps its last
     * 32 MiB; the return value then says so.
     */
    private fun whole(app: Context, id: String, out: File): String? {
        val parts = ArrayList<File>()
        var end = 0L
        var read = 0L
        var cut: String? = null
        try {
            while (true) {
                check(!stopExport) { "Stopped." }
                val (c, problem) = chunk(app, id, end, OneiosLogs.CHUNK_MAX)
                checkNotNull(c) { "${OneiosLogs.path(id)}: $problem" }
                val part = File(out.parentFile, "${out.name}.part${parts.size}")
                part.bufferedWriter().use { w -> c.lines.forEach { w.write(it); w.write("\n") } }
                parts += part
                read += c.end - c.start
                if (c.first || c.end == c.start) break
                if (read >= SHARE_BYTES) {
                    cut = "the last ${read shr 20} MiB of ${c.size shr 20} MiB"
                    break
                }
                end = c.start
            }
            out.outputStream().buffered(1 shl 16).use { o -> parts.asReversed().forEach { p -> p.inputStream().use { it.copyTo(o, 1 shl 16) } } }
        } finally {
            parts.forEach { it.delete() }
        }
        return cut
    }

    private const val READ_LIMIT_MS = 45_000L

    /** Read by itself when a log is opened, and by each Load earlier. */
    private const val AUTO_BYTES = 4L * 1024 * 1024

    /** The viewer holds this many lines at most; the whole log is in Share. */
    const val MAX_SHOWN_LINES = 250_000
    private const val SHARE_BYTES = 32L * 1024 * 1024

    // 1 MiB of short lines.
    private const val MAX_LINES = 600_000
    private const val MAX_LINE = 4000
}
