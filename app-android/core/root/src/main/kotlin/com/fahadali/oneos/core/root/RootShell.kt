package com.fahadali.oneos.core.root

import java.io.FilterOutputStream
import java.io.IOException
import java.io.OutputStream
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference
import kotlin.concurrent.thread

/**
 * One `su -c <command>` whose stdin the app writes while it reads stdout line
 * by line (AA11; [RootProbeRunner] closes stdin at once). The 10 GB image
 * goes through here: the app streams it from the picked file through
 * GZIPInputStream into the root script's `receive`, which writes it with
 * `head -c` and checks it itself.
 *
 * Blocks until su ends; call it off the main thread. A run with no output and
 * no stdin progress for longer than the silence limit, or longer than the
 * total limit, is killed. When [Feed] fails for any reason other than root
 * closing the pipe, su is killed, so root never takes a short stream for a
 * whole one (its size and hash checks would refuse it anyway).
 */
class RootShell(
    private val command: String,
    /** What runs [command]: `su -c` on the phone; a plain shell in the tests, which run the same code against a fake root. */
    private val launch: List<String> = listOf("su", "-c"),
    private val environment: Map<String, String> = emptyMap(),
) {
    /** Writes stdin; returns normally when everything is written (RootShell closes the stream). */
    fun interface Feed {
        fun write(out: OutputStream)
    }

    data class End(
        /** Exit code of su; null when it never started or was killed. */
        val exitCode: Int?,
        /** The last few kB su printed on stderr. */
        val stderr: String,
        val cancelled: Boolean,
        /** Killed because it went silent, ran too long, or the feed failed. */
        val killed: Boolean,
        /** Could not start su, or the feed failed (its message). */
        val error: String?,
        /** Bytes written to stdin. */
        val written: Long,
    )

    @Volatile private var process: Process? = null

    @Volatile private var cancelled = false

    @Volatile private var killed = false

    fun cancel() {
        cancelled = true
        process?.destroyForcibly()
    }

    fun run(feed: Feed?, onLine: (String) -> Unit, silenceLimitMs: () -> Long, totalLimitMs: Long): End {
        if (cancelled) return End(null, "", cancelled = true, killed = false, error = null, written = 0)
        val proc = try {
            ProcessBuilder(launch + command).apply { environment().putAll(environment) }.start()
        } catch (e: IOException) {
            return End(null, "", cancelled = false, killed = false, error = "su could not be started: ${e.message}", written = 0)
        }
        process = proc
        val activity = AtomicLong(System.currentTimeMillis())
        val started = activity.get()
        val written = AtomicLong(0)
        val stderr = StringBuilder()
        val feedError = AtomicReference<String?>(null)

        val errReader = thread(name = "root-stderr", isDaemon = true) {
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
        val writer = thread(name = "root-stdin", isDaemon = true) {
            val counting = object : FilterOutputStream(proc.outputStream) {
                override fun write(b: ByteArray, off: Int, len: Int) {
                    try {
                        out.write(b, off, len)
                    } catch (e: IOException) {
                        throw PipeClosed(e)
                    }
                    written.addAndGet(len.toLong())
                    activity.set(System.currentTimeMillis())
                }

                override fun write(b: Int) {
                    write(byteArrayOf(b.toByte()), 0, 1)
                }

                override fun flush() {
                    try {
                        out.flush()
                    } catch (e: IOException) {
                        throw PipeClosed(e)
                    }
                }
            }
            try {
                feed?.write(counting)
                counting.flush()
            } catch (_: PipeClosed) {
                // Root closed stdin (it has what it needs, or it refused): its
                // reply says what happened.
            } catch (e: Throwable) {
                // The source failed (the picked file, an asset): never let root
                // take what arrived so far for the whole file.
                feedError.set("${e.javaClass.simpleName}: ${e.message}")
                killed = true
                proc.destroyForcibly()
            } finally {
                runCatching { proc.outputStream.close() }
            }
        }
        val watchdog = thread(name = "root-watchdog", isDaemon = true) {
            while (proc.isAlive) {
                val now = System.currentTimeMillis()
                if (now - activity.get() > silenceLimitMs() || now - started > totalLimitMs) {
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
            proc.inputStream.bufferedReader(Charsets.UTF_8).useLines { lines ->
                for (l in lines) {
                    activity.set(System.currentTimeMillis())
                    onLine(l)
                }
            }
        } catch (_: IOException) {
            // Killed or cancelled: the stream simply ends.
        } finally {
            if (!proc.waitFor(10, TimeUnit.SECONDS)) {
                killed = true
                proc.destroyForcibly()
            }
            writer.join(5000)
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
            error = feedError.get(),
            written = written.get(),
        )
    }

    /** Writing to su's stdin failed: root closed it or ended. */
    private class PipeClosed(cause: IOException) : IOException(cause.message, cause)
}
