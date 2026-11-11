package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.ProbeStreamParser
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import kotlin.concurrent.thread

/**
 * Runs the probe as root: exactly `su -c "sh <runner> <list>"`, where the
 * runner and the list are the app's own copies of `assets/probe/probe.sh` and
 * `assets/probe/commands.list` (docs/app/compat-safety-logs.md section 7).
 * Root writes nothing: the runner prints every output base64 framed, and the
 * lines go straight to [ProbeStreamParser], whose sink is the app's cache.
 *
 * Blocks until the runner ends, so call it off the main thread. A runner that
 * prints nothing for longer than [silenceLimitMs] (the current entry's
 * timeout plus a margin) or runs past [TOTAL_LIMIT_MS] is killed.
 */
class RootProbeRunner(private val runner: File, private val list: File) {
    data class End(
        /** Exit code of su; null when it never started or was killed. */
        val exitCode: Int?,
        /** The last few kB su printed on stderr. */
        val stderr: String,
        val cancelled: Boolean,
        /** Killed because it went silent or ran too long. */
        val killed: Boolean,
        /** Could not start su at all. */
        val error: String?,
    )

    @Volatile private var process: Process? = null

    @Volatile private var cancelled = false

    @Volatile private var killed = false

    /** Stops the run (kills the su process); [run] then returns with [End.cancelled]. */
    fun cancel() {
        cancelled = true
        process?.destroyForcibly()
    }

    fun run(parser: ProbeStreamParser, silenceLimitMs: () -> Long): End {
        val cmd = "sh ${runner.absolutePath} ${list.absolutePath}"
        require(SAFE_PATH.matches(runner.absolutePath) && SAFE_PATH.matches(list.absolutePath)) { "unexpected path: $cmd" }
        if (cancelled) return End(null, "", cancelled = true, killed = false, error = null)
        val proc = try {
            ProcessBuilder("su", "-c", cmd).start()
        } catch (e: IOException) {
            return End(null, "", cancelled = false, killed = false, error = "su could not be started: ${e.message}")
        }
        process = proc
        val stderr = StringBuilder()
        val errReader = thread(name = "probe-stderr", isDaemon = true) {
            runCatching {
                proc.errorStream.bufferedReader().useLines { lines ->
                    lines.forEach { l -> synchronized(stderr) { if (stderr.length < 4096) stderr.append(l).append('\n') } }
                }
            }
        }
        val lastLine = AtomicLong(System.currentTimeMillis())
        val started = lastLine.get()
        val watchdog = thread(name = "probe-watchdog", isDaemon = true) {
            while (proc.isAlive) {
                val now = System.currentTimeMillis()
                if (now - lastLine.get() > silenceLimitMs() || now - started > TOTAL_LIMIT_MS) {
                    killed = true
                    proc.destroyForcibly()
                    break
                }
                try {
                    Thread.sleep(1000)
                } catch (_: InterruptedException) {
                    break
                }
            }
        }
        try {
            proc.outputStream.close()
            proc.inputStream.bufferedReader(Charsets.ISO_8859_1).useLines { lines ->
                for (l in lines) {
                    lastLine.set(System.currentTimeMillis())
                    parser.accept(l)
                }
            }
        } catch (_: IOException) {
            // Killed or cancelled: the stream simply ends.
        } finally {
            // Cancelled or killed: its exit code is not read, so it is not waited 5 s for (Skip saving logs, 11-10).
            if (!proc.waitFor(if (cancelled || killed) 200L else 5000L, TimeUnit.MILLISECONDS)) proc.destroyForcibly()
            watchdog.interrupt()
            errReader.join(1000)
            process = null
        }
        val exit = if (proc.isAlive) null else runCatching { proc.exitValue() }.getOrNull()
        return End(
            exitCode = if (killed || cancelled) null else exit,
            stderr = synchronized(stderr) { stderr.toString() },
            cancelled = cancelled,
            killed = killed,
            error = null,
        )
    }

    companion object {
        /** Hard cap for one run (the longest entry is 300 s; a full run takes about a minute). */
        const val TOTAL_LIMIT_MS = 20 * 60 * 1000L

        /** Paths passed through `su -c` are the app's own and need no quoting. */
        private val SAFE_PATH = Regex("^/[A-Za-z0-9._/-]+$")
    }
}
