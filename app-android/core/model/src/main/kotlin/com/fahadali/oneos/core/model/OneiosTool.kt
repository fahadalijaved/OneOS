package com.fahadali.oneos.core.model

/**
 * The lines of `oneios-tool serve` (OneiOS's tools/oneios-tool/README.md, "serve: one process for the app (the
 * protocol)"; this fork's docs/oneios.md, "oneios-tool in the app"): one JSON object a line each way, protocol 1.
 * The app writes requests (`{"id":"7","cmd":"sums","dir":"..."}`, the command's keys at the top level) and
 * `{"cmd":"cancel","id":"7"}`; the tool writes events, each beginning `{"ev":`. This file only reads and writes
 * those lines; every check, hash and step decision is the tool's, and the screens show what it sent
 * ([OneiosToolFlow]). Keys the app does not use are kept in [Event.raw].
 */
object OneiosTool {
    const val PROTOCOL = 1

    /** The commands the app sends (the tool's README has their keys and results). */
    object Cmd {
        const val CANCEL = "cancel"
        const val PING = "ping"
        const val MAKE_IMAGE = "make-image"
        const val PRELINK = "prelink"
        const val TWEAKS = "tweaks"
        const val FETCH = "fetch"
        const val IM4P = "im4p"
        const val PAUSE = "pause"
        const val RESUME = "resume"
        const val SUMS = "sums"
        const val CPU = "cpu"
        const val LOG = "log"
        const val LOG_LIST = "log-list"
        const val IOSLOG_BOOTS = "ioslog-boots"
        const val IOSLOG_SHOW = "ioslog-show"
    }

    /**
     * The IPSW profile the staged runtime carries (OneiOS's `profiles/ios-27.0.1-iPhone18,2.toml`, packed as
     * `lib/profiles/` with the comma as a dash): the members' names, sizes and hashes the tool's `fetch` checks.
     * Relative to the stage.
     */
    const val IPSW_PROFILE = "runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml"

    /** The kernel update's work folder (stage-relative): the fetched IM4P, its decode, the build's `out`. */
    const val KERNEL_WORK = "make-kernel"

    /** The profile's kernelcache member: its role (`fetch`'s `only`) and its file name in `indir`. */
    const val KERNELCACHE_ROLE = "kernelcache"
    const val KERNELCACHE_MEMBER = "kernelcache.release.v54"

    /**
     * The kernel update's download (docs/oneios.md, "Kernel updates"): only Apple's kernelcache member of the
     * IPSW, from Apple's server by range requests (about 23 MB; the profile pins its size, CRC-32 and SHA-384,
     * and the tool refuses another file with `mismatch`), into `make-kernel/inputs`. `resume`: a pause, a lost
     * network or an ended app leaves the parts, and the next run goes on from them.
     */
    fun kernelcacheFetchRequest(stage: String): Pair<String, Map<String, Any?>> = Cmd.FETCH to mapOf(
        "profile" to "$stage/$IPSW_PROFILE",
        "indir" to "$stage/$KERNEL_WORK/inputs",
        "only" to listOf(KERNELCACHE_ROLE),
        "resume" to true,
    )

    /**
     * The fetched IM4P decoded by the tool's own decoder (`im4p`: `in`, `out`; its `ok` has `kind`, `bytes` and
     * `sha256`), into the work folder: root's `kbcache` moves it into `kb/` once its SHA-256 is the pin of the
     * app's `kb/kb.json`.
     */
    fun kernelcacheDecodeRequest(stage: String): Pair<String, Map<String, Any?>> = Cmd.IM4P to mapOf(
        "in" to "$stage/$KERNEL_WORK/inputs/$KERNELCACHE_MEMBER",
        "out" to "$stage/$KERNEL_WORK/kernelcache.macho",
    )

    /**
     * The `prelink` request that builds the phone's kernel (docs/oneios.md, "Kernel updates"): for the staged
     * runtime's kernel at [xnuPath] (its runtime.json's `kernel.path`), every path under [stage] (the tool
     * refuses anything outside it). No `reference` (the phone has none), no `keep_work`, no record commits.
     */
    fun prelinkRequest(xnuPath: String, stage: String): Pair<String, Map<String, Any?>> = Cmd.PRELINK to mapOf(
        "kernel" to "$stage/runtime/$xnuPath",
        "kernelcache" to "$stage/kb/kernelcache.macho",
        "profile" to "$stage/kb/profile.toml",
        "reviewed" to "$stage/kb/reviewed.json",
        "more_reviewed" to listOf("$stage/kb/lead.json", "$stage/kb/user.json"),
        "pairs" to "$stage/kb/pairs.json",
        "stubs" to "$stage/kb/stubs.json",
        "xnuprelink" to "$stage/kb/match",
        "out" to "$stage/make-kernel/out",
    )

    /** A step's mark, as the tool's README defines it from the `start` list and the `step` events. */
    enum class StepState { PENDING, NEXT, RUNNING, DONE, FAILED, REFUSED, CANCELLED }

    sealed class Event {
        abstract val raw: Map<String, Any?>
        open val id: String? get() = null

        /** The first line: protocol, tool version, worker threads, nice, idle time, the commands it knows. */
        data class Hello(val protocol: Int, val tool: String?, val pid: Long?, val jobs: Long?, val nice: Long?, val cmds: List<String>, override val raw: Map<String, Any?>) : Event()

        /** A line the tool could not take as a request. */
        /** A line the tool could not take, or a pause or resume it cannot do (`code` `not-pausable`, `not-paused`, ...; with the request's `id`). */
        data class Error(override val id: String?, val code: String?, val text: String, override val raw: Map<String, Any?>) : Event()

        /** The last line: why (`eof`, `idle`, `sigterm`, `requests`, `stdout`), and the threads and children left. */
        data class Bye(val why: String?, val threads: Long?, val children: Long?, override val raw: Map<String, Any?>) : Event()

        data class Queued(override val id: String, val ahead: Long?, override val raw: Map<String, Any?>) : Event()

        data class Start(override val id: String, val cmd: String?, val jobs: Long?, val steps: List<Pair<String, String?>>, override val raw: Map<String, Any?>) : Event()

        data class Space(override val id: String, val path: String?, val need: Long?, val free: Long?, val reserve: Long?, override val raw: Map<String, Any?>) : Event()

        data class Step(override val id: String, val step: String, val n: Long?, val of: Long?, val text: String?, override val raw: Map<String, Any?>) : Event()

        data class Progress(
            override val id: String, val step: String?, val done: Long?, val total: Long?, val unit: String?, val percent: Double?,
            val rate: Long?, val eta: Long?, val itemsDone: Long?, val itemsTotal: Long?, override val raw: Map<String, Any?>,
        ) : Event()

        data class Row(override val id: String, val kind: String?, override val raw: Map<String, Any?>) : Event()

        data class Line(override val id: String, val stream: String?, val text: String, override val raw: Map<String, Any?>) : Event()

        /** The work paused or went on for heat or the battery. */
        data class Heat(override val id: String, val state: String?, val why: String?, val text: String?, override val raw: Map<String, Any?>) : Event()

        /** The request stopped for a `pause` and kept what it has (`paused`), or goes on after a `resume` (`resumed`). */
        data class Paused(override val id: String, val paused: Boolean, val by: String?, val text: String?, override val raw: Map<String, Any?>) : Event()

        /** The network went away and the tool waits and retries (`waiting`, with the seconds to the next try), or it is back (`resumed`). */
        data class Net(override val id: String, val state: String?, val retryIn: Long?, val text: String?, override val raw: Map<String, Any?>) : Event()

        data class Ok(override val id: String, val cmd: String?, val seconds: Double?, val text: String?, override val raw: Map<String, Any?>) : Event()

        data class Refused(override val id: String, val cmd: String?, val code: String?, val text: String, override val raw: Map<String, Any?>) : Event()

        data class Failed(override val id: String, val cmd: String?, val code: String?, val text: String, override val raw: Map<String, Any?>) : Event()

        data class Cancelled(override val id: String, val cmd: String?, val by: String?, val removed: Long?, val text: String?, override val raw: Map<String, Any?>) : Event()

        /** An event this app does not know (the tool may add some). */
        data class Other(val ev: String?, override val raw: Map<String, Any?>) : Event()

        /** One of the four last events of a request: nothing with its id comes after it. */
        val ends: Boolean get() = this is Ok || this is Refused || this is Failed || this is Cancelled
    }

    /** One request line (with its newline): [keys] are the command's own, at the top level. */
    fun request(id: String, cmd: String, keys: Map<String, Any?> = emptyMap()): String {
        require(ID.matches(id)) { "'$id' is not a request id" }
        require(CMD.matches(cmd)) { "'$cmd' is not a command" }
        require("id" !in keys && "cmd" !in keys) { "id and cmd are not keys of a command" }
        val sb = StringBuilder()
        compact(sb, linkedMapOf<String, Any?>("id" to id, "cmd" to cmd) + keys)
        return sb.append('\n').toString()
    }

    /** Stops request [id] (answered at once, also while it runs). */
    fun cancel(id: String): String = request(id, Cmd.CANCEL)

    /** Holds request [id] where it is (a download keeps its parts); answered at once with `paused`. */
    fun pause(id: String): String = request(id, Cmd.PAUSE)

    /** Lets request [id] go on after a pause; answered with `resumed`. */
    fun resume(id: String): String = request(id, Cmd.RESUME)

    /**
     * One line of the tool's standard output: null when it is not one of the tool's (it does not begin with
     * `{"ev":`, as the root script's own `@@` lines before the tool starts, or a banner of su). Those are the
     * caller's.
     */
    fun parse(line: String): Event? {
        val t = line.trim()
        if (!t.startsWith("{\"ev\":")) return null
        val m = runCatching { JsonRead.parse(t) }.getOrNull() as? Map<*, *> ?: return null
        @Suppress("UNCHECKED_CAST")
        val raw = m as Map<String, Any?>
        val ev = raw["ev"] as? String
        val s = { k: String -> (raw[k] as? String)?.take(MAX_TEXT) }
        val n = { k: String -> raw[k] as? Long }
        when (ev) {
            "hello" -> return Event.Hello(n("proto")?.toInt() ?: 0, s("tool"), n("pid"), n("jobs"), n("nice"), (raw["cmds"] as? List<*>)?.filterIsInstance<String>().orEmpty(), raw)
            "error" -> return Event.Error(s("id")?.takeIf(ID::matches), s("code"), s("text") ?: "", raw)
            "bye" -> return Event.Bye(s("why"), n("threads"), n("children"), raw)
        }
        val id = s("id")?.takeIf(ID::matches) ?: return Event.Other(ev, raw)
        return when (ev) {
            "queued" -> Event.Queued(id, n("ahead"), raw)
            "start" -> Event.Start(
                id, s("cmd"), n("jobs"),
                (raw["steps"] as? List<*>)?.mapNotNull { st -> (st as? Map<*, *>)?.let { (it["step"] as? String)?.let { name -> name to (it["text"] as? String) } } }.orEmpty(),
                raw,
            )
            "space" -> Event.Space(id, s("path"), n("need"), n("free"), n("reserve"), raw)
            "step" -> Event.Step(id, s("step") ?: return Event.Other(ev, raw), n("n"), n("of"), s("text"), raw)
            "progress" -> Event.Progress(
                id, s("step"), n("done"), n("total"), s("unit"), (raw["percent"] as? Number)?.toDouble(), n("rate"), n("eta"),
                n("items_done"), n("items_total"), raw,
            )
            "row" -> Event.Row(id, s("kind"), raw)
            "line" -> Event.Line(id, s("stream"), s("text").orEmpty(), raw)
            "heat" -> Event.Heat(id, s("state"), s("why"), s("text"), raw)
            "paused" -> Event.Paused(id, true, s("by"), s("text"), raw)
            "resumed" -> Event.Paused(id, false, s("by"), s("text"), raw)
            "net" -> Event.Net(id, s("state"), (raw["next"] as? Number)?.let { Math.round(it.toDouble()) } ?: n("retry_in"), s("text"), raw)
            "ok" -> Event.Ok(id, s("cmd"), (raw["seconds"] as? Number)?.toDouble(), s("text"), raw)
            "refused" -> Event.Refused(id, s("cmd"), s("code"), s("text") ?: "refused (${s("code") ?: "no reason"})", raw)
            "failed" -> Event.Failed(id, s("cmd"), s("code"), s("text") ?: "failed (${s("code") ?: "no reason"})", raw)
            "cancelled" -> Event.Cancelled(id, s("cmd"), s("by"), n("removed"), s("text"), raw)
            else -> Event.Other(ev, raw)
        }
    }

    private val ID = Regex("^[A-Za-z0-9._-]{1,64}$")
    private val CMD = Regex("^[a-z][a-z0-9-]{0,39}$")
    const val MAX_TEXT = 4000

    /** JSON on one line (Json.write pretty-prints over several, which a line protocol cannot take). */
    private fun compact(out: StringBuilder, v: Any?) {
        when (v) {
            null -> out.append("null")
            is String -> str(out, v)
            is Boolean, is Int, is Long, is Short, is Byte -> out.append(v.toString())
            is Double -> out.append(if (v.isFinite()) v.toString() else "null")
            is Float -> out.append(if (v.isFinite()) v.toString() else "null")
            is Number -> out.append(v.toString())
            is Map<*, *> -> {
                out.append('{')
                v.entries.forEachIndexed { i, e ->
                    if (i > 0) out.append(',')
                    str(out, e.key.toString())
                    out.append(':')
                    compact(out, e.value)
                }
                out.append('}')
            }
            is Iterable<*> -> {
                out.append('[')
                v.forEachIndexed { i, x -> if (i > 0) out.append(','); compact(out, x) }
                out.append(']')
            }
            else -> str(out, v.toString())
        }
    }

    private fun str(out: StringBuilder, s: String) {
        out.append('"')
        for (c in s) {
            when {
                c == '"' -> out.append("\\\"")
                c == '\\' -> out.append("\\\\")
                c == '\n' -> out.append("\\n")
                c == '\r' -> out.append("\\r")
                c == '\t' -> out.append("\\t")
                c < ' ' || c == ' ' || c == ' ' -> out.append(String.format("\\u%04x", c.code))
                else -> out.append(c)
            }
        }
        out.append('"')
    }
}

/**
 * What a screen shows of one request, folded from the tool's lines in order: its steps with their marks, what
 * runs now with its progress and the time left, the space it needs and has, a heat pause, the output lines and
 * rows, and how it ended. The marks follow the tool's own rule (its README): a step is done when the next one's
 * `step` event comes or the request's last event does; the steps after the running one are next. Every number
 * and word is the last one the tool sent.
 */
data class OneiosToolFlow(
    val cmd: String? = null,
    /** The steps of the `start` event, in order: (step, text). */
    val plan: List<Pair<String, String?>> = emptyList(),
    /** The step of the last `step` event; null before the first one. */
    val current: String? = null,
    val queuedAhead: Long? = null,
    val done: Long? = null,
    val total: Long? = null,
    val unit: String? = null,
    val percent: Double? = null,
    val rate: Long? = null,
    val eta: Long? = null,
    val itemsDone: Long? = null,
    val itemsTotal: Long? = null,
    val spaceNeed: Long? = null,
    val spaceFree: Long? = null,
    val spacePath: String? = null,
    /** The tool's words while the work waits for heat or the battery; null when it runs. */
    val paused: String? = null,
    /** The request is held by a `pause` (the tool said `paused`), until its `resumed`. */
    val held: Boolean = false,
    /** The tool waits for the network: its words, and the seconds to its next try. */
    val netWaiting: String? = null,
    val netRetryIn: Long? = null,
    /** The tool's last `error` about this request (a pause it cannot do): its code and words. */
    val note: String? = null,
    val lines: List<String> = emptyList(),
    val rows: List<Map<String, Any?>> = emptyList(),
    val end: End? = null,
    /** The last event's text: the result line, the refusal's or failure's reason, what a cancel removed. */
    val text: String? = null,
    /** A refusal's or failure's code (`space`, `session`, `heat`, `mismatch`, `not-ported`, ...). */
    val code: String? = null,
    val result: Map<String, Any?>? = null,
) {
    enum class End { OK, REFUSED, FAILED, CANCELLED, LOST }

    data class Step(val id: String, val text: String?, val state: OneiosTool.StepState)

    val running: Boolean get() = end == null

    val steps: List<Step>
        get() {
            val at = plan.indexOfFirst { it.first == current }
            return plan.mapIndexed { i, (id, text) ->
                val state = when {
                    end == End.OK -> OneiosTool.StepState.DONE
                    at < 0 -> if (i == 0 && end == null) OneiosTool.StepState.NEXT else OneiosTool.StepState.PENDING
                    i < at -> OneiosTool.StepState.DONE
                    i == at -> when (end) {
                        null -> OneiosTool.StepState.RUNNING
                        End.REFUSED -> OneiosTool.StepState.REFUSED
                        End.CANCELLED -> OneiosTool.StepState.CANCELLED
                        else -> OneiosTool.StepState.FAILED
                    }
                    i == at + 1 && end == null -> OneiosTool.StepState.NEXT
                    else -> OneiosTool.StepState.PENDING
                }
                Step(id, text, state)
            }
        }

    /** The step after the running one. */
    val next: Step? get() = steps.firstOrNull { it.state == OneiosTool.StepState.NEXT }

    /** "3.2 GB of 17.9 GB (18%) · 310 of 2315 files · 168 MB/s · about 2 min left"; null before any progress. */
    val progressLine: String?
        get() {
            val d = done ?: return null
            val t = total ?: 0
            val bytes = unit == null || unit == "bytes"
            val amount = when {
                t > 0 && bytes -> "${Units.bytes(d)} of ${Units.bytes(t)} (${percent?.let { "%.0f".format(java.util.Locale.ROOT, it) } ?: (d * 100 / t)}%)"
                t > 0 -> "$d of $t $unit"
                bytes -> Units.bytes(d)
                else -> "$d $unit"
            }
            val items = if (itemsDone != null && itemsTotal != null) "$itemsDone of $itemsTotal files" else null
            val speed = rate?.takeIf { bytes }?.let { ByteMeter.speed(it) }
            val left = eta?.let { ByteMeter.left(it.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()) }
            return listOfNotNull(amount, items, speed, left).joinToString(" · ")
        }

    fun with(e: OneiosTool.Event): OneiosToolFlow = when (e) {
        is OneiosTool.Event.Queued -> copy(queuedAhead = e.ahead)
        is OneiosTool.Event.Start -> copy(cmd = e.cmd ?: cmd, plan = e.steps, queuedAhead = null)
        is OneiosTool.Event.Step -> copy(
            current = e.step, done = null, total = null, percent = null, rate = null, eta = null, itemsDone = null, itemsTotal = null,
            plan = if (plan.any { it.first == e.step }) plan else plan + (e.step to e.text),
        )
        is OneiosTool.Event.Progress -> copy(
            current = e.step ?: current, done = e.done, total = e.total, unit = e.unit, percent = e.percent, rate = e.rate, eta = e.eta,
            itemsDone = e.itemsDone, itemsTotal = e.itemsTotal,
        )
        is OneiosTool.Event.Space -> copy(spaceNeed = e.need, spaceFree = e.free, spacePath = e.path)
        is OneiosTool.Event.Heat -> copy(paused = if (e.state == "paused") (e.text ?: e.why ?: "paused") else null)
        is OneiosTool.Event.Paused -> copy(held = e.paused)
        is OneiosTool.Event.Error -> copy(note = listOfNotNull(e.code, e.text.ifEmpty { null }).joinToString(": "))
        is OneiosTool.Event.Net -> if (e.state == "waiting") copy(netWaiting = e.text ?: "waiting for the network", netRetryIn = e.retryIn) else copy(netWaiting = null, netRetryIn = null)
        is OneiosTool.Event.Line -> copy(lines = (lines + e.text).takeLast(MAX_LINES))
        is OneiosTool.Event.Row -> copy(rows = (rows + e.raw).takeLast(MAX_ROWS))
        is OneiosTool.Event.Ok -> copy(end = End.OK, text = e.text, result = e.raw, eta = null, paused = null, held = false, netWaiting = null, netRetryIn = null)
        is OneiosTool.Event.Refused -> copy(end = End.REFUSED, text = e.text, code = e.code, eta = null, paused = null, held = false, netWaiting = null, netRetryIn = null)
        is OneiosTool.Event.Failed -> copy(end = End.FAILED, text = e.text, code = e.code, eta = null, paused = null, held = false, netWaiting = null, netRetryIn = null)
        is OneiosTool.Event.Cancelled -> copy(end = End.CANCELLED, text = e.text, code = e.by, eta = null, paused = null, held = false, netWaiting = null, netRetryIn = null)
        else -> this
    }

    /** The tool went away before the request ended (it died, root ended it, the pipe broke): [why] in the app's words. */
    fun lost(why: String): OneiosToolFlow = if (end != null) this else copy(end = End.LOST, text = why, eta = null)

    companion object {
        const val MAX_LINES = 5000
        const val MAX_ROWS = 2000
    }
}
