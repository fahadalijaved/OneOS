package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CompatEvaluatorTest {
    private fun eval(f: DeviceFacts) = CompatEvaluator.evaluate(f)

    private fun CompatReport.level(id: String): Level? = find(id)?.level

    @Test
    fun f8uWithKernelSuUncheckedIsCompatible() {
        val r = eval(Fixtures.facts())
        assertEquals(Verdict.COMPATIBLE, r.verdict)
        assertEquals(Level.OK, r.level("tested-model"))
        // Where it has run comes from the image table, not a fixed text.
        assertEquals("Has run on the Z Fold (F8U): ColorOS 17 · Find N6 build; Pixel 11 Fold.", r.find("tested-model")!!.detail)
        // 0.4.31: the testers' reports of 2026-10-29/30 (docs/compatibility.md) add
        // Infinity-X on the S26 Ultra, S25 Ultra, S25, S24 Ultra and Z Flip5, the CN
        // ColorOS build on the Galaxy A57, and the global build on the Z Flip5.
        assertEquals("Has run on: ColorOS 17 · Find N6 build on the Z Fold (F8U); Pixel 11 Fold on the Z Fold (F8U); " +
            "ColorOS 17 · Find X9 Ultra build on the Galaxy S26 Ultra; Infinity-X 4.1 on the Galaxy S26 Ultra; " +
            "ColorOS 17 · Find X9 Ultra build on the Galaxy S25 Ultra; Infinity-X 4.1 on the Galaxy S25 Ultra; " +
            "ColorOS 17 · Find X9 Ultra build on the Galaxy S25; Infinity-X 4.1 on the Galaxy S25; " +
            "ColorOS 17 · Find N6 build on the Galaxy Z Fold8; Pixel 11 Fold on the Galaxy Z Fold8; " +
            "Infinity-X 4.1 on the Galaxy S24 Ultra; ColorOS 17 · Find X9 Ultra build on the Galaxy A57; " +
            "ColorOS 17 · global build on the Galaxy Z Flip5; Infinity-X 4.1 on the Galaxy Z Flip5.",
            CompatEvaluator.TESTED_SCOPE,
        )
        assertEquals(Level.OK, r.level("soc-snapdragon"))
        assertEquals(Level.OK, r.level("sdk-package"))
        assertEquals(Level.OK, r.level("free-space"))
        assertEquals(Level.INFO, r.level("root-unchecked"))
        assertEquals(0, r.count(Level.WARN))
        assertEquals(0, r.count(Level.BLOCK))
    }

    @Test
    fun rootProbeOutcomes() {
        fun withProbe(state: SuState, uid: Int?) = eval(
            Fixtures.facts(
                root = RootSignals(listOf("me.weishu.kernelsu"), probe = SuProbeResult(state, uid, "u:r:su:s0", "")),
            ),
        )
        val ok = withProbe(SuState.GRANTED, 0)
        assertEquals(Verdict.COMPATIBLE, ok.verdict)
        assertEquals(Level.OK, ok.level("root-ok"))

        val timeout = withProbe(SuState.TIMEOUT, null)
        assertEquals(Verdict.WARNING, timeout.verdict)
        assertEquals(Level.WARN, timeout.level("root-timeout"))

        for (state in listOf(SuState.DENIED, SuState.NOT_FOUND, SuState.ERROR)) {
            val r = withProbe(state, null)
            assertEquals(Verdict.NOT_SUPPORTED, r.verdict)
            assertEquals(Level.BLOCK, r.level("root-missing"))
        }
    }

    /**
     * OneOS Probe installs next to OneOS and needs its own root grant: every
     * root finding names the app that asks, never the other one.
     */
    @Test
    fun rootFindingsNameTheAppThatAsks() {
        val ids = listOf("root-timeout", "root-missing", "root-unchecked", "root-not-found")
        val facts = listOf(
            Fixtures.facts(root = RootSignals(listOf("me.weishu.kernelsu"), probe = SuProbeResult(SuState.TIMEOUT, null, null, ""))),
            Fixtures.facts(root = RootSignals(listOf("me.weishu.kernelsu"), probe = SuProbeResult(SuState.NOT_FOUND, null, null, ""))),
            Fixtures.facts(root = RootSignals(listOf("me.weishu.kernelsu"))),
            Fixtures.facts(root = RootSignals()),
        )
        for ((id, f) in ids.zip(facts)) {
            val probe = CompatEvaluator.evaluate(f, app = "OneOS Probe").find(id)
            assertNotNull(id, probe)
            val text = "${probe!!.title} ${probe.detail}"
            assertTrue("$id: $text", text.contains("OneOS Probe"))
            assertFalse("$id names OneOS: $text", Regex("""OneOS(?! Probe)""").containsMatchIn(text))
            // The full edition (the default) keeps its texts.
            val full = eval(f).find(id)!!
            assertEquals(text.replace("OneOS Probe", "OneOS"), "${full.title} ${full.detail}")
        }
    }

    @Test
    fun noRootManagerFoundIsWarn() {
        val r = eval(Fixtures.facts(root = RootSignals()))
        assertEquals(Verdict.WARNING, r.verdict)
        assertEquals(Level.WARN, r.level("root-not-found"))
    }

    @Test
    fun s26UltraSnapdragonIsCompatible() {
        // DESIGN.md 4.5: an S26 Ultra (Snapdragon) + ColorOS, same SDK, runs; WARN until
        // 0.4.7, when the Find X9 Ultra build was marked tested on it.
        val r = eval(Fixtures.s26Ultra())
        assertEquals(Verdict.COMPATIBLE, r.verdict)
        assertEquals(Level.OK, r.level("tested-model"))
        assertEquals("Has run on the Galaxy S26 Ultra: ColorOS 17 · Find X9 Ultra build; Infinity-X 4.1.", r.find("tested-model")!!.detail)
        assertNull(r.find("untested-model"))
        assertNull(r.find("form-prefix-mismatch"))
        assertEquals(FormFactor.BAR, Fixtures.s26Ultra().form.form)
    }

    @Test
    fun exynosIsBlocked() {
        // An Exynos S26 Ultra: no profile, so Exynos stays a block.
        val r = eval(
            Fixtures.facts(
                model = "SM-S948B", device = "m3s",
                soc = SocProps(manufacturer = "Samsung", model = "s5e9965", platform = "s5e9965"),
            ),
        )
        assertEquals(Verdict.NOT_SUPPORTED, r.verdict)
        assertEquals(Level.BLOCK, r.level("soc-exynos"))
    }

    /** 0.4.17: an Exynos phone with its own profile (the Z Flip7) gets a first-runs warning, not the block. */
    @Test
    fun exynosWithAProfileIsAFirstRun() {
        val r = eval(
            Fixtures.facts(
                model = "SM-F766U", device = "b7s",
                soc = SocProps(manufacturer = "Samsung", model = "s5e9955", platform = "s5e9955"),
            ),
        )
        assertEquals(Level.WARN, r.level("soc-exynos"))
    }

    @Test
    fun notSamsungIsBlocked() {
        val r = eval(Fixtures.facts(brand = "google", model = "Pixel 10 Pro Fold", device = "rango"))
        assertEquals(Verdict.NOT_SUPPORTED, r.verdict)
        assertEquals(Level.BLOCK, r.level("not-samsung"))
        // The model-scope rule is about Samsung models only.
        assertNull(r.find("model-out-of-scope"))
        assertNull(r.find("oneui-missing"))
    }

    @Test
    fun otherSamsungModelIsOutOfScope() {
        val r = eval(Fixtures.facts(model = "SM-A566B", device = "a56x", hinge = false, inputs = emptyList()))
        assertEquals(Verdict.NOT_SUPPORTED, r.verdict)
        assertEquals(Level.BLOCK, r.level("model-out-of-scope"))
        assertNull(r.find("untested-model"))
    }

    /**
     * Owner, 0.3.4: in scope is Z Fold / Z Flip / S Ultra or an explicit
     * profile. The friend's Galaxy S25 bundle (0.2.1-probe) was BLOCK
     * model-out-of-scope; with its profile it is in scope, tested since 0.4.7.
     */
    @Test
    fun galaxyS25IsInScopeThroughItsProfile() {
        val f = Bundles.S25.facts
        assertEquals(ModelFamily.S_SERIES, f.family)
        assertEquals(Profiles.S_8750, Profiles.resolve(f).profile)
        assertTrue(CompatEvaluator.inScope(f.family, Profiles.S_8750))
        val r = eval(f)
        assertNull(r.find(CompatEvaluator.ID_OUT_OF_SCOPE))
        assertEquals(Verdict.WARNING, r.verdict)
        assertEquals(0, r.count(Level.BLOCK))
        assertEquals(Level.OK, r.level("tested-model"))
        assertEquals("Has run on the Galaxy S25: ColorOS 17 · Find X9 Ultra build; Infinity-X 4.1.", r.find("tested-model")!!.detail)
        assertNull(r.find("untested-model"))
        assertNull(r.find(CompatEvaluator.ID_NO_PROFILE))
        assertNull(r.find("profile-form-mismatch"))
        assertNull(r.find("form-prefix-mismatch"))
        // Its CPU (no SVE/SME) with its first image, the Find X9 Ultra: some OPPO features may crash.
        assertEquals(Level.WARN, r.level(CpuRules.ID_APP_FEATURES))
        assertEquals(Level.OK, r.level("soc-snapdragon"))
        assertEquals(Level.OK, r.level("free-space"))
    }

    @Test
    fun otherSSeriesModelsStayOutOfScope() {
        val s25 = Bundles.S25.facts
        // Another S-series model, and an S25 model number with another codename or chip.
        for (f in listOf(
            s25.copy(model = "SM-S901B", device = "r0q", soc = SocRules.resolve(SocProps("QTI", "SM8450", "taro"))),
            s25.copy(model = "SM-S921B", device = "e1q", soc = SocRules.resolve(SocProps("QTI", "SM8650", "pineapple"))),
            s25.copy(device = "pa3q"),
            s25.copy(soc = SocRules.resolve(SocProps("QTI", "SM8850", "canoe"))),
        )) {
            assertNull(f.model, Profiles.resolve(f).profile)
            assertFalse(CompatEvaluator.inScope(f.family, null))
            val r = eval(f)
            assertEquals(f.model, Verdict.NOT_SUPPORTED, r.verdict)
            assertEquals(f.model, Level.BLOCK, r.level(CompatEvaluator.ID_OUT_OF_SCOPE))
            // The BLOCK names the S-series phones that have a profile.
            val detail = r.find(CompatEvaluator.ID_OUT_OF_SCOPE)!!.detail
            assertTrue(detail.contains("Galaxy S25 (SM-S931* / pa1q / SM8750)"))
            assertTrue(detail.contains("Galaxy S26 (docomo) (SC-51G* / m1q / SM8850)"))
        }
        // The family alone still decides for the flagships.
        assertTrue(CompatEvaluator.inScope(ModelFamily.S_ULTRA, null))
        assertFalse(CompatEvaluator.inScope(ModelFamily.OTHER, null))
    }

    @Test
    fun noArm64IsBlocked() {
        val r = eval(Fixtures.facts(abis64 = emptyList()))
        assertEquals(Level.BLOCK, r.level("not-arm64"))
        assertEquals(Verdict.NOT_SUPPORTED, r.verdict)
    }

    @Test
    fun freeSpace() {
        val short = eval(Fixtures.facts(storage = StorageInfo(15_000_000_000, 256_000_000_000)))
        assertEquals(Level.BLOCK, short.level("free-space-short"))
        assertEquals(Verdict.NOT_SUPPORTED, short.verdict)

        val unknown = eval(Fixtures.facts(storage = null))
        assertEquals(Level.WARN, unknown.level("free-space-unknown"))

        // The F8U profile's image (Find N6) and its files.
        val need = SpaceRule.toStage(Images.FIND_N6, PackageSets.N6_F8U)
        val exact = eval(Fixtures.facts(storage = StorageInfo(need, 512_000_000_000)))
        assertEquals(Level.OK, exact.level("free-space"))
        assertEquals(Level.BLOCK, eval(Fixtures.facts(storage = StorageInfo(need - 1, 512_000_000_000))).level("free-space-short"))

        assertEquals(10_276_003_840L + 11L * SpaceRule.GIB, SpaceRule.required())
        assertEquals(10_385_141_760L + 267_147_970L + 11L * SpaceRule.GIB, SpaceRule.toStage(Images.FIND_X9U, PackageSets.X9U_SULTRA))
    }

    @Test
    fun oneUiAndSdkOutsideProfilesWarn() {
        val r = eval(Fixtures.facts(oneUi = "80500", sdk = 36))
        assertEquals(Level.WARN, r.level("oneui-unseen"))
        assertEquals(Level.WARN, r.level(CompatEvaluator.ID_ANDROID_DIFFERS))
        assertEquals(Verdict.WARNING, r.verdict)

        val missing = eval(Fixtures.facts(oneUi = ""))
        assertEquals(Level.WARN, missing.level("oneui-missing"))
    }

    @Test
    fun formMismatchWarns() {
        val r = eval(Fixtures.facts(panels = listOf(Fixtures.F8U_INNER), hinge = false, inputs = emptyList()))
        assertEquals(Level.WARN, r.level("form-prefix-mismatch"))
        assertEquals(Verdict.WARNING, r.verdict)
    }

    @Test
    fun infoNeverChangesTheVerdict() {
        val r = eval(Fixtures.facts(battery = BatteryInfo(10, false, 45f)))
        assertEquals(Level.INFO, r.level("battery-now"))
        assertEquals(Verdict.COMPATIBLE, r.verdict)
    }

    @Test
    fun sortedPutsWorstFirst() {
        val r = eval(Fixtures.facts(abis64 = emptyList(), oneUi = "80500"))
        val levels = r.sorted.map { it.level }
        assertEquals(Level.BLOCK, levels.first())
        assertTrue(levels.indexOf(Level.WARN) < levels.indexOf(Level.OK))
        assertTrue(levels.lastIndexOf(Level.OK) < levels.indexOf(Level.INFO))
        assertNotNull(r.find("not-arm64"))
    }

    @Test
    fun findingIdsAreUnique() {
        for (f in listOf(Fixtures.facts(), Fixtures.s26Ultra(), Fixtures.facts(brand = "google"))) {
            val ids = eval(f).findings.map { it.id }
            assertEquals(ids.size, ids.toSet().size)
        }
    }
}
