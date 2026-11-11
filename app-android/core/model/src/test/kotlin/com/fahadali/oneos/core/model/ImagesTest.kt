package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ImagesTest {
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

        assertEquals("coloros17-findn6", n6.id)
        assertEquals("OneOS_ColorOS17_FindN6_Global.img.gz", n6.gzName)
        // 0.4.38: the global build (CPH2765 EX01, no debloat), 2026-11-01.
        assertEquals(7_213_271_568L, n6.gzBytes)
        assertEquals("b3061160ab3fdb37cd491e94c05e41238898320c1a5efb016debabc20991f3ee", n6.gzSha256)
        assertEquals(Images.SHARED_FOLDER_URL, n6.downloadUrl)
        assertEquals(14_829_686_784L, n6.rawBytes)
        assertEquals("eec6c10581657b17f3164d6f964c749b351c4a7ec07233840da5f6a0ce28a47c", n6.rawSha256)
        // The typical size the space hints quote stays the CN build's; a chosen image uses its own.
        assertTrue(n6.rawBytes > SpaceRule.TYPICAL_IMAGE_BYTES)

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
        // Find X9 Ultra IN build, Nothing OS (0.4.33) and the Find N6 global build (0.4.38) have them in the
        // image and a launch may hide them
        // (Nothing's are product/priv-app GmsCore, Phonesky, GooglePartnerSetup, GoogleRestore, ConfigUpdater
        // and system_ext/priv-app GoogleServicesFramework: six folders guest_prepare.sh's patterns cover).
        assertEquals(
            listOf(n6, xin, pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX, Images.NOTHING_METROID, Images.OXYGEN16, Images.ORIGINOS7),
            Images.ALL.filter { it.googleServices },
        )
        // 0.4.73: OriginOS 7 presents the Play services of its own gmssystem payload, as the Pixel images.
        assertEquals(listOf(pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX, Images.ORIGINOS7), Images.ALL.filter { it.presentsGms })
        assertEquals(listOf(n6, xin, Images.NOTHING_METROID, Images.OXYGEN16), Images.ALL.filter { it.gmsHideable })
        assertTrue(pixel.copy(presentsGms = false).gmsHideable)
        assertEquals(
            listOf(n6, xin, pixel, Images.PIXEL_KODIAK, Images.PIXEL_KOMODO, Images.INFINITYX, Images.HYPEROS_LHASA, Images.NOTHING_METROID, Images.OXYGEN16,
                Images.ORIGINOS7),
            Images.ALL,
        )
        // 0.4.67: OxygenOS 16 is the one SDK 36 image, of its own family; nothing past ARMv8.2 in its core binaries.
        assertEquals(listOf(Images.OXYGEN16), Images.ALL.filter { it.sdk == 36 })
        assertEquals(SystemFamily.OXYGENOS, Images.OXYGEN16.family)
        assertEquals(emptyList<String>(), Images.OXYGEN16.cpuRequired)
        // HyperOS (docs/hyperos.md): on the shared folder from 0.4.31; its own system family.
        val hyper = Images.HYPEROS_LHASA
        assertEquals("hyperos-lhasa", hyper.id)
        assertEquals("OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz", hyper.gzName)
        assertEquals(4_666_011_150L, hyper.gzBytes)
        assertEquals("745e43c2d116c4277af06b65c5d8fbaefec11731dcc23f0c067631fce04554a3", hyper.gzSha256)
        assertEquals(7_749_939_200L, hyper.rawBytes)
        assertEquals("269309b8869d4de41c5c852d230b4b7075b8ff733d9244f4fb868ec7109baeac", hyper.rawSha256)
        assertEquals(Images.SHARED_FOLDER_URL, hyper.downloadUrl)
        assertEquals(null, hyper.testedOn)
        assertEquals(SystemFamily.HYPEROS, hyper.family)
        assertEquals("HyperOS (Android 17)", hyper.displayName)
        // Nothing OS 5.0 (docs/nothing.md): built here from the Metroid (A024) firmware with MysticGSI,
        // its own system family, untested on a phone. Its loader uses SVE/SVE2, as the Pixel 11 builds do.
        val nothing = Images.NOTHING_METROID
        assertEquals("nothingos5-metroid", nothing.id)
        assertEquals("OneOS_NothingOS5_Metroid.img.gz", nothing.gzName)
        assertEquals(3_276_156_748L, nothing.gzBytes)
        assertEquals("3026923ea476e998fd1ae828f441937106ffbe8fbaf613a316bce444998997bd", nothing.gzSha256)
        assertEquals(6_067_867_648L, nothing.rawBytes)
        assertEquals("484f0e3a3dd2929f37b3201a57ceaf56aeca98b049a6a1f58558a2139f8a0b7b", nothing.rawSha256)
        assertEquals("AQ3A.250924.001", nothing.buildId)
        assertEquals(Images.SHARED_FOLDER_URL, nothing.downloadUrl)
        assertEquals(null, nothing.testedOn)
        assertEquals(emptyList<String>(), nothing.cpuRequired) // 0.4.36: no SVE needed after all
        assertEquals(emptyList<String>(), nothing.cpuUsedByApps)
        assertEquals(SystemFamily.NOTHING, nothing.family)
        assertEquals("Nothing OS 5.0 (Android 17)", nothing.displayName)
        assertEquals(6_067_867_648L - (1L shl 32), nothing.gzIsize)
        // 0.4.11: the Find X9 Ultra IN build is back (0.3.3-0.3.6, dropped in 0.3.7); 0.4.38: rebuilt without the debloat.
        assertEquals("coloros17-findx9u-in", xin.id)
        assertEquals("OneOS_ColorOS17_FindX9Ultra_IN_Full.img.gz", xin.gzName)
        assertEquals(7_071_596_999L, xin.gzBytes)
        assertEquals("c2eadd7e4ca2a136a91aa28f806fd99498b829d45929ff3d6fb6865d66f89bab", xin.gzSha256)
        assertEquals(14_669_168_640L, xin.rawBytes)
        assertEquals("92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6", xin.rawSha256)
        assertEquals(null, xin.testedOn)
        assertEquals(xin, Images.byGzSize(7_071_596_999L))
        assertEquals(xin, Images.byRawSize(14_669_168_640L))
        assertEquals("Find X9 Ultra IN", Images.shortName(xin.id))
        // 0.4.51: the debloated Find X9 Ultra build is retired; a retired image's name stays known (old stages,
        // the last session), and its file is named, not called "not a OneOS image".
        assertEquals(listOf("coloros17-findx9u"), Images.RETIRED.map { it.id })
        assertEquals(ImageIdentifier.R_RETIRED, ImageIdentifier.identify(ImageFileCheck("OneOS_ColorOS17_FindX9Ultra_S26U.img.gz", 5_290_346_735L), Profiles.S_ULTRA_8850).finding.reason)
        assertEquals("Find X8 Ultra", Images.shortName(old.id, retired = listOf(old)))
        assertEquals("Find N6", Images.shortName(n6.id))
        assertEquals("not-an-image", Images.shortName("not-an-image"))
        // Guest data stays with its own system (0.3.7): the ColorOS builds and the Pixel images.
        assertEquals(
            listOf(
                SystemFamily.COLOROS, SystemFamily.COLOROS,
                SystemFamily.PIXEL, SystemFamily.PIXEL, SystemFamily.PIXEL,
                SystemFamily.INFINITYX, SystemFamily.HYPEROS, SystemFamily.NOTHING, SystemFamily.OXYGENOS, SystemFamily.ORIGINOS,
            ),
            Images.ALL.map { it.family },
        )
        // The Pixel 9 Pro XL image (0.4.22) needs no SVE, unlike the Pixel 11 builds.
        assertEquals(emptyList<String>(), Images.PIXEL_KOMODO.cpuRequired)
        assertEquals(listOf("sve", "sve2"), Images.PIXEL_KODIAK.cpuRequired)
        for (i in Images.ALL) assertEquals(i.id, i.id.startsWith("coloros17-"), i.family == SystemFamily.COLOROS)

        for (i in Images.ALL) {
            // 0.4.67: SDK 37 (One UI 9) for all but OxygenOS 16 (SDK 36, One UI 8).
            assertEquals(i.id, if (i.family == SystemFamily.OXYGENOS) 36 else 37, i.sdk)
            for (h in listOf(i.gzSha256, i.rawSha256)) assertTrue(h.matches(Regex("[0-9a-f]{64}")))
        }
        // Sizes tell the images apart (the picker identifies by size first).
        val sizes = Images.ALL.flatMap { listOf(it.gzBytes, it.rawBytes) }
        assertEquals(sizes.size, sizes.toSet().size)
        assertEquals(xin, Images.byGzSize(xin.gzBytes))
        assertEquals(n6, Images.byRawSize(14_829_686_784L))
        assertNull(Images.byGzSize(5_290_346_734L))
        assertTrue(xin.rawMatches(xin.rawBytes, xin.rawSha256.uppercase()))
        assertTrue(!xin.rawMatches(xin.rawBytes - 1, xin.rawSha256))
    }

    private fun id(check: ImageFileCheck, profile: PhoneProfile? = Profiles.S_ULTRA_8850) = ImageIdentifier.identify(check, profile)

    @Test
    fun verifiedOnlyWithTheRightSizeAndHash() {
        val ok = id(ImageFileCheck(xin.gzName, xin.gzBytes, xin.gzSha256, xin.gzBytes))
        assertEquals(ImageState.VERIFIED, ok.state)
        assertEquals(Level.OK, ok.finding.level)
        assertEquals(xin, ok.image)

        val n6OnFold = ImageIdentifier.identify(ImageFileCheck(null, n6.gzBytes, n6.gzSha256, n6.gzBytes), Profiles.F8U)
        assertEquals(ImageState.VERIFIED, n6OnFold.state)
    }

    @Test
    fun sizeOnlyIsNotEnough() {
        val r = id(ImageFileCheck(xin.gzName, xin.gzBytes))
        assertEquals(ImageState.NOT_CHECKED, r.state)
        assertEquals(Level.BLOCK, r.finding.level)
        assertEquals("Check the file first", r.finding.title)
    }

    @Test
    fun wrongHashOrTruncatedIsDamaged() {
        val badHash = id(ImageFileCheck("x.img.gz", xin.gzBytes, "0".repeat(64), xin.gzBytes))
        assertEquals(ImageState.DAMAGED, badHash.state)
        assertEquals(Level.BLOCK, badHash.finding.level)
        assertTrue(badHash.finding.detail.contains("Download it again"))

        // The provider said the right size, but the stream ended early.
        val short = id(ImageFileCheck("x.img.gz", xin.gzBytes, xin.gzSha256, xin.gzBytes - 1))
        assertEquals(Level.BLOCK, short.finding.level)

        // Hash right, provider size different: refused.
        val mixed = id(ImageFileCheck("x.img.gz", xin.gzBytes + 1, xin.gzSha256, xin.gzBytes))
        assertEquals(ImageState.DAMAGED, mixed.state)
    }

    @Test
    fun wrongImageForThePhone() {
        val n6OnS26 = id(ImageFileCheck("OneOS_ColorOS17_FindN6_Global.img.gz", n6.gzBytes, n6.gzSha256, n6.gzBytes))
        assertEquals(ImageState.WRONG_FOR_PHONE, n6OnS26.state)
        assertEquals(Level.BLOCK, n6OnS26.finding.level)
        // The BLOCK names every image the phone takes.
        assertEquals(
            "This is the Find N6 image; Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN_Full.img.gz) " +
                "or the Pixel 11 Pro image (OneOS_Pixel11Pro_Full_S26U.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz) or the Xiaomi 18 Fold image (OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz) " +
                "or the Nothing OS image (OneOS_NothingOS5_Metroid.img.gz) or the OriginOS 7 image (OneOS_OriginOS7_PD2609MA.img.gz).",
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
        // The Galaxy Z Fold7 takes the Find N6 image, Infinity-X (0.4.27) and HyperOS (0.4.31), no Pixel: Pixel 11's system code needs
        // SVE, which SM8750 lacks.
        val pixelOnFold7 = ImageIdentifier.identify(ImageFileCheck(null, pixel.gzBytes, pixel.gzSha256, pixel.gzBytes), Profiles.FOLD7)
        assertEquals(ImageState.WRONG_FOR_PHONE, pixelOnFold7.state)
        assertEquals(
            "This is the Pixel 11 Fold image; Galaxy Z Fold7 takes the Find N6 image (OneOS_ColorOS17_FindN6_Global.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz) or the Xiaomi 18 Fold image (OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz) " +
                "or the Nothing OS image (OneOS_NothingOS5_Metroid.img.gz) or the OriginOS 7 image (OneOS_OriginOS7_PD2609MA.img.gz).",
            pixelOnFold7.finding.detail,
        )
        // The owner does not want the X9U (CN) image on his Fold; by size alone already.
        for (check in listOf(ImageFileCheck(null, xin.gzBytes, xin.gzSha256, xin.gzBytes), ImageFileCheck(null, xin.gzBytes))) {
            val x9uOnFold = ImageIdentifier.identify(check, Profiles.F8U)
            assertEquals(ImageState.WRONG_FOR_PHONE, x9uOnFold.state)
            assertEquals(Level.BLOCK, x9uOnFold.finding.level)
            assertEquals(xin, x9uOnFold.image)
            assertEquals(
                "This is the Find X9 Ultra IN image; Z Fold (F8U) takes the Find N6 image (OneOS_ColorOS17_FindN6_Global.img.gz) " +
                    "or the Pixel 11 Fold image (OneOS_Pixel11Fold_Full_ZFold8.img.gz) or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz) " +
                    "or the Xiaomi 18 Fold image (OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz) " +
                    "or the Nothing OS image (OneOS_NothingOS5_Metroid.img.gz) or the OriginOS 7 image (OneOS_OriginOS7_PD2609MA.img.gz).",
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
        // 0.4.27: Infinity-X, on every phone; 0.4.31: HyperOS after it, on every phone too.
        val ifx = Images.INFINITYX
        val hyper = Images.HYPEROS_LHASA
        // 0.4.33: Nothing OS on the Z Fold (F8U); 0.4.35 on every SVE + SME phone.
        val nothing = Images.NOTHING_METROID
        // 0.4.73: OriginOS 7 on the Snapdragon S25/S26 series and the Z Fold7/8 phones; 0.4.82 the Snapdragon S24 and S23 phones;
        // 0.4.83 the Exynos S24 and S24+.
        val origin = Images.ORIGINOS7
        val takes = mapOf(
            Profiles.F8U to listOf(n6, pixel, ifx, hyper, nothing, origin),
            Profiles.S_ULTRA_8850 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing, origin),
            // 0.4.22: the Pixel 9 Pro XL image on the phones without SVE.
            Profiles.S_ULTRA_8750 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin),
            Profiles.S_8750 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin),
            Profiles.FOLD7 to listOf(n6, ifx, hyper, nothing, origin),
            Profiles.S_PLUS_8750 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin),
            Profiles.FOLD8 to listOf(n6, pixel, ifx, hyper, nothing, origin),
            Profiles.S_8850 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing, origin),
            Profiles.S_ULTRA_8650 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin), // 0.4.82
            Profiles.S_8550 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, Images.OXYGEN16, origin), // 0.4.82; 0.4.91 OxygenOS 16
            Profiles.S_9945 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin), // 0.4.83
            Profiles.S_PLUS_9945 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper, nothing, origin), // 0.4.83
            Profiles.S_FE_9945 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper),
            Profiles.S_PLUS_8850 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing, origin),
            Profiles.S_PLUS_9965 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing),
            Profiles.S_9965 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing),
            Profiles.FLIP7 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper),
            Profiles.A57 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper),
            Profiles.FLIP5 to listOf(xin, Images.PIXEL_KOMODO, ifx, hyper),
            Profiles.FLIP8 to listOf(xin, Images.PIXEL_KODIAK, ifx, hyper, nothing),
            Profiles.A36 to listOf(xin, ifx, hyper), // 0.4.57: no Pixel 9 Pro XL on ARMv8.2
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
            "Z Fold (F8U) takes the Find N6 image (OneOS_ColorOS17_FindN6_Global.img.gz) or the Pixel 11 Fold image " +
                "(OneOS_Pixel11Fold_Full_ZFold8.img.gz) or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz) or the Xiaomi 18 Fold image " +
                "(OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz) or the Nothing OS image (OneOS_NothingOS5_Metroid.img.gz) " +
                "or the OriginOS 7 image (OneOS_OriginOS7_PD2609MA.img.gz)",
            ImageIdentifier.accepts(Profiles.F8U),
        )
        assertEquals(
            "Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN_Full.img.gz) " +
                "or the Pixel 11 Pro image (OneOS_Pixel11Pro_Full_S26U.img.gz) " +
                "or the Infinity-X image (OneOS_InfinityX_FindX9Ultra.img.gz) or the Xiaomi 18 Fold image (OneOS_HyperOS_Xiaomi18Fold_ZFold8.img.gz) " +
                "or the Nothing OS image (OneOS_NothingOS5_Metroid.img.gz) or the OriginOS 7 image (OneOS_OriginOS7_PD2609MA.img.gz)",
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
        val cnOnFold = staged(xin.rawBytes)
        assertEquals(ImageState.WRONG_FOR_PHONE, cnOnFold.state)
        assertEquals(Level.BLOCK, cnOnFold.finding.level)
        assertTrue(cnOnFold.finding.detail.contains("Find X9 Ultra IN image; Z Fold (F8U) takes the Find N6 image"))
        val n6OnS26 = staged(n6.rawBytes, n6.rawSha256, Profiles.S_ULTRA_8850)
        assertEquals(ImageState.WRONG_FOR_PHONE, n6OnS26.state)
        assertTrue(n6OnS26.finding.detail, n6OnS26.finding.detail.contains("Galaxy S26 Ultra takes the Find X9 Ultra IN image (OneOS_ColorOS17_FindX9Ultra_IN_Full.img.gz) or the Pixel 11 Pro image"))
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
        val raw = id(ImageFileCheck("oneos-coloros-xin.img", xin.rawBytes))
        assertEquals(ImageState.UNCOMPRESSED, raw.state)
        assertEquals(Level.BLOCK, raw.finding.level)

        val other = id(ImageFileCheck("holiday.mp4", 123_456_789))
        assertEquals(ImageState.UNKNOWN, other.state)
        assertEquals(Level.BLOCK, other.finding.level)
        assertTrue(other.finding.detail.contains(xin.gzName))

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
        assertEquals("ColorOS 17 · Find N6 global build (Android 17)", n6.displayName)
        assertEquals("Pixel 11 Fold", pixel.nameWithVariant)
        assertEquals("Pixel 11 Fold (Android 17)", pixel.displayName)
        assertEquals("Pixel 11 Fold", Images.systemName(pixel, Profiles.F8U))
        // {system}: the name, with the variant only when the phone takes another of that name
        // (the Fold takes ColorOS 17 and Pixel 11 Fold; from 0.4.11 the bar phones take two ColorOS 17 builds).
        assertEquals("ColorOS 17", Images.systemName(n6))
        assertEquals("ColorOS 17", Images.systemName(n6, Profiles.F8U))
        // 0.4.51: the bar phones take one ColorOS 17 again (the debloated Find X9 Ultra build retired).
        assertEquals("ColorOS 17", Images.systemName(xin, Profiles.S_ULTRA_8850))
        assertEquals("Find X9 Ultra", Images.shortName("coloros17-findx9u"))
        val twin = Profiles.F8U.copy(choices = Profiles.F8U.choices + ImageChoice(xin.id, PackageSets.ID_X9U_IN_SULTRA, false))
        assertEquals("ColorOS 17 · Find N6 global build", Images.systemName(n6, twin))
        assertEquals("the other system", Images.systemName(null))
        // The Fold's recommended system is the one that has run on it.
        assertEquals(Images.ID_FIND_N6, Profiles.F8U.recommended!!.imageId)
        assertEquals(Images.ID_FIND_X9U_IN, Profiles.S_ULTRA_8850.recommended!!.imageId)
    }

    @Test
    fun everyBlockHasAReason() {
        val checks = listOf(
            ImageFileCheck(null, null),
            ImageFileCheck("x", 12345),
            ImageFileCheck("x", n6.rawBytes),
            ImageFileCheck("x", xin.gzBytes),
            ImageFileCheck("x", n6.gzBytes),
            ImageFileCheck("x", n6.gzBytes, "0".repeat(64), n6.gzBytes),
            ImageFileCheck("x", old.gzBytes),
        )
        for (c in checks) {
            val f = ImageIdentifier.identify(c, Profiles.F8U, retiredImages = listOf(old)).finding
            if (f.level == Level.BLOCK) assertTrue("$c", f.reason != null)
        }
        for (raw in listOf(StagedRaw(null), StagedRaw(1), StagedRaw(xin.rawBytes), StagedRaw(n6.rawBytes, "0".repeat(64)))) {
            val f = ImageIdentifier.identifyStaged(raw, Profiles.F8U).finding
            if (f.level == Level.BLOCK) assertTrue("$raw", f.reason != null)
        }
    }
}
