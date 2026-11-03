package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.PackageSet
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.model.ProbeStatus
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SessionEnv
import com.fahadali.oneos.core.model.ShaList
import com.fahadali.oneos.core.model.StageMarker
import com.fahadali.oneos.core.model.StagedRaw
import com.fahadali.oneos.core.model.SystemFamily
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StageStatusTest {
    private val s = RootScript.STAGE
    private val profile = Profiles.S_ULTRA_8850
    private val image = Images.FIND_X9U
    private val set = PackageSets.X9U_SULTRA

    private fun status(out: Map<String, String>, missing: Set<String> = emptySet(), failed: Set<String> = emptySet()): StageStatus {
        val statuses = StageStatus.OUTPUTS.keys.associateWith { id ->
            when (id) {
                in failed -> ProbeStatus.FAILED
                in missing -> ProbeStatus.NOT_PRESENT
                else -> ProbeStatus.OK
            }
        }
        return StageStatus.parse(statuses) { path -> out[StageStatus.OUTPUTS.entries.first { it.value == path }.key] }
    }

    private val names = RootScript.SCRIPTS + set.names
    private val shas = names.associateWith { Hashes.sha256(it) }

    /** [profile]'s stage prepared with [image] and [set] (by default the S Ultra's, with the X9U CN build). */
    private fun prepared(
        extra: Map<String, String> = emptyMap(),
        image: ImageRef = this.image,
        set: PackageSet = this.set,
        profile: PhoneProfile = this.profile,
    ): Map<String, String> = preparedFor(image, set, profile) + extra

    private fun preparedFor(image: ImageRef, set: PackageSet, profile: PhoneProfile): Map<String, String> {
        val names = RootScript.SCRIPTS + set.names
        val shas = names.associateWith { Hashes.sha256(it) }
        return mapOf(
            "stage.dir" to "dir 0 0 755\n",
            "stage.list" to (names.map { "f 0 644 10 $it" } + listOf("f 0 644 ${image.rawBytes} system.raw", "d 0 755 4096 data", "d 0 755 4096 bin", "f 0 755 30000 bin/oneos_root.sh"))
                .joinToString("\n", postfix = "\n"),
            "stage.marker" to StageMarker(4, profile.id, image.id, set.id, 1_792_000_000).toJson(),
            "stage.sums" to ShaList.render(shas),
            "stage.hashes" to (shas.entries.joinToString("") { "${it.value}  $s/${it.key}\n" } + "${"c".repeat(64)}  $s/bin/oneos_root.sh\n"),
            "stage.raw" to "now ${image.rawBytes} 64773:1234:${image.rawBytes}:1792000000\nid ${image.rawBytes} ${image.rawSha256} 64773:1234:${image.rawBytes}:1792000000\n",
            "stage.env" to SessionEnv.generate(profile),
            "stage.table" to "${"d".repeat(64)}  $s/host_installd.table\n",
            "stage.mounts" to "root ok\n",
            "stage.bridges" to "",
            "stage.loops" to "",
            "stage.session" to "boot=11111111-2222\n",
            "stage.guest" to "packages com.oplus.\n",
            "stage.old" to "",
            "stage.tools" to "/data/adb/ksu/bin/busybox\n/data/adb/ksu/bin/resetprop\n",
            "stage.props" to "ro.csc.sales_code=ATT\nro.boot.sales_code=ATT\nro.csc.countryiso_code=US\ngsm.sim.operator.iso-country=us\n",
        )
    }

    @Test
    fun preparedStageVerifies() {
        val st = status(prepared())
        assertTrue(st.complete)
        assertTrue(st.ours)
        assertEquals(GuestData.COLOROS, st.guest)
        assertEquals("c".repeat(64), st.rootScriptSha)
        assertEquals(emptyList<String>(), st.verify(profile, image, set))
        val gate = st.stageState(profile)!!
        assertTrue(gate.filesVerified)
        assertFalse(gate.sessionActive)
        assertEquals(profile.id, gate.marker!!.profileId)
        assertEquals(true, com.fahadali.oneos.core.model.CarrierRules.voLteOnly(st.carrier))
    }

    /** status.list reads a 0.3.6 stage at its old path until the root script renames it: the same status. */
    @Test
    fun aStageAtItsOldPathReadsTheSame() {
        val old = prepared().mapValues { (k, v) -> if (k == "stage.hashes" || k == "stage.table") v.replace("$s/", "${RootScript.LEGACY_STAGE}/") else v }
        assertTrue(old.getValue("stage.hashes").contains("/data/local/tmp/lineage_stage/"))
        val st = status(old)
        assertEquals("c".repeat(64), st.rootScriptSha)
        assertEquals(emptyList<String>(), st.verify(profile, image, set))
        // Another folder's hash lines are never taken for the stage's.
        val other = status(prepared(mapOf("stage.hashes" to prepared().getValue("stage.hashes").replace("$s/", "/data/local/tmp/oneos_x/"))))
        assertTrue(other.hashes.isEmpty())
    }

    @Test
    fun changesAreFound() {
        fun problems(extra: Map<String, String>) = status(prepared(extra)).verify(profile, image, set)
        val changed = prepared()["stage.hashes"]!!.replaceFirst(shas.getValue("art_payload.img"), "e".repeat(64))
        assertTrue(problems(mapOf("stage.hashes" to changed)).contains("art_payload.img changed since it was prepared"))
        val leftover = prepared()["stage.list"] + "f 0 644 10 framework_patched.jar\n"
        assertTrue(problems(mapOf("stage.list" to leftover)).any { it.startsWith("framework_patched.jar") })
        val moved = "now ${image.rawBytes} 64773:9999:${image.rawBytes}:1792000001\nid ${image.rawBytes} ${image.rawSha256} 64773:1234:${image.rawBytes}:1792000000\n"
        assertTrue(problems(mapOf("stage.raw" to moved)).contains("system.raw changed since it was verified"))
        val n6 = "now 1 x\nid ${Images.FIND_N6.rawBytes} ${Images.FIND_N6.rawSha256} x\n"
        assertTrue(problems(mapOf("stage.raw" to n6)).contains("system.raw is not the Find X9 Ultra image"))
        val env = SessionEnv.generate(profile) + "ONEOS_RETURN_MAX=0\n"
        assertTrue(problems(mapOf("stage.env" to env)).any { it.contains("forbidden key ONEOS_RETURN_MAX") })
    }

    @Test
    fun foreignAndUnsafeStages() {
        // OneLineage's stage on the S26 Ultra: drwxrwxrwx, no marker.
        val s26 = status(prepared(mapOf("stage.dir" to "dir 2000 2000 777\n", "stage.guest" to "packages org.lineageos.\n")), missing = setOf("stage.marker"))
        assertFalse(s26.safe)
        assertTrue(s26.foreign)
        assertEquals(GuestData.LINEAGEOS, s26.guest)
        // Its persist_session.active never counts as a session (it is moved aside unread).
        val withSession = status(
            prepared(mapOf("stage.dir" to "dir 0 0 777\n", "stage.session" to "boot=b\nactive\nformat=1\n")),
            missing = setOf("stage.marker"),
        )
        assertFalse(withSession.sessionActive)
        // A root-owned 0755 stage without a marker (deploy-phone.sh on the owner's Fold): safe, still foreign.
        val fold = status(prepared(), missing = setOf("stage.marker"))
        assertTrue(fold.safe)
        assertFalse(fold.ours)
        assertNull(fold.stageState(profile)!!.marker)
    }

    @Test
    fun beginModes() {
        val k = RootScript.BeginMode.KEEP
        val a = RootScript.BeginMode.ASIDE
        assertEquals(listOf(k, a), status(prepared()).beginModes(null))
        assertEquals(listOf(k, a), status(prepared(), missing = setOf("stage.marker")).beginModes(null))
        assertEquals(listOf(a), status(prepared(mapOf("stage.dir" to "dir 2000 2000 777\n", "stage.guest" to "packages org.lineageos.\n")), missing = setOf("stage.marker")).beginModes(null))
        assertEquals(listOf(a), status(prepared(mapOf("stage.guest" to "packages none\n", "stage.list" to "f 0 644 1 x.log\n")), missing = setOf("stage.marker")).beginModes(null))
        // A preparation of OneOS's that stopped half way (bin/oneos_root.sh, no marker, no guest data yet): keep it.
        val half = status(prepared(mapOf("stage.guest" to "packages none\n")), missing = setOf("stage.marker"))
        assertTrue(half.partial)
        assertEquals(listOf(k, a), half.beginModes(null))
        assertEquals(emptyList<RootScript.BeginMode>(), status(prepared(mapOf("stage.dir" to "link\n"))).beginModes(null))
        val fresh = status(mapOf("stage.dir" to "dir 0 0 755\n", "stage.list" to "d 0 755 4096 bin\nf 0 755 1 bin/oneos_root.sh\n", "stage.mounts" to "root ok\n"))
        assertEquals(listOf(RootScript.BeginMode.NEW), fresh.beginModes(null))
    }

    /**
     * 0.3.3: guest data stays with the image that made it; another image's data is only moved aside (root refuses
     * to keep it). 0.3.7: the Fold's two systems, ColorOS (Find N6) and Pixel.
     */
    @Test
    fun anotherImagesGuestDataIsOnlyMovedAside() {
        val k = RootScript.BeginMode.KEEP
        val a = RootScript.BeginMode.ASIDE
        val fold = Profiles.F8U
        val n6 = Images.FIND_N6
        val pixelId = Images.ID_PIXEL_YOGI
        // The Fold's stage of the Find N6 global build with its ColorOS data.
        val st = status(prepared(image = n6, set = PackageSets.N6_F8U, profile = fold))
        assertEquals(listOf(k, a), st.beginModes(n6.id))
        assertNull(st.otherImageData(n6.id))
        assertEquals(listOf(a), st.beginModes(pixelId))
        assertEquals(n6.id, st.otherImageData(pixelId))
        // The other way round (a Pixel guest's packages are none of the ColorOS or LineageOS words), and a data
        // folder ColorOS never filled: the same.
        val pixelStage = status(prepared(mapOf("stage.guest" to ""), image = Images.PIXEL_YOGI, set = PackageSets.PIXEL_F8U, profile = fold))
        assertEquals(GuestData.OTHER, pixelStage.guest)
        assertEquals(listOf(k, a), pixelStage.beginModes(pixelId))
        assertEquals(listOf(a), pixelStage.beginModes(n6.id))
        assertEquals(pixelId, pixelStage.otherImageData(n6.id))
        assertEquals(listOf(a), status(prepared(mapOf("stage.guest" to "packages none\n"), image = n6, set = PackageSets.N6_F8U, profile = fold)).beginModes(pixelId))
        // Prepared but never switched (no guest data): kept for either image.
        val noData = status(prepared(image = n6, set = PackageSets.N6_F8U, profile = fold), missing = setOf("stage.guest"))
        assertEquals(GuestData.NONE, noData.guest)
        assertEquals(listOf(k, a), noData.beginModes(pixelId))
        assertNull(noData.otherImageData(pixelId))
        // A 0.3.2 stage (oneos.stage/1) names its image too.
        val v1 = StageMarker(6, fold.id, n6.id, null, 1_792_000_000).toJson()
        assertEquals(listOf(a), status(prepared(mapOf("stage.marker" to v1), image = n6, set = PackageSets.N6_F8U, profile = fold)).beginModes(pixelId))
        // Not identified yet: as before (Prepare is blocked until it is).
        assertEquals(listOf(k, a), st.beginModes(null))
    }

    /**
     * 0.3.7: status.list names Pixel's launcher, so a Pixel guest's data reads as Pixel data, and data stays with its
     * own system: ColorOS data is never offered "keep" for the Pixel image, nor Pixel data for a ColorOS image, also
     * on a stage OneOS did not prepare (scripts/deploy-phone.sh, no marker) or one whose preparation stopped.
     */
    @Test
    fun guestDataStaysWithItsOwnSystem() {
        val k = RootScript.BeginMode.KEEP
        val a = RootScript.BeginMode.ASIDE
        val fold = Profiles.F8U
        val n6 = Images.FIND_N6
        val pixel = Images.PIXEL_YOGI
        val pixelLine = "packages ${StageStatus.PIXEL_WORD}\n"
        assertEquals("com.google.android.apps.nexuslauncher", StageStatus.PIXEL_WORD)
        fun pixelStage(missing: Set<String> = emptySet(), extra: Map<String, String> = emptyMap()) =
            status(prepared(mapOf("stage.guest" to pixelLine) + extra, image = pixel, set = PackageSets.PIXEL_F8U, profile = fold), missing = missing)
        fun n6Stage(missing: Set<String> = emptySet(), extra: Map<String, String> = emptyMap()) =
            status(prepared(extra, image = n6, set = PackageSets.N6_F8U, profile = fold), missing = missing)

        // Parsing: Pixel's launcher alone is Pixel data; with a ColorOS package it is ColorOS data (as root decides).
        assertEquals(GuestData.PIXEL, pixelStage().guest)
        assertEquals(GuestData.COLOROS, status(prepared(mapOf("stage.guest" to "packages com.oplus.\n$pixelLine"))).guest)
        assertEquals(GuestData.LINEAGEOS, status(prepared(mapOf("stage.guest" to "packages org.lineageos.\n$pixelLine"))).guest)
        assertEquals(SystemFamily.PIXEL, GuestData.PIXEL.family)
        assertEquals(SystemFamily.COLOROS, GuestData.COLOROS.family)
        for (g in listOf(GuestData.NONE, GuestData.EMPTY, GuestData.LINEAGEOS, GuestData.OTHER)) {
            assertNull(g.family)
            assertFalse(g.otherSystemThan(pixel))
            assertFalse(g.otherSystemThan(n6))
        }
        assertTrue(GuestData.COLOROS.otherSystemThan(pixel))
        assertTrue(GuestData.PIXEL.otherSystemThan(n6))
        assertFalse(GuestData.PIXEL.otherSystemThan(pixel))

        // OneOS's own stages: as before (the marker's image decides).
        assertEquals(listOf(k, a), pixelStage().beginModes(pixel.id))
        assertEquals(listOf(a), pixelStage().beginModes(n6.id))
        // A stage OneOS did not prepare (deploy-phone.sh: no marker, no root script in bin).
        val noBin = mapOf("stage.list" to "f 0 644 10 system.raw\nd 0 755 4096 data\n")
        val foreignN6 = n6Stage(setOf("stage.marker"), noBin)
        assertTrue(foreignN6.foreign)
        assertEquals(listOf(k, a), foreignN6.beginModes(null))
        assertEquals(listOf(k, a), foreignN6.beginModes(n6.id))
        assertEquals(listOf(a), foreignN6.beginModes(pixel.id))
        val foreignPixel = pixelStage(setOf("stage.marker"), noBin)
        assertTrue(foreignPixel.foreign)
        assertEquals(listOf(k, a), foreignPixel.beginModes(null))
        assertEquals(listOf(k, a), foreignPixel.beginModes(pixel.id))
        assertEquals(listOf(a), foreignPixel.beginModes(n6.id))
        // A preparation that stopped (no marker, OneOS's root script in bin).
        val partialPixel = pixelStage(setOf("stage.marker"))
        assertTrue(partialPixel.partial)
        assertEquals(listOf(k, a), partialPixel.beginModes(pixel.id))
        assertEquals(listOf(a), partialPixel.beginModes(n6.id))
        val partialN6 = n6Stage(setOf("stage.marker"))
        assertTrue(partialN6.partial)
        assertEquals(listOf(k, a), partialN6.beginModes(n6.id))
        assertEquals(listOf(a), partialN6.beginModes(pixel.id))
        // A marker that names another image than its data's system (deploy-phone.sh over an app stage without --fresh).
        val lying = n6Stage(extra = mapOf("stage.guest" to pixelLine))
        assertTrue(lying.ours)
        assertEquals(listOf(a), lying.beginModes(n6.id))
        // An image no build knows (a retired one): no family to compare, the marker still decides.
        assertEquals(listOf(k, a), foreignPixel.beginModes("coloros16-findx8u"))
    }

    @Test
    fun runningOrUnfinishedSessions() {
        val mounted = status(prepared(mapOf("stage.mounts" to "root ok\ninit $s/rootfs\nself $s/rootfs\n")))
        assertEquals(listOf("$s/rootfs"), mounted.mounts)
        assertTrue(mounted.sessionActive)
        val hard = status(prepared(mapOf("stage.session" to "boot=new\nactive\nformat=2\nboot_id=old\nepoch=1\n")))
        assertTrue(hard.unfinishedSession)
        assertTrue(hard.sessionActive)
        val same = status(prepared(mapOf("stage.session" to "boot=b\nactive\nformat=2\nboot_id=b\n")))
        assertFalse(same.unfinishedSession)
        assertTrue(same.sessionActive)
    }

    @Test
    fun incompleteChecksFailClosed() {
        assertNull(status(prepared(), failed = setOf("stage.mounts")).stageState(profile))
        assertNull(status(prepared(mapOf("stage.mounts" to ""))).stageState(profile))
        val absent = status(emptyMap(), missing = StageStatus.OUTPUTS.keys - "stage.mounts" - "stage.session" - "stage.bridges" - "stage.loops" - "stage.old" - "stage.tools" - "stage.props")
        assertFalse(absent.exists)
        assertTrue(absent.empty)
    }

    /** 0.3.7: the Pixel image on the Fold, with its own set; the marker names both, and only that pair verifies. */
    @Test
    fun theMarkersImageAndSetDecide() {
        val fold = Profiles.F8U
        val pixel = Images.PIXEL_YOGI
        val pixelSet = PackageSets.PIXEL_F8U
        val st = status(prepared(image = pixel, set = pixelSet, profile = fold))
        assertEquals(pixel to pixelSet, st.staged(fold))
        assertEquals(emptyList<String>(), st.verify(fold, pixel, pixelSet))
        assertTrue(st.stageState(fold)!!.filesVerified)
        // Another pair against this stage, or this stage for another phone.
        assertTrue(st.verify(fold, Images.FIND_N6, PackageSets.N6_F8U).any { it.startsWith("the marker names pixel11fold-yogi with pixel-f8u for f8u") })
        assertTrue(st.verify(fold, pixel, PackageSets.N6_F8U).any { it.contains("n6-f8u is not the Pixel 11 Fold set for f8u") })
        assertNull(st.staged(Profiles.S_ULTRA_8850))
        assertFalse(st.stageState(Profiles.S_ULTRA_8850)!!.filesVerified)
        // A marker naming a set that is not the image's on this phone: never verified.
        val wrongSet = status(prepared(mapOf("stage.marker" to StageMarker(4, fold.id, pixel.id, PackageSets.ID_N6_F8U, 1).toJson()), image = pixel, set = pixelSet, profile = fold))
        assertTrue(wrongSet.ours)
        assertNull(wrongSet.staged(fold))
        assertFalse(wrongSet.stageState(fold)!!.filesVerified)
    }

    /**
     * Files of one set left in a stage prepared with another: what the session scripts would bind or read is
     * flagged (root's check_files refuses them at launch; finish moves them to the attic).
     */
    @Test
    fun anotherSetsFilesAreLeftovers() {
        val fold = Profiles.F8U
        fun problems(image: ImageRef, set: PackageSet, extra: String) =
            status(prepared(mapOf("stage.list" to preparedFor(image, set, fold).getValue("stage.list") + extra), image = image, set = set, profile = fold))
                .verify(fold, image, set)
        // The Pixel set's files in a ColorOS stage.
        for (n in listOf("OneOSPixelStatusBar.apk", "OneOSPhoneInjection.apk", "oneos-telephony.jar", "oneos-telephony.sha256", "gmssystem_payload.img")) {
            assertTrue(n, problems(Images.FIND_N6, PackageSets.N6_F8U, "f 0 644 10 $n\n").contains("$n is in the stage but was not prepared"))
        }
        // The session's own watchdog feeder is not another set's file.
        assertFalse(problems(Images.FIND_N6, PackageSets.N6_F8U, "f 0 700 10 oneos_wdog_feeder.sh\n").any { "oneos_wdog_feeder.sh" in it })
        // ColorOS's files in the Pixel stage.
        for (n in listOf("surfaceflinger_patched", "oplus-services_patched.jar", "OneOSWallpapersFoldGrid.apk")) {
            assertTrue(n, problems(Images.PIXEL_YOGI, PackageSets.PIXEL_F8U, "f 0 644 10 $n\n").contains("$n is in the stage but was not prepared"))
        }
        // The sessions' own state files are not leftovers.
        assertEquals(emptyList<String>(), problems(Images.PIXEL_YOGI, PackageSets.PIXEL_F8U, "f 0 644 10 takeover_app.log\nf 0 644 10 payload_loops\n"))
    }

    /** A 0.3.0-0.3.2 stage (oneos.stage/1, no set): still OneOS's (keep, restore), never verified for a switch. */
    @Test
    fun anOlderStageStaysOursButDoesNotSwitch() {
        val v1 = StageMarker(6, profile.id, image.id, null, 1_792_000_000).toJson()
        val st = status(prepared(mapOf("stage.marker" to v1, "stage.session" to "boot=new\nactive\nformat=2\nboot_id=old\n")))
        assertTrue(st.ours)
        assertTrue(st.unfinishedSession)
        assertEquals(listOf(RootScript.BeginMode.KEEP, RootScript.BeginMode.ASIDE), st.beginModes(image.id))
        assertNull(st.staged(profile))
        assertFalse(st.stageState(profile)!!.filesVerified)
        assertTrue(st.verify(profile, image, set).any { it.contains("with no file set") })
    }

    /**
     * Google services may be hidden only where a session can hide them (a launch writes the 1): never on a CN
     * build (none), nor on the Pixel image, whose sessions present them (oneos_switch.sh refuses).
     */
    @Test
    fun hiddenGoogleServicesOnlyWhereASessionCanHideThem() {
        val hidden = SessionEnv.generate(profile).replace("ONEOS_GUEST_HIDE_GMS=0", "ONEOS_GUEST_HIDE_GMS=1")
        assertTrue(status(prepared(mapOf("stage.env" to hidden))).verify(profile, image, set).any { it.contains("has no Google services") })
        val fold = Profiles.F8U
        val pixel = Images.PIXEL_YOGI
        val pixelSet = PackageSets.PIXEL_F8U
        val foldHidden = SessionEnv.generate(fold).replace("ONEOS_GUEST_HIDE_GMS=0", "ONEOS_GUEST_HIDE_GMS=1")
        assertTrue(status(prepared(mapOf("stage.env" to foldHidden), image = pixel, set = pixelSet, profile = fold)).verify(fold, pixel, pixelSet).any { it.contains("cannot be hidden") })
        assertEquals(emptyList<String>(), status(prepared(image = pixel, set = pixelSet, profile = fold)).verify(fold, pixel, pixelSet))
    }

    /** "Use the image already on this phone": the hash root recorded counts only while the file is unchanged. */
    @Test
    fun rawVerifiedOnlyWhileUnchanged() {
        val st = status(prepared())
        assertEquals(image.rawSha256, st.rawVerifiedSha256)
        assertEquals(StagedRaw(image.rawBytes, image.rawSha256), st.stagedRaw)
        val touched = "now ${image.rawBytes} 64773:1234:${image.rawBytes}:1792000999\nid ${image.rawBytes} ${image.rawSha256} 64773:1234:${image.rawBytes}:1792000000\n"
        assertNull(status(prepared(mapOf("stage.raw" to touched))).rawVerifiedSha256)
        assertEquals(StagedRaw(image.rawBytes, null), status(prepared(mapOf("stage.raw" to touched))).stagedRaw)
        val noId = "now ${image.rawBytes} 64773:1234:${image.rawBytes}:1792000000\n"
        assertNull(status(prepared(mapOf("stage.raw" to noId))).rawVerifiedSha256)
        assertEquals(StagedRaw(null, null), status(prepared(), missing = setOf("stage.raw")).stagedRaw)
    }
}
