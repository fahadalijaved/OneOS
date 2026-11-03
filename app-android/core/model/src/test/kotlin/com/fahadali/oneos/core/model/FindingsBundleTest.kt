package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.zip.ZipFile

class FindingsBundleTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private val fixture = File(System.getProperty("oneos.installdFixture") ?: "../../../switcher/patches/host_installd.txt")
    private val fp = "samsung/q8qxxx/q8q:17/CP2A.260605.016/F976BXXS3AZIJ:user/release-keys"

    private val secrets = listOf(
        "R5CX21ABCDE", "490154203237518", "a4:c3:f0:85:ac:2d", "Alex-Home-5G", "8996601234567890123",
        "420011234567890", "+966501234567", "0551234567", "alex.doe@example.com", "2041A3B5C7D9E1F3",
        "Alex's Keyboard",
    )

    private fun capture(root: File): Pair<List<ProbeResult>, ByteArray> {
        fun put(rel: String, text: String) = File(root, rel).also { it.parentFile.mkdirs() }.writeText(text)
        put(
            "props/getprop.txt",
            """
            [ro.build.fingerprint]: [$fp]
            [ro.product.model]: [SM-F976B]
            [ro.serialno]: [R5CX21ABCDE]
            [ril.imei]: [490154203237518]
            [ro.boot.wifimacaddr]: [a4:c3:f0:85:ac:2d]
            [persist.vendor.wifi.lastssid]: [Alex-Home-5G]
            [ril.iccid.sim1]: [8996601234567890123]
            [ril.imsi]: [420011234567890]
            [ril.msisdn]: [+966501234567]
            [ro.boot.em.did]: [2041A3B5C7D9E1F3]
            """.trimIndent(),
        )
        put("props/key.txt", "ro.build.fingerprint=$fp\nro.build.version.oneui=90000\n")
        put("cpu/cpuinfo.txt", Fixtures.NO_SVE_CPUINFO)
        put("cpu/uname.txt", "Linux localhost 6.12.23-android16 #1 SMP PREEMPT aarch64\n")
        put("selinux/types.txt", ProbeFindings.GENERIC_APP_TYPES.joinToString("\n") { "(type $it" } + "\n(typealias foo\n")
        put("root/manager.txt", "kernelsu ksud 1.0.5\n")
        put("root/id.txt", "uid=0(root) gid=0(root) context=u:r:su:s0\nEnforcing\n")
        put(
            "input/getevent.txt",
            "add device 7: /dev/input/event7\n  name: \"BT keyboard owner alex.doe@example.com 0551234567\"\n" +
                "add device 9: /dev/input/event9\n  name:     \"Alex's Keyboard\"\n",
        )
        put(
            "input/proc_bus_input_devices.txt",
            "I: Bus=0005 Vendor=046d Product=b342 Version=0001\nN: Name=\"Alex's Keyboard\"\nH: Handlers=kbd event9\n\n",
        )
        put("installd/jars.txt", "28190726 ${"d".repeat(64)}  /system/framework/services.jar\n")
        // A system binary with bytes that look like a serial: copied unchanged (not personal data).
        val dex = ByteArray(4096) { (it % 251).toByte() }
        File(root, "installd/system_framework_services.jar").mkdirs()
        File(root, "installd/system_framework_services.jar/classes.dex").writeBytes(dex)

        fun ok(id: String, vararg files: String) = ProbeResult(
            id, ProbeStatus.OK, 0,
            files.map { CapturedFile(it, "-", File(root, it).length(), Hashes.sha256(File(root, it)), 0) },
            emptyList(), 25,
        )
        val results = listOf(
            ok("build.getprop", "props/getprop.txt"),
            ok("cpu.cpuinfo", "cpu/cpuinfo.txt"),
            ok("installd.dex", "installd/system_framework_services.jar/classes.dex"),
            ProbeResult("storage.stage", ProbeStatus.NOT_PRESENT, 3, emptyList(), emptyList(), 5),
            ProbeResult("display.sf", ProbeStatus.TIMEOUT, 124, emptyList(), emptyList(), 20_000),
        )
        return results to dex
    }

    @Test
    fun bundleIsRedactedCompleteAndHashed() {
        val cap = tmp.newFolder("capture")
        val (results, dex) = capture(cap)
        val methods = InstalldTableFormat.parseLegacy(fixture.readText())
        val input = FindingsInput(
            app = AppInfo("com.fahadali.oneos", "0.2.0-probe", 2, "OneOS"),
            generatedAt = "2026-10-22T15:10:31+03:00",
            date = "2026-10-22",
            facts = Fixtures.facts(cpu = null, root = RootSignals(listOf("me.weishu.kernelsu"), probe = SuProbeResult(SuState.GRANTED, 0, "u:r:su:s0", "uid=0"))),
            commands = ProbeCommandList.parse(
                "#== G\n#: a\nrun build.getprop 30 props/getprop.txt 'getprop'\n#: b\nrun cpu.cpuinfo 10 cpu/cpuinfo.txt 'cat /proc/cpuinfo'\n" +
                    "#: c\nfiles installd.dex 300 installd 'true'\n#: d\nrun storage.stage 10 storage/s.txt 'true'\n" +
                    "#: e\nrun display.sf 20 display/sf.txt 'true'\n#: f\nrun hal.services 20 hal/s.txt 'true'\n",
            ),
            runnerSha256 = "1".repeat(64),
            commandsSha256 = "2".repeat(64),
            stream = ProbeStreamOutcome(1, true, null, results, 0),
            installd = InstalldDerivation(
                methods, "/system/framework/services.jar", "classes.dex", "d".repeat(64),
                listOf("installd/system_framework_services.jar/classes.dex"), null,
            ),
        )
        val out = tmp.newFolder("findings")
        val r = FindingsBuilder(Redactor("bundle".toByteArray())).build(input, cap, out)

        assertEquals("findings-SM-F976B-2026-10-22", r.name)
        assertEquals(File(out, "findings-SM-F976B-2026-10-22.zip"), r.zip)
        assertTrue(r.zip.isFile)

        ZipFile(r.zip).use { z ->
            val names = z.entries().toList().map { it.name }
            val expected = listOf(
                "report.json", "summary.txt", "redaction.txt", "props/getprop.txt", "props/key.txt", "cpu/cpuinfo.txt",
                "installd/table.txt", "installd/host_installd.txt", "installd/system_framework_services.jar/classes.dex",
                "input/getevent.txt",
            ).map { "findings-SM-F976B-2026-10-22/$it" }
            assertTrue(names.toString(), names.containsAll(expected))
            assertEquals("findings-SM-F976B-2026-10-22/report.json", names.first())
            for (e in z.entries()) {
                val text = z.getInputStream(e).readBytes().toString(Charsets.ISO_8859_1)
                for (s in secrets) assertFalse("${e.name} leaks $s", text.contains(s))
            }
            val dexEntry = z.getEntry("findings-SM-F976B-2026-10-22/installd/system_framework_services.jar/classes.dex")
            assertTrue(dex.contentEquals(z.getInputStream(dexEntry).readBytes()))
        }

        // Every file but report.json is listed with its real SHA-256.
        val report = File(r.folder, "report.json").readText()
        for (f in r.files.filter { it.path != "report.json" }) {
            assertEquals(Hashes.sha256(File(r.folder, f.path)), f.sha256)
            assertTrue(report.contains("\"sha256\": \"${f.sha256}\""))
        }
        assertTrue(report.contains("\"schema\": \"oneos.findings/1\""))
        assertTrue(report.contains("\"verdict\": \"WARN\""))
        assertTrue(report.contains("\"version\": \"0.2.0-probe\""))
        assertTrue(report.contains("\"versionCode\": 2"))
        assertTrue(report.contains("\"id\": \"${CpuRules.ID_APP_FEATURES}\""))
        assertTrue(report.contains("\"status\": \"timed out\""))
        assertTrue(report.contains("\"status\": \"not run\""))

        // Verdict: the CPU from the root capture (the app could not read it) lacks SVE2/SME.
        assertEquals(Level.WARN, r.report.find(CpuRules.ID_APP_FEATURES)?.level)
        assertEquals(Level.OK, r.report.find("installd-table")?.level)
        assertEquals(Level.OK, r.report.find("selinux-types")?.level)
        assertEquals(Level.INFO, r.report.find("probes-incomplete")?.level)
        assertEquals(null, r.report.find("stage-present"))

        val summary = File(r.folder, "summary.txt").readText()
        assertTrue(summary.contains("Verdict:  Warning"))
        // The Fold's first image (0.4.38: the Find N6 global build) needs no SVE2 or SME itself, only some apps.
        assertTrue(summary.contains("Some app and media features may crash"))
        assertTrue(summary.contains("installd: 85 methods from /system/framework/services.jar!classes.dex"))
        assertTrue(summary.contains("timed out"))

        val table = File(r.folder, "installd/table.txt").readText()
        assertEquals(emptyList<String>(), InstalldTableFormat.validate(table, fp))

        assertTrue(r.redaction.total >= 10)
        assertTrue(File(r.folder, "redaction.txt").readText().contains("ro.serialno"))
        assertTrue(File(r.folder, "props/getprop.txt").readText().contains("[ro.product.model]: [SM-F976B]"))
    }

    @Test
    fun aRebuildReplacesTheOldBundle() {
        val cap = tmp.newFolder("capture")
        val (results, _) = capture(cap)
        val input = FindingsInput(
            app = AppInfo("com.fahadali.oneos", "0.2.0-probe", 2, "OneOS"),
            generatedAt = "2026-10-22T15:10:31+03:00",
            date = "2026-10-22",
            facts = null,
            factsError = "SecurityException: test",
            commands = emptyList(),
            runnerSha256 = "1".repeat(64),
            commandsSha256 = "2".repeat(64),
            stream = ProbeStreamOutcome(1, false, null, results, 0),
            installd = InstalldDerivation.failed("IInstalld\$Stub not found"),
        )
        val out = tmp.newFolder("findings")
        val first = FindingsBuilder(Redactor.forBundle()).build(input, cap, out)
        File(first.folder, "stale.txt").writeText("old")
        val second = FindingsBuilder(Redactor.forBundle()).build(input, cap, out)
        assertFalse(File(second.folder, "stale.txt").exists())
        assertEquals(Level.WARN, second.report.find("facts-unread")?.level)
        assertEquals(Level.WARN, second.report.find("installd-unknown")?.level)
        assertEquals(Level.INFO, second.report.find("probe-run-incomplete")?.level)
        assertFalse(File(second.folder, "installd/table.txt").exists())
        assertTrue(second.summary.contains("not derived on the phone"))
    }

    /** The bundle's root finding names the app that ran the tests (OneOS Probe has its own root grant). */
    @Test
    fun theRootFindingNamesTheAppThatRan() {
        val cap = tmp.newFolder("capture")
        val (results, _) = capture(cap)
        val input = FindingsInput(
            app = AppInfo("com.fahadali.oneos.probe", "0.3.4-probe", 8, "OneOS Probe"),
            generatedAt = "2026-10-23T15:10:31+03:00",
            date = "2026-10-23",
            facts = Fixtures.facts(root = RootSignals(listOf("me.weishu.kernelsu"), probe = SuProbeResult(SuState.TIMEOUT, null, null, ""))),
            commands = emptyList(),
            runnerSha256 = "1".repeat(64),
            commandsSha256 = "2".repeat(64),
            stream = ProbeStreamOutcome(1, false, null, results, 0),
            installd = InstalldDerivation.failed("IInstalld\$Stub not found"),
        )
        val r = FindingsBuilder(Redactor.forBundle()).build(input, cap, tmp.newFolder("findings"))
        assertEquals("Allow OneOS Probe in your root manager, then check root again.", r.report.find("root-timeout")?.detail)
    }
}
