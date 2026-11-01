package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.root.RootScript.BeginMode
import com.fahadali.oneos.core.root.StageFixtures.prepared
import com.fahadali.oneos.core.root.StageFixtures.status
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Setup picks what to do with the stage itself; nothing is ever deleted, and another system's data is never kept. */
class SetupPlanTest {
    private val fold = Profiles.F8U
    private val n6 = Images.FIND_N6
    private val app = 4

    @Test
    fun selfConsistentOldPayloadsStillRequireTheNewApksUpdate() {
        val st = status(prepared(fold, n6, PackageSets.N6_F8U))
        assertTrue(st.stageState(fold, st.hashes)!!.filesVerified)
        // The old stage's checksums still agree with its own files, but the APK ships a new renderer.
        val currentApk = st.hashes + ("OneOSBootStatus.dex" to "e".repeat(64))
        assertFalse(st.stageState(fold, currentApk)!!.filesVerified)
        assertFalse(st.stageState(fold, emptyMap())!!.filesVerified)
    }

    @Test
    fun interruptedUpdateRemainsAnUpdateWithoutTheRawVerificationRecord() {
        val complete = prepared(fold, n6, PackageSets.N6_F8U)
        val interrupted = status(complete + ("stage.marker" to "updating\n${complete.getValue("stage.marker")}"))
            .copy(rawId = null)
        assertFalse(interrupted.ours)
        assertTrue(interrupted.partial)
        assertNull(interrupted.marker)
        assertEquals(n6.id, interrupted.pendingUpdate?.imageId)
        assertFalse(interrupted.stageState(fold)!!.filesVerified)
        val retry = SetupPlan.decide(interrupted, n6, fold, app, hasDownload = true)!!
        assertEquals(SetupPlan.Kind.UPDATE, retry.kind)
        assertEquals(BeginMode.KEEP, retry.mode)
        assertEquals(SetupPlan.Source.ON_PHONE, retry.source)
        assertTrue(SetupPlan.updateWithoutDownload(interrupted, n6, fold, app))
        // This is permission to re-hash the existing image, never permission to boot it.
        assertFalse(SetupPlan.reusesInstalled(interrupted.copy(rawSize = 1), n6, fold, app))
        val other = SetupPlan.decide(interrupted, Images.PIXEL_YOGI, fold, app, false)!!
        assertEquals(BeginMode.ASIDE, other.mode)
        assertTrue(other.setsAsideData)
    }

    @Test
    fun invalidUpdateCheckpointDoesNotSupplyAnInstalledIdentity() {
        val complete = prepared(fold, n6, PackageSets.N6_F8U)
        val broken = status(complete + ("stage.marker" to "updating\nnot a stage marker"))
        assertNull(broken.marker)
        assertNull(broken.pendingUpdate)
        assertFalse(broken.stageState(fold)!!.filesVerified)
    }

    @Test
    fun nothingThereStartsNew() {
        val p = SetupPlan.decide(StageFixtures.absent, n6, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.NEW, p.mode)
        assertEquals(SetupPlan.Kind.NEW, p.kind)
        assertEquals(SetupPlan.Source.DOWNLOAD, p.source)
        assertFalse(p.setsAsideData)
    }

    @Test
    fun theSameSystemKeepsItsAppsAndData() {
        val st = status(prepared(fold, n6, PackageSets.N6_F8U))
        val p = SetupPlan.decide(st, n6, fold, app, hasDownload = false)!!
        assertEquals(BeginMode.KEEP, p.mode)
        assertTrue(p.keepsData)
        assertEquals(SetupPlan.Kind.REPAIR, p.kind)
        // Root verified its system.raw: reused, no download (root re-hashes it in keep-raw).
        assertEquals(SetupPlan.Source.ON_PHONE, p.source)
        assertFalse(p.needsDownload)
        // Even with a download picked, the verified system on the phone is used.
        assertEquals(SetupPlan.Source.ON_PHONE, SetupPlan.decide(st, n6, fold, app, hasDownload = true)!!.source)
    }

    @Test
    fun anAppUpdateNeedsNoDownload() {
        val st = status(prepared(fold, n6, PackageSets.N6_F8U, versionCode = 3))
        val p = SetupPlan.decide(st, n6, fold, app, hasDownload = false)!!
        assertEquals(SetupPlan.Kind.UPDATE, p.kind)
        assertEquals(BeginMode.KEEP, p.mode)
        assertEquals(SetupPlan.Source.ON_PHONE, p.source)
        assertTrue(SetupPlan.updateWithoutDownload(st, n6, fold, app))
        // Same app version and set: not an update, but a repair would reuse it too.
        assertFalse(SetupPlan.updateWithoutDownload(status(prepared(fold, n6, PackageSets.N6_F8U)), n6, fold, app))
        assertTrue(SetupPlan.reusesInstalled(status(prepared(fold, n6, PackageSets.N6_F8U)), n6, fold, app))
        assertEquals(SetupPlan.Kind.REPAIR, SetupPlan.decide(status(prepared(fold, n6, PackageSets.N6_F8U)), n6, fold, app, false)!!.kind)
    }

    @Test
    fun anotherFileSetIsAnUpdate() {
        val pixel = Images.PIXEL_YOGI
        val pixelData = "packages ${StageStatus.PIXEL_WORD}"
        // A ColorOS set staged with the Pixel image on the Fold (which takes pixel-f8u), with Pixel data.
        val st = status(prepared(fold, pixel, PackageSets.N6_F8U, guest = pixelData))
        assertEquals(SetupPlan.Kind.UPDATE, SetupPlan.decide(st, pixel, fold, app, false)!!.kind)
        // Its own set: a repair.
        assertEquals(SetupPlan.Kind.REPAIR, SetupPlan.decide(status(prepared(fold, pixel, PackageSets.PIXEL_F8U, guest = pixelData)), pixel, fold, app, false)!!.kind)
        // 0.3.7: ColorOS data under the Pixel image's marker is another system's: set aside, never updated in place.
        val colorOsData = SetupPlan.decide(status(prepared(fold, pixel, PackageSets.PIXEL_F8U)), pixel, fold, app, false)!!
        assertEquals(BeginMode.ASIDE, colorOsData.mode)
        assertTrue(colorOsData.setsAsideData)
    }

    @Test
    fun aSystemRootNoLongerVouchesForNeedsTheDownload() {
        val st = status(prepared(fold, n6, PackageSets.N6_F8U, versionCode = 3, rawVerified = false))
        assertNull(st.rawVerifiedSha256)
        assertEquals(SetupPlan.Source.DOWNLOAD, SetupPlan.decide(st, n6, fold, app, hasDownload = true)!!.source)
        // No download picked: the same-size file is offered to root, which hashes it before use.
        assertEquals(SetupPlan.Source.ON_PHONE, SetupPlan.decide(st, n6, fold, app, hasDownload = false)!!.source)
        // Home does not promise "no download" then.
        assertFalse(SetupPlan.updateWithoutDownload(st, n6, fold, app))
    }

    @Test
    fun anotherSystemIsSetAsideNeverKept() {
        // The Fold's ColorOS stage, then the Pixel image picked (the showcase's first setup).
        val pixel = Images.PIXEL_YOGI
        val st = status(prepared(fold, n6, PackageSets.N6_F8U))
        val p = SetupPlan.decide(st, pixel, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.ASIDE, p.mode)
        assertEquals(SetupPlan.Kind.REPLACE, p.kind)
        assertEquals(SetupPlan.Source.DOWNLOAD, p.source)
        assertTrue(p.setsAsideData)
        assertEquals(n6.id, p.asideImageId)
        assertFalse(SetupPlan.updateWithoutDownload(st, pixel, fold, app))
        // Without guest data there is nothing of value in it, but it is still set aside, not replaced.
        val empty = status(prepared(fold, n6, PackageSets.N6_F8U, guest = "packages none"))
        val q = SetupPlan.decide(empty, pixel, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.ASIDE, q.mode)
        assertFalse(q.setsAsideData)
        assertNull(q.asideImageId)
        // And back: a Pixel stage with its data, then the Find N6 image: the Pixel data is set aside, never kept.
        val pixelStage = status(prepared(fold, pixel, PackageSets.PIXEL_F8U, guest = "packages ${StageStatus.PIXEL_WORD}"))
        val back = SetupPlan.decide(pixelStage, n6, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.ASIDE, back.mode)
        assertEquals(SetupPlan.Kind.REPLACE, back.kind)
        assertTrue(back.setsAsideData)
        assertEquals(pixel.id, back.asideImageId)
    }

    @Test
    fun aStageOneOsDidNotPrepareIsSetAside() {
        val lineage = status(
            prepared(fold, n6, PackageSets.N6_F8U, guest = "packages org.lineageos.", extra = mapOf("stage.dir" to "dir 2000 2000 777\n")),
            missing = setOf("stage.marker"),
        )
        val p = SetupPlan.decide(lineage, n6, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.ASIDE, p.mode)
        assertTrue(p.setsAsideData)
        assertNull(p.asideImageId)
        // A foreign root-owned stage with the other system's data: offered keep or aside, set aside automatically.
        val foreign = status(prepared(fold, n6, PackageSets.N6_F8U, extra = mapOf("stage.list" to "f 0 644 10 x.log\nd 0 755 4096 data\n")), missing = setOf("stage.marker"))
        assertTrue(foreign.foreign)
        assertEquals(listOf(BeginMode.KEEP, BeginMode.ASIDE), foreign.beginModes(n6.id))
        assertEquals(BeginMode.ASIDE, SetupPlan.decide(foreign, n6, fold, app, true)!!.mode)
        // 0.3.7: that ColorOS stage with the Pixel image: never offered keep, set aside with its data.
        val pixel = Images.PIXEL_YOGI
        assertEquals(listOf(BeginMode.ASIDE), foreign.beginModes(pixel.id))
        val toPixel = SetupPlan.decide(foreign, pixel, fold, app, true)!!
        assertEquals(BeginMode.ASIDE, toPixel.mode)
        assertTrue(toPixel.setsAsideData)
        // The Fold's Pixel stage from scripts/deploy-phone.sh (runs 41-44, no marker): Home sets it aside too (the
        // .gz is needed; Advanced › Set up again may keep it for the Pixel image, never for a ColorOS one).
        val adbPixel = status(
            prepared(fold, pixel, PackageSets.PIXEL_F8U, guest = "packages ${StageStatus.PIXEL_WORD}", extra = mapOf("stage.list" to "f 0 644 10 x.log\nd 0 755 4096 data\n")),
            missing = setOf("stage.marker"),
        )
        assertTrue(adbPixel.foreign)
        assertEquals(GuestData.PIXEL, adbPixel.guest)
        val home = SetupPlan.decide(adbPixel, pixel, fold, app, true)!!
        assertEquals(BeginMode.ASIDE, home.mode)
        assertEquals(SetupPlan.Source.DOWNLOAD, home.source)
        assertTrue(home.setsAsideData)
        assertEquals(listOf(BeginMode.KEEP, BeginMode.ASIDE), adbPixel.beginModes(pixel.id))
        assertEquals(listOf(BeginMode.ASIDE), adbPixel.beginModes(n6.id))
    }

    @Test
    fun aSetupThatStoppedIsKeptOnlyWhenItCanBeThisSystem() {
        // Stopped before any data: kept.
        val half = status(prepared(fold, n6, PackageSets.N6_F8U, guest = "packages none"), missing = setOf("stage.marker"))
        assertTrue(half.partial)
        val p = SetupPlan.decide(half, n6, fold, app, hasDownload = true)!!
        assertEquals(BeginMode.KEEP, p.mode)
        assertEquals(SetupPlan.Kind.REPAIR, p.kind)
        // With data, and root vouches that its system is this one: kept.
        val withData = status(prepared(fold, n6, PackageSets.N6_F8U), missing = setOf("stage.marker"))
        assertEquals(BeginMode.KEEP, SetupPlan.decide(withData, n6, fold, app, true)!!.mode)
        // With data from what may be another system: set aside.
        assertEquals(BeginMode.ASIDE, SetupPlan.decide(withData, Images.PIXEL_YOGI, fold, app, true)!!.mode)
        // 0.3.7: the same for the Pixel image. An update of a Pixel stage that stopped after keep-raw (marker in the
        // attic, system.raw verified again as the Pixel image) keeps its apps and data, with no download.
        val pixel = Images.PIXEL_YOGI
        val pixelHalf = status(
            prepared(fold, pixel, PackageSets.PIXEL_F8U, guest = "packages ${StageStatus.PIXEL_WORD}"),
            missing = setOf("stage.marker"),
        )
        assertTrue(pixelHalf.partial)
        val keep = SetupPlan.decide(pixelHalf, pixel, fold, app, hasDownload = false)!!
        assertEquals(BeginMode.KEEP, keep.mode)
        assertFalse(keep.setsAsideData)
        assertEquals(SetupPlan.Source.ON_PHONE, keep.source)
        assertEquals(SetupPlan.Kind.REPAIR, keep.kind)
        // Never for a ColorOS image.
        val toN6 = SetupPlan.decide(pixelHalf, n6, fold, app, true)!!
        assertEquals(BeginMode.ASIDE, toN6.mode)
        assertTrue(toN6.setsAsideData)
        // Stopped before root verified system.raw again (keep-raw): set aside, as a ColorOS stage then is.
        val unverified = status(
            prepared(fold, pixel, PackageSets.PIXEL_F8U, rawVerified = false, guest = "packages ${StageStatus.PIXEL_WORD}"),
            missing = setOf("stage.marker"),
        )
        assertEquals(BeginMode.ASIDE, SetupPlan.decide(unverified, pixel, fold, app, true)!!.mode)
        val unverifiedN6 = status(prepared(fold, n6, PackageSets.N6_F8U, rawVerified = false), missing = setOf("stage.marker"))
        assertEquals(BeginMode.ASIDE, SetupPlan.decide(unverifiedN6, n6, fold, app, true)!!.mode)
    }

    @Test
    fun aLinkInTheStagesPlaceIsRefused() {
        val link = status(prepared(fold, n6, PackageSets.N6_F8U, extra = mapOf("stage.dir" to "link\n")))
        assertNull(SetupPlan.decide(link, n6, fold, app, true))
    }
}
