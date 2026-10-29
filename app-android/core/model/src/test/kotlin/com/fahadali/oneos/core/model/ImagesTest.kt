package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ImagesTest {
    private val x9u = Images.FIND_X9U
    private val n6 = Images.FIND_N6
    private val pixel = Images.PIXEL_YOGI
    private val xin = Images.FIND_X9U_IN

    /** A sample of an image an earlier build took (none is retired in 0.4.11). */
    private val old = RetiredImage(
        id = "coloros16-findx8u",
        shortName = "Find X8 Ultra",
        gzName = "OneOS_ColorOS16_FindX8Ultra.img.gz",
        gzBytes = 4_000_000_001L,
        rawBytes = 9_000_000_000L,
    )

    @Test
    fun builtInTable() {
        assertEquals("coloros17-findx9u", x9u.id)
        assertEquals("OneOS_ColorOS17_FindX9Ultra_S26U.img.gz", x9u.gzName)
        assertEquals(5_290_346_735L, x9u.gzBytes)
        assertEquals("9796d27676dfd709ab4b26caf30fa19bc78ab2a24f5cf19e974a3e8708e919fe", x9u.gzSha256)
        assertEquals(10_385_141_760L, x9u.rawBytes)
        assertEquals("302467fc4e77998e84c10e037326508a39ab9e4be34058b751f0a768c7ff23e7", x9u.rawSha256)
        // gzip ISIZE of the upload (x9u-package study).
        assertEquals(1_795_207_168L, x9u.gzIsize)

        assertEquals("coloros17-findn6", n6.id)
        assertEquals("OneOS_ColorOS17_FindN6_ZFold8.img.gz", n6.gzName)
        assertEquals(5_285_345_619L, n6.gzBytes)
        assertEquals("4d371cbeb5da0b7c4b67ff44ce437ca56a244b0e3a93e1a696099ab6071d1809", n6.gzSha256)
        assertEquals(10_276_003_840L, n6.rawBytes)
        assertEquals("bdf5ef00aee3333758afdde152a29e0d2ca7bdaf89029ccd74bad34eec5bf444", n6.rawSha256)
        assertEquals(SpaceRule.TYPICAL_IMAGE_BYTES, n6.rawBytes)

        // 0.3.7: the Pixel 11 Fold image, verified on the server (gunzip of the .gz == image, 2026-10-24).
        assertEquals("pixel11fold-yogi", pixel.id)
        assertEquals("OneOS_Pixel11Fold_Full_ZFold8.img.gz", pixel.gzName)
        assertEquals(3_288_346_862L, pixel.gzBytes)
        assertEquals("8fbe950c47629c439af0807fc6bbb2afa29308c65c215849bcfa7a01f6b9290d", pixel.gzSha256)
        assertEquals(6_559_223_808L, pixel.rawBytes)
        assertEquals("8b303c37916288545b3b4a317c368d89680b5c3ce09873dc764381ddd0e32830", pixel.rawSha256)
        assertEquals("CD1A.261005.003.B1", pixel.buildId)
        assertEquals("Pixel 11 Fold", pixel.name)
        assertEquals(null, pixel.variant)
        assertEquals("Z Fold (F8U)", pixel.testedOn)
        assertEquals(6_559_223_808L - (1L shl 32), pixel.gzIsize)
        // Its loader is built for SVE2 (the disassembly of its linker64); SME and MOPS have fallbacks.
        assertEquals(listOf("sve", "sve2"), pixel.cpuRequired)
        assertEquals(emptyList<String>(), pixel.cpuUsedByApps)
        // The Pixel images and Infinity-X (0.4.27) have Google services and their sessions present them; the
        // Find X9 Ultra IN build has them in the image and a launch may hide them.
        assertEquals(listOf(xin, pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX), Images.ALL.filter { it.googleServices })
        assertEquals(listOf(pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX), Images.ALL.filter { it.presentsGms })
        assertEquals(listOf(xin), Images.ALL.filter { it.gmsHideable })
        assertTrue(pixel.copy(presentsGms = false).gmsHideable)
        assertEquals(listOf(n6, x9u, xin, pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX), Images.ALL)
        // 0.4.11: the Find X9 Ultra IN build is back (0.3.3-0.3.6, dropped in 0.3.7), the same file.
        assertEquals("coloros17-findx9u-in", xin.id)
        assertEquals("OneOS_ColorOS17_FindX9Ultra_IN.img.gz", xin.gzName)
        assertEquals(5_882_128_321L, xin.gzBytes)
        assertEquals("413380426cdff8b5e760f1424895fc5b43e7a6ffe5f889e0406e437590c0d04e", xin.gzSha256)
        assertEquals(12_069_945_344L, xin.rawBytes)
        assertEquals("a36ef550f4b2530fb9c7c6d363180d9eb4437e0497ebc87292697e4bf2a580b0", xin.rawSha256)
        assertEquals(x9u.buildId, xin.buildId)
        assertEquals(null, xin.testedOn)
        assertEquals(xin, Images.byGzSize(5_882_128_321L))
        assertEquals(xin, Images.byRawSize(12_069_945_344L))
        assertEquals("Find X9 Ultra IN", Images.shortName(xin.id))
        // Nothing is retired now; a retired image's name stays known (old stages, the last session).
        assertEquals(emptyList<RetiredImage>(), Images.RETIRED)
        assertEquals("Find X8 Ultra", Images.shortName(old.id, retired = listOf(old)))
        assertEquals("Find N6", Images.shortName(n6.id))
        assertEquals("not-an-image", Images.shortName("not-an-image"))
        // Guest data stays with its own system (0.3.7): the ColorOS builds and the Pixel images.
        assertEquals(listOf(SystemFamily.COLOROS, SystemFamily.COLOROS, SystemFamily.COLOROS, SystemFamily.PIXEL, SystemFamily.PIXEL, SystemFamily.PIXEL, SystemFamily.INFINITYX), Images.ALL.map { it.family })
        // The Pixel 9 Pro XL image (0.4.22) needs no SVE, unlike the Pixel 11 builds.
        assertEquals(emptyList<String>(), Images.PIXEL_KOMODO.cpuRequired)
        assertEquals(listOf("sve", "sve2"), Images.PIXEL_KODIAK.cpuRequired)
        for (i in Images.ALL) assertEquals(i.id, i.id.startsWith("coloros17-"), i.family == SystemFamily.COLOROS)

        for (i in Images.ALL) {
            assertEquals(37, i.sdk)
            for (h in listOf(i.gzSha256, i.rawSha256)) assertTrue(h.matches(Regex("[0-9a-f]{64}")))
        }
        // Sizes tell the images apart (the picker identifies by size first).
        val sizes = Images.ALL.flatMap { listOf(it.gzBytes, it.rawBytes) }
        assertEquals(sizes.size, sizes.toSet().size)
        assertEquals(x9u, Images.byGzSize(5_290_346_735L))
        assertEquals(n6, Images.byRawSize(10_276_003_840L))
        assertNull(Images.byGzSize(5_290_346_734L))
        assertTrue(x9u.rawMatches(10_385_141_760L, x9u.rawSha256.uppercase()))
        assertTrue(!x9u.rawMatches(10_385_141_759L, x9u.rawSha256))
    }

    private fun id(check: ImageFileCheck, profile: PhoneProfile? = Profiles.S_ULTRA_8850) = ImageIdentifier.identify(check, profile)

    @Test
    fun verifiedOnlyWithTheRightSizeAndHash() {
        val ok = id(ImageFileCheck(x9u.gzName, x9u.gzBytes, x9u.gzSha256, x9u.gzBytes))
        assertEquals(ImageState.VERIFIED, ok.state)
        assertEquals(Level.OK, ok.finding.level)
        assertEquals(x9u, ok.image)

        val n6OnFold = ImageIdentifier.identify(ImageFileCheck(null, n6.gzBytes, n6.gzSha256, n6.gzBytes), Profiles.F8U)
        assertEquals(ImageState.VERIFIED, n6OnFold.state)
    }

    @Test
    fun sizeOnlyIsNotEnough() {
        val r = id(ImageFileCheck("OneOS_ColorOS17_FindX9Ultra_S26U.img.gz", x9u.gzBytes))
        assertEquals(ImageState.NOT_CHECKED, r.state)
        assertEquals(Level.BLOCK, r.finding.level)
        assertEquals("Check the file first", r.finding.title)
    }

    @Test
    fun wrongHashOrTruncatedIsDamaged() {
        val badHash = id(ImageFileCheck("x.img.gz", x9u.gzBytes, "0".repeat(64), x9u.gzBytes))
        assertEquals(ImageState.DAMAGED, badHash.state)
        assertEquals(Level.BLOCK, badHash.finding.level)
        assertTrue(badHash.finding.detail.contains("Download it again"))

        // The provider said the right size, but the stream ended early.
        val short = id(ImageFileCheck("x.img.gz", x9u.gzBytes, x9u.gzSha256, x9u.gzBytes - 1))
        assertEquals(Level.BLOCK, short.finding.level)

        // Hash right, provider size different: refused.
        val mixed = id(ImageFileCheck("x.img.gz", x9u.gzBytes + 1, x9u.gzSha256, x9u.gzBytes))
        assertEquals(ImageState.DAMAGED, mixed.state)
    }

    @Test
    fun wrongImageForThePhone() {
        val n6OnS26 = id(ImageFileCheck("OneOS_ColorOS17_FindN6_ZFold8.img.gz", n6.gzBytes, n6.gzSha256, n6.gzBytes))
        assertEquals(ImageState.WRONG_FOR_PHONE, n6OnS26.state)
        assertEquals(Level.BLOCK, n6OnS26.finding.level)
        // The BLOCK names every image the phone takes.
        assertEquals(
            "This is the Find N6 image; Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN.img.gz) " +
                "or the Find X9 Ultra image (OneOS_ColorOS17_FindX9Ultra_S26U.img.gz) or the Pixel 11 Pro image (OneOS_Pixel11Pro_Full_S26U.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz).",
            n6OnS26.finding.detail,
        )
        // The Pixel image is the Fold's only (0.3.7): refused on an S Ultra and the Galaxy S25, by size alone already.
        for (p in listOf(Profiles.S_ULTRA_8850, Profiles.S_ULTRA_8750, Profiles.S_8750)) {
            for (check in listOf(ImageFileCheck(null, pixel.gzBytes, pixel.gzSha256, pixel.gzBytes), ImageFileCheck(null, pixel.gzBytes))) {
                val pixelOnBar = ImageIdentifier.identify(check, p)
                assertEquals(p.id, ImageState.WRONG_FOR_PHONE, pixelOnBar.state)
                assertEquals(pixel, pixelOnBar.image)
                assertTrue(pixelOnBar.finding.detail, pixelOnBar.finding.detail.startsWith("This is the Pixel 11 Fold image; ${p.label} takes the Find X9 Ultra IN image"))
            }
        }
        // The Galaxy Z Fold7 takes the Find N6 image and Infinity-X (0.4.27), no Pixel: Pixel 11's system code needs
        // SVE, which SM8750 lacks.
        val pixelOnFold7 = ImageIdentifier.identify(ImageFileCheck(null, pixel.gzBytes, pixel.gzSha256, pixel.gzBytes), Profiles.FOLD7)
        assertEquals(ImageState.WRONG_FOR_PHONE, pixelOnFold7.state)
        assertEquals(
            "This is the Pixel 11 Fold image; Galaxy Z Fold7 takes the Find N6 image (OneOS_ColorOS17_FindN6_ZFold8.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz).",
            pixelOnFold7.finding.detail,
        )
        // The owner does not want the X9U (CN) image on his Fold; by size alone already.
        for (check in listOf(ImageFileCheck(null, x9u.gzBytes, x9u.gzSha256, x9u.gzBytes), ImageFileCheck(null, x9u.gzBytes))) {
            val x9uOnFold = ImageIdentifier.identify(check, Profiles.F8U)
            assertEquals(ImageState.WRONG_FOR_PHONE, x9uOnFold.state)
            assertEquals(Level.BLOCK, x9uOnFold.finding.level)
            assertEquals(x9u, x9uOnFold.image)
            assertEquals(
                "This is the Find X9 Ultra image; Z Fold (F8U) takes the Find N6 image (OneOS_ColorOS17_FindN6_ZFold8.img.gz) " +
                    "or the Pixel 11 Fold image (OneOS_Pixel11Fold_Full_ZFold8.img.gz) or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz).",
                x9uOnFold.finding.detail,
            )
        }
        // The unpacked image of one the phone does not take: what it takes, not that image's .gz.
        val rawN6OnS25 = ImageIdentifier.identify(ImageFileCheck("n6.img", n6.rawBytes), Profiles.S_ULTRA_8750)
        assertEquals(ImageState.UNCOMPRESSED, rawN6OnS25.state)
        assertTrue(rawN6OnS25.finding.detail.contains("Galaxy S25 Ultra takes"))
    }

    /** Each profile takes its own images (0.3.3; 0.3.7: the Pixel image on the Fold only) and the check says which one the file is. */
    @Test
    fun identifiesWhichImageThePhoneTakes() {
        fun verified(i: ImageRef, p: PhoneProfile) = ImageIdentifier.identify(ImageFileCheck(i.gzName, i.gzBytes, i.gzSha256, i.gzBytes), p)
        // 0.4.27: Infinity-X, last, on every phone.
        val ifx = Images.INFINITYX
        val takes = mapOf(
            Profiles.F8U to listOf(n6, pixel, ifx),
            Profiles.S_ULTRA_8850 to listOf(xin, x9u, Images.PIXEL_KODIAK, ifx),
            // 0.4.22: the Pixel 9 Pro XL image on the phones without SVE.
            Profiles.S_ULTRA_8750 to listOf(xin, x9u, Images.PIXEL_KOMODO, ifx),
            Profiles.S_8750 to listOf(xin, x9u, Images.PIXEL_KOMODO, ifx),
            Profiles.FOLD7 to listOf(n6, ifx),
            Profiles.S_PLUS_8750 to listOf(xin, x9u, Images.PIXEL_KOMODO, ifx),
            Profiles.FOLD8 to listOf(n6, pixel, ifx),
            Profiles.S_8850 to listOf(xin, x9u, Images.PIXEL_KODIAK, ifx),
            Profiles.S_ULTRA_8650 to listOf(xin, x9u, Images.PIXEL_KOMODO, ifx),
            Profiles.S_8550 to listOf(xin, x9u, ifx),
            Profiles.S_PLUS_8850 to listOf(xin, x9u, Images.PIXEL_KODIAK, ifx),
            Profiles.S_PLUS_9965 to listOf(xin, x9u, Images.PIXEL_KODIAK, ifx),
            Profiles.FLIP7 to listOf(xin, x9u, ifx),
            Profiles.A57 to listOf(xin, x9u, ifx),
            Profiles.FLIP5 to listOf(xin, x9u, ifx),
        )
        for ((p, good) in takes) {
            assertEquals(p.id, good, p.images())
            for (i in Images.ALL) {
                val r = verified(i, p)
                if (i in good) {
                    assertEquals("${p.id} ${i.id}", ImageState.VERIFIED, r.state)
                    assertEquals(i, r.image)
                    assertEquals("${i.shortName} image verified", r.finding.title)
                    assertTrue(r.finding.detail.startsWith(i.label))
                } else {
                    assertEquals("${p.id} ${i.id}", ImageState.WRONG_FOR_PHONE, r.state)
                    assertEquals(Level.BLOCK, r.finding.level)
                }
            }
        }
        // By size first: the Pixel file before Check file.
        val sized = ImageIdentifier.identify(ImageFileCheck(pixel.gzName, pixel.gzBytes), Profiles.F8U)
        assertEquals(ImageState.NOT_CHECKED, sized.state)
        assertEquals(pixel, sized.image)
        assertTrue(sized.finding.detail.contains("Pixel 11 Fold image"))
        // The Pixel size with the Find N6 hash: damaged, not the Find N6 image.
        val mixed = ImageIdentifier.identify(ImageFileCheck(null, pixel.gzBytes, n6.gzSha256, pixel.gzBytes), Profiles.F8U)
        assertEquals(ImageState.DAMAGED, mixed.state)
        assertEquals(pixel, mixed.image)
        // Nothing picked: what the phone takes.
        assertEquals(
            "Z Fold (F8U) takes the Find N6 image (OneOS_ColorOS17_FindN6_ZFold8.img.gz) or the Pixel 11 Fold image " +
                "(OneOS_Pixel11Fold_Full_ZFold8.img.gz) or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz)",
            ImageIdentifier.accepts(Profiles.F8U),
        )
        assertEquals(
            "Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN.img.gz) or the Find X9 Ultra image " +
                "(OneOS_ColorOS17_FindX9Ultra_S26U.img.gz) or the Pixel 11 Pro image (OneOS_Pixel11Pro_Full_S26U.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz)",
            ImageIdentifier.accepts(Profiles.S_ULTRA_8850),
        )
    }

    /** Two images of one size (not the case today): the SHA-256 decides, and a match the phone does not take is refused. */
    @Test
    fun theHashDecidesBetweenImagesOfOneSize() {
        val twin = pixel.copy(id = "pixel-twin", shortName = "Twin", gzSha256 = "1".repeat(64))
        val images = Images.ALL + twin
        val p = Profiles.F8U
        assertEquals(ImageState.VERIFIED, ImageIdentifier.identify(ImageFileCheck(null, pixel.gzBytes, pixel.gzSha256, pixel.gzBytes), p, images).state)
        val other = ImageIdentifier.identify(ImageFileCheck(null, twin.gzBytes, twin.gzSha256, twin.gzBytes), p, images)
        assertEquals(ImageState.WRONG_FOR_PHONE, other.state)
        assertEquals(twin, other.image)
        val accepts = p.copy(choices = p.choices + ImageChoice(twin.id, PackageSets.ID_PIXEL_F8U, false))
        assertEquals(twin, ImageIdentifier.identify(ImageFileCheck(null, twin.gzBytes, twin.gzSha256, twin.gzBytes), accepts, images).image)
    }

    /** "Use the image already on this phone": the stage's system.raw, by size and (root's record) SHA-256. */
    @Test
    fun imageAlreadyOnThePhone() {
        fun staged(bytes: Long?, sha: String? = null, p: PhoneProfile = Profiles.F8U) = ImageIdentifier.identifyStaged(StagedRaw(bytes, sha), p)

        // The size is enough to prepare: root hashes it in keep-raw.
        val sized = staged(pixel.rawBytes)
        assertEquals(ImageState.NOT_CHECKED, sized.state)
        assertEquals(Level.OK, sized.finding.level)
        assertEquals(pixel, sized.image)
        assertEquals("Pixel 11 Fold image already on this phone", sized.finding.title)
        assertEquals(ImageState.VERIFIED, staged(pixel.rawBytes, pixel.rawSha256).state)
        assertEquals(ImageState.VERIFIED, staged(n6.rawBytes, n6.rawSha256).state)
        assertEquals(n6, staged(n6.rawBytes, n6.rawSha256.uppercase()).image)
        // Root staged another image of that size.
        val other = staged(n6.rawBytes, "2".repeat(64))
        assertEquals(ImageState.DAMAGED, other.state)
        assertEquals(Level.BLOCK, other.finding.level)
        // An image this phone does not take: BLOCK naming what it takes.
        val cnOnFold = staged(x9u.rawBytes)
        assertEquals(ImageState.WRONG_FOR_PHONE, cnOnFold.state)
        assertEquals(Level.BLOCK, cnOnFold.finding.level)
        assertTrue(cnOnFold.finding.detail.contains("Find X9 Ultra image; Z Fold (F8U) takes the Find N6 image"))
        val n6OnS26 = staged(n6.rawBytes, n6.rawSha256, Profiles.S_ULTRA_8850)
        assertEquals(ImageState.WRONG_FOR_PHONE, n6OnS26.state)
        assertTrue(n6OnS26.finding.detail, n6OnS26.finding.detail.contains("Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN.img.gz) or the Find X9 Ultra image (OneOS_ColorOS17_FindX9Ultra_S26U.img.gz)"))
        val pixelOnS26 = staged(pixel.rawBytes, pixel.rawSha256, Profiles.S_ULTRA_8850)
        assertEquals(ImageState.WRONG_FOR_PHONE, pixelOnS26.state)
        assertEquals(pixel, pixelOnS26.image)
        // Nothing there, or not a OneOS image.
        assertEquals(Level.BLOCK, staged(null).finding.level)
        assertEquals(ImageState.UNKNOWN, staged(123L).state)
        assertEquals(Level.BLOCK, staged(123L).finding.level)
    }

    @Test
    fun unpackedUnknownAndSizeless() {
        val raw = id(ImageFileCheck("oneos-coloros-x9u.img", x9u.rawBytes))
        assertEquals(ImageState.UNCOMPRESSED, raw.state)
        assertEquals(Level.BLOCK, raw.finding.level)

        val other = id(ImageFileCheck("holiday.mp4", 123_456_789))
        assertEquals(ImageState.UNKNOWN, other.state)
        assertEquals(Level.BLOCK, other.finding.level)
        assertTrue(other.finding.detail.contains("OneOS_ColorOS17_FindX9Ultra_S26U.img.gz"))

        // A remembered .gz of a retired image: named, and not called "not a OneOS image".
        val oldGz = ImageIdentifier.identify(ImageFileCheck(old.gzName, old.gzBytes), Profiles.S_ULTRA_8850, retiredImages = listOf(old))
        assertEquals(ImageState.UNKNOWN, oldGz.state)
        assertEquals(ImageIdentifier.R_RETIRED, oldGz.finding.reason)
        assertEquals("Image no longer supported", oldGz.finding.title)
        assertTrue(oldGz.finding.detail, oldGz.finding.detail.contains("Find X8 Ultra") && oldGz.finding.detail.contains(xin.gzName))
        val oldRaw = ImageIdentifier.identifyStaged(StagedRaw(old.rawBytes), Profiles.S_ULTRA_8850, retiredImages = listOf(old))
        assertEquals(ImageIdentifier.R_RAW_NOT_OURS, oldRaw.finding.reason)
        assertTrue(oldRaw.finding.detail, oldRaw.finding.detail.contains("Find X8 Ultra"))

        val sizeless = id(ImageFileCheck(null, null))
        assertEquals(ImageState.UNKNOWN, sizeless.state)
        assertEquals(Level.BLOCK, sizeless.finding.level)

        // Without a profile the right-phone check is skipped (the profile gate refuses that phone).
        assertEquals(ImageState.VERIFIED, id(ImageFileCheck(null, n6.gzBytes, n6.gzSha256, n6.gzBytes), profile = null).state)
    }

    /** The redesign's display fields: every image has a name and a card line; a phone never offers two that read the same. */
    @Test
    fun displayNames() {
        for (i in Images.ALL) {
            assertTrue(i.id, i.name.isNotBlank())
            assertTrue(i.id, i.blurb.isNotBlank())
            assertTrue(i.id, i.displayName.startsWith(i.name))
            assertTrue(i.id, i.displayName.endsWith("(Android ${AndroidRelease.name(i.sdk)})"))
            i.downloadUrl?.let { assertTrue(i.id, it.startsWith("https://")) }
        }
        for (p in Profiles.BUILT_IN) {
            val shown = p.images().map { it.name to it.variant }
            assertEquals(p.id, shown.size, shown.toSet().size)
            val names = p.images().map { Images.systemName(it, p) }
            assertEquals(p.id, names.size, names.toSet().size)
            assertTrue(p.id, p.recommended != null)
        }
        assertEquals("ColorOS 17 · Find N6 build (Android 17)", n6.displayName)
        assertEquals("Pixel 11 Fold", pixel.nameWithVariant)
        assertEquals("Pixel 11 Fold (Android 17)", pixel.displayName)
        assertEquals("Pixel 11 Fold", Images.systemName(pixel, Profiles.F8U))
        // {system}: the name, with the variant only when the phone takes another of that name
        // (the Fold takes ColorOS 17 and Pixel 11 Fold; from 0.4.11 the bar phones take two ColorOS 17 builds).
        assertEquals("ColorOS 17", Images.systemName(n6))
        assertEquals("ColorOS 17", Images.systemName(n6, Profiles.F8U))
        assertEquals("ColorOS 17 · Find X9 Ultra build", Images.systemName(x9u, Profiles.S_ULTRA_8850))
        assertEquals("ColorOS 17 · global build", Images.systemName(xin, Profiles.S_ULTRA_8850))
        val twin = Profiles.F8U.copy(choices = Profiles.F8U.choices + ImageChoice(x9u.id, PackageSets.ID_X9U_SULTRA, false))
        assertEquals("ColorOS 17 · Find N6 build", Images.systemName(n6, twin))
        assertEquals("the other system", Images.systemName(null))
        // The Fold's recommended system is the one that has run on it.
        assertEquals(Images.ID_FIND_N6, Profiles.F8U.recommended!!.imageId)
        assertEquals(Images.ID_FIND_X9U, Profiles.S_ULTRA_8850.recommended!!.imageId)
    }

    @Test
    fun everyBlockHasAReason() {
        val checks = listOf(
            ImageFileCheck(null, null),
            ImageFileCheck("x", 12345),
            ImageFileCheck("x", n6.rawBytes),
            ImageFileCheck("x", x9u.gzBytes),
            ImageFileCheck("x", n6.gzBytes),
            ImageFileCheck("x", n6.gzBytes, "0".repeat(64), n6.gzBytes),
            ImageFileCheck("x", old.gzBytes),
        )
        for (c in checks) {
            val f = ImageIdentifier.identify(c, Profiles.F8U, retiredImages = listOf(old)).finding
            if (f.level == Level.BLOCK) assertTrue("$c", f.reason != null)
        }
        for (raw in listOf(StagedRaw(null), StagedRaw(1), StagedRaw(x9u.rawBytes), StagedRaw(n6.rawBytes, "0".repeat(64)))) {
            val f = ImageIdentifier.identifyStaged(raw, Profiles.F8U).finding
            if (f.level == Level.BLOCK) assertTrue("$raw", f.reason != null)
        }
    }
}
