package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.AppInfo
import com.fahadali.oneos.core.model.Redactor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files
import java.util.zip.ZipFile

class SessionLogsTest {
    private fun redactor() = Redactor(ByteArray(16) { it.toByte() })

    private fun redact(text: String, r: Redactor = redactor(), stats: LogStats = LogStats(), chunk: Int = 7): String {
        val out = ByteArrayOutputStream()
        RedactingOutputStream(out, "logcat/boot.log", r, stats, ByteArray(16)).use { s ->
            val b = text.toByteArray()
            var i = 0
            while (i < b.size) {
                val n = minOf(chunk, b.size - i)
                s.write(b, i, n)
                i += n
            }
        }
        return out.toString("UTF-8")
    }

    @Test
    fun personalTagsAreDroppedWhole() {
        val text = """
            10-22 13:20:52.343   470   470 I GlobalActionsComponent: power menu shown
            10-22 13:20:52.400  1234  1250 D SmsProvider: insert sms from +966501234567 body=hello
            10-22 13:20:52.401  1234  1250 I SIPMSG[0]: INVITE sip:+15551234567@ims
            10-22 13:20:52.402  1234  1250 I wpa_supplicant: wlan0: CTRL-EVENT-CONNECTED - Connection to aa:bb:cc:dd:ee:ff
            10-22 13:20:52.403  1234  1250 I OplusGeofenceManager: fence at 52.5163,13.3777
            10-22 13:20:52.404  1234  1250 I HomeGetUpcomingContactsUseCase: Mom
            --------- beginning of main
        """.trimIndent() + "\n"
        val stats = LogStats()
        val out = redact(text, stats = stats)
        assertEquals(listOf("10-22 13:20:52.343   470   470 I GlobalActionsComponent: power menu shown", "--------- beginning of main"), out.lines().filter { it.isNotEmpty() })
        assertEquals(5, stats.droppedLines)
        assertEquals(7, stats.lines)
        assertEquals(1L, stats.droppedByTag["SmsProvider"])
    }

    @Test
    fun valuesAreMaskedLineByLineAcrossChunks() {
        val r = redactor()
        val ssids = LogRules.ssids(
            "name=\"SSID\">&quot;Alex Home&quot;\nname=\"SSID\">&quot;Cafe &amp; Co&quot;\nname=\"WifiSsid\">\"MyHotspot5\"\n",
        )
        assertEquals(listOf("Alex Home", "Cafe & Co", "MyHotspot5"), ssids)
        r.learnNames(com.fahadali.oneos.core.model.RedactionKind.SSID, ssids)
        val text = "10-22 13:00:00.000 1 2 I WifiService: connected to Alex Home, signal good\n" +
            "10-22 13:00:01.000 1 2 I Gallery: saved /storage/emulated/0/DCIM/Camera/IMG_20261022.jpg\n" +
            "10-22 13:00:02.000 1 2 I Telephony: imsi 420011234567890 iccid 8996601234567890123\n" +
            "10-22 13:00:03.000 1 2 I Account: Account {name=someone@example.com, type=com.google}\n" +
            "no newline at the end, a MAC a4:c3:f0:11:22:33"
        for (chunk in listOf(1, 5, 64, 4096)) {
            val stats = LogStats()
            val out = redact(text, r, stats, chunk)
            assertFalse(out, out.contains("Alex Home"))
            assertFalse(out.contains("IMG_20261022.jpg"))
            assertTrue(out.contains("/storage/emulated/0/DCIM/Camera/<file:"))
            assertFalse(out.contains("420011234567890"))
            assertFalse(out.contains("8996601234567890123"))
            assertFalse(out.contains("someone@example.com"))
            assertFalse(out.contains("a4:c3:f0:11:22:33"))
            assertTrue(out.endsWith("\n"))
            assertEquals(5, out.lines().count { it.isNotEmpty() })
            assertEquals(1, stats.maskedFiles)
        }
    }

    @Test
    fun longLinesAreCut() {
        val stats = LogStats()
        val out = redact("x".repeat(RedactingOutputStream.MAX_LINE * 2 + 10) + "\nend\n", stats = stats, chunk = 1000)
        assertEquals(2, stats.cutLines)
        assertEquals(listOf(RedactingOutputStream.MAX_LINE, RedactingOutputStream.MAX_LINE, 10, 3), out.lines().filter { it.isNotEmpty() }.map { it.length })
    }

    @Test
    fun recordingsAndScreenshotsAreNeverCollected() {
        for (n in listOf("oneos_rec_1.mp4", "shot_4630946379103915412.png", "fold_1.png", "x.JPG")) assertTrue(n, LogRules.neverCollected(n))
        for (n in listOf("boot.log.01", "surfaceflinger.txt", "screencap.err", "auto_return.log")) assertFalse(n, LogRules.neverCollected(n))
    }

    // auto_return.log lines as runs 33-35 wrote them (out/logs/run3x/auto_return.log).
    private val header = "=== OneOS session 2026-10-22 16:34:00 epoch 1792679640 boot b app 1 profile f8u return max 600s black 150s keys 1 ==="

    @Test
    fun outcomes() {
        fun o(ret: String?, app: String? = null, reason: String? = "reboot,oneos-return") = ReturnOutcomes.parse(ret, app, reason)
        val keys = "$header\nThu Oct 22 16:43:59 +03 2026 Volume Up + Volume Down held 3 s\n" +
            "Thu Oct 22 16:44:06 +03 2026 guest requested 'keys:volume-up+down' after 590s, returning to One UI\n" +
            "=== [1/5] Terminating Container Supervision & Zygote ===\n"
        assertEquals(OutcomeKind.USER_RETURN, o(keys).kind)
        assertEquals(590, o(keys).afterSeconds)
        val reboot = "Thu Oct 22 13:20:58 +03 2026 guest requested 'reboot' after 590s, returning to One UI\n"
        assertEquals(OutcomeKind.GUEST_REBOOT, o(reboot).kind)
        val dead = "Thu Oct 22 14:59:55 +03 2026 guest zygote/system_server gone for 30s after 590s, returning to One UI\n"
        assertEquals(OutcomeKind.GUEST_DEAD, o(dead).kind)
        assertEquals(590, o(dead).afterSeconds)
        // Only the newest session counts: an older session's line before the last header is ignored.
        assertEquals(OutcomeKind.USER_RETURN, o(dead + keys).kind)
        assertEquals(OutcomeKind.UNKNOWN, o(keys + header + "\n").kind)
        assertEquals(OutcomeKind.BLACK_SCREEN, o("x black screen after 150s (surfaceflinger: 1), returning to One UI\n").kind)
        val sfGone = o("x black screen after 50s (the guest's surfaceflinger gone for 30s, nothing restarts it), returning to One UI\n")
        assertEquals(OutcomeKind.BLACK_SCREEN, sfGone.kind)
        assertEquals(50, sfGone.afterSeconds)
        assertEquals(OutcomeKind.BOOT_TIMEOUT, o("x guest still not booted after 600s, returning to One UI\n").kind)
        assertEquals(OutcomeKind.GUEST_SHUTDOWN, o("x guest requested 'shutdown,battery' after 100s, returning to One UI\n").kind)
        assertEquals(OutcomeKind.HARD_RESET, o("", reason = "reboot,longkey").kind)
        // takeover_app.log of the launch decides first.
        val launch = "=== OneOS app launch 0123456789abcdef session 2026-10-22 ===\n"
        assertEquals(OutcomeKind.REFUSED, o(keys, launch + "PREFLIGHT REFUSED: no resetprop at the root manager's paths\n").kind)
        assertEquals(OutcomeKind.PREPARE_FAILED, o(null, launch + "ERROR: guest_prepare.sh failed (code 3)! Returning to One UI.\n").kind)
        // A session of 0.3.6, whose script was still called master_prepare.sh.
        assertEquals(OutcomeKind.PREPARE_FAILED, o(null, launch + "ERROR: master_prepare.sh failed (code 3)! Returning to One UI.\n").kind)
        assertEquals(OutcomeKind.DRY_RUN, o(null, launch + "ONEOS_PREPARE_ONLY=1: container prepared and checked, returning to One UI without starting the guest.\n").kind)
        // A refusal of an older launch does not count.
        assertEquals(OutcomeKind.USER_RETURN, o(keys, "=== OneOS app launch a session ===\nPREFLIGHT REFUSED: x\n$launch").kind)
    }

    /** Back to One UI in the guest's OneOS app (its screen or its Quick Settings tile) is its own outcome, not a guest restart. */
    @Test
    fun theInGuestAppReturn() {
        fun o(ret: String) = ReturnOutcomes.parse(ret, null, "reboot,oneos-return")
        val app = "$header\nSat Oct 24 21:04:01 +03 2026 Back to One UI asked in the guest's OneOS app (app)\n" +
            "Sat Oct 24 21:04:10 +03 2026 guest requested 'app:app' after 2520s, returning to One UI\n"
        assertEquals(OutcomeKind.APP_RETURN, o(app).kind)
        assertEquals(2520, o(app).afterSeconds)
        assertEquals(OutcomeKind.APP_RETURN, o("x guest requested 'app:tile' after 60s, returning to One UI\n").kind)
        // A reboot asked in the guest is still a guest restart.
        assertEquals(OutcomeKind.GUEST_REBOOT, o("x guest requested 'reboot,userrequested' after 60s, returning to One UI\n").kind)
        assertEquals("You came back with Back to One UI", OutcomeKind.APP_RETURN.title("Pixel 11 Fold"))
        assertTrue(OutcomeKind.APP_RETURN.good)
        assertTrue(o(app).detail("Pixel 11 Fold").startsWith("You tapped Back to One UI in Pixel 11 Fold after 42 min 0 s"))
    }

    /** The outcome texts name the system they are given, never a fixed one. */
    @Test
    fun outcomeTitlesNameTheSystem() {
        for (k in OutcomeKind.entries) {
            val t = k.title("Pixel 11 Fold")
            val other = k.title("the other system")
            for (text in listOf(t, other, k.label, ReturnOutcome(k, 61, null, null).detail("Pixel 11 Fold"))) {
                assertFalse("$k: $text", Regex("ColorOS|OPPO|Lineage").containsMatchIn(text))
                assertTrue("$k: $text", text.length <= 140)
            }
            assertFalse("$k: $other", other.contains(" the other system") && other.startsWith("the"))
        }
        assertEquals("Pixel 11 Fold didn't finish starting. OneOS brought you back.", OutcomeKind.BOOT_TIMEOUT.title("Pixel 11 Fold"))
        assertEquals("The other system restarted, so OneOS brought you back", OutcomeKind.GUEST_REBOOT.title("the other system"))
        assertEquals("You came back with the volume keys", OutcomeKind.USER_RETURN.title("Pixel 11 Fold"))
    }

    /** The real run logs on the server, when present (out/ is not in git). */
    @Test
    fun realRunLogs() {
        val run34 = File(Shipped.runLogs, "run34/auto_return.log")
        assumeTrue("out/logs not on this machine", run34.isFile)
        val o = ReturnOutcomes.parse(run34.readText(), null, "reboot,oneos-return")
        assertTrue(o.kind == OutcomeKind.USER_RETURN || o.kind == OutcomeKind.GUEST_DEAD)
        assertTrue(o.afterSeconds != null)
    }

    @Test
    fun bundle() {
        val dir = Files.createTempDirectory("oneos-logs").toFile()
        try {
            val folder = File(dir, LogBundle.name("0123456789abcdef")).apply { mkdirs() }
            File(folder, "capture").mkdirs()
            val r = redactor()
            val stats = LogStats()
            RedactingOutputStream(File(folder, "capture/boot.log").outputStream(), "capture/boot.log", r, stats, ByteArray(16)).use {
                it.write("10-22 13:00:00.000 1 2 I X: mail me at someone@example.com\n".toByteArray())
            }
            val outcome = ReturnOutcomes.parse("x guest requested 'reboot' after 61s, returning to One UI\n", null, "reboot,oneos-return")
            val zip = LogBundle.build(
                LogBundleInput(
                    AppInfo("com.fahadali.oneos", "0.3.0", 4, "OneOS"), "0123456789abcdef", "2026-10-23T10:00:00+03:00",
                    "f8u", "coloros17-findn6", "d".repeat(64), dryRun = false, outcome = outcome,
                    listSha256 = "a".repeat(64), runnerSha256 = "b".repeat(64), incomplete = emptyList(), learnedNames = 2,
                ),
                folder, r, stats,
            )
            ZipFile(zip).use { z ->
                val names = z.entries().toList().map { it.name }.sorted()
                assertEquals(
                    listOf("oneos-logs-0123456789abcdef/capture/boot.log", "oneos-logs-0123456789abcdef/redaction.txt", "oneos-logs-0123456789abcdef/report.json", "oneos-logs-0123456789abcdef/summary.txt"),
                    names,
                )
                val report = z.getInputStream(z.getEntry("oneos-logs-0123456789abcdef/report.json")).readBytes().toString(Charsets.UTF_8)
                assertTrue(report.contains("\"schema\": \"oneos.logbundle/1\""))
                assertTrue(report.contains("\"kind\": \"GUEST_REBOOT\""))
                val log = z.getInputStream(z.getEntry("oneos-logs-0123456789abcdef/capture/boot.log")).readBytes().toString(Charsets.UTF_8)
                assertFalse(log.contains("someone@example.com"))
            }
            assertNull(LogRules.tag("not a logcat line"))
        } finally {
            dir.deleteRecursively()
        }
    }
}
