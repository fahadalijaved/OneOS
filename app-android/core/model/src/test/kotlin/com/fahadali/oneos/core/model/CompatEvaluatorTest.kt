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
        assertEquals("Has run on the Z Fold (F8U): ColorOS 17 · Find N6 global build; Pixel 11 Fold; OriginOS 7.", r.find("tested-model")!!.detail)
        // 0.4.31: the testers' reports of 2026-10-29/30 (docs/compatibility.md) add
        // Infinity-X on the S26 Ultra, S25 Ultra, S25, S24 Ultra and Z Flip5, the CN
        // ColorOS build on the Galaxy A57, and the global build on the Z Flip5.
        assertEquals("Has run on: ColorOS 17 · Find N6 global build on the Z Fold (F8U); Pixel 11 Fold on the Z Fold (F8U); OriginOS 7 on the Z Fold (F8U); " +
            "ColorOS 17 · global build on the Galaxy S26 Ultra; Infinity-X 4.1 on the Galaxy S26 Ultra; " +
            "ColorOS 17 · global build on the Galaxy S25 Ultra; Infinity-X 4.1 on the Galaxy S25 Ultra; " +
            "ColorOS 17 · global build on the Galaxy S25; Infinity-X 4.1 on the Galaxy S25; " +
            "Pixel 11 Fold on the Galaxy Z Fold8; " +
            "Infinity-X 4.1 on the Galaxy S24 Ultra; ColorOS 17 · global build on the Galaxy A57; " +
            "ColorOS 17 · global build on the Galaxy Z Flip5; Infinity-X 4.1 on the Galaxy Z Flip5; Infinity-X 4.1 on the Galaxy A07; Infinity-X 4.1 on the Galaxy A17; Infinity-X 4.1 on the Galaxy A16 5G; Infinity-X 4.1 on the Galaxy A16 4G.",
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
        assertEquals("Has run on the Galaxy S26 Ultra: ColorOS 17 · global build; Infinity-X 4.1.", r.find("tested-model")!!.detail)
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
        assertEquals("Has run on the Galaxy S25: ColorOS 17 · global build; Infinity-X 4.1.", r.find("tested-model")!!.detail)
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
            s25.copy(model = "SM-G991U", device = "o1q", soc = SocRules.resolve(SocProps("QTI", "SM8350", "lahaina"))), // Galaxy S21 (the S22 has a profile since 0.4.68)
            s25.copy(model = "SM-S926B", device = "e2q", soc = SocRules.resolve(SocProps("QTI", "SM8650", "pineapple"))),
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
        // 0.4.85: a warning, not "Not supported" (a phone that was switching read "OneOS can't run on
        // this phone" when it ran low: the rule counts the image a set-up system already has).
        val short = eval(Fixtures.facts(storage = StorageInfo(15_000_000_000, 256_000_000_000)))
        assertEquals(Level.WARN, short.level("free-space-short"))
        assertEquals(Verdict.WARNING, short.verdict)
        assertTrue(short.find("free-space-short")!!.detail.endsWith("A system that is already set up keeps its image: switching to it needs about 11.8 GB free."))

        val unknown = eval(Fixtures.facts(storage = null))
        assertEquals(Level.WARN, unknown.level("free-space-unknown"))

        // The F8U profile's image (Find N6) and its files.
        val need = SpaceRule.toStage(Images.FIND_N6, PackageSets.N6_F8U)
        val exact = eval(Fixtures.facts(storage = StorageInfo(need, 512_000_000_000)))
        assertEquals(Level.OK, exact.level("free-space"))
        assertEquals(Level.WARN, eval(Fixtures.facts(storage = StorageInfo(need - 1, 512_000_000_000))).level("free-space-short"))

        assertEquals(10_276_003_840L + 11L * SpaceRule.GIB, SpaceRule.required())
        assertEquals(14_669_168_640L + 634_332_311L + 11L * SpaceRule.GIB, SpaceRule.toStage(Images.FIND_X9U_IN, PackageSets.X9U_IN_SULTRA))
    }

    /** 0.4.85: the device report goes by the systems of this phone that fit its Android version. */
    @Test
    fun oneUi85PhonesAreJudgedByTheirOwnSystems() {
        fun bar(model: String, device: String, soc: SocProps, free: Long = 100_000_000_000) = Fixtures.facts(
            model = model, device = device, soc = soc, oneUi = "80500", sdk = 36, storage = StorageInfo(free, 128_000_000_000),
            panels = listOf(Panel(0, "Built-in Screen", 1080, 2340, 400f, 400f)), hinge = false, inputs = listOf("hall", "sec_touchscreen"),
        ).copy(androidRelease = "16")
        val mediatek = SocProps(manufacturer = "Mediatek", model = "MT6789")

        // Galaxy A15 (ColorOS 17 first in its list, OxygenOS 16 for One UI 8.5): no version warnings,
        // and space is counted for OxygenOS 16, the system it can set up.
        val oxygen = Images.byId(Images.ID_OXYGEN16)!!
        val a15 = eval(bar("SM-A155F", "a15", mediatek))
        assertNull(a15.find("oneui-unseen"))
        assertNull(a15.find(CompatEvaluator.ID_ANDROID_DIFFERS))
        assertTrue(a15.find(CompatEvaluator.ID_ANDROID_MATCHES)!!.detail.startsWith(oxygen.label))
        val need = SpaceRule.toStage(oxygen, PackageSets.byId(PackageSets.ID_OXYGEN16))
        assertEquals(Level.OK, eval(bar("SM-A155F", "a15", mediatek, free = need)).level("free-space"))
        // Low on space with a system already set up (the Galaxy A24 of the reports): a warning.
        val a24 = eval(bar("SM-A245F", "a24", mediatek, free = 14_400_000_000))
        assertEquals(Level.WARN, a24.level("free-space-short"))
        assertTrue(a24.findings.none { it.level == Level.BLOCK })
        assertEquals(Verdict.WARNING, a24.verdict)

        // Galaxy A56: every system is Android 17, so One UI 8.5 is too old for it, and still "not seen".
        val a56 = eval(bar("SM-A566B", "a56x", SocProps(manufacturer = "Samsung", model = "s5e8855")))
        assertEquals(Level.WARN, a56.level("oneui-unseen"))
        val differs = a56.find(CompatEvaluator.ID_ANDROID_DIFFERS)!!
        assertEquals("The systems for this phone need Android 17: update One UI first", differs.title)
        assertTrue(differs.detail, differs.detail.contains("the systems for the Galaxy A56 are Android 17 (SDK 37)"))
        assertNull(a56.find(CompatEvaluator.ID_ANDROID_MATCHES))
        // One UI 8.5 on a phone with no profile is not seen either.
        assertEquals(Level.WARN, eval(Fixtures.facts(model = "SM-S948B", device = "m3s", soc = SocProps(manufacturer = "Samsung", model = "s5e9955"), oneUi = "80500", sdk = 36)).level("oneui-unseen"))
    }

    @Test
    fun oneUiAndSdkOutsideProfilesWarn() {
        // 0.4.67: SDK 36 has an image now (OxygenOS 16); One UI 7 on Android 15 has none.
        val r = eval(Fixtures.facts(oneUi = "70000", sdk = 35))
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
