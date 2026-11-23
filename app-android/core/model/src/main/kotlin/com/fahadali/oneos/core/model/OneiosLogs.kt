package com.fahadali.oneos.core.model

/**
 * The session logs of the iOS 27 (OneiOS) system (docs/oneios.md, "Session
 * logs"): what `oneios_root.sh logs` and `logfile` print, and the reading of
 * an xnuhost log: how far the boot got, the kernel panic, the processes that
 * died, how the session ended.
 *
 * The log's format is xnuhost's (`runtime/xnuhost/src/log.c` in OneiOS, and
 * its `docs/booter.md`): `[seconds.millis] xnuhost I|E|D text` are the host's
 * lines, `[seconds.millis] guest     text` the iOS kernel's console, and
 * `xnuhost !! text 0x.. 0x..` (no time) is written from a signal handler.
 * Every marker below is a line xnuhost's sources print or one the kernel
 * printed in OneiOS's boot logs on the PC; none is a guess at a format.
 */
data class OneiosLogFile(
    val id: String,
    val bytes: Long,
    /** Seconds since 1970 of the file's last write: for a session log, when the session's last line was written. */
    val modified: Long,
    /** Its last lines (40 at most, each cut at 400 characters). */
    val tail: List<String> = emptyList(),
) {
    /** An xnuhost log (this session's or the last one's, or an earlier one), not a script's or a helper's. */
    val session: Boolean get() = id == OneiosLogs.SESSION || id.startsWith("xnuhost-")
}

enum class OneiosLogFilter(val label: String) { ERRORS("E"), SIGNAL("!!"), PANIC("panic"), GUEST("guest") }

enum class OneiosBootStage(val title: String) {
    HOST("xnuhost started"),
    KERNEL_ENTERED("kernel entered"),
    KERNEL("kernel start (Darwin banner)"),
    ROOT("root mount (BSD root)"),
    INIT("launchd loading"),
    LAUNCHD("launchd running"),
    BACKBOARDD("backboardd"),
    SPRINGBOARD("SpringBoard"),
    READY("ready: first frame (session/ready)"),
}

enum class OneiosEndKind { GUEST_OFF, GUEST_RETURN, STOP_SIGNAL, PANIC, KERNEL_FAULT, HOST_FAULT, RESTART_FAILED, SETUP, HOST_STOP, UNKNOWN }

object OneiosLogs {
    const val SESSION = "session"

    /** The other logs of the stage: the switch's, the return's and the watcher's, the display helper's, the watchdog feeder's. */
    val OTHERS: List<String> = listOf("switch", "return", "display", "feeder")

    /** Earlier session logs kept by the switch, and shown. */
    const val EARLIER = 5

    /** The most `logfile` hands over in one call (LOG_CHUNK_MAX in oneios_root.sh). */
    const val CHUNK_MAX = 1_048_576

    /** The first read of a log: its end. */
    const val FIRST_CHUNK = 262_144

    private val EARLIER_ID = Regex("^xnuhost-[0-9]{1,18}$")

    /** Kernel-update receipts (`logs/update-<epoch>.log`, `-<n>` when two share a second), written by root's `finish kernel` and `restore kernel`. */
    private val UPDATE_ID = Regex("^update-[0-9]{1,18}(-[0-9]{1,18})?$")

    fun validId(id: String): Boolean = id == SESSION || id in OTHERS || EARLIER_ID.matches(id) || UPDATE_ID.matches(id)

    /** The file's name on the phone and in a shared zip. */
    fun fileName(id: String): String = when (id) {
        SESSION -> "xnuhost.log"
        "feeder" -> "watchdog_feeder.log"
        else -> "$id.log"
    }

    /** Where the log is, under the stage. */
    fun path(id: String): String = when (id) {
        SESSION -> "session/xnuhost.log"
        "display" -> "control/display.log"
        "feeder" -> "control/watchdog_feeder.log"
        "switch", "return" -> "$id.log"
        else -> "logs/$id.log"
    }

    // --- What root prints ---------------------------------------------------------

    data class Listing(val sessionOpen: Boolean, val files: List<OneiosLogFile>) {
        val sessions: List<OneiosLogFile> get() = files.filter { it.session }
        val others: List<OneiosLogFile> get() = files.filterNot { it.session }
    }

    /** `logs`: `@@RESULT session open|none`, `@@RESULT log <id> <bytes> <mtime>` and `| <id> <line>` for the last lines. */
    fun parseList(results: List<String>, lines: List<String>): Listing {
        val tails = HashMap<String, MutableList<String>>()
        for (l in lines) {
            if (!l.startsWith("| ")) continue
            val rest = l.substring(2)
            val id = rest.substringBefore(' ')
            if (validId(id)) tails.getOrPut(id) { mutableListOf() } += rest.substringAfter(' ', "")
        }
        var open = false
        val files = mutableListOf<OneiosLogFile>()
        for (r in results) {
            val w = r.trim().split(' ')
            when (w.firstOrNull()) {
                "session" -> open = w.getOrNull(1) == "open"
                "log" -> {
                    val id = w.getOrNull(1) ?: continue
                    val bytes = w.getOrNull(2)?.toLongOrNull() ?: continue
                    val modified = w.getOrNull(3)?.toLongOrNull() ?: continue
                    if (w.size == 4 && validId(id) && files.none { it.id == id }) files += OneiosLogFile(id, bytes, modified, tails[id].orEmpty())
                }
            }
        }
        val earlier = files.filter { it.id.startsWith("xnuhost-") }.sortedByDescending { it.id.removePrefix("xnuhost-").toLong() }.take(EARLIER)
        return Listing(open, files.filter { it.id == SESSION } + earlier + OTHERS.mapNotNull { id -> files.firstOrNull { it.id == id } })
    }

    /** One read of a log: the bytes [[start], [end]) of a file of [size] bytes, as whole lines. */
    data class Chunk(val id: String, val size: Long, val start: Long, val end: Long, val lines: List<String>) {
        /** Nothing of the file is before this chunk. */
        val first: Boolean get() = start == 0L
    }

    /** `logfile <id> <end> <bytes>`: `@@RESULT chunk <id> <size> <start> <end>` and the lines, each after `| `. */
    fun parseChunk(id: String, results: List<String>, lines: List<String>): Chunk? {
        val w = results.firstOrNull { it.startsWith("chunk $id ") }?.trim()?.split(' ') ?: return null
        if (w.size != 5) return null
        val size = w[2].toLongOrNull() ?: return null
        val start = w[3].toLongOrNull() ?: return null
        val end = w[4].toLongOrNull() ?: return null
        if (start < 0 || start > end || end > size || end - start > CHUNK_MAX) return null
        return Chunk(id, size, start, end, lines.filter { it.startsWith("| ") || it == "|" }.map { it.removePrefix("|").removePrefix(" ") })
    }

    // --- Lines ----------------------------------------------------------------------

    enum class Source { HOST_INFO, HOST_ERROR, HOST_DEBUG, SIGNAL, GUEST, OTHER }

    private val STAMP = Regex("""^\[ *\d+\.\d{3}] """)

    /** The line without its time. */
    fun body(line: String): String = if (line.startsWith("[")) STAMP.find(line)?.let { line.substring(it.range.last + 1) } ?: line else line

    fun source(line: String): Source {
        val b = body(line)
        return when {
            b.startsWith("guest ") -> Source.GUEST
            b.startsWith("xnuhost I ") -> Source.HOST_INFO
            b.startsWith("xnuhost E ") -> Source.HOST_ERROR
            b.startsWith("xnuhost D ") -> Source.HOST_DEBUG
            b.startsWith("xnuhost !! ") -> Source.SIGNAL
            else -> Source.OTHER
        }
    }

    /** The word panic by itself: not `-no_slto_panic`, `ml-timeout-lock-panic-scale` or `gPanicBase` of the boot arguments and the early console. */
    private val PANIC_WORD = Regex("""(?<![\w-])panic(?![\w-])""", RegexOption.IGNORE_CASE)

    fun matches(line: String, filter: OneiosLogFilter): Boolean = when (filter) {
        OneiosLogFilter.ERRORS -> source(line) == Source.HOST_ERROR
        OneiosLogFilter.SIGNAL -> source(line) == Source.SIGNAL
        OneiosLogFilter.GUEST -> source(line) == Source.GUEST
        OneiosLogFilter.PANIC -> PANIC_WORD.containsMatchIn(line)
    }

    /** A line is shown when it has [query] (any case) and, with filters chosen, matches one of them. */
    fun shown(line: String, filters: Set<OneiosLogFilter>, query: String): Boolean =
        (filters.isEmpty() || filters.any { matches(line, it) }) && (query.isEmpty() || line.contains(query, ignoreCase = true))

    // --- The summary ------------------------------------------------------------------

    /** A process the kernel's console reported dead: how often, and by which signals (Darwin's numbers) where it said. */
    data class Death(val name: String, val count: Int, val signals: Map<Int, Int>) {
        val text: String
            get() {
                val by = signals.entries.sortedByDescending { it.value }.joinToString(", ") { (s, n) -> if (n == count) signalName(s) else "${signalName(s)} ×$n" }
                return "$name ×$count" + if (by.isEmpty()) "" else " ($by)"
            }
    }

    data class End(
        val kind: OneiosEndKind,
        /** One sentence. */
        val text: String,
        /** A few words, for a list row. */
        val short: String,
        /** xnuhost's `exit N` line; null when the log has none. */
        val exitCode: Int? = null,
        /** The stop signal, or the signal of a fault in xnuhost's own code. */
        val signal: Int? = null,
    )

    data class Summary(
        /** The furthest stage any boot in this log reached; null when not even xnuhost's first line is there. */
        val stage: OneiosBootStage?,
        val stages: Set<OneiosBootStage>,
        /** The furthest stage of the last boot, when the guest restarted in place. */
        val lastBootStage: OneiosBootStage?,
        /** The first panic string of the last boot that had one. */
        val panic: String?,
        val panics: Int,
        val deaths: List<Death>,
        val end: End,
        /** In-place restarts of the guest ("starting again"). */
        val restarts: Int,
        val lines: Int,
        val errors: Int,
        val signalLines: Int,
        /** False while only the end of the log has been read: earlier stages, panics and deaths may be missing. */
        val complete: Boolean,
        val returned: ReturnNote? = null,
    )

    private val PANIC = Regex("""^panic\(cpu \d+ caller 0x[0-9a-f]+\): (.*)$""")
    private val SHENG_EXIT = Regex("""^sheng-exit: (.+)\[(\d+)] status 0x([0-9a-f]+) reason ns (\d+) code 0x([0-9a-f]+)""")
    private val CRASHED = Regex("""^Process\[(\d+)] crashed: (.+?)\. """)
    private val KILLED = Regex("""^\[(.+): killed] exiting with signal (\d+)""")
    private val STOPPING = Regex("""^stopping: (.*) \(reason (\d+), code (\d+)\)$""")
    private val EXIT = Regex("""^exit (\d+)$""")
    private val FAULT = Regex("""^(fault inside a host call|fault on a host thread): signal, address 0x([0-9a-f]{16})""")

    private val SIGNALS = mapOf(
        1 to "SIGHUP", 2 to "SIGINT", 3 to "SIGQUIT", 4 to "SIGILL", 5 to "SIGTRAP", 6 to "SIGABRT", 7 to "SIGEMT", 8 to "SIGFPE",
        9 to "SIGKILL", 10 to "SIGBUS", 11 to "SIGSEGV", 12 to "SIGSYS", 13 to "SIGPIPE", 14 to "SIGALRM", 15 to "SIGTERM",
    )

    /** Darwin's name of a guest signal (the numbers up to 15 that a dying process shows). */
    fun signalName(signal: Int): String = SIGNALS[signal] ?: "signal $signal"

    /** Linux's name of a signal xnuhost itself got: 7 is SIGBUS there, 10 SIGUSR1. */
    private fun hostSignalName(signal: Int): String = when (signal) {
        7 -> "SIGBUS"
        10 -> "SIGUSR1"
        12 -> "SIGUSR2"
        else -> signalName(signal)
    }

    private class Boot {
        val stages = HashSet<OneiosBootStage>()
        var stoppingWhy: String? = null
        var stoppingReason = -1
        var exit: Int? = null
        var fault: String? = null
        var faultSignal: Int? = null
        var kernelFault = false
        var lastError: String? = null
        var gaveUp = false
        var panic: String? = null
    }

    /**
     * Reads a whole xnuhost log, or its end ([complete] false). [returned] is
     * what the return's own log says of this session ([returnFor]).
     */
    fun summarize(lines: Iterable<String>, complete: Boolean = true, returned: ReturnNote? = null): Summary {
        var count = 0
        val all = HashSet<OneiosBootStage>()
        var boot = Boot()
        var boots = 0
        var restarts = 0
        var panics = 0
        var panic: String? = null
        var errors = 0
        var signalLines = 0
        // Deaths: by process name, the pids the console named (with the signal where it said) and the lines without a pid.
        val byPid = LinkedHashMap<String, HashMap<String, Int?>>()
        val killed = HashMap<String, HashMap<Int, Int>>()
        for (line in lines) {
            count++
            val b = body(line)
            when {
                b.startsWith("guest ") -> {
                    val t = b.substring(6).trimStart()
                    when {
                        t.startsWith("Darwin Kernel Version") -> boot.stages += OneiosBootStage.KERNEL
                        t.startsWith("BSD root: ") -> boot.stages += OneiosBootStage.ROOT
                        t.startsWith("load_init_program: attempting to load") -> boot.stages += OneiosBootStage.INIT
                        t.startsWith("com.apple.xpc.launchd|") -> boot.stages += OneiosBootStage.LAUNCHD
                        t.startsWith("panic(") -> PANIC.find(t)?.let { m ->
                            panics++
                            if (boot.panic == null) boot.panic = m.groupValues[1].trim()
                            panic = boot.panic
                        }
                        t.startsWith("sheng-exit: ") -> SHENG_EXIT.find(t)?.let { m ->
                            val status = m.groupValues[3].toIntOrNull(16) ?: 0
                            byPid.getOrPut(m.groupValues[1]) { HashMap() }["$boots/${m.groupValues[2]}"] = (status and 0x7f).takeIf { it != 0 }
                        }
                        t.startsWith("Process[") -> CRASHED.find(t)?.let { m ->
                            byPid.getOrPut(m.groupValues[2]) { HashMap() }.let { pids -> pids.putIfAbsent("$boots/${m.groupValues[1]}", null) }
                        }
                        t.startsWith("[") -> KILLED.find(t)?.let { m ->
                            val signal = m.groupValues[2].toIntOrNull() ?: 0
                            killed.getOrPut(m.groupValues[1]) { HashMap() }.merge(signal, 1, Int::plus)
                        }
                    }
                    // The first console line that names the process with its pid: it runs.
                    if (OneiosBootStage.BACKBOARDD !in boot.stages && t.contains("backboardd[")) boot.stages += OneiosBootStage.BACKBOARDD
                    if (OneiosBootStage.SPRINGBOARD !in boot.stages && (t.contains("SpringBoard[") || t.contains("crashed: SpringBoard."))) {
                        boot.stages += OneiosBootStage.SPRINGBOARD
                    }
                }
                b.startsWith("xnuhost I ") -> {
                    val t = b.substring(10)
                    when {
                        t.startsWith("xnuhost: session ABI ") -> {
                            // xnuhost's first line: a new start (the first, or the guest's restart in place).
                            all += boot.stages
                            boot = Boot()
                            boots++
                            boot.stages += OneiosBootStage.HOST
                        }
                        t.startsWith("cpu0: entering the kernel at ") -> boot.stages += OneiosBootStage.KERNEL_ENTERED
                        t.startsWith("guest ready: first frame") -> boot.stages += OneiosBootStage.READY
                        t.startsWith("the guest asked for a restart: starting again") -> restarts++
                        t.startsWith("stopping: ") -> STOPPING.find(t)?.let { m ->
                            boot.stoppingWhy = m.groupValues[1]
                            boot.stoppingReason = m.groupValues[2].toIntOrNull() ?: -1
                        }
                        t.startsWith("exit ") -> EXIT.find(t)?.let { boot.exit = it.groupValues[1].toIntOrNull() }
                    }
                }
                b.startsWith("xnuhost E ") -> {
                    errors++
                    val t = b.substring(10)
                    if (t.startsWith("the guest restarted ") && t.contains("without getting ready")) boot.gaveUp = true
                    boot.lastError = t
                }
                b.startsWith("xnuhost !! ") -> {
                    signalLines++
                    val t = b.substring(11)
                    FAULT.find(t)?.let { m ->
                        boot.fault = m.groupValues[1]
                        boot.faultSignal = m.groupValues[2].toLongOrNull(16)?.toInt()
                    }
                    if (t.startsWith("kernel fault with no exception upcall")) boot.kernelFault = true
                }
            }
        }
        all += boot.stages
        val deaths = (byPid.keys + killed.keys).distinct().map { name ->
            val pids = byPid[name].orEmpty()
            val signals = HashMap<Int, Int>()
            pids.values.filterNotNull().forEach { signals.merge(it, 1, Int::plus) }
            // A "[name: killed]" line with no pid is the same death as a pid line of that signal; only the extra ones count.
            var extra = 0
            for ((signal, n) in killed[name].orEmpty()) {
                val more = n - (signals[signal] ?: 0)
                if (more > 0) {
                    signals.merge(signal, more, Int::plus)
                    extra += more
                }
            }
            val unsignalled = pids.values.count { it == null }
            Death(name, maxOf(pids.size + extra - minOf(extra, unsignalled), 1), signals)
        }.sortedWith(compareByDescending<Death> { it.count }.thenBy { it.name })
        return Summary(
            stage = all.maxByOrNull { it.ordinal },
            stages = all,
            lastBootStage = if (restarts > 0) boot.stages.maxByOrNull { it.ordinal } else null,
            panic = panic,
            panics = panics,
            deaths = deaths,
            end = end(boot, returned),
            restarts = restarts,
            lines = count,
            errors = errors,
            signalLines = signalLines,
            complete = complete,
            returned = returned,
        )
    }

    private fun end(b: Boot, returned: ReturnNote?): End {
        val why = b.stoppingWhy
        val signal = why?.takeIf { it.startsWith("signal ") }?.removePrefix("signal ")?.toIntOrNull()
        val kind: OneiosEndKind
        var text: String
        var short: String
        when {
            b.fault != null -> {
                kind = OneiosEndKind.HOST_FAULT
                val name = b.faultSignal?.let(::hostSignalName) ?: "a signal"
                text = "xnuhost crashed: $name, a ${b.fault} (its own code, not the guest's)"
                short = "xnuhost crashed ($name)"
            }
            signal != null -> {
                kind = OneiosEndKind.STOP_SIGNAL
                val name = hostSignalName(signal)
                text = "Stopped by $name" + if (signal == 15) " (the return to One UI ends xnuhost with it)" else ""
                short = "stopped by $name"
            }
            why == "kernel fault" -> {
                kind = OneiosEndKind.KERNEL_FAULT
                text = "A kernel fault the kernel did not take"
                short = "kernel fault"
            }
            why != null && b.stoppingReason == 2 && why.startsWith("the guest halted") -> {
                kind = OneiosEndKind.PANIC
                text = "Kernel panic" + (b.panic?.let { ": ${it.take(200)}" } ?: " ($why)")
                short = "kernel panic"
            }
            why != null && b.stoppingReason == 3 -> {
                kind = OneiosEndKind.GUEST_RETURN
                text = "The guest asked to return to One UI"
                short = "the guest asked to return"
            }
            why != null && b.stoppingReason == 1 -> {
                kind = OneiosEndKind.RESTART_FAILED
                text = if (b.gaveUp) "The guest kept restarting without getting ready; xnuhost did not start it again" else "The guest asked for a restart ($why) and xnuhost could not start it again"
                short = "restart not possible"
            }
            why != null && b.stoppingReason == 0 -> {
                kind = OneiosEndKind.GUEST_OFF
                text = "The guest shut down ($why)"
                short = "the guest shut down"
            }
            why != null -> {
                kind = OneiosEndKind.HOST_STOP
                text = "xnuhost stopped: $why"
                short = why.take(60)
            }
            b.kernelFault -> {
                kind = OneiosEndKind.KERNEL_FAULT
                text = "A kernel fault the kernel did not take"
                short = "kernel fault"
            }
            OneiosBootStage.HOST in b.stages && OneiosBootStage.KERNEL_ENTERED !in b.stages && b.lastError != null -> {
                kind = OneiosEndKind.SETUP
                text = "xnuhost did not get as far as the kernel. Its last error: ${b.lastError!!.take(300)}"
                short = "setup failed"
            }
            else -> {
                kind = OneiosEndKind.UNKNOWN
                text = "The log has no stopping or exit line: xnuhost was killed, the phone restarted, or the session still runs"
                short = "no end line"
            }
        }
        val exit = b.exit
        if (exit != null) {
            text += "; xnuhost exit $exit (${exitMeaning(exit)})"
            short = "exit $exit · $short"
        } else if (why != null && b.fault == null) {
            text += "; no exit line after it (ended before it finished stopping)"
        }
        returned?.let { text += ". Return: ${it.text}" }
        return End(kind, text, short, exit, signal ?: b.faultSignal)
    }

    /** OneiOS docs/booter.md, the exit code table. */
    fun exitMeaning(code: Int): String = when (code) {
        0 -> "shut down, a stop signal, or a return asked from inside"
        2 -> "bad arguments or a failed setup"
        3 -> "a restart that could not be done"
        4 -> "kernel panic or kernel fault"
        5 -> "a fault in xnuhost's own code"
        else -> "not one of xnuhost's codes"
    }

    /** The words of a list row for a session log: how it ended, from its last lines. */
    fun endLine(tail: List<String>): String {
        val s = summarize(tail, complete = false)
        return if (s.end.kind == OneiosEndKind.UNKNOWN && s.end.exitCode == null) {
            tail.lastOrNull { it.isNotBlank() }?.let { body(it).take(120) } ?: "empty"
        } else s.end.short
    }

    /** The summary as the lines shown above a log and put first in a shared one. */
    fun summaryLines(s: Summary): List<String> = buildList {
        val stage = s.stage
        add(
            "Boot got to: " + (stage?.let { "${it.title} (${it.ordinal + 1} of ${OneiosBootStage.entries.size})" } ?: "nothing of xnuhost's in what was read") +
                (s.lastBootStage?.takeIf { it != stage }?.let { "; the last boot got to ${it.title}" } ?: ""),
        )
        val missed = OneiosBootStage.entries.filter { stage != null && it.ordinal < stage.ordinal && it !in s.stages }
        if (missed.isNotEmpty() && s.complete) add("Not seen on the way: " + missed.joinToString(", ") { it.title })
        add("Kernel panic: " + (s.panic?.take(400) ?: "none") + if (s.panics > 1) " (${s.panics} panic lines)" else "")
        add("Processes that died: " + if (s.deaths.isEmpty()) "none reported" else s.deaths.joinToString(", ") { it.text })
        add("Ended: ${s.end.text}")
        if (s.restarts > 0) add("Guest restarts in place: ${s.restarts}")
        add("${s.lines} lines, ${s.errors} xnuhost errors (E), ${s.signalLines} lines from signal context (!!)")
        if (!s.complete) add("Only the end of the log has been read: earlier stages, panics and deaths may be missing.")
    }

    // --- return.log -------------------------------------------------------------------

    /** One return in `return.log`: who started it, the watcher's or the key reader's reason, how it came out. */
    data class ReturnNote(
        /** `yyyy-MM-dd` when the watcher or a key reader wrote the line before it; the return's own lines carry no date. */
        val date: String?,
        /** Seconds into the day of the return's first line. */
        val secondOfDay: Int,
        /** watcher, app, keys-direct, manual, switch-not-armed. */
        val who: String,
        val why: String?,
        val result: String?,
    ) {
        val text: String
            get() {
                val by = when (who) {
                    "watcher" -> "the watcher" + (why?.let { ": $it" } ?: "")
                    "app" -> "Back to One UI in the app"
                    "keys-direct" -> "the volume keys, without the watcher" + (why?.let { " ($it)" } ?: "")
                    "manual" -> "oneios_return.sh run by hand"
                    "switch-not-armed" -> "the switch, which could not arm the way back"
                    else -> who
                }
                return by + (result?.let { "; $it" } ?: "")
            }

        /** The volume keys asked for it. */
        val keys: Boolean get() = who == "keys-direct" || why?.contains("keys:") == true
    }

    private val WATCHER = Regex("""^(\d{4}-\d\d-\d\d) (\d\d):(\d\d):(\d\d) watcher: (.*); returning to One UI$""")
    private val KEYS = Regex("""^(\d{4}-\d\d-\d\d) (\d\d):(\d\d):(\d\d) keys: the watcher did not start the return within 5 s of '(.*)'; starting it from the key reader$""")
    private val RETURN = Regex("""^(\d\d):(\d\d):(\d\d) === Return to One UI \(([A-Za-z0-9._-]+)\), session state '([^']*)'""")
    private val RESULT = Regex("""^\d\d:\d\d:\d\d (One UI restored in place.*|FAILSAFE: .*|GUARD: .*|Reboot return asked|The switch ended before One UI's framework was stopped.*)$""")

    private val NOTHING = Regex("""^\d\d:\d\d:\d\d (no open session \(|no session folder: |another return is already running )""")

    /** Every return `return.log` holds, oldest first (oneios_return.sh's `say` lines and the watcher's). */
    fun returns(returnLog: List<String>): List<ReturnNote> {
        val out = mutableListOf<ReturnNote>()
        var date: String? = null
        var why: String? = null
        for (l in returnLog) {
            (WATCHER.find(l) ?: KEYS.find(l))?.let { m ->
                date = m.groupValues[1]
                why = m.groupValues[5]
            }
            val r = RETURN.find(l)
            if (r != null) {
                val (h, m, s, who) = r.destructured
                out += ReturnNote(date, h.toInt() * 3600 + m.toInt() * 60 + s.toInt(), who, why, null)
                date = null
                why = null
                continue
            }
            if (out.isEmpty() || out.last().result != null) continue
            // A return that found nothing open, or another one already at work, returned from nothing.
            if (NOTHING.containsMatchIn(l)) out.removeAt(out.lastIndex)
            else RESULT.find(l)?.let { m -> out[out.lastIndex] = out.last().copy(result = m.groupValues[1].take(200)) }
        }
        return out
    }

    /**
     * The return that ended the session whose log was last written on [date]
     * (`yyyy-MM-dd`, the phone's time) at [secondOfDay]: one that started
     * within two minutes of it. For the newest log ([newest]) with no such
     * match, the last return in the file: a guest that had gone quiet writes
     * its last line long before the return.
     */
    fun returnFor(notes: List<ReturnNote>, date: String, secondOfDay: Int, newest: Boolean): ReturnNote? {
        val near = notes.lastOrNull { n ->
            val d = Math.floorMod(n.secondOfDay - secondOfDay, 86_400).let { if (it > 43_200) it - 86_400 else it }
            d in -120..120 && (n.date == null || n.date == date || secondOfDay < 120 || secondOfDay > 86_400 - 120)
        }
        return near ?: if (newest) notes.lastOrNull() else null
    }
}
