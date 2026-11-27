package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The experimental tester build (-Poneos.a17OnA16=true, [Experimental.a17OnA16]): One UI 9.5 on phones still on
 * One UI 8.0/8.5. Off, every rule is the normal build's; on, only that pair gets through. The global flag is never
 * set here: the profiles and gates take it as a parameter.
 */
class ExperimentalA17OnA16Test {
    private val patches = File(System.getProperty("oneos.installdFixture") ?: "../../../switcher/patches/host_installd.txt").parentFile
    private val a90 = File(patches, "host_installd.txt").readText()
    private val a85 = File(patches, "host_installd_a16.txt").readText()
    private val a80 = javaClass.getResource("/host_installd_oneui80.txt")!!.readText()
    private val tester = Profiles.withOneUi95OnA16(Profiles.STABLE)

    private fun table(text: String) =
        InstalldDerivation(InstalldTableFormat.parseLegacy(text), "/system/framework/services.jar", "classes.dex", null, emptyList(), null)

    private fun bar(model: String, device: String, soc: SocProps, oneUi: String = "80000", sdk: Int = 36) = Fixtures.facts(
        model = model, device = device, soc = soc, oneUi = oneUi, sdk = sdk,
        panels = listOf(Panel(0, "Built-in Screen", 1080, 2340, 400f, 400f)), hinge = false, inputs = listOf("hall", "sec_touchscreen"),
    ).copy(androidRelease = if (sdk == 36) "16" else "17")

    private val s22Ultra = bar("SM-S908B", "b0q", SocProps(manufacturer = "QTI", model = "SM8450"))
    private val a56 = bar("SM-A566B", "a56x", SocProps(manufacturer = "Samsung", model = "s5e8855"), oneUi = "80500")

    private fun staged(p: PhoneProfile, image: String, set: String?) =
        StageState(emptyList(), emptyList(), false, StageMarker(4, p.id, image, set, 1_792_000_000), true)

    private fun switch(f: DeviceFacts, installd: String, stage: StageState?, on: Boolean, profiles: List<PhoneProfile>) = SwitchGates.evaluate(
        GatePhase.SWITCH,
        GateInput(
            f, false, false, table(installd), stage ?: StageState(emptyList(), emptyList(), false, null, false),
            expectedInstalld = a90, expectedInstalldA16 = a85, appVersionCode = 4, a17OnA16 = on,
        ),
        profiles,
    )

    @Test
    fun offByDefaultAndTheNormalProfilesStay() {
        assertFalse(Experimental.a17OnA16)
        assertSame(Profiles.STABLE, Profiles.BUILT_IN)
        assertNull(Profiles.S_ULTRA_8450.choice(Images.ID_ONEUI95))
        assertEquals(Experimental.a17OnA16Pair(36, Images.ONEUI95), false)
        assertTrue(Experimental.a17OnA16Pair(36, Images.ONEUI95, on = true))
        // Only that image, only on an SDK 36 phone.
        assertFalse(Experimental.a17OnA16Pair(37, Images.ONEUI95, on = true))
        assertFalse(Experimental.a17OnA16Pair(36, Images.FIND_X9U_IN_1105, on = true))
        assertFalse(Experimental.a17OnA16Pair(36, Images.OXYGEN16, on = true))
        assertFalse(Experimental.a17OnA16Pair(36, null, on = true))
    }

    /**
     * One UI 9.5 last on every enabled phone that lacks it (the ones held on One UI 8); oneui8test5: the plain One UI 9.5
     * set swapped for the One UI 8 one where a phone offers it (the A35 on One UI 8); the others unchanged.
     */
    @Test
    fun theTesterBuildOffersOneUi95Everywhere() {
        assertEquals(Profiles.STABLE.map { it.id }, tester.map { it.id })
        for ((stable, test) in Profiles.STABLE.zip(tester)) {
            if (stable.enabled && stable.choices.any { it.imageId == Images.ID_ONEUI95 && it.packageSetId == PackageSets.ID_ONEUI95 }) {
                assertEquals(stable.id, stable.choices.map {
                    if (it.imageId == Images.ID_ONEUI95 && it.packageSetId == PackageSets.ID_ONEUI95) it.copy(packageSetId = PackageSets.ID_ONEUI95_A16) else it
                }, test.choices)
                assertEquals(stable.id, stable.copy(choices = test.choices), test)
            } else if (!stable.enabled || stable.choice(Images.ID_ONEUI95) != null || stable in Profiles.TABLETS) {
                // 0.5.41: a Galaxy Tab keeps its one tablet system.
                assertSame(stable.id, stable, test)
            } else {
                assertEquals(stable.id, stable.choices + ImageChoice(Images.ID_ONEUI95, PackageSets.ID_ONEUI95_A16, tested = false), test.choices)
            }
        }
        assertTrue(tester.filter { it.enabled && it.id !in Profiles.TABLETS.map { t -> t.id } }.all { it.choice(Images.ID_ONEUI95) != null })
        val added = tester.filter { it !in Profiles.TABLETS && Profiles.byId(it.id, Profiles.STABLE)!!.choice(Images.ID_ONEUI95) == null }.map { it.id }.toSet()
        assertEquals(PackageSets.ID_ONEUI95_A16, tester.first { it.id == Profiles.A35.id }.choice(Images.ID_ONEUI95)!!.packageSetId)
        assertTrue(added.containsAll(setOf(Profiles.S_ULTRA_8450.id, Profiles.S_ULTRA_9925.id, Profiles.A06.id, Profiles.A07_5G.id)))
        // Exactly the phones whose STABLE choices don't include One UI 9.5 (One UI 8 only).
        assertEquals(Profiles.STABLE.filter { p -> p !in Profiles.TABLETS && p.choice(Images.ID_ONEUI95) == null }.map { it.id }.toSet(), added)
    }

    @Test
    fun installdTablesOfOneUi8OnlyForThePair() {
        assertEquals(setOf(InstalldExpected.SHA256, InstalldExpected.SHA256_95), InstalldExpected.accepted(37))
        assertEquals(
            setOf(InstalldExpected.SHA256, InstalldExpected.SHA256_95, InstalldExpected.SHA256_A16, InstalldExpected.SHA256_A16_ONEUI80),
            InstalldExpected.accepted(37, a17OnA16 = true),
        )
        assertEquals(InstalldExpected.accepted(36), InstalldExpected.accepted(36, a17OnA16 = true))
        for (t in listOf(a85, a80)) {
            assertTrue(InstalldExpected.problems(table(t), a90, 37).isNotEmpty())
            assertEquals(emptyList<String>(), InstalldExpected.problems(table(t), a90, 37, a17OnA16 = true))
        }
    }

    /** The S22 Ultra on One UI 8.0 with One UI 9.5 staged: refused in a normal build, a WARN and a tick in the tester build. */
    @Test
    fun s22UltraOnOneUi8() {
        val p = tester.first { it.id == Profiles.S_ULTRA_8450.id }
        val stage = staged(p, Images.ID_ONEUI95, PackageSets.ID_ONEUI95_A16)
        // Normal build: the phone does not take the image at all.
        val normal = switch(s22Ultra, a80, staged(Profiles.S_ULTRA_8450, Images.ID_ONEUI95, PackageSets.ID_ONEUI95), false, Profiles.STABLE)
        assertTrue(normal.blocked)
        assertEquals(SwitchGates.R_IMAGE_OTHER_PHONE, normal.find(SwitchGates.ID_IMAGE)!!.finding.reason)
        // The tester build's profiles without the flag (cannot happen in an APK): the Android and installd gates refuse.
        val flagOff = switch(s22Ultra, a80, stage, false, tester)
        assertEquals(Level.BLOCK, flagOff.find(SwitchGates.ID_ANDROID)!!.level)
        assertEquals(Level.BLOCK, flagOff.find(SwitchGates.ID_INSTALLD)!!.level)
        // The tester build, One UI 8.0's and 8.5's tables.
        for (t in listOf(a80, a85)) {
            val r = switch(s22Ultra, t, stage, true, tester)
            assertEquals(Images.ONEUI95, r.image)
            assertEquals(PackageSets.ONEUI95_A16, r.set)
            val android = r.find(SwitchGates.ID_ANDROID)!!
            assertEquals(Level.WARN to SwitchGates.R_ANDROID_EXPERIMENTAL, android.level to android.finding.reason)
            assertEquals(SwitchGates.A17_ON_A16_ACK, android.ack)
            assertEquals(Level.OK, r.find(SwitchGates.ID_INSTALLD)!!.level)
            assertEquals(Level.OK, r.find(SwitchGates.ID_IMAGE)!!.level)
            assertTrue(r.toTick.map { it.id }.contains(SwitchGates.ID_ANDROID))
            val plain = Plain.of(android.finding, r.image, p)
            assertEquals(FixAction.ACKNOWLEDGE, plain.action)
            assertTrue(plain.line.length <= PlainMessage.MAX_LINE)
        }
        // OxygenOS 16 on the same phone is untouched by the flag.
        val oxygen = switch(s22Ultra, a80, staged(p, Images.ID_OXYGEN16, PackageSets.ID_OXYGEN16), true, tester)
        assertEquals(Level.OK, oxygen.find(SwitchGates.ID_ANDROID)!!.level)
        assertEquals(Level.OK, oxygen.find(SwitchGates.ID_INSTALLD)!!.level)
        // A phone on One UI 9 (SDK 37) runs One UI 9.5 as before: no experimental WARN.
        val s26u = Bundles.S26U
        val p26 = Profiles.resolve(s26u.facts, tester).profile!!
        val oneUi9 = switch(s26u.facts, a90, staged(p26, Images.ID_ONEUI95, PackageSets.ID_ONEUI95), true, tester)
        assertEquals(Level.OK, oneUi9.find(SwitchGates.ID_ANDROID)!!.level)
    }

    /** The Galaxy A56 on One UI 8.5, every system Android 17: "update One UI first" normally, One UI 9.5 on trial in the tester build. */
    @Test
    fun a56OnOneUi85() {
        val normal = switch(a56, a85, null, false, Profiles.STABLE).find(SwitchGates.ID_ANDROID)!!.finding
        assertEquals(Level.BLOCK to SwitchGates.R_ANDROID_OLDER, normal.level to normal.reason)
        val nothing = switch(a56, a85, null, true, tester)
        assertEquals(Level.WARN to SwitchGates.R_ANDROID_EXPERIMENTAL, nothing.find(SwitchGates.ID_ANDROID)!!.level to nothing.find(SwitchGates.ID_ANDROID)!!.finding.reason)
        assertEquals(Level.OK, nothing.find(SwitchGates.ID_INSTALLD)!!.level)
        // Another Android 17 system staged: still refused, with "choose another system".
        val color = switch(a56, a85, staged(Profiles.A56, Profiles.A56.choices.first().imageId, Profiles.A56.choices.first().packageSetId), true, tester)
        val android = color.find(SwitchGates.ID_ANDROID)!!.finding
        assertEquals(Level.BLOCK to SwitchGates.R_ANDROID_DIFFERS, android.level to android.reason)
        assertEquals(Level.BLOCK, color.find(SwitchGates.ID_INSTALLD)!!.level)
        assertEquals(FixAction.CHOOSE_SYSTEM, Plain.of(android, color.image, Profiles.A56).action)
        // One UI 9.5 staged: through, with the tick.
        val oneUi95 = switch(a56, a85, staged(Profiles.A56, Images.ID_ONEUI95, PackageSets.ID_ONEUI95), true, tester)
        assertEquals(Level.WARN, oneUi95.find(SwitchGates.ID_ANDROID)!!.level)
        assertEquals(Level.OK, oneUi95.find(SwitchGates.ID_INSTALLD)!!.level)
    }

    @Test
    fun deviceReport() {
        val normal = CompatEvaluator.evaluate(a56)
        assertEquals(Level.WARN, normal.findings.first { it.id == CompatEvaluator.ID_ANDROID_DIFFERS }.level)
        assertTrue(normal.findings.none { it.id == CompatEvaluator.ID_ANDROID_EXPERIMENTAL })
        val test = CompatEvaluator.evaluate(a56, profiles = tester, a17OnA16 = true)
        assertEquals(Level.WARN, test.findings.first { it.id == CompatEvaluator.ID_ANDROID_EXPERIMENTAL }.level)
        assertTrue(test.findings.none { it.id == CompatEvaluator.ID_ANDROID_DIFFERS })
        assertTrue(test.findings.none { it.id == "oneui-unseen" })
        // The tester build on a One UI 9 phone: as normal.
        val oneUi9 = CompatEvaluator.evaluate(Bundles.S26U.facts, profiles = tester, a17OnA16 = true)
        assertTrue(oneUi9.findings.none { it.id == CompatEvaluator.ID_ANDROID_EXPERIMENTAL })
    }
}
