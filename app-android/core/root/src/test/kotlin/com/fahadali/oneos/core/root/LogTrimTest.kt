package com.fahadali.oneos.core.root

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.time.LocalDateTime
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

class LogTrimTest {
    @get:Rule
    val tmp = TemporaryFolder()

    // An earlier session's block, then this one's (S25 Ultra 26ea59af's shape).
    private val autoReturn = """
        === OneOS session 2026-10-28 09:00:00 epoch 1 boot x app 1 profile s-ultra-8750 return max 600s black 150s keys 1 ===
        Wed Oct 28 09:05:00 +03 2026 Volume Up + Volume Down held 3 s
        === OneOS session 2026-10-29 10:52:15 epoch 1793260335 boot y app 1 profile s-ultra-8750 return max 600s black 150s keys 1 ===
        Thu Oct 29 10:53:08 +03 2026 display diagnostics saved in /data/local/tmp/oneos/diag_20
        Thu Oct 29 10:53:58 +03 2026 guest zygote/system_server gone for 30s after 40s, returning to One UI
        === [1/4] Terminating Container Supervision & Zygote ===
        10:54:36 In-place return (baseline: oneos-baseline 1793260342)
        10:56:28 One UI restored in place (Enforcing).
    """.trimIndent()

    private fun at(s: String) = LocalDateTime.parse(s)

    @Test
    fun windowsAroundTheStartAndTheReturn() {
        val w = LogTrim.windows(autoReturn, null)!!
        assertEquals(2, w.size)
        // Both stop 30 s after the watcher's return line: then One UI starts again.
        assertEquals(LogTrim.Window(at("2026-10-29T10:51:45"), at("2026-10-29T10:54:28")), w[0])
        assertEquals(LogTrim.Window(at("2026-10-29T10:51:58"), at("2026-10-29T10:54:28")), w[1])
        // A long session: the first 5 minutes, and 2 minutes before the return.
        val long = "=== OneOS session 2026-10-29 10:00:00 epoch 1 ===\n" +
            "Thu Oct 29 10:40:00 +03 2026 guest zygote/system_server gone for 30s after 2400s, returning to One UI\n"
        assertEquals(
            listOf(LogTrim.Window(at("2026-10-29T09:59:30"), at("2026-10-29T10:05:00")), LogTrim.Window(at("2026-10-29T10:38:00"), at("2026-10-29T10:40:30"))),
            LogTrim.windows(long, null),
        )
    }

    @Test
    fun noReturnLoggedEndsAtTheLastLoggedLine() {
        // A force restart (S23 Ultra 99ef8224): only the header and diagnostics.
        val log = "=== OneOS session 2026-10-29 11:30:04 epoch 1 ===\n"
        val w = LogTrim.windows(log, at("2026-10-29T11:31:18"))!!
        assertEquals(LogTrim.Window(at("2026-10-29T11:29:18"), at("2026-10-29T11:31:48")), w[1])
        assertEquals(1, LogTrim.windows(log, null)!!.size)
        assertNull(LogTrim.windows("no header here\n", null))
    }

    @Test
    fun aReturnPastMidnightIsTheNextDay() {
        val log = "=== OneOS session 2026-10-29 23:58:00 epoch 1 ===\n" +
            "Fri Oct 30 00:03:00 +03 2026 black screen after 300s (surfaceflinger: ), returning to One UI\n" +
            "00:04:10 One UI restored in place (Enforcing).\n"
        val w = LogTrim.windows(log, null)!!
        assertEquals(LogTrim.Window(at("2026-10-30T00:01:00"), at("2026-10-30T00:03:30")), w[1])
    }

    @Test
    fun logcatLinesByTime() {
        val near = at("2026-10-29T10:52:15")
        val w = LogTrim.windows(autoReturn, null)!!
        assertEquals(at("2026-10-29T10:52:50"), LogTrim.lineTime("10-29 10:52:50.181  2200  2200 D AndroidRuntime: >>>>>> START", near))
        assertTrue(LogTrim.keep("10-29 10:52:56.899  2799  2799 E AndroidRuntime: *** FATAL EXCEPTION IN SYSTEM PROCESS: main", w, near))
        // One UI before the switch, and long after the return: cut.
        assertFalse(LogTrim.keep("10-29 10:46:04.478  3094  3708 I WindowManager: Relayout", w, near))
        assertFalse(LogTrim.keep("10-29 11:30:00.000  1  1 I x: y", w, near))
        assertTrue(LogTrim.keep("--------- beginning of crash", w, near))
        assertFalse(LogTrim.keep("a line without a time", w, near))
        // New Year: a December line of a January session is last year's.
        assertEquals(at("2026-12-31T23:59:59"), LogTrim.lineTime("12-31 23:59:59.000 1 1 I a: b", at("2027-01-01T00:00:10")))
    }

    @Test
    fun shortenKeepsTheWindowsAndEveryOtherFileWhole() {
        val dir = "oneos-logs-26ea59af970a0766"
        val full = tmp.newFile("full.zip")
        val capture = buildString {
            append("--------- beginning of main\n")
            append("10-29 10:46:04.478  3094  3708 I WindowManager: before the switch\n")
            append("10-29 10:52:56.899  2799  2799 E AndroidRuntime: *** FATAL EXCEPTION IN SYSTEM PROCESS: main\n")
            append("10-29 11:30:00.000  1  1 I late: after the return\n")
        }
        ZipOutputStream(full.outputStream()).use { z ->
            for ((name, text) in listOf(
                "$dir/summary.txt" to "OneOS session logs\n",
                "$dir/stage/data_local_tmp_oneos_auto_return.log" to autoReturn,
                "$dir/capture/data_local_tmp_oneos_logs_boot.log" to capture,
                "$dir/boot/last_kmsg.txt" to "10-29 09:00:00.000 kept whole\n",
            )) {
                z.putNextEntry(ZipEntry(name))
                z.write(text.toByteArray())
                z.closeEntry()
            }
        }
        val short = File(tmp.root, "short.zip")
        assertTrue(LogTrim.shorten(full, short))
        ZipFile(short).use { z ->
            fun text(n: String) = z.getInputStream(z.getEntry("$dir/$n")).bufferedReader().readText()
            assertEquals(
                "--------- beginning of main\n10-29 10:52:56.899  2799  2799 E AndroidRuntime: *** FATAL EXCEPTION IN SYSTEM PROCESS: main\n",
                text("capture/data_local_tmp_oneos_logs_boot.log"),
            )
            assertEquals("10-29 09:00:00.000 kept whole\n", text("boot/last_kmsg.txt"))
            assertEquals(autoReturn, text("stage/data_local_tmp_oneos_auto_return.log"))
            assertTrue(text(LogTrim.TRIM_NOTE).contains("capture/data_local_tmp_oneos_logs_boot.log: 2 of 4 lines"))
        }
        // No session header: nothing to cut by, the whole bundle is sent.
        val bare = tmp.newFile("bare.zip")
        ZipOutputStream(bare.outputStream()).use { z ->
            z.putNextEntry(ZipEntry("$dir/summary.txt"))
            z.write("x".toByteArray())
            z.closeEntry()
        }
        assertFalse(LogTrim.shorten(bare, File(tmp.root, "bare-short.zip")))
    }

    /** A real bundle, when one is named: how much the short log keeps (prints only). */
    @Test
    fun realBundleWhenGiven() {
        val path = System.getenv("ONEOS_TRIM_SAMPLE") ?: return
        val out = File(tmp.root, "sample-short.zip")
        assertTrue(LogTrim.shorten(File(path), out))
        ZipFile(out).use { z -> println(z.getInputStream(z.entries().toList().first { it.name.endsWith(LogTrim.TRIM_NOTE) }).bufferedReader().readText()) }
        println("full ${File(path).length()} bytes, short ${out.length()} bytes")
    }
}
