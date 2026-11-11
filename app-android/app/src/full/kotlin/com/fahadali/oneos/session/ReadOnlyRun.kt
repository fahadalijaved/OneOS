package com.fahadali.oneos.session

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.ProbeAudit
import com.fahadali.oneos.core.model.ProbeCommand
import com.fahadali.oneos.core.model.ProbeCommandList
import com.fahadali.oneos.core.model.ProbeResult
import com.fahadali.oneos.core.model.ProbeSink
import com.fahadali.oneos.core.model.ProbeStatus
import com.fahadali.oneos.core.model.ProbeStreamOutcome
import com.fahadali.oneos.core.model.ProbeStreamParser
import com.fahadali.oneos.core.root.RootProbeRunner
import java.io.File
import java.io.OutputStream
import java.util.concurrent.CopyOnWriteArraySet
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicLong

/** One job at a time, kept in the app process so it survives rotation (like ProbeSession). */
abstract class BackgroundJob<S : Any>(initial: S, name: String) {
    private val main = Handler(Looper.getMainLooper())
    protected val executor = Executors.newSingleThreadExecutor { r -> Thread(r, name) }
    private val listeners = CopyOnWriteArraySet<(S) -> Unit>()

    @Volatile var state: S = initial
        private set

    /** Calls [listener] now and on every change (main thread); returns the unsubscribe call. */
    fun observe(listener: (S) -> Unit): () -> Unit {
        listeners += listener
        listener(state)
        return { listeners -= listener }
    }

    /**
     * [observe] for a screen that shows only [key] of the state: [listener] runs when that changes,
     * not for every progress line. A page that rebuilt its rows for each of them lost the tap on a
     * row rebuilt under the finger (11-10: "Skip saving logs doesn't respond to touch").
     */
    fun <K> observeBy(key: (S) -> K, listener: (S) -> Unit): () -> Unit {
        var first = true
        var last: K? = null
        return observe { s ->
            val k = key(s)
            if (first || k != last) {
                first = false
                last = k
                listener(s)
            }
        }
    }

    protected fun update(s: S) {
        state = s
        main.post { listeners.forEach { it(s) } }
    }
}

/**
 * A read-only list (the probe grammar) run as root by the probe runner:
 * `su -c "sh <files>/<dir>/probe.sh <files>/<dir>/<list>"`, the same as Run
 * tests. The list and the runner are audited (ProbeAudit) before root is
 * asked; a list that fails is never run. Root writes nothing: the output
 * goes over the pipe to [ProbeSink].
 */
class ReadOnlyRun(private val listAsset: String, private val dirName: String) {
    data class Bundled(val listText: String, val runnerText: String, val commands: List<ProbeCommand>, val problems: List<String>) {
        val listSha256: String get() = Hashes.sha256(listText)
        val runnerSha256: String get() = Hashes.sha256(runnerText)
    }

    data class Outcome(val stream: ProbeStreamOutcome, val end: RootProbeRunner.End) {
        val statuses: Map<String, ProbeStatus> get() = stream.results.associate { it.id to it.status }
        val stopped: Boolean get() = end.cancelled || end.killed || end.error != null
    }

    @Volatile private var runner: RootProbeRunner? = null

    fun bundled(ctx: Context): Bundled {
        val assets = ctx.applicationContext.assets
        val list = assets.open(listAsset).use { it.readBytes().toString(Charsets.UTF_8) }
        val runner = assets.open(RUNNER_ASSET).use { it.readBytes().toString(Charsets.UTF_8) }
        val problems = mutableListOf<String>()
        val commands = try {
            ProbeCommandList.parse(list)
        } catch (e: ProbeCommandList.ParseException) {
            problems += "$listAsset: ${e.message}"
            emptyList()
        }
        problems += ProbeAudit.audit(commands)
        problems += ProbeAudit.auditRunner(runner).map { "probe.sh: $it" }
        return Bundled(list, runner, commands, problems)
    }

    fun cancel() {
        runner?.cancel()
    }

    /**
     * Runs the list; [onStarted] / [onFinished] report each entry. Blocks; call it off the main thread.
     * [cancelled]: asked once the run can be cancelled, for a [cancel] that came before that (it found no run to stop).
     */
    fun run(
        ctx: Context,
        sink: (String) -> OutputStream,
        onStarted: (String) -> Unit = {},
        onFinished: (ProbeResult) -> Unit = {},
        cancelled: () -> Boolean = { false },
    ): Outcome {
        val b = bundled(ctx)
        check(b.problems.isEmpty()) { "the bundled list failed its read-only check: ${b.problems.first()}" }
        val dir = File(ctx.applicationContext.filesDir, dirName).apply { mkdirs() }
        val runnerFile = File(dir, "probe.sh").apply { writeText(b.runnerText) }
        val listFile = File(dir, File(listAsset).name).apply { writeText(b.listText) }
        check(Hashes.sha256(runnerFile) == b.runnerSha256 && Hashes.sha256(listFile) == b.listSha256) { "the list did not copy exactly" }
        val silence = AtomicLong(SILENCE_MARGIN_MS)
        val parser = ProbeStreamParser(object : ProbeSink {
            override fun probeStarted(id: String, timeoutSec: Int) {
                silence.set(timeoutSec * 1000L + SILENCE_MARGIN_MS)
                onStarted(id)
            }

            override fun open(path: String): OutputStream = sink(path)

            override fun probeFinished(result: ProbeResult) = onFinished(result)
        })
        val r = RootProbeRunner(runnerFile, listFile)
        runner = r
        if (cancelled()) r.cancel()
        val end = r.run(parser) { silence.get() }
        runner = null
        return Outcome(parser.finish(), end)
    }

    /** A sink into [root] (relative paths only). */
    fun fileSink(root: File): (String) -> OutputStream {
        val base = root.canonicalPath + File.separator
        return { path ->
            val f = File(root, path)
            check(f.canonicalPath.startsWith(base)) { "output outside the folder: $path" }
            f.parentFile?.mkdirs()
            f.outputStream().buffered(1 shl 16)
        }
    }

    companion object {
        const val RUNNER_ASSET = "probe/probe.sh"
        const val STATUS_LIST = "root/status.list"
        const val INSTALLD_LIST = "root/installd.list"
        const val COLLECT_LIST = "logs/collect.list"

        private const val SILENCE_MARGIN_MS = 30_000L
    }
}
