package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.util.concurrent.Executors

/** What the long copies share: the screen's updates, reading ahead, hashing beside the copy. */
class TransferTest {
    @Test
    fun theScreenHearsOfTheBytesFourTimesASecondAtMost() {
        var now = 1000L
        val meter = ByteMeter({ now }, updateMs = 250, estimateMs = 5000)
        val total = 10_000L * (1 shl 20)
        var samples = 0
        // A buffer every millisecond for ten seconds, as a fast copy sends them.
        for (i in 1..10_000) {
            now++
            if (meter.tick(i.toLong() shl 20, total) != null) samples++
        }
        assertTrue("$samples updates in 10 s", samples in 38..41)
        // The first count is shown at once, and a forced one in any case.
        val fresh = ByteMeter({ now })
        assertNotNull(fresh.tick(0, 100))
        assertNull(fresh.tick(1, 100))
        assertNotNull(fresh.tick(2, 100, force = true))
    }

    @Test
    fun theSpeedAndTheTimeLeftComeFromTheByteFlow() {
        var now = 0L
        val meter = ByteMeter({ now }, updateMs = 250, estimateMs = 5000)
        val total = 100_000_000_000L
        var last: ByteMeter.Sample? = null
        // 400 MB/s for eight seconds.
        for (ms in 0..8000 step 10) {
            now = ms.toLong()
            meter.tick(ms * 400_000L, total)?.let { last = it }
            if (ms == 3000) assertNull("no time left before it is measured", last!!.etaSeconds)
        }
        val s = last!!
        assertEquals(400_000_000.0, s.bytesPerSecond.toDouble(), 4_000_000.0)
        assertEquals((total - s.done) / 400_000_000.0, s.etaSeconds!!.toDouble(), 3.0)
        assertEquals("400 MB/s", ByteMeter.speed(s.bytesPerSecond))
        assertNull(ByteMeter.speed(0))
        assertEquals("less than a minute left", ByteMeter.left(40))
        assertEquals("about 3 min left", ByteMeter.left(170))
        meter.reset()
        assertEquals(0L, meter.tick(0, total)!!.bytesPerSecond)
    }

    private fun bytes(n: Int) = ByteArray(n) { (it * 7 + it / 251).toByte() }

    @Test
    fun readingAheadGivesTheSameBytesInAnyReadSize() {
        val data = bytes(1_000_003)
        for (buffer in listOf(1, 4096, 300_000, 4 shl 20)) {
            // A source that gives odd amounts, as a decompressor does.
            val source = object : ByteArrayInputStream(data) {
                override fun read(b: ByteArray, off: Int, len: Int): Int = super.read(b, off, minOf(len, 1237))
            }
            ReadAhead(source, bufferBytes = maxOf(buffer, 16), buffers = 2).use { r ->
                val out = ByteArrayOutputStream()
                val buf = ByteArray(77_777)
                while (true) {
                    val n = r.read(buf, 0, minOf(buf.size, 1 + out.size() % 5000))
                    if (n < 0) break
                    out.write(buf, 0, n)
                }
                assertTrue("buffer $buffer", out.toByteArray().contentEquals(data))
                assertEquals(-1, r.read(buf))
            }
        }
    }

    @Test
    fun anErrorOfTheSourceArrivesWhereItHappenedAndTheSourceIsClosedByItsReader() {
        val data = bytes(200_000)
        var closedBy: String? = null
        val source = object : InputStream() {
            var at = 0
            override fun read(): Int = throw IOException("whole buffers only")

            override fun read(b: ByteArray, off: Int, len: Int): Int {
                if (at >= 150_000) throw IOException("the frame is damaged")
                val n = minOf(len, 150_000 - at, 999)
                data.copyInto(b, off, at, at + n)
                at += n
                return n
            }

            override fun close() {
                closedBy = Thread.currentThread().name
            }
        }
        val r = ReadAhead(source, bufferBytes = 4096, buffers = 2, name = "ahead")
        val got = ByteArrayOutputStream()
        val e = runCatching {
            val buf = ByteArray(10_000)
            while (true) {
                val n = r.read(buf)
                if (n < 0) break
                got.write(buf, 0, n)
            }
        }.exceptionOrNull()
        assertTrue(e is IOException && e.message == "the frame is damaged")
        // Everything read before the error was handed over first (whole buffers of it).
        assertTrue(got.size() in 147_000..150_000)
        assertTrue(got.toByteArray().contentEquals(data.copyOf(got.size())))
        r.close()
        assertEquals("ahead", closedBy)
    }

    @Test
    fun closingEarlyEndsTheReader() {
        val endless = object : InputStream() {
            @Volatile var closed = false
            override fun read(): Int = 0
            override fun read(b: ByteArray, off: Int, len: Int): Int = len
            override fun close() {
                closed = true
            }
        }
        val r = ReadAhead(endless, bufferBytes = 1 shl 16, buffers = 2)
        assertEquals(100, r.read(ByteArray(100)))
        r.close()
        assertTrue(endless.closed)
        assertTrue(runCatching { r.read(ByteArray(1)) }.exceptionOrNull() is IOException)
    }

    @Test
    fun theCopyHashesBesideTheWriteAndGivesTheSameSha256() {
        val pool = Executors.newSingleThreadExecutor()
        try {
            for (n in listOf(0, 1, 4095, 4096, 4097, 100_000)) {
                val data = bytes(n)
                val out = ByteArrayOutputStream()
                var seen = 0L
                val sha = HashedCopy.copy(ByteArrayInputStream(data), out, pool, bufferBytes = 4096) { seen = it }
                assertEquals("$n bytes", Hashes.sha256(data), sha)
                assertTrue(out.toByteArray().contentEquals(data))
                assertEquals(n.toLong(), seen)
            }
            // Without a hasher nothing is hashed here: root's check is the one.
            val out = ByteArrayOutputStream()
            assertNull(HashedCopy.copy(ByteArrayInputStream(bytes(9000)), out, null, bufferBytes = 4096))
            assertEquals(9000, out.size())
            // A stop ends it between buffers.
            var buffers = 0
            val e = runCatching {
                HashedCopy.copy(ByteArrayInputStream(bytes(100_000)), ByteArrayOutputStream(), pool, bufferBytes = 4096, stop = { buffers++ >= 3 })
            }.exceptionOrNull()
            assertTrue(e is IOException && e.message == "stopped")
        } finally {
            pool.shutdown()
        }
    }
}
