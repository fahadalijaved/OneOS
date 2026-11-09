package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CpuAndVerdictTest {
    private fun CompatReport.level(id: String): Level? = find(id)?.level

    @Test
    fun parsesCoresFeaturesAndIds() {
        val cpu = CpuInfoParser.parse(Fixtures.SM8850_CPUINFO)
        assertEquals(8, cpu.cores.size)
        assertEquals("Qualcomm Technologies, Inc", cpu.hardware)
        // The tested Fold has every reported feature but SME2 and MOPS.
        for (f in CpuRules.REPORTED - setOf("sme2", "mops")) assertTrue(f, cpu.has(f))
        assertFalse(cpu.has("sme2") || cpu.has("mops"))
        assertTrue(cpu.has("SVE2")) // case-insensitive
        assertFalse(cpu.has("sve3"))
        val c0 = cpu.cores[0]
        assertEquals(0, c0.index)
        assertEquals("0x51", c0.implementer)
        assertEquals("0x002", c0.part)
        assertEquals("0x3", c0.variant)
        assertEquals("2", c0.revision)
        assertEquals("Qualcomm 0x002 r3p2", c0.label)
        assertEquals("8 cores: 2 x Qualcomm 0x002 r3p2, 6 x Qualcomm 0x001 r3p2", cpu.summary)
        assertFalse(cpu.heterogeneous)
        assertTrue(CpuRules.missingForColorOs(cpu).isEmpty())
    }

    @Test
    fun featuresAreTheOnesEveryCoreHas() {
        val text = Fixtures.cpuinfo("fp asimd sve sve2 sme mops", cores = 2) +
            Fixtures.cpuinfo("fp asimd sve2 mops", cores = 1).replace("processor\t: 0", "processor\t: 2")
        val cpu = CpuInfoParser.parse(text)
        assertEquals(3, cpu.cores.size)
        assertTrue(cpu.heterogeneous)
        assertEquals(setOf("fp", "asimd", "sve2", "mops"), cpu.features)
        assertEquals(listOf("sme"), CpuRules.missingForColorOs(cpu))
    }

    @Test
    fun armPartNamesAndEmptyInput() {
        val cpu = CpuInfoParser.parse(Fixtures.cpuinfo("fp asimd", cores = 1, implementer = "0x41", parts = listOf("0xd81")))
        assertEquals("Arm Cortex-A720 r3p2", cpu.cores[0].label)
        val empty = CpuInfoParser.parse("")
        assertTrue(empty.cores.isEmpty())
        assertTrue(empty.features.isEmpty())
        assertEquals(CpuRules.ID_UNKNOWN, CpuRules.finding(empty).id)
    }

    @Test
    fun cpuWithoutSveSmeWarnsWithTheExactTitle() {
        val cpu = CpuInfoParser.parse(Fixtures.NO_SVE_CPUINFO)
        assertEquals(listOf("sve2", "sme"), CpuRules.missingForColorOs(cpu))
        val f = CpuRules.finding(cpu)
        assertEquals(CpuRules.ID_MISSING, f.id)
        assertEquals(Level.WARN, f.level)
        assertEquals("CPU lacks SVE2, SME used by the system images", f.title)
        assertEquals(CpuRules.R_MISSING, f.reason)
        assertTrue(f.detail.contains("SVE NO") || f.detail.contains("SVE no"))

        val onlySme = CpuInfoParser.parse(Fixtures.cpuinfo("fp asimd sve sve2", cores = 1))
        assertEquals("CPU lacks SME used by the system images", CpuRules.finding(onlySme).title)

        // The tested Fold has no MOPS or SME2 and runs ColorOS: no warning.
        val fold = CpuInfoParser.parse(Fixtures.SM8850_CPUINFO)
        assertEquals(false, fold.has("mops"))
        assertEquals(CpuRules.ID_OK, CpuRules.finding(fold).id)
    }

    @Test
    fun cpuFindingInTheDeviceReport() {
        val ok = CompatEvaluator.evaluate(Fixtures.facts())
        assertEquals(Level.OK, ok.level(CpuRules.ID_OK))
        assertEquals(Verdict.COMPATIBLE, ok.verdict)

        val missing = CompatEvaluator.evaluate(Fixtures.facts(cpu = CpuInfoParser.parse(Fixtures.NO_SVE_CPUINFO)))
        // 0.4.38: the F8U's first image (Find N6 global) needs no SVE itself, only some of its apps.
        assertEquals(Level.WARN, missing.level(CpuRules.ID_APP_FEATURES))
        assertEquals(Verdict.WARNING, missing.verdict)

        // Unreadable /proc/cpuinfo is a note, not a warning.
        val unknown = CompatEvaluator.evaluate(Fixtures.facts(cpu = null))
        assertEquals(Level.INFO, unknown.level(CpuRules.ID_UNKNOWN))
        assertEquals(Verdict.COMPATIBLE, unknown.verdict)
    }

    @Test
    fun androidVersionOtherThan17Warns() {
        // 0.4.67: Android 16 has an image (OxygenOS 16); Android 15 (SDK 35) has none.
        val r = CompatEvaluator.evaluate(Fixtures.facts(sdk = 35))
        val f = r.find(CompatEvaluator.ID_ANDROID_DIFFERS)!!
        assertEquals(Level.WARN, f.level)
        assertEquals("Android version differs from the OneOS images (16, 17); switching may not work", f.title)
        assertEquals(Verdict.WARNING, r.verdict)
        assertNull(r.find(CompatEvaluator.ID_ANDROID_MATCHES))

        val same = CompatEvaluator.evaluate(Fixtures.facts(sdk = 37))
        assertNull(same.find(CompatEvaluator.ID_ANDROID_DIFFERS))
        assertEquals(Level.OK, same.level(CompatEvaluator.ID_ANDROID_MATCHES))
        val a16 = CompatEvaluator.evaluate(Fixtures.facts(sdk = 36))
        assertNull(a16.find(CompatEvaluator.ID_ANDROID_DIFFERS))
        assertEquals(Level.OK, a16.level(CompatEvaluator.ID_ANDROID_MATCHES))

        assertEquals("17", AndroidRelease.name(37))
        assertEquals("16", AndroidRelease.name(36))
        assertEquals("SDK 40", AndroidRelease.name(40))
    }

    @Test
    fun oneUi90IsTheTestedVersion() {
        assertNull(CompatEvaluator.evaluate(Fixtures.facts(oneUi = "90000")).find("oneui-unseen"))
        assertEquals(Level.WARN, CompatEvaluator.evaluate(Fixtures.facts(oneUi = "90100")).level("oneui-unseen"))
    }

    @Test
    fun s25UltraIsATestedPhoneInTheReport() {
        // Owner, 0.3.1: the S25 Ultra profile is on, untested (the S26 Ultra's WARN);
        // 0.4.7: the Find X9 Ultra build is marked tested on it.
        val f = Fixtures.s25Ultra()
        assertEquals(ModelFamily.S_ULTRA, f.family)
        assertEquals("Snapdragon 8 Elite (SM8750, sun)", f.soc.display)
        val r = CompatEvaluator.evaluate(f)
        assertEquals(Verdict.COMPATIBLE, r.verdict)
        assertNull(r.find(CompatEvaluator.ID_PROFILE_DISABLED))
        assertEquals(Level.OK, r.level("tested-model"))
        assertNull(r.find("untested-model"))
        assertEquals(Level.OK, r.level("soc-snapdragon"))
        assertEquals(0, r.count(Level.BLOCK))

        // Same phone without SVE/SME (the real SM8750): the Find X9 Ultra image does not
        // need them; a WARN that some OPPO features may crash, never BLOCK.
        val noSve = CompatEvaluator.evaluate(Fixtures.s25Ultra(cpu = CpuInfoParser.parse(Fixtures.NO_SVE_CPUINFO)))
        assertEquals(Verdict.WARNING, noSve.verdict)
        assertEquals(Level.WARN, noSve.level(CpuRules.ID_APP_FEATURES))
        assertNull(noSve.find(CpuRules.ID_MISSING))
        assertEquals(0, noSve.count(Level.BLOCK))
    }

    @Test
    fun s26UltraIsTested() {
        val r = CompatEvaluator.evaluate(Fixtures.s26Ultra())
        assertEquals(Verdict.COMPATIBLE, r.verdict)
        assertEquals(Level.OK, r.level("tested-model"))
        assertEquals(0, r.count(Level.BLOCK))
    }
}
