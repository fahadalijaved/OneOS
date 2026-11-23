package com.fahadali.oneos.core.model

import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ExecutorService
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/**
 * What the long copies of this app share (setting up an Android system, importing
 * a OneiOS package): how often the screen hears of the bytes, the speed and the
 * time left; reading ahead on a thread of its own; hashing beside the copy.
 */

/**
 * The byte count of a long copy, for the screen: a [Sample] at most every
 * [updateMs] however often [tick] is called, with the speed (a moving average
 * over samples at least [sampleMs] apart) and, after [estimateMs] of byte flow,
 * the time left.
 *
 * One update per buffer kept a core busy redrawing the setup screen and slowed
 * the 0.4.41 download to a sixth of the phone's speed; the OneiOS import of
 * 0.4.76 sent one per MiB, each rebuilding its whole screen.
 */
class ByteMeter(
    private val clock: () -> Long,
    private val updateMs: Long = 250,
    private val estimateMs: Long = 30_000,
    private val sampleMs: Long = 1000,
) {
    data class Sample(
        val done: Long,
        val total: Long,
        /** 0 = not measured yet. */
        val bytesPerSecond: Long,
        /** Null = still estimating. */
        val etaSeconds: Int?,
    )

    private var startMs = -1L
    private var lastMs = 0L
    private var lastBytes = 0L
    private var bps = 0.0
    private var lastUpdateMs = -1L

    @Synchronized
    fun reset() {
        startMs = -1
        lastMs = 0
        lastBytes = 0
        bps = 0.0
        lastUpdateMs = -1
    }

    /** Takes every byte count; answers the ones the screen should hear of ([force]: this one in any case). */
    @Synchronized
    fun tick(done: Long, total: Long, force: Boolean = false): Sample? {
        val now = clock()
        var eta: Int? = null
        if (startMs < 0) {
            startMs = now
            lastMs = now
            lastBytes = done
        } else {
            val dt = now - lastMs
            if (dt >= sampleMs) {
                val sample = (done - lastBytes).coerceAtLeast(0) * 1000.0 / dt
                bps = if (bps == 0.0) sample else bps * 0.8 + sample * 0.2
                lastMs = now
                lastBytes = done
            }
            if (now - startMs >= estimateMs && bps > 0.0) eta = ((total - done).coerceAtLeast(0) / bps).toInt()
        }
        if (!force && lastUpdateMs >= 0 && now - lastUpdateMs < updateMs) return null
        lastUpdateMs = now
        return Sample(done, total, bps.toLong(), eta)
    }

    companion object {
        /** "412 MB/s", or null while not measured. */
        fun speed(bytesPerSecond: Long): String? = if (bytesPerSecond <= 0) null else "${Units.bytes(bytesPerSecond)}/s"

        /** "less than a minute left", "about 3 min left". */
        fun left(etaSeconds: Int): String = if (etaSeconds < 60) "less than a minute left" else "about ${(etaSeconds + 59) / 60} min left"
    }
}

/**
 * [source] read on a thread of its own, [buffers] buffers of [bufferBytes]
 * ahead of the reader: a decompressor under it works while the reader writes
 * (or waits for root), instead of taking turns with it on one thread.
 *
 * Only the reading thread touches [source], and it closes it: a native
 * decompressor is never freed under a read. An error of [source] reaches the
 * reader at the place in the stream where it happened.
 */
class ReadAhead(
    private val source: InputStream,
    private val bufferBytes: Int = 4 shl 20,
    buffers: Int = 2,
    name: String = "read-ahead",
) : InputStream() {
    private class Chunk(val data: ByteArray, val length: Int, val error: Throwable? = null)

    private val full = ArrayBlockingQueue<Chunk>(buffers)
    private val free = ArrayBlockingQueue<ByteArray>(buffers + 2)

    @Volatile private var closed = false
    private var current: Chunk? = null
    private var at = 0
    private var ended = false

    private val thread = Thread({
        try {
            var made = 0
            while (!closed) {
                val buf = free.poll() ?: if (made < buffers + 2) ByteArray(bufferBytes).also { made++ } else free.take()
                var n = 0
                var end = false
                while (n < buf.size) {
                    val r = source.read(buf, n, buf.size - n)
                    if (r < 0) {
                        end = true
                        break
                    }
                    n += r
                }
                if (n > 0) full.put(Chunk(buf, n))
                if (end) {
                    full.put(Chunk(EMPTY, -1))
                    break
                }
            }
        } catch (_: InterruptedException) {
            // Closed while waiting for room.
        } catch (e: Throwable) {
            runCatching { full.put(Chunk(EMPTY, -1, e)) }
        } finally {
            runCatching { source.close() }
        }
    }, name).apply {
        isDaemon = true
        start()
    }

    override fun read(): Int {
        val b = ByteArray(1)
        return if (read(b, 0, 1) < 0) -1 else b[0].toInt() and 0xff
    }

    override fun read(b: ByteArray, off: Int, len: Int): Int {
        if (len == 0) return 0
        if (closed) throw IOException("the stream is closed")
        var c = current
        if (c == null || at >= c.length) {
            if (ended) return -1
            if (c != null) free.offer(c.data)
            c = try {
                full.take()
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                throw IOException("interrupted")
            }
            current = c
            at = 0
            if (c.length < 0) {
                ended = true
                when (val e = c.error) {
                    null -> return -1
                    is IOException -> throw e
                    else -> throw IOException("${e.javaClass.simpleName}: ${e.message}", e)
                }
            }
        }
        val n = minOf(len, c.length - at)
        System.arraycopy(c.data, at, b, off, n)
        at += n
        return n
    }

    override fun close() {
        if (closed) return
        closed = true
        thread.interrupt()
        // The reading thread closes the source when its read returns.
        full.clear()
        runCatching { thread.join(10_000) }
    }

    private companion object {
        val EMPTY = ByteArray(0)
    }
}

/** A copy to a slow place (root's stdin) whose SHA-256 is worked out on another thread while each buffer is written. */
object HashedCopy {
    const val BUFFER_BYTES = 4 shl 20

    /**
     * Copies [input] to its end into [out] and returns the SHA-256 of what was
     * copied (null without a [hasher]: nothing is hashed here). [onBytes] gets
     * the bytes copied so far after each buffer; [stop] ends the copy with an
     * IOException("stopped").
     */
    fun copy(
        input: InputStream,
        out: OutputStream,
        hasher: ExecutorService?,
        bufferBytes: Int = BUFFER_BYTES,
        stop: () -> Boolean = { false },
        onBytes: (Long) -> Unit = {},
    ): String? {
        val md = if (hasher != null) MessageDigest.getInstance("SHA-256") else null
        // Two buffers in turn: the one being hashed is never the one being filled.
        val bufs = arrayOf(ByteArray(bufferBytes), ByteArray(bufferBytes))
        val busy = arrayOfNulls<Future<*>>(2)
        var which = 0
        var copied = 0L
        fun settle(f: Future<*>?) {
            try {
                f?.get(10, TimeUnit.MINUTES)
            } catch (e: Exception) {
                throw IOException("the SHA-256 could not be worked out: ${e.message}", e)
            }
        }
        try {
            while (true) {
                if (stop()) throw IOException("stopped")
                settle(busy[which])
                busy[which] = null
                val buf = bufs[which]
                var n = 0
                // Whole buffers: fewer, larger writes, and one hashing task for each.
                while (n < buf.size) {
                    val r = input.read(buf, n, buf.size - n)
                    if (r < 0) break
                    n += r
                }
                if (n == 0) break
                if (md != null) busy[which] = hasher!!.submit { md.update(buf, 0, n) }
                out.write(buf, 0, n)
                copied += n
                onBytes(copied)
                which = 1 - which
                if (n < buf.size) break
            }
        } finally {
            // Also on a failure: no task of this copy is left reading its buffers.
            busy.forEach { f -> runCatching { f?.get(10, TimeUnit.MINUTES) } }
        }
        return md?.let { Hashes.hex(it.digest()) }
    }
}
