package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosTool
import java.io.Closeable
import java.io.IOException
import java.io.OutputStream
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
import kotlin.concurrent.thread

/**
 * One `oneios-tool serve` for one flow of the app (docs/oneios.md, "oneios-tool in the app"): one `su -c
 * "<launcher of oneios_root.sh tool work|read>"`, whose stdin takes the app's requests and whose stdout gives the
 * tool's lines ([OneiosTool]). The app does none of the work: it writes requests, hands every line to the
 * request's listener, and ends the process.
 *
 * Threads: [start] and [call] block, so they run on a worker thread of the app (the foreground service's job),
 * never on the main thread. A reader thread reads stdout, a second one keeps the last lines of stderr, and a
 * watchdog ends a session whose tool went silent while a request is open.
 *
 * Ending: [close] closes stdin (the tool ends at the end of its input and ends what it started), waits
 * [closeWaitMs], then destroys the process and runs [backstop] (the app's `untool`, a root command of its own:
 * with KernelSU the tool is root's and the app's signal cannot reach it). [cancel] sends the tool a cancel request
 * for one request; the session stays open for the next one.
 */
class OneiosToolSession(
    private val command: String,
    /** What runs [command]: `su -c` on the phone; a plain shell in the tests. */
    private val launch: List<String> = listOf("su", "-c"),
    private val environment: Map<String, String> = emptyMap(),
    /** Ends what is left of the tool as root (`untool`); runs at most once, only when the tool did not end by itself. */
    private val backstop: (() -> Unit)? = null,
    /** A request with no line from the tool for this long ends the session (the tool sends progress while it works). */
    private val silenceMs: Long = 120_000,
    private val helloMs: Long = 60_000,
    private val closeWaitMs: Long = 10_000,
) : Closeable {
    /** How [start] ended: the tool's hello, or why there is none. */
    sealed class Start {
        data class Ready(val hello: OneiosTool.Event.Hello) : Start()

        /** The root script refused (`@@REFUSED ...`), or the tool spoke another protocol. */
        data class Refused(val reason: String) : Start()

        data class Failed(val reason: String) : Start()
    }

    private class Pending(val listener: (OneiosTool.Event) -> Unit) {
        val done = CountDownLatch(1)

        @Volatile var last: OneiosTool.Event? = null
    }

    @Volatile private var process: Process? = null

    @Volatile private var stdin: OutputStream? = null

    @Volatile var hello: OneiosTool.Event.Hello? = null
        private set

    /** Why the session ended, once it has (the tool's bye, its exit, a broken pipe, the watchdog). */
    @Volatile var ended: String? = null
        private set

    /** The tool said the work waits for heat or the battery (`heat` `paused`), until its `resumed`. */
    @Volatile private var paused = false

    private val ids = AtomicInteger(0)
    private val pending = ConcurrentHashMap<String, Pending>()
    private val activity = AtomicLong(System.currentTimeMillis())
    private val stderr = StringBuilder()
    private val rootReply = RootReply()
    private val helloSeen = CountDownLatch(1)
    private val closed = java.util.concurrent.atomic.AtomicBoolean(false)
    private var reader: Thread? = null
    private var errReader: Thread? = null
    private var watchdog: Thread? = null

    /** The last lines of the tool's stderr, for a failure's details. */
    val errors: String get() = synchronized(stderr) { stderr.toString() }

    /** Starts the tool and waits for its hello. Call once, off the main thread. */
    fun start(): Start {
        check(process == null && !closed.get()) { "start once" }
        val proc = try {
            ProcessBuilder(launch + command).apply { environment().putAll(environment) }.start()
        } catch (e: IOException) {
            ended = "su could not be started: ${e.message}"
            return Start.Failed(ended!!)
        }
        process = proc
        stdin = proc.outputStream
        errReader = thread(name = "oneios-tool-stderr", isDaemon = true) {
            runCatching {
                proc.errorStream.bufferedReader().useLines { lines ->
                    lines.forEach { l ->
                        synchronized(stderr) {
                            if (stderr.length > 8192) stderr.delete(0, 4096)
                            stderr.append(l.take(500)).append('\n')
                        }
                    }
                }
            }
        }
        reader = thread(name = "oneios-tool-stdout", isDaemon = true) { read(proc) }
        watchdog = thread(name = "oneios-tool-watchdog", isDaemon = true) {
            while (proc.isAlive && !closed.get()) {
                if (pending.isNotEmpty() && !paused && System.currentTimeMillis() - activity.get() > silenceMs) {
                    lose("the tool sent nothing for ${silenceMs / 1000} s")
                    break
                }
                try {
                    Thread.sleep(500)
                } catch (_: InterruptedException) {
                    break
                }
            }
        }
        if (!helloSeen.await(helloMs, TimeUnit.MILLISECONDS)) {
            close()
            return Start.Failed("the tool did not start within ${helloMs / 1000} s")
        }
        val h = hello
        if (h == null) {
            val refused = rootReply.refused
            val why = refused ?: rootReply.failed?.let { "failed: $it" } ?: ended ?: "the tool ended before it said hello"
            close()
            return if (refused != null) Start.Refused(refused) else Start.Failed(why)
        }
        if (h.protocol != OneiosTool.PROTOCOL) {
            close()
            return Start.Refused("this runtime's oneios-tool speaks protocol ${h.protocol}; this app speaks ${OneiosTool.PROTOCOL}: get the runtime that matches")
        }
        return Start.Ready(h)
    }

    private fun read(proc: Process) {
        try {
            proc.inputStream.bufferedReader(Charsets.UTF_8).useLines { lines ->
                for (l in lines) {
                    activity.set(System.currentTimeMillis())
                    val e = OneiosTool.parse(l)
                    if (e == null) {
                        // The root script's own lines before it starts the tool: @@OK tool, or its refusal.
                        if (hello == null) rootReply.accept(l)
                        continue
                    }
                    when (e) {
                        is OneiosTool.Event.Hello -> { hello = e; helloSeen.countDown() }
                        is OneiosTool.Event.Bye -> ended = "the tool ended: ${e.why ?: "no reason"}"
                        // A heat pause may be quiet for minutes: the silence limit waits for the resume.
                        is OneiosTool.Event.Heat -> { paused = e.state == "paused"; deliver(e) }
                        else -> deliver(e)
                    }
                }
            }
        } catch (_: IOException) {
            // The process ended or was ended: the stream simply stops.
        }
        lose(ended ?: exitWords(proc))
    }

    /** An event of a request to its listener; its last event ends the request's [call]. */
    private fun deliver(e: OneiosTool.Event) {
        val id = e.id ?: return
        val p = pending[id] ?: return
        runCatching { p.listener(e) }
        if (e.ends) {
            p.last = e
            pending.remove(id)
            p.done.countDown()
        }
    }

    private fun exitWords(proc: Process): String {
        if (proc.waitFor(2, TimeUnit.SECONDS)) {
            val err = errors.lines().lastOrNull { it.isNotBlank() }
            return "the tool ended (exit ${proc.exitValue()})" + (err?.let { ": $it" } ?: "")
        }
        return "the tool closed its output"
    }

    /** Every open request ends as lost, with [why]; the session is over. */
    private fun lose(why: String) {
        if (ended == null) ended = why
        helloSeen.countDown()
        for ((id, p) in pending) {
            pending.remove(id)
            p.done.countDown()
        }
    }

    /** Writes one line to the tool; false when the pipe is gone. */
    private fun write(line: String): Boolean = synchronized(this) {
        val out = stdin ?: return false
        try {
            out.write(line.toByteArray(Charsets.UTF_8))
            out.flush()
            true
        } catch (_: IOException) {
            false
        }
    }

    /** Sends a request; [listener] hears each of its lines on the reader thread. Returns its id, or null when the session is over. */
    fun send(cmd: String, keys: Map<String, Any?> = emptyMap(), listener: (OneiosTool.Event) -> Unit): String? = post(cmd, keys, listener)?.first

    private fun post(cmd: String, keys: Map<String, Any?>, listener: (OneiosTool.Event) -> Unit): Pair<String, Pending>? {
        if (hello == null || ended != null || closed.get()) return null
        val id = ids.incrementAndGet().toString()
        val p = Pending(listener)
        pending[id] = p
        activity.set(System.currentTimeMillis())
        if (!write(OneiosTool.request(id, cmd, keys))) {
            pending.remove(id)
            lose("the tool's input closed")
            return null
        }
        return id to p
    }

    /**
     * Sends a request and waits until it ends. Returns its last line (result, refused, failed, cancelled), or null
     * when the session ended first ([ended] says why). [onId] hears the request's id first (for a cancel).
     */
    fun call(cmd: String, keys: Map<String, Any?> = emptyMap(), onId: (String) -> Unit = {}, listener: (OneiosTool.Event) -> Unit = {}): OneiosTool.Event? {
        val (id, p) = post(cmd, keys, listener) ?: return null
        onId(id)
        p.done.await()
        return p.last
    }

    /** Asks the tool to stop request [id]; its own `cancelled` line ends it. False when the session is over. */
    fun cancel(id: String): Boolean {
        if (hello == null || ended != null) return false
        return write(OneiosTool.cancel(id))
    }

    /** Asks the tool to stop every open request. */
    fun cancelAll() {
        pending.keys.toList().forEach { cancel(it) }
    }

    /** The open requests' ids. */
    val open: Set<String> get() = pending.keys.toSet()

    /** The process [start] started (the tests look at it and what is below it). */
    internal val processForTests: Process? get() = process

    /** The tool's process is still there. */
    val alive: Boolean get() = process?.isAlive == true

    /**
     * Ends the session: stdin closed (the tool's end of input), up to [closeWaitMs] for it to end, then [backstop]
     * (root's `untool`) and last the process destroyed. The backstop runs first: it finds what the tool started by
     * the tool's own process, which must still be there (a killed parent leaves its children to init, where no
     * parent links them to the tool any more). Safe to call more than once and from any thread but the main one.
     */
    override fun close() {
        if (!closed.compareAndSet(false, true)) return
        val proc = process
        synchronized(this) {
            runCatching { stdin?.close() }
            stdin = null
        }
        if (proc == null) return
        if (!proc.waitFor(closeWaitMs, TimeUnit.MILLISECONDS)) {
            // The tool may be root's and out of the app's reach (KernelSU): root ends it and what it started.
            runCatching { backstop?.invoke() }
            if (!proc.waitFor(3, TimeUnit.SECONDS)) {
                proc.destroy()
                if (!proc.waitFor(2, TimeUnit.SECONDS)) proc.destroyForcibly()
                proc.waitFor(5, TimeUnit.SECONDS)
            }
        }
        reader?.join(5000)
        watchdog?.interrupt()
        errReader?.join(1000)
        lose(ended ?: "closed")
        process = null
    }
}
