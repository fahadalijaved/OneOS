package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GatesTest {
    private fun stage(
        p: PhoneProfile,
        image: String = usual(p).imageId,
        verified: Boolean = true,
        set: String? = p.choice(image)?.packageSetId,
    ) = StageState(emptyList(), emptyList(), false, StageMarker(4, p.id, image, set, 1_792_000_000), verified)

    private fun gz(i: ImageRef) = ImageFileCheck(i.gzName, i.gzBytes, i.gzSha256, i.gzBytes)

    /** The image these tests stage by default: the profile's first that is not the IN build (listed first on the bar phones from 0.4.11). */
    private fun usual(p: PhoneProfile) = p.choices.first { it.imageId != Images.ID_FIND_X9U_IN }

    /** Everything right for [phone] with [image] (screen lock removed, old switcher gone); default: [usual]. */
    private fun input(
        phone: Bundles.Phone,
        profile: PhoneProfile? = Profiles.resolve(phone.facts).profile,
        image: ImageRef? = profile?.let { Images.byId(usual(it).imageId) },
    ) = GateInput(
        facts = phone.facts,
        screenLockSet = false,
        oldSwitcherInstalled = false,
        installd = phone.installd,
        stage = if (profile != null && image != null) stage(profile, image.id) else StageState(emptyList(), emptyList(), false, null, false),
        imageFile = image?.let(::gz),
        appVersionCode = 4,
    )

    private fun eval(phase: GatePhase, i: GateInput) = SwitchGates.evaluate(phase, i)

    private fun GateReport.level(id: String): Level? = find(id)?.level

    @Test
    fun s26UltraSwitchNeedsTheCarrierTick() {
        val r = eval(GatePhase.SWITCH, input(Bundles.S26U))
        assertEquals(Profiles.S_ULTRA_8850, r.profile)
        assertEquals(Images.FIND_X9U, r.image)
        assertEquals(PackageSets.X9U_SULTRA, r.set)
        assertFalse(r.blocked)
        // The Find X9 Ultra build is tested on it since 0.4.7: only the carrier tick.
        assertEquals(listOf(SwitchGates.ID_CARRIER), r.toTick.map { it.id })
        // The ticks name the system: with the IN build next to it (0.3.3-0.3.6, again from 0.4.11) the CN
        // build is "ColorOS 17 · Find X9 Ultra build" (0.3.7-0.4.10, its only ColorOS 17 build: "ColorOS 17").
        val system = Images.systemName(Images.FIND_X9U, Profiles.S_ULTRA_8850)
        assertEquals("ColorOS 17 · Find X9 Ultra build", system)
        assertEquals(CarrierRules.noCallsAck(system), r.find(SwitchGates.ID_CARRIER)!!.ack)
        assertEquals("I understand phone calls, including emergency calls, won't work in $system", r.find(SwitchGates.ID_CARRIER)!!.ack)
        assertNull(r.find(SwitchGates.ID_PROFILE)!!.ack)

        val keys = r.toTick.mapNotNull { it.tickKey }.toSet()
        assertTrue(r.allows(keys))
        assertFalse(r.allows(emptySet()))
        // A tick for another text does not count.
        assertFalse(r.allows(keys - r.find(SwitchGates.ID_CARRIER)!!.tickKey!! + "${SwitchGates.ID_CARRIER}|${CarrierRules.maybeCallsAck(system)}"))

        for (id in listOf(
            SwitchGates.ID_ROOT, SwitchGates.ID_ANDROID, SwitchGates.ID_FORM, SwitchGates.ID_IMAGE, SwitchGates.ID_INSTALLD,
            SwitchGates.ID_OLD_SWITCHER, SwitchGates.ID_STAGE, SwitchGates.ID_SPACE, SwitchGates.ID_SCREEN_LOCK,
            SwitchGates.ID_BATTERY, SwitchGates.ID_PROFILE,
        )) {
            assertEquals(id, Level.OK, r.level(id))
        }
        assertEquals(Level.OK, r.level(CpuRules.ID_OK))
        assertEquals(r.gates.size, r.gates.map { it.id }.toSet().size)
    }

    @Test
    fun f8uSwitchHasNothingToTick() {
        val r = eval(GatePhase.SWITCH, input(Bundles.F8U))
        assertEquals(Profiles.F8U, r.profile)
        assertFalse(r.blocked)
        assertTrue(r.toTick.isEmpty())
        assertTrue(r.allows(emptySet()))
        assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
        assertEquals(Level.INFO, r.level(SwitchGates.ID_CARRIER))
    }

    @Test
    fun s25UltraSwitchNeedsItsTicks() {
        val r = eval(GatePhase.SWITCH, input(Bundles.S25U))
        assertEquals(Profiles.S_ULTRA_8750, r.profile)
        assertFalse(r.blocked)
        assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
        assertNull(r.find(SwitchGates.ID_PROFILE)!!.ack)
        assertTrue(r.allows(r.toTick.mapNotNull { it.tickKey }.toSet()))
        // Its real CPU (no SVE/SME): the X9U image does not need them; some OPPO features may crash.
        assertEquals(Level.WARN, r.level(CpuRules.ID_APP_FEATURES))
        assertEquals(Level.WARN, r.level("profile-vendor-older"))
        assertFalse(eval(GatePhase.PREPARE, input(Bundles.S25U)).blocked)
    }

    /** Galaxy S25 (0.3.4): the S25 Ultra's gates and notes, its own profile id; tested since 0.4.7, so no profile tick. */
    @Test
    fun galaxyS25SwitchNeedsItsTicks() {
        val r = eval(GatePhase.SWITCH, input(Bundles.S25))
        assertEquals(Profiles.S_8750, r.profile)
        assertEquals(Images.FIND_X9U, r.image)
        assertEquals(PackageSets.X9U_SULTRA, r.set)
        assertFalse(r.blocked)
        assertTrue(r.toTick.isEmpty())
        assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
        assertTrue(r.allows(emptySet()))
        assertEquals(Level.OK, r.level(SwitchGates.ID_FORM))
        assertEquals(Level.OK, r.level(SwitchGates.ID_INSTALLD))
        assertEquals(Level.WARN, r.level(CpuRules.ID_APP_FEATURES))
        assertEquals(Level.WARN, r.level("profile-vendor-older"))
        assertFalse(eval(GatePhase.PREPARE, input(Bundles.S25)).blocked)
        // A stage prepared for the S25 Ultra is not this phone's.
        val other = eval(GatePhase.SWITCH, input(Bundles.S25).copy(stage = stage(Profiles.S_ULTRA_8750)))
        assertEquals(Level.BLOCK, other.level(SwitchGates.ID_IMAGE))
        assertEquals("Prepared for another phone or image", other.find(SwitchGates.ID_IMAGE)!!.finding.title)
    }

    @Test
    fun screenLockBlocksAtSwitchAndCannotBeTicked() {
        // The S26 Ultra's findings: a lock is set.
        val locked = eval(GatePhase.SWITCH, input(Bundles.S26U).copy(screenLockSet = true))
        assertEquals(Level.BLOCK, locked.level(SwitchGates.ID_SCREEN_LOCK))
        assertNull(locked.find(SwitchGates.ID_SCREEN_LOCK)!!.ack)
        assertFalse(locked.allows(setOf("anything") + locked.toTick.mapNotNull { it.tickKey }))

        val unknown = eval(GatePhase.SWITCH, input(Bundles.S26U).copy(screenLockSet = null))
        assertEquals(Level.BLOCK, unknown.level(SwitchGates.ID_SCREEN_LOCK))

        // Prepare only warns.
        val prepare = eval(GatePhase.PREPARE, input(Bundles.S26U).copy(screenLockSet = true))
        assertEquals(Level.WARN, prepare.level(SwitchGates.ID_SCREEN_LOCK))
    }

    @Test
    fun oldSwitcherBlocks() {
        for (v in listOf(true, null)) {
            for (phase in GatePhase.entries) {
                val r = eval(phase, input(Bundles.F8U).copy(oldSwitcherInstalled = v))
                assertEquals("$phase $v", Level.BLOCK, r.level(SwitchGates.ID_OLD_SWITCHER))
            }
        }
        val installed = eval(GatePhase.SWITCH, input(Bundles.F8U).copy(oldSwitcherInstalled = true)).find(SwitchGates.ID_OLD_SWITCHER)!!.finding
        assertEquals(SwitchGates.R_OLD_SWITCHER_INSTALLED, installed.reason)
        // No system or app name in the text (the package id stays in SwitchGates.OLD_SWITCHER_PACKAGE).
        assertFalse(installed.detail.contains("lineage", ignoreCase = true))
    }

    @Test
    fun installdMustBeByteEqual() {
        val good = input(Bundles.S26U)
        val m = good.installd!!.methods
        val changed = good.copy(installd = good.installd.copy(methods = m.map { if (it.code == 13) it.copy(code = 113) else it }))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, changed).level(SwitchGates.ID_INSTALLD))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, changed).level(SwitchGates.ID_INSTALLD))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, good.copy(installd = null)).level(SwitchGates.ID_INSTALLD))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, good.copy(installd = InstalldDerivation.failed("x"))).level(SwitchGates.ID_INSTALLD))
    }

    @Test
    fun androidVersionAndFormBlock() {
        val sdk36 = input(Bundles.S26U).let { it.copy(facts = it.facts.copy(sdk = 36, androidRelease = "16")) }
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, sdk36).level(SwitchGates.ID_ANDROID))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, sdk36).level(SwitchGates.ID_ANDROID))

        // An S26 Ultra whose hardware looked foldable: the session settings would be wrong.
        val f = Bundles.S26U.facts
        val fold = f.copy(form = FormFactorRules.resolve(FormSignals(f.model, f.panels, true, true, listOf("flip"))))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, input(Bundles.S26U).copy(facts = fold)).level(SwitchGates.ID_FORM))
    }

    @Test
    fun otherPhonesAreBlocked() {
        fun profileGate(f: DeviceFacts) = SwitchGates.evaluate(
            GatePhase.SWITCH,
            GateInput(f, false, false, Bundles.F8U.installd, StageState(emptyList(), emptyList(), false, null, false)),
        )
        val exynos = profileGate(Fixtures.facts(model = "SM-S948B", device = "m3s", soc = SocProps(manufacturer = "Samsung", model = "s5e9955")))
        assertEquals(Level.BLOCK, exynos.level(SwitchGates.ID_PROFILE))
        assertNull(exynos.profile)
        // Galaxy S23 Ultra: no profile (the S24 Ultra has one since 0.4.11).
        val s23u = profileGate(Fixtures.facts(model = "SM-S918B", device = "dm3q", soc = SocProps(manufacturer = "QTI", model = "SM8550")))
        assertEquals(Level.BLOCK, s23u.level(SwitchGates.ID_PROFILE))
        assertTrue(s23u.find(SwitchGates.ID_PROFILE)!!.finding.detail.contains("Galaxy S26 Ultra (SM-S948* / m3q / SM8850)"))
        val wrongCodename = profileGate(Fixtures.s26Ultra().copy(device = "pa3q"))
        assertEquals(Level.BLOCK, wrongCodename.level(SwitchGates.ID_PROFILE))
        assertTrue(wrongCodename.find(SwitchGates.ID_PROFILE)!!.finding.detail.contains("codename pa3q (profile: m3q)"))
    }

    @Test
    fun rootMustAnswerUid0() {
        val f = Bundles.S26U.facts
        for (probe in listOf(null, SuProbeResult(SuState.DENIED, null, null, ""), SuProbeResult(SuState.TIMEOUT, null, null, ""))) {
            val r = eval(GatePhase.SWITCH, input(Bundles.S26U).copy(facts = f.copy(root = f.root.copy(probe = probe))))
            assertEquals(Level.BLOCK, r.level(SwitchGates.ID_ROOT))
        }
    }

    @Test
    fun stageMustBeIdle() {
        val i = input(Bundles.F8U)
        val s = i.stage!!
        for (bad in listOf(
            null,
            s.copy(mounts = listOf("/data/local/tmp/oneos/data")),
            s.copy(activeBridges = listOf("/data/system/users")),
            s.copy(sessionActive = true),
        )) {
            for (phase in GatePhase.entries) {
                assertEquals("$phase $bad", Level.BLOCK, eval(phase, i.copy(stage = bad)).level(SwitchGates.ID_STAGE))
            }
        }
    }

    @Test
    fun switchNeedsThisPhonesPreparedImage() {
        val i = input(Bundles.S26U)
        val p = Profiles.S_ULTRA_8850
        assertEquals(Level.OK, eval(GatePhase.SWITCH, i).level(SwitchGates.ID_IMAGE))
        for (bad in listOf(
            stage(p, image = Images.ID_FIND_N6),
            stage(p).copy(marker = StageMarker(4, Profiles.ID_F8U, Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, 1)),
            stage(p).copy(marker = null),
            stage(p, verified = false),
            stage(p).copy(marker = StageMarker(3, p.id, Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, 1)),
        )) {
            assertEquals("$bad", Level.BLOCK, eval(GatePhase.SWITCH, i.copy(stage = bad)).level(SwitchGates.ID_IMAGE))
        }
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, i.copy(stage = null)).level(SwitchGates.ID_IMAGE))
        // Without appVersionCode the marker's build is not compared.
        assertEquals(
            Level.OK,
            eval(
                GatePhase.SWITCH,
                i.copy(appVersionCode = null, stage = stage(p).copy(marker = StageMarker(3, p.id, Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, 1))),
            ).level(SwitchGates.ID_IMAGE),
        )
    }

    @Test
    fun prepareNeedsThisPhonesVerifiedImage() {
        val i = input(Bundles.S26U)
        assertEquals(Level.OK, eval(GatePhase.PREPARE, i).level(SwitchGates.ID_IMAGE))
        val n6 = Images.FIND_N6
        val wrong = eval(GatePhase.PREPARE, i.copy(imageFile = ImageFileCheck(n6.gzName, n6.gzBytes, n6.gzSha256, n6.gzBytes)))
        assertEquals(Level.BLOCK, wrong.level(SwitchGates.ID_IMAGE))
        assertEquals("Wrong image for this phone", wrong.find(SwitchGates.ID_IMAGE)!!.finding.title)
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, i.copy(imageFile = null)).level(SwitchGates.ID_IMAGE))
        val x9u = Images.FIND_X9U
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, i.copy(imageFile = ImageFileCheck(null, x9u.gzBytes))).level(SwitchGates.ID_IMAGE))
        // Prepare has no ticks: the warnings are ticked at Switch.
        val r = eval(GatePhase.PREPARE, i)
        assertTrue(r.toTick.isEmpty())
        assertEquals(Level.WARN, r.level(SwitchGates.ID_CARRIER))
        assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
        assertNull(r.find(SwitchGates.ID_BATTERY))
        assertFalse(r.blocked)
    }

    @Test
    fun freeSpaceFromTheImagesRawSize() {
        val i = input(Bundles.S26U)
        val need = SpaceRule.toStage(Images.FIND_X9U, PackageSets.X9U_SULTRA)
        assertEquals(Level.OK, eval(GatePhase.PREPARE, i.copy(freeBytes = need)).level(SwitchGates.ID_SPACE))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, i.copy(freeBytes = need - 1)).level(SwitchGates.ID_SPACE))
        // The F8U's N6 image is smaller: the same free space is enough there.
        val n6Need = SpaceRule.toStage(Images.FIND_N6, PackageSets.N6_F8U)
        assertTrue(n6Need < need)
        assertEquals(Level.OK, eval(GatePhase.PREPARE, input(Bundles.F8U).copy(freeBytes = n6Need)).level(SwitchGates.ID_SPACE))
        // An adopted stage's old system.raw that root removes first counts.
        assertEquals(Level.OK, eval(GatePhase.PREPARE, i.copy(freeBytes = need - 100, reclaimBytes = 100)).level(SwitchGates.ID_SPACE))
        // At launch the image is staged: 11 GiB.
        assertEquals(Level.OK, eval(GatePhase.SWITCH, i.copy(freeBytes = 11L * SpaceRule.GIB)).level(SwitchGates.ID_SPACE))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, i.copy(freeBytes = 11L * SpaceRule.GIB - 1)).level(SwitchGates.ID_SPACE))
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, i.copy(freeBytes = null)).level(SwitchGates.ID_SPACE))
    }

    @Test
    fun battery() {
        val i = input(Bundles.F8U)
        fun level(b: BatteryInfo?) = eval(GatePhase.SWITCH, i.copy(facts = i.facts.copy(battery = b))).level(SwitchGates.ID_BATTERY)
        assertEquals(Level.OK, level(BatteryInfo(30, false, 41.9f)))
        assertEquals(Level.OK, level(BatteryInfo(5, true, 30f)))
        assertEquals(Level.BLOCK, level(BatteryInfo(29, false, 30f)))
        assertEquals(Level.BLOCK, level(BatteryInfo(90, true, 42f)))
        assertEquals(Level.BLOCK, level(BatteryInfo(90, true, null)))
        assertEquals(Level.BLOCK, level(null))
    }

    @Test
    fun carrierUnknownStillNeedsATick() {
        val r = eval(GatePhase.SWITCH, input(Bundles.F8U).copy(carrier = null))
        assertEquals(CarrierRules.maybeCallsAck(Images.systemName(Images.FIND_N6, Profiles.F8U)), r.find(SwitchGates.ID_CARRIER)!!.ack)
        assertEquals(CarrierRules.R_UNKNOWN, r.find(SwitchGates.ID_CARRIER)!!.finding.reason)
        assertFalse(r.allows(emptySet()))
        assertTrue(r.allows(setOf(r.find(SwitchGates.ID_CARRIER)!!.tickKey!!)))
    }

    @Test
    fun uncollectedLogsWarnWithoutTick() {
        val r = eval(GatePhase.SWITCH, input(Bundles.F8U).copy(uncollectedLogs = true))
        assertEquals(Level.WARN, r.level(SwitchGates.ID_LOGS))
        assertNull(r.find(SwitchGates.ID_LOGS)!!.ack)
        assertTrue(r.allows(emptySet()))
    }

    @Test
    fun everyGateFailsClosedWithNothingKnown() {
        val f = Bundles.S26U.facts.copy(root = RootSignals(), storage = null, battery = null, carrier = null)
        val r = SwitchGates.evaluate(GatePhase.SWITCH, GateInput(f, null, null, null, null))
        for (id in listOf(
            SwitchGates.ID_ROOT, SwitchGates.ID_IMAGE, SwitchGates.ID_INSTALLD, SwitchGates.ID_OLD_SWITCHER,
            SwitchGates.ID_STAGE, SwitchGates.ID_SPACE, SwitchGates.ID_SCREEN_LOCK, SwitchGates.ID_BATTERY,
        )) {
            assertEquals(id, Level.BLOCK, r.level(id))
        }
        assertTrue(r.blocked)
    }

    @Test
    fun stageMarkerRoundTrip() {
        val m = StageMarker(11, "f8u", "pixel11fold-yogi", "pixel-f8u", 1_792_000_000)
        val json = m.toJson()
        assertEquals(
            "{\n  \"schema\": \"oneos.stage/2\",\n  \"versionCode\": 11,\n  \"profile\": \"f8u\",\n" +
                "  \"image\": \"pixel11fold-yogi\",\n  \"set\": \"pixel-f8u\",\n  \"created\": 1792000000\n}\n",
            json,
        )
        assertEquals(m, StageMarker.parse(json))
        assertEquals(
            m,
            StageMarker.parse("""{"created":1792000000,"set":"pixel-f8u","image":"pixel11fold-yogi","profile":"f8u","versionCode":11,"schema":"oneos.stage/2"}"""),
        )
        // 0.3.0-0.3.2 wrote oneos.stage/1 without a set: still read (keep, restore), with no set.
        val v1 = "{\n  \"schema\": \"oneos.stage/1\",\n  \"versionCode\": 6,\n  \"profile\": \"s-ultra-8850\",\n" +
            "  \"image\": \"coloros17-findx9u\",\n  \"created\": 1792000000\n}\n"
        val old = StageMarker.parse(v1)
        assertEquals(StageMarker(6, "s-ultra-8850", "coloros17-findx9u", null, 1_792_000_000), old)
        assertEquals(v1, old!!.toJson())
        for (bad in listOf(
            "",
            "{}",
            json.replace("oneos.stage/2", "oneos.stage/3"),
            json.replace("oneos.stage/2", "oneos.stage/1"), // a set in a v1 marker
            v1.replace("oneos.stage/1", "oneos.stage/2"), // a v2 marker without a set
            json.replace("\"set\": \"pixel-f8u\"", "\"set\": \"\""),
            json.replace("pixel-f8u", "../x"),
            json.replace("\"versionCode\": 11", "\"versionCode\": \"11\""),
            json.replace("\"f8u\"", "\"Z Fold\""),
            json.replace("\"f8u\"", "\"../x\""),
            json.replace("\"created\": 1792000000", "\"created\": 1792000000, \"extra\": 1"),
            json.replace("\"versionCode\": 11,", ""),
            json.replace("\"versionCode\": 11", "\"versionCode\": 0"),
            json.replace("\"profile\": \"f8u\",", "\"profile\": \"f8u\", \"profile\": \"s-ultra-8850\","),
            "[1]",
        )) {
            assertNull(bad, StageMarker.parse(bad))
        }
        assertNotNull(StageMarker.parse("  $json  "))
    }

    /** 0.3.7: the Fold takes the Pixel 11 Fold image with its own set; runs 41-44 booted it there, so no untested tick. */
    @Test
    fun foldTakesThePixelImageAsATestedPair() {
        val image = Images.PIXEL_YOGI
        val i = input(Bundles.F8U, image = image)
        for (phase in GatePhase.entries) {
            val r = eval(phase, i)
            assertEquals("$phase", image, r.image)
            assertEquals(PackageSets.PIXEL_F8U, r.set)
            assertFalse("$phase", r.blocked)
            assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
            assertEquals("Tested phone: Z Fold (F8U)", r.find(SwitchGates.ID_PROFILE)!!.finding.title)
            assertTrue(r.find(SwitchGates.ID_PROFILE)!!.finding.detail.endsWith(", with the Pixel 11 Fold image."))
            // Its loader needs SVE2 (and SVE): the Fold's SM8850 has both.
            assertEquals(Level.OK, r.level(CpuRules.ID_OK))
        }
        val r = eval(GatePhase.SWITCH, i)
        assertEquals(Level.OK, r.level(SwitchGates.ID_IMAGE))
        assertEquals("Pixel 11 Fold image prepared", r.find(SwitchGates.ID_IMAGE)!!.finding.title)
        assertTrue(r.toTick.none { it.id == SwitchGates.ID_PROFILE })
        // The same ticks as the tested Find N6 pair on this phone: none.
        assertTrue(r.allows(emptySet()))
        assertTrue(eval(GatePhase.SWITCH, input(Bundles.F8U)).allows(emptySet()))
        // {system} in the ticks and texts: the image's name, no variant (the Fold has no other Pixel image).
        assertEquals("Pixel 11 Fold", Images.systemName(image, Profiles.F8U))
        assertEquals("ColorOS 17", Images.systemName(Images.FIND_N6, Profiles.F8U))
    }

    /** An image that has not run on the Fold (the Pixel image before runs 41-44) needs the untested tick naming it. */
    @Test
    fun anUntestedImageOnTheFoldNeedsTheUntestedTick() {
        val p = Profiles.F8U.copy(choices = Profiles.F8U.choices.map { if (it.imageId == Images.ID_PIXEL_YOGI) it.copy(tested = false) else it })
        val profiles = listOf(p) + Profiles.BUILT_IN.drop(1)
        val image = Images.PIXEL_YOGI
        val i = input(Bundles.F8U, image = image).copy(stage = stage(p, image.id))
        val prepare = SwitchGates.evaluate(GatePhase.PREPARE, i, profiles)
        assertEquals(image, prepare.image)
        assertEquals(PackageSets.PIXEL_F8U, prepare.set)
        assertFalse(prepare.blocked)
        assertEquals(Level.WARN, prepare.level(SwitchGates.ID_PROFILE))
        assertEquals("First sessions of the Pixel 11 Fold image", prepare.find(SwitchGates.ID_PROFILE)!!.finding.title)
        assertTrue(prepare.find(SwitchGates.ID_PROFILE)!!.finding.detail.contains("with Find N6, not yet with this image"))
        assertTrue(prepare.toTick.isEmpty())

        val r = SwitchGates.evaluate(GatePhase.SWITCH, i, profiles)
        assertEquals(image, r.image)
        assertEquals(PackageSets.PIXEL_F8U, r.set)
        assertFalse(r.blocked)
        val ack = r.find(SwitchGates.ID_PROFILE)!!.ack
        assertEquals(SwitchGates.untestedAck(p, image), ack)
        assertEquals("I understand this phone hasn't run Pixel 11 Fold before", ack)
        assertFalse(r.allows(emptySet()))
        assertTrue(r.allows(r.toTick.mapNotNull { it.tickKey }.toSet()))
        // The tick for the phone-wide text (or none) does not count.
        assertFalse(r.allows(setOf("${SwitchGates.ID_PROFILE}|${SwitchGates.untestedAck(p)}")))
        // The tested pair on the same phone: nothing to tick.
        assertTrue(SwitchGates.evaluate(GatePhase.SWITCH, input(Bundles.F8U), profiles).allows(emptySet()))
    }

    /** The S Ultra profiles and the S25 take the Find X9 Ultra (CN) build, tested on them since 0.4.7 (0.3.3-0.3.6: the IN build too; until 0.4.7 an untested tick). */
    @Test
    fun sUltraTakesTheX9UltraBuild() {
        for ((phone, p) in listOf(Bundles.S26U to Profiles.S_ULTRA_8850, Bundles.S25U to Profiles.S_ULTRA_8750, Bundles.S25 to Profiles.S_8750)) {
            // 0.4.10: the S26 Ultra also takes the Pixel 11 Pro image (SM8850 has SVE); 0.4.11: the IN build first;
            // 0.4.22: the SM8750 phones the Pixel 9 Pro XL image (no SVE needed).
            val usual = listOf(Images.FIND_X9U_IN, Images.FIND_X9U)
            // 0.4.27: Infinity-X, on every phone; 0.4.31: HyperOS after it.
            assertEquals(usual + (if (p == Profiles.S_ULTRA_8850) Images.PIXEL_KODIAK else Images.PIXEL_KOMODO) + Images.INFINITYX + Images.HYPEROS_LHASA, p.images())
            for ((image, set) in listOf(Images.FIND_X9U to PackageSets.X9U_SULTRA)) {
                for (phase in GatePhase.entries) {
                    val r = eval(phase, input(phone, image = image))
                    assertEquals("${p.id} ${image.id} $phase", image, r.image)
                    assertEquals(set, r.set)
                    assertFalse(r.blocked)
                    assertEquals(Level.OK, r.level(SwitchGates.ID_PROFILE))
                }
                assertNull(eval(GatePhase.SWITCH, input(phone, image = image)).find(SwitchGates.ID_PROFILE)!!.ack)
            }
        }
        // The CPU rule comes with the image: the CN build needs nothing beyond arm64 (its apps WARN on the
        // SM8750); the Pixel image's loader needs SVE and SVE2, which the SM8750 lacks (it is the Fold's only).
        assertEquals(Level.WARN, eval(GatePhase.SWITCH, input(Bundles.S25U, image = Images.FIND_X9U)).level(CpuRules.ID_APP_FEATURES))
        assertNull(eval(GatePhase.SWITCH, input(Bundles.S25U, image = Images.FIND_X9U)).find(CpuRules.ID_MISSING))
        val pixelOnSm8750 = CpuRules.forImage(Images.PIXEL_YOGI, Bundles.S25U.facts.cpu)
        assertEquals(CpuRules.ID_MISSING, pixelOnSm8750.id)
        assertEquals(Level.WARN, pixelOnSm8750.level)
        assertEquals("CPU lacks SVE, SVE2 used by Pixel 11 Fold", pixelOnSm8750.title)
        assertEquals(CpuRules.ID_OK, CpuRules.forImage(Images.PIXEL_YOGI, Bundles.F8U.facts.cpu).id)
    }

    @Test
    fun anImageThePhoneDoesNotTakeIsBlocked() {
        // PREPARE: the X9U (CN) .gz on the Fold, the N6 or Pixel .gz on an S Ultra or the S25.
        val wrong = listOf(Bundles.F8U to Images.FIND_X9U) +
            listOf(Bundles.S26U, Bundles.S25U, Bundles.S25).flatMap { listOf(it to Images.FIND_N6, it to Images.PIXEL_YOGI) }
        for ((phone, image) in wrong) {
            val r = eval(GatePhase.PREPARE, input(phone).copy(imageFile = gz(image)))
            assertEquals(Level.BLOCK, r.level(SwitchGates.ID_IMAGE))
            assertEquals("Wrong image for this phone", r.find(SwitchGates.ID_IMAGE)!!.finding.title)
            assertTrue(r.find(SwitchGates.ID_IMAGE)!!.finding.detail.contains("takes the"))
            assertNull(r.image)
            assertNull(r.set)
            assertTrue(r.blocked)
        }
        // Nothing picked: the BLOCK says what the phone takes.
        val none = eval(GatePhase.PREPARE, input(Bundles.F8U).copy(imageFile = null))
        assertEquals("Pick the image first", none.find(SwitchGates.ID_IMAGE)!!.finding.title)
        assertTrue(none.find(SwitchGates.ID_IMAGE)!!.finding.detail.contains("OneOS_Pixel11Fold_Full_ZFold8.img.gz"))
        // SWITCH: a stage holding the CN image on the Fold.
        val cn = eval(GatePhase.SWITCH, input(Bundles.F8U).copy(stage = stage(Profiles.F8U, Images.ID_FIND_X9U, set = PackageSets.ID_X9U_SULTRA)))
        assertEquals(Level.BLOCK, cn.level(SwitchGates.ID_IMAGE))
        assertEquals("Prepared for another phone or image", cn.find(SwitchGates.ID_IMAGE)!!.finding.title)
        // SWITCH: a stage holding the Pixel image on an S Ultra.
        val px = eval(GatePhase.SWITCH, input(Bundles.S26U).copy(stage = stage(Profiles.S_ULTRA_8850, Images.ID_PIXEL_YOGI, set = PackageSets.ID_PIXEL_F8U)))
        assertEquals(Level.BLOCK, px.level(SwitchGates.ID_IMAGE))
        assertEquals("Prepared for another phone or image", px.find(SwitchGates.ID_IMAGE)!!.finding.title)
    }

    /** The staged image decides the set: a marker with another set (or none, 0.3.2) is never switched to. */
    @Test
    fun theStagedImageDecidesTheSet() {
        val p = Profiles.F8U
        val i = input(Bundles.F8U, image = Images.PIXEL_YOGI)
        assertEquals(Level.OK, eval(GatePhase.SWITCH, i).level(SwitchGates.ID_IMAGE))
        // The Pixel image with a ColorOS set, the old IN set, another or none: never.
        for (set in listOf(PackageSets.ID_N6_F8U, PackageSets.ID_X9U_SULTRA, "x9u-in-f8u", "pixel-other", null)) {
            val r = eval(GatePhase.SWITCH, i.copy(stage = stage(p, Images.ID_PIXEL_YOGI, set = set)))
            assertEquals("$set", Level.BLOCK, r.level(SwitchGates.ID_IMAGE))
            assertNull(r.image)
            assertNull(r.set)
        }
        // Nor the Find N6 image with the Pixel set.
        assertEquals(Level.BLOCK, eval(GatePhase.SWITCH, i.copy(stage = stage(p, Images.ID_FIND_N6, set = PackageSets.ID_PIXEL_F8U))).level(SwitchGates.ID_IMAGE))
        // A 0.3.2 stage (no set, build 6): prepare again.
        val old = eval(GatePhase.SWITCH, i.copy(appVersionCode = 7, stage = stage(p, Images.ID_FIND_N6, set = null).copy(marker = StageMarker(6, p.id, Images.ID_FIND_N6, null, 1))))
        assertEquals("Prepared by another OneOS version", old.find(SwitchGates.ID_IMAGE)!!.finding.title)
        val noSet = eval(GatePhase.SWITCH, i.copy(appVersionCode = null, stage = stage(p, Images.ID_FIND_N6, set = null)))
        assertEquals("Prepared with another file set", noSet.find(SwitchGates.ID_IMAGE)!!.finding.title)
        // A stage the IN build left (0.3.3-0.3.6): its image is no longer one the Fold takes.
        val inStage = eval(GatePhase.SWITCH, i.copy(stage = stage(p, "coloros17-findx9u-in", set = "x9u-in-f8u")))
        assertEquals("Prepared for another phone or image", inStage.find(SwitchGates.ID_IMAGE)!!.finding.title)
    }

    @Test
    fun freeSpaceFromTheChosenImage() {
        val cnNeed = SpaceRule.toStage(Images.FIND_X9U, PackageSets.X9U_SULTRA)
        val cn = input(Bundles.S26U, image = Images.FIND_X9U).copy(freeBytes = cnNeed)
        assertEquals(Level.OK, eval(GatePhase.PREPARE, cn).level(SwitchGates.ID_SPACE))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, cn.copy(freeBytes = cnNeed - 1)).level(SwitchGates.ID_SPACE))
        // On the Fold: the Pixel image is smaller than the Find N6 one, with a bigger set; each needs its own.
        val n6Need = SpaceRule.toStage(Images.FIND_N6, PackageSets.N6_F8U)
        val pixelNeed = SpaceRule.toStage(Images.PIXEL_YOGI, PackageSets.PIXEL_F8U)
        assertTrue(pixelNeed < n6Need)
        val n6 = input(Bundles.F8U, image = Images.FIND_N6).copy(freeBytes = pixelNeed)
        val pixel = input(Bundles.F8U, image = Images.PIXEL_YOGI).copy(freeBytes = pixelNeed)
        assertEquals(Level.OK, eval(GatePhase.PREPARE, pixel).level(SwitchGates.ID_SPACE))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, n6).level(SwitchGates.ID_SPACE))
        assertTrue(eval(GatePhase.PREPARE, n6).find(SwitchGates.ID_SPACE)!!.finding.detail.contains("the Find N6 image"))
        assertEquals(Level.OK, eval(GatePhase.PREPARE, n6.copy(freeBytes = n6Need)).level(SwitchGates.ID_SPACE))
        val short = eval(GatePhase.PREPARE, pixel.copy(freeBytes = pixelNeed - 1))
        assertEquals(Level.BLOCK, short.level(SwitchGates.ID_SPACE))
        assertTrue(short.find(SwitchGates.ID_SPACE)!!.finding.detail.contains("the Pixel 11 Fold image 6.6 GB"))
        // No image picked yet: no space figure (the image gate BLOCKs).
        assertNull(eval(GatePhase.PREPARE, cn.copy(imageFile = null)).find(SwitchGates.ID_SPACE))
    }

    /** "Use the image already on this phone": the stage's system.raw is identified like a picked file. */
    @Test
    fun theImageAlreadyOnThePhone() {
        val i = input(Bundles.F8U).copy(imageFile = null)
        val pixelRaw = eval(GatePhase.PREPARE, i.copy(onPhone = StagedRaw(Images.PIXEL_YOGI.rawBytes)))
        assertEquals(Level.OK, pixelRaw.level(SwitchGates.ID_IMAGE))
        assertEquals(Images.PIXEL_YOGI, pixelRaw.image)
        assertEquals(PackageSets.PIXEL_F8U, pixelRaw.set)
        val n6 = eval(GatePhase.PREPARE, i.copy(onPhone = StagedRaw(Images.FIND_N6.rawBytes, Images.FIND_N6.rawSha256)))
        assertEquals(Images.FIND_N6, n6.image)
        assertFalse(n6.blocked)
        // The CN image in the Fold's stage, or nothing there: BLOCK.
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, i.copy(onPhone = StagedRaw(Images.FIND_X9U.rawBytes))).level(SwitchGates.ID_IMAGE))
        assertEquals(Level.BLOCK, eval(GatePhase.PREPARE, i.copy(onPhone = StagedRaw(null))).level(SwitchGates.ID_IMAGE))
        // With the image on the phone chosen, a picked file does not count.
        val both = eval(GatePhase.PREPARE, input(Bundles.F8U).copy(onPhone = StagedRaw(Images.PIXEL_YOGI.rawBytes)))
        assertEquals(Images.PIXEL_YOGI, both.image)
    }
}
