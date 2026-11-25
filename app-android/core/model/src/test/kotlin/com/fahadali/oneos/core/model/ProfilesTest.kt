package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProfilesTest {
    @Test
    fun theFourBundlesResolveToTheirProfiles() {
        assertEquals(Profiles.F8U, Profiles.resolve(Bundles.F8U.facts).profile)
        assertEquals(Profiles.S_ULTRA_8850, Profiles.resolve(Bundles.S26U.facts).profile)
        assertEquals(Profiles.S_ULTRA_8750, Profiles.resolve(Bundles.S25U.facts).profile)
        assertEquals(Profiles.S_8750, Profiles.resolve(Bundles.S25.facts).profile)
        // The hardware says what the profile says.
        assertEquals(FormFactor.FOLD, Bundles.F8U.facts.form.form)
        assertEquals(FormFactor.BAR, Bundles.S26U.facts.form.form)
        assertEquals(FormFactor.BAR, Bundles.S25U.facts.form.form)
        assertEquals(FormFactor.BAR, Bundles.S25.facts.form.form)
        assertTrue(Bundles.S25.facts.form.evidence.contains("1 built-in display"))
    }

    @Test
    fun builtInTable() {
        // 0.4.27: Infinity-X, last, on every phone, untested.
        val ifx = ImageChoice(Images.ID_INFINITYX, PackageSets.ID_INFINITYX, tested = false)
        // 0.4.31: tested where a tester's session reached the home screen on it
        // (reports of 2026-10-29/30, docs/compatibility.md).
        val ifxT = ifx.copy(tested = true)
        // 0.5.06: LineageOS 24 right after Infinity-X on every phone that offers it, untested.
        val lineage = ImageChoice(Images.ID_LINEAGE, PackageSets.ID_LINEAGE, tested = false)
        // 0.4.31: HyperOS after it, on every phone, untested.
        val hyper = ImageChoice(Images.ID_HYPEROS_LHASA, PackageSets.ID_HYPER_F8U, tested = false)
        // 0.5.27: HyperOS 4 Global right after it, on the same phones, untested here (tested on the A36 as an image).
        val hyperHk = ImageChoice(Images.ID_HYPEROS_HONGKONG, PackageSets.ID_HYPER_HK, tested = false)
        // 0.4.35: Nothing OS, last, on every phone whose chip has its SVE, SVE2 and SME, untested.
        val nothing = ImageChoice(Images.ID_NOTHING_METROID, PackageSets.ID_NOTHING_F8U, tested = false)
        // 0.4.73: OriginOS 7, last, on the Snapdragon S25/S26 series and the Z Fold7/8 phones; tested on the Z Fold8 Ultra.
        val origin = ImageChoice(Images.ID_ORIGINOS7, PackageSets.ID_ORIGINOS, tested = false)
        // 0.5.22: One UI 9.5 (the Galaxy S26 Ultra build), last, on every phone that runs One UI 9, untested.
        val oneui = ImageChoice(Images.ID_ONEUI95, PackageSets.ID_ONEUI95, tested = false)
        // 0.5.35: PixelOS 17 before One UI 9.5 on every bar phone on One UI 9 (owner).
        val px = ImageChoice(Images.ID_PIXELOS_ONYX, PackageSets.ID_PIXELOS, tested = false)
        val f8u = Profiles.F8U
        assertEquals(listOf("SM-F976", "q8q", "SM8850"), listOf(f8u.modelPrefix, f8u.codename, f8u.socModel))
        assertEquals(FormFactor.FOLD, f8u.form)
        assertEquals(
            listOf(
                ImageChoice("coloros17-findn6", "n6-f8u", tested = true),
                // 0.3.7: the Pixel 11 Fold image, which runs 41-44 booted on this phone.
                ImageChoice("pixel11fold-yogi", "pixel-f8u", tested = true),
                // 0.5.15: Infinity-X, LineageOS and Nothing OS tested by the team here (the owner's runs).
                ifx.copy(tested = true),
                lineage.copy(tested = true),
                // HyperOS (0.4.31: on every phone), untested.
                ImageChoice("hyperos-lhasa", "hyper-f8u", tested = false),
                ImageChoice("hyperos-hongkong", "hyper-hk", tested = false),
                ImageChoice("nothingos5-metroid", "nothing-f8u", tested = true),
                // OriginOS 7 (0.4.73): runs 13-24 on this phone.
                ImageChoice("originos7-pd2609ma", "originos", tested = true),
                ImageChoice("oneui95-s948b", "oneui95", tested = false),
            ),
            f8u.choices,
        )
        assertTrue(f8u.testedWithAnyImage && f8u.enabled)

        val s26 = Profiles.S_ULTRA_8850
        assertEquals(listOf("SM-S948", "m3q", "SM8850"), listOf(s26.modelPrefix, s26.codename, s26.socModel))
        assertEquals(FormFactor.BAR, s26.form)
        // The Find X9 Ultra CN image, tested on the S Ultras and the S25 since 0.4.7; from
        // 0.4.11 the IN build first, untested.
        // 0.5.10: the November build replaces the first IN build everywhere, tested where that one was.
        val xin = ImageChoice(Images.ID_FIND_X9U_IN_1105, PackageSets.ID_X9U_IN_1105_SULTRA, tested = false)
        val xinT = xin.copy(tested = true)
        // 0.4.51: the IN build only (the debloated Find X9 Ultra build retired), tested where that one was.
        val sUltra = listOf(xinT)
        // 0.4.10: and the Pixel 11 Pro image with its own set, untested.
        assertEquals(sUltra + ImageChoice(Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, tested = false) + ifxT + lineage + hyper + hyperHk + nothing + origin + px + oneui, s26.choices)
        assertTrue(s26.testedWithAnyImage && s26.enabled)

        val s25 = Profiles.S_ULTRA_8750
        assertEquals(listOf("SM-S938", "pa3q", "SM8750"), listOf(s25.modelPrefix, s25.codename, s25.socModel))
        assertEquals(FormFactor.BAR, s25.form)
        // 0.4.22: and the Pixel 9 Pro XL image with its own set, untested.
        val pixel9 = ImageChoice(Images.ID_PIXEL_KOMODO, PackageSets.ID_PIXEL9_SULTRA, tested = false)
        assertEquals(sUltra + pixel9 + ifxT + lineage + hyper + hyperHk + nothing + origin + px + oneui, s25.choices)
        assertTrue(s25.testedWithAnyImage && s25.enabled)

        // Galaxy S25 (0.3.4): the S Ultra image and set (tested since 0.4.7), the S25 Ultra's notes.
        val s25Base = Profiles.S_8750
        assertEquals("s-8750", s25Base.id)
        assertEquals("Galaxy S25", s25Base.label)
        assertEquals(listOf("SM-S931", "pa1q", "SM8750"), listOf(s25Base.modelPrefix, s25Base.codename, s25Base.socModel))
        assertEquals(FormFactor.BAR, s25Base.form)
        // 0.5.28: HyperOS 4 Global and One UI 9.5 ran on an S25 (reports of 2026-11-20).
        assertEquals(sUltra + pixel9 + ifxT + lineage + hyper + hyperHk.copy(tested = true) + nothing + origin + px + oneui.copy(tested = true), s25Base.choices)
        assertTrue(s25Base.testedWithAnyImage && s25Base.enabled)
        assertEquals(s25.notes, s25Base.notes)
        assertEquals(listOf("profile-vendor-older"), s25Base.notes.map { it.id })
        // Galaxy Z Fold7 (0.4.8): the Find N6 image with the Fold's set, untested; the SM8750 notes; no Pixel image (SVE).
        val fold7 = Profiles.FOLD7
        assertEquals("f7", fold7.id)
        assertEquals("Galaxy Z Fold7", fold7.label)
        assertEquals(listOf("SM-F966", "q7q", "SM8750"), listOf(fold7.modelPrefix, fold7.codename, fold7.socModel))
        assertEquals(FormFactor.FOLD, fold7.form)
        assertEquals(listOf(ImageChoice(Images.ID_FIND_N6, PackageSets.ID_N6_F8U, tested = false), ifx, lineage, hyper, hyperHk, nothing, origin, oneui), fold7.choices)
        assertTrue(fold7.enabled && !fold7.testedWithAnyImage)
        assertEquals(s25.notes, fold7.notes)
        assertTrue(fold7.choice(Images.ID_PIXEL_YOGI) == null)
        // Galaxy S25+ (0.4.10): the S25's image and set, untested; the SM8750 notes.
        val s25Plus = Profiles.S_PLUS_8750
        assertEquals(listOf("s-plus-8750", "Galaxy S25+"), listOf(s25Plus.id, s25Plus.label))
        assertEquals(listOf("SM-S936", "pa2q", "SM8750"), listOf(s25Plus.modelPrefix, s25Plus.codename, s25Plus.socModel))
        assertEquals(FormFactor.BAR, s25Plus.form)
        assertEquals(listOf(xin, pixel9, ifx, lineage, hyper, hyperHk, nothing, origin, px, oneui), s25Plus.choices)
        assertEquals(s25.notes, s25Plus.notes)
        // Galaxy Z Fold8 (0.4.10): the Fold's images and sets, untested; no older-vendor note (vendor API 202504).
        val fold8 = Profiles.FOLD8
        assertEquals(listOf("f8", "Galaxy Z Fold8"), listOf(fold8.id, fold8.label))
        assertEquals(listOf("SM-F971", "h8q", "SM8850"), listOf(fold8.modelPrefix, fold8.codename, fold8.socModel))
        assertEquals(FormFactor.FOLD, fold8.form)
        // 0.4.38: the Find N6 global image with the Folds' set (n6-f8 of pull request #1 was the CN build's).
        assertEquals(
            listOf(
                ImageChoice(Images.ID_FIND_N6, PackageSets.N6_GLOBAL_F8.id, tested = false),
                ImageChoice(Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8, tested = true),
                ifx,
                lineage,
                hyper, hyperHk,
                nothing,
                origin,
                // 0.5.35: the Fold8's own One UI 9.5 set with Josh's Fold8 files.
                ImageChoice(Images.ID_ONEUI95, PackageSets.ID_ONEUI95_F8, tested = false),
            ),
            fold8.choices,
        )
        assertTrue(fold8.notes.isEmpty() && fold8.testedWithAnyImage)
        // 0.4.38: the Pixel image, the one the Fold8 has run (the Find N6 global build not yet).
        assertEquals(Images.ID_PIXEL_YOGI, fold8.recommended?.imageId)
        // Galaxy S26 (0.4.11): the S Ultra's images and sets, untested; one profile per model number.
        val s26Base = Profiles.S_8850
        assertEquals(listOf("s-8850", "Galaxy S26"), listOf(s26Base.id, s26Base.label))
        assertEquals(listOf("SM-S942", "m1q", "SM8850"), listOf(s26Base.modelPrefix, s26Base.codename, s26Base.socModel))
        assertEquals(FormFactor.BAR, s26Base.form)
        assertEquals(
            listOf(
                xin,
                ImageChoice(Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, tested = false),
                ifx,
                lineage,
                hyper, hyperHk,
                nothing,
                origin,
                px,
                oneui,
            ),
            s26Base.choices,
        )
        assertTrue(s26Base.notes.isEmpty() && !s26Base.testedWithAnyImage)
        val s26Jp = Profiles.S_8850_JP
        assertEquals(listOf("s-8850-jp", "SC-51G", "m1q", "SM8850"), listOf(s26Jp.id, s26Jp.modelPrefix, s26Jp.codename, s26Jp.socModel))
        assertEquals(s26Base.choices, s26Jp.choices)
        assertEquals(s26Base.form, s26Jp.form)
        // Galaxy S24 Ultra (0.4.11): the X9U image, untested; the older-vendor note with its own versions.
        val s24u = Profiles.S_ULTRA_8650
        assertEquals(listOf("s-ultra-8650", "Galaxy S24 Ultra"), listOf(s24u.id, s24u.label))
        assertEquals(listOf("SM-S928", "e3q", "SM8650"), listOf(s24u.modelPrefix, s24u.codename, s24u.socModel))
        assertEquals(listOf(xin, pixel9, ifxT, lineage, hyper, hyperHk, nothing, origin, px, oneui), s24u.choices) // 0.4.82: OriginOS 7, untested
        assertEquals(listOf(Profiles.ID_NOTE_OLDER_VENDOR), s24u.notes.map { it.id })
        assertTrue(s24u.notes.single().detail.contains("vendor API 34 (Android 14) and kernel 6.1"))
        // Galaxy S26+ (0.4.12): the S26's images and sets, untested, no notes (vendor API 202504).
        val s26Plus = Profiles.S_PLUS_8850
        assertEquals(listOf("s-plus-8850", "Galaxy S26+"), listOf(s26Plus.id, s26Plus.label))
        assertEquals(listOf("SM-S947", "m2q", "SM8850"), listOf(s26Plus.modelPrefix, s26Plus.codename, s26Plus.socModel))
        assertEquals(FormFactor.BAR, s26Plus.form)
        assertEquals(s26Base.choices, s26Plus.choices)
        assertTrue(s26Plus.notes.isEmpty() && !s26Plus.testedWithAnyImage)
        // The Exynos Galaxy S26+ and Z Flip7 (0.4.17): their own codenames and chips, untested, the Exynos note;
        // the S26+ takes the S26's images (SVE for Pixel), the Flip7 the Find X9 Ultra builds as a phone.
        val s26PlusExynos = Profiles.S_PLUS_9965
        assertEquals(listOf("s-plus-9965", "Galaxy S26+ (Exynos)"), listOf(s26PlusExynos.id, s26PlusExynos.label))
        assertEquals(listOf("SM-S947", "m2s", "s5e9965"), listOf(s26PlusExynos.modelPrefix, s26PlusExynos.codename, s26PlusExynos.socModel))
        assertEquals(FormFactor.BAR, s26PlusExynos.form)
        assertEquals(s26Base.choices - origin, s26PlusExynos.choices) // 0.4.73: OriginOS on the Snapdragon S26s only
        // The Exynos Galaxy S26 (0.4.52): the S26's model number, its own codename and the S26+ (Exynos)'s chip and images.
        val s26Exynos = Profiles.S_9965
        assertEquals(listOf("s-9965", "Galaxy S26 (Exynos)"), listOf(s26Exynos.id, s26Exynos.label))
        assertEquals(listOf("SM-S942", "m1s", "s5e9965"), listOf(s26Exynos.modelPrefix, s26Exynos.codename, s26Exynos.socModel))
        assertEquals(FormFactor.BAR, s26Exynos.form)
        assertEquals(s26PlusExynos.choices, s26Exynos.choices)
        assertEquals(s26PlusExynos.notes, s26Exynos.notes)
        assertTrue(!s26Exynos.testedWithAnyImage)
        val flip7 = Profiles.FLIP7
        assertEquals(listOf("flip7", "Galaxy Z Flip7"), listOf(flip7.id, flip7.label))
        assertEquals(listOf("SM-F766", "b7s", "s5e9955"), listOf(flip7.modelPrefix, flip7.codename, flip7.socModel))
        assertEquals(FormFactor.FLIP, flip7.form)
        assertEquals(listOf(xin, ImageChoice(Images.ID_PIXEL_KOMODO, PackageSets.ID_PIXEL9_SULTRA, tested = false), ifx, lineage, hyper, hyperHk, oneui), flip7.choices)
        // The Galaxy A57 (0.4.29): the first A-series phone, Exynos, a bar phone with the Flip7's images.
        val a57 = Profiles.A57
        assertEquals(listOf("a57", "Galaxy A57"), listOf(a57.id, a57.label))
        assertEquals(listOf("SM-A576", "a57x", "s5e8865"), listOf(a57.modelPrefix, a57.codename, a57.socModel))
        assertEquals(FormFactor.BAR, a57.form)
        // 0.4.31: a tester's session reached home on the CN ColorOS build (2026-10-30),
        // the first A-series report; the rest is still the Flip7's list.
        assertEquals(
            listOf(xinT, pixel9, ifx, lineage, hyper, hyperHk, ImageChoice(Images.ID_NOTHING_ASTEROIDS, PackageSets.ID_NOTHING_A, tested = false), px, oneui), // 0.5.15: Nothing OS (A series); 0.5.22: One UI 9.5, last
            a57.choices,
        )
        assertTrue(a57.testedWithAnyImage)
        // The Galaxy A56 (0.4.31): the A57's smaller sibling, one Exynos generation down.
        val a56 = Profiles.A56
        assertEquals(listOf("a56", "Galaxy A56"), listOf(a56.id, a56.label))
        assertEquals(listOf("SM-A566", "a56x", "s5e8855"), listOf(a56.modelPrefix, a56.codename, a56.socModel))
        assertEquals(FormFactor.BAR, a56.form)
        // 0.5.28: HyperOS 4 Global and One UI 9.5 ran on an A56 (reports of 2026-11-19/20).
        assertEquals(
            (flip7.choices - oneui + ImageChoice(Images.ID_NOTHING_ASTEROIDS, PackageSets.ID_NOTHING_A, tested = false) + px + oneui)
                .map { if (it.imageId == Images.ID_HYPEROS_HONGKONG || it.imageId == Images.ID_ONEUI95) it.copy(tested = true) else it },
            a56.choices,
        )
        assertTrue(a56.testedWithAnyImage)
        for (p in listOf(s26PlusExynos, flip7, a56)) {
            assertEquals(listOf(Profiles.ID_NOTE_EXYNOS), p.notes.map { it.id })
            assertEquals(Level.WARN, p.notes.single().level)
        }
        assertFalse(s26PlusExynos.testedWithAnyImage)
        assertFalse(flip7.testedWithAnyImage)
        // Galaxy Z Flip5 (0.4.29): the S23s' chip and vendor, a flip with their images and note.
        val flip5 = Profiles.FLIP5
        assertEquals(listOf("flip5", "Galaxy Z Flip5"), listOf(flip5.id, flip5.label))
        assertEquals(listOf("SM-F731", "b5q", "SM8550"), listOf(flip5.modelPrefix, flip5.codename, flip5.socModel))
        assertEquals(FormFactor.FLIP, flip5.form)
        // 0.4.31: reported on the global ColorOS build and Infinity-X (camera broken on both),
        // so it is no longer the S23's untested list.
        assertEquals(
            listOf(xinT, pixel9, ifxT, lineage, hyper, hyperHk, origin, oneui), // 0.5.46: OriginOS (owner)
            flip5.choices,
        )
        assertEquals(listOf(Profiles.ID_NOTE_EXPECT_NO_START), flip5.notes.map { it.id })
        // Galaxy Z Flip8 (0.4.35): the S26+ (Exynos)'s chip in a flip, its images and the Exynos note.
        val flip8 = Profiles.FLIP8
        assertEquals(listOf("flip8", "Galaxy Z Flip8"), listOf(flip8.id, flip8.label))
        assertEquals(listOf("SM-F776", "b8s", "s5e9965"), listOf(flip8.modelPrefix, flip8.codename, flip8.socModel))
        assertEquals(FormFactor.FLIP, flip8.form)
        assertEquals(s26Base.choices - origin - px, flip8.choices)
        assertEquals(listOf(Profiles.ID_NOTE_EXYNOS), flip8.notes.map { it.id })
        // Galaxy A36 (0.4.35): a mid-range Snapdragon with the S25s' vendor, the S25+'s images and note.
        val a36 = Profiles.A36
        assertEquals(listOf("a36", "Galaxy A36"), listOf(a36.id, a36.label))
        assertEquals(listOf("SM-A366", "a36xq", "SM6475"), listOf(a36.modelPrefix, a36.codename, a36.socModel))
        assertEquals(FormFactor.BAR, a36.form)
        // 0.4.57: without the Pixel 9 Pro XL (ARMv8.2, as the A26).
        // 0.5.15: Nothing OS for the A series (the Phone (3a) build), last.
        // 0.5.22: One UI 9.5 after it.
        assertEquals(s25Plus.choices - nothing - origin - oneui - px - s25Plus.choices.filter { it.imageId == Images.ID_PIXEL_KOMODO } +
            ImageChoice(Images.ID_NOTHING_ASTEROIDS, PackageSets.ID_NOTHING_A, tested = false) +
            // 0.5.35: PixelOS 17 (the Pixel-style system ARMv8.2 can run) before One UI 9.5.
            ImageChoice(Images.ID_PIXELOS_ONYX, PackageSets.ID_PIXELOS, tested = false) + oneui, a36.choices)
        assertEquals(listOf(Profiles.ID_NOTE_OLDER_VENDOR), a36.notes.map { it.id })
        // Nothing OS (0.4.35) on the SVE + SME phones; 0.4.36 also the S25s, S24 Ultra, Fold7 and Fold6 (brightness scale ~5); 0.4.61 the S24 (Snapdragon, scale 5.0);
        // 0.4.83 the Exynos S24 and S24+ (scale 5.0 on One UI 9); 0.5.19 the S23, S23+ and S23 Ultra (owner, untested).
        assertEquals(
            listOf(Profiles.F8U, Profiles.S_ULTRA_8850, Profiles.S_ULTRA_8750, Profiles.S_8750, Profiles.FOLD7, Profiles.S_PLUS_8750,
                Profiles.FOLD8, Profiles.S_8850, Profiles.S_8850_JP, Profiles.S_ULTRA_8650, Profiles.S_8650, Profiles.S_8550, Profiles.S_PLUS_8550,
                Profiles.S_PLUS_8850, Profiles.S_PLUS_9965, Profiles.FOLD6, Profiles.FLIP8, Profiles.S_ULTRA_8550, Profiles.S_9945, Profiles.S_EDGE_8750,
                Profiles.S_9965, Profiles.S_PLUS_9945, Profiles.S_ULTRA_8550_JP, Profiles.S_8550_JP, Profiles.S_PLUS_8650),
            Profiles.BUILT_IN.filter { it.choice(Images.ID_NOTHING_METROID) != null },
        )
        // Galaxy S23 and S23+ (0.4.11): the X9U image, untested, with the will-most-likely-not-start note.
        val s23 = Profiles.S_8550
        val s23Plus = Profiles.S_PLUS_8550
        assertEquals(listOf("s-8550", "Galaxy S23"), listOf(s23.id, s23.label))
        assertEquals(listOf("SM-S911", "dm1q", "SM8550"), listOf(s23.modelPrefix, s23.codename, s23.socModel))
        assertEquals(listOf("s-plus-8550", "Galaxy S23+"), listOf(s23Plus.id, s23Plus.label))
        assertEquals(listOf("SM-S916", "dm2q", "SM8550"), listOf(s23Plus.modelPrefix, s23Plus.codename, s23Plus.socModel))
        for (p in listOf(s23, s23Plus)) {
            assertEquals(FormFactor.BAR, p.form)
            // 0.4.91 (owner: "add oxygenos to s23 series on oneui8/8.5"): OxygenOS 16 for the ones still on One UI 8, before OriginOS.
            assertEquals(
                listOf(xin, ImageChoice(Images.ID_PIXEL_KOMODO, PackageSets.ID_PIXEL9_SULTRA, tested = false), ifx, lineage, hyper, hyperHk,
                    ImageChoice(Images.ID_OXYGEN16, PackageSets.ID_OXYGEN16, tested = false), nothing, origin, px, oneui), // 0.5.22: One UI 9.5; 0.5.19: Nothing OS (Metroid), owner
                p.choices.map { it.copy(tested = false) },
            )
            assertEquals(Profiles.S_ULTRA_8550.choices.map { it.copy(tested = false) }, p.choices.map { it.copy(tested = false) })
            assertEquals(listOf(Profiles.ID_NOTE_EXPECT_NO_START), p.notes.map { it.id })
            assertEquals(Level.WARN, p.notes.single().level)
        }
        // 0.5.28: what ran (reports of 2026-11-19/20): the S23 ColorOS global, HyperOS 4 Global and One UI 9.5;
        // the S23 Ultra HyperOS 4 Global and Nothing OS; the S23+ nothing yet.
        assertEquals(listOf(Images.ID_FIND_X9U_IN_1105, Images.ID_HYPEROS_HONGKONG, Images.ID_ONEUI95), s23.choices.filter { it.tested }.map { it.imageId })
        assertEquals(listOf(Images.ID_HYPEROS_HONGKONG, Images.ID_NOTHING_METROID), Profiles.S_ULTRA_8550.choices.filter { it.tested }.map { it.imageId })
        assertFalse(s23Plus.testedWithAnyImage)
        // 0.4.82: OriginOS 7 also on the Snapdragon S24 and S23 phones (untested there), last in their lists;
        // 0.4.83 (owner: "the same supported roms as s24 ultra to plus and base too") the Exynos S24 and S24+,
        // the only Exynos phones with it. Tested on the Z Fold8 Ultra only.
        val offerOrigin = Profiles.BUILT_IN.filter { it.choice(Images.ID_ORIGINOS7) != null }
        assertEquals(
            setOf(
                Profiles.ID_F8U, Profiles.ID_FOLD8, Profiles.ID_FOLD7,
                Profiles.ID_S_ULTRA_8850, Profiles.ID_S_PLUS_8850, Profiles.ID_S_8850, Profiles.ID_S_8850_JP,
                Profiles.ID_S_ULTRA_8750, Profiles.ID_S_PLUS_8750, Profiles.ID_S_8750, Profiles.ID_S_EDGE_8750,
                Profiles.ID_S_ULTRA_8650, Profiles.ID_S_8650, Profiles.ID_S_9945, Profiles.ID_S_PLUS_9945, Profiles.ID_S_PLUS_8650,
                Profiles.ID_S_ULTRA_8550, Profiles.ID_S_PLUS_8550, Profiles.ID_S_8550,
                Profiles.ID_S_ULTRA_8550_JP, // 0.4.92: the au S23 Ultra, the S23 Ultra's list
                Profiles.ID_S_8550_JP, // 0.4.93: the au S23, the S23's list
                Profiles.ID_FLIP5, // 0.5.46 (owner): the S23s' chip
                Profiles.ID_FOLD5, // 0.5.47 (owner): the same chip
            ),
            offerOrigin.map { it.id }.toSet(),
        )
        assertEquals(
            listOf(Profiles.ID_S_9945, Profiles.ID_S_PLUS_9945),
            offerOrigin.filter { p -> p.notes.any { it.id == Profiles.ID_NOTE_EXYNOS } }.map { it.id },
        )
        assertEquals(listOf(Profiles.ID_F8U), offerOrigin.filter { it.choice(Images.ID_ORIGINOS7)!!.tested }.map { it.id })
        // 0.5.22: OriginOS 7 is last but One UI 9.5, which every phone with it also offers.
        for (p in offerOrigin) assertEquals(p.id, listOf(Images.ID_ORIGINOS7, Images.ID_ONEUI95), p.choices.filter { it.imageId != Images.ID_PIXELOS_ONYX }.takeLast(2).map { it.imageId })
        assertEquals(
            listOf(
                Profiles.F8U, Profiles.S_ULTRA_8850, Profiles.S_ULTRA_8750, Profiles.S_8750, Profiles.FOLD7, Profiles.S_PLUS_8750, Profiles.FOLD8,
                Profiles.S_8850, Profiles.S_8850_JP, Profiles.S_ULTRA_8650, Profiles.S_8650, Profiles.S_8550, Profiles.S_PLUS_8550, Profiles.S_PLUS_8850,
                Profiles.S_PLUS_9965, Profiles.FLIP7, Profiles.A56, Profiles.A57, Profiles.FLIP5,
                Profiles.FOLD6, Profiles.A07, Profiles.FLIP8, Profiles.A36, Profiles.FOLD5, Profiles.FOLD4,
                Profiles.S_ULTRA_8550, Profiles.FLIP6, Profiles.S_9945, Profiles.S_EDGE_8750, Profiles.S_FE_9945,
                Profiles.A26, Profiles.A17, Profiles.A16, Profiles.S_9965, Profiles.A16_4G, Profiles.A16_S166, Profiles.A35, Profiles.A54, Profiles.A27, Profiles.A17_5G, Profiles.FLIP7_FE,
                Profiles.A06, Profiles.A07_5G, Profiles.A15, Profiles.A24, Profiles.A25, Profiles.A33, Profiles.A34, Profiles.A53, Profiles.E55,
                Profiles.S_FE_9925, Profiles.S_FE_8450, Profiles.S_PLUS_9925, Profiles.S_ULTRA_9925, Profiles.S_ULTRA_8450,
                Profiles.A55, Profiles.S25_FE, Profiles.S_8450, Profiles.M55S, Profiles.S_ULTRA_8450_JP, Profiles.S_PLUS_9945,
                Profiles.S_ULTRA_8550_JP, Profiles.S_9925, Profiles.A16_MTK, Profiles.S_8550_JP,
                Profiles.M35, Profiles.M36, Profiles.A15_5G, Profiles.S_PLUS_8650,
                // 0.5.28: the Galaxy S26 FE (Exynos 2500), the Z Flip7's systems on the bar settings.
                Profiles.S26_FE,
                // 0.5.42: the Galaxy S22+ with Snapdragon.
                Profiles.S_PLUS_8450,
                // 0.5.41: the Galaxy Tabs, OxygenOS 17 for tablets only (testing).
                Profiles.TAB_S9, Profiles.TAB_S10_FE, Profiles.TAB_S10_FE_WIFI, Profiles.TAB_S12_ULTRA, Profiles.TAB_S9_FE_PLUS, Profiles.TAB_S9_FE,
                // 0.5.47: the Galaxy Tab S9 FE 5G (owner).
                Profiles.TAB_S9_FE_5G,
                Profiles.TAB_S9_ULTRA, Profiles.TAB_S11,
                // 0.5.48: the Galaxy Tab S11 Ultra (owner).
                Profiles.TAB_S11_ULTRA,
            ),
            Profiles.BUILT_IN,
        )
        assertEquals(
            listOf("s26-fe", "SM-S741", "r14s", "s5e9955", FormFactor.BAR),
            listOf(Profiles.S26_FE.id, Profiles.S26_FE.modelPrefix, Profiles.S26_FE.codename, Profiles.S26_FE.socModel, Profiles.S26_FE.form),
        )
        // 0.5.35: the S26 FE (a bar phone) also takes PixelOS, the Flip7 not.
        assertEquals(Profiles.FLIP7.choices, Profiles.S26_FE.choices.filter { it.imageId != Images.ID_PIXELOS_ONYX })
        assertEquals(Profiles.S26_FE, Profiles.resolve("SM-S741U", "r14s", "s5e9955").profile

        )
        // 0.4.67: the phones still on One UI 8 take OxygenOS 16 only, untested, as bar phones.
        for (p in listOf(Profiles.A06, Profiles.A07_5G, Profiles.A24, Profiles.A25, Profiles.A33, Profiles.A53, Profiles.E55,
                Profiles.S_FE_9925, Profiles.S_FE_8450, Profiles.S_PLUS_9925, Profiles.S_ULTRA_9925, Profiles.S_ULTRA_8450, Profiles.S_8450, Profiles.M55S, Profiles.S_ULTRA_8450_JP,
                Profiles.S_9925, Profiles.A16_MTK, Profiles.A15_5G)) {
            assertEquals(p.id, listOf(ImageChoice(Images.ID_OXYGEN16, PackageSets.ID_OXYGEN16, tested = false)), p.choices)
            assertEquals(p.id, FormFactor.BAR, p.form)
        }
        // 0.4.74: the A34 got One UI 9 (Android 17): the A07's systems, untested, and OxygenOS 16 for One UI 8.
        // 0.4.74: so did the A15 (MT6789, the A07's chip).
        for (p in listOf(Profiles.A34, Profiles.A15)) {
            assertEquals(p.id, listOf(Images.ID_FIND_X9U_IN_1105, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_HYPEROS_LHASA, Images.ID_HYPEROS_HONGKONG, Images.ID_OXYGEN16, Images.ID_NOTHING_ASTEROIDS, Images.ID_PIXELOS_ONYX, Images.ID_ONEUI95), p.choices.map { it.imageId })
            // 0.5.28: HyperOS 4 Global ran on both (reports of 2026-11-20: 114 min on an A34, 8 h on an A15).
            assertEquals(p.id, listOf(Images.ID_HYPEROS_HONGKONG), p.choices.filter { it.tested }.map { it.imageId })
            assertEquals(FormFactor.BAR, p.form)
        }
        // 0.4.74: the au S22 Ultra (SCG14) by its own model number and codename.
        assertEquals(Profiles.S_ULTRA_8450_JP, Profiles.resolve("SCG14", "SCG14", "SM8450").profile)
        assertEquals(Profiles.S_ULTRA_8450.choices, Profiles.S_ULTRA_8450_JP.choices)
        // 0.4.92: the au S23 Ultra (SCG20) the same way: the S23 Ultra's systems and note; not by the
        // S23 Ultra's own codename (its ro.product.device is SCG20, only the vendor device is dm3q).
        assertEquals(Profiles.S_ULTRA_8550_JP, Profiles.resolve("SCG20", "SCG20", "SM8550").profile)
        assertEquals(
            listOf("s-ultra-8550-jp", "Galaxy S23 Ultra (au)", FormFactor.BAR),
            listOf(Profiles.S_ULTRA_8550_JP.id, Profiles.S_ULTRA_8550_JP.label, Profiles.S_ULTRA_8550_JP.form),
        )
        assertEquals(
            listOf(Profiles.S_ULTRA_8550.choices, Profiles.S_ULTRA_8550.notes),
            listOf(Profiles.S_ULTRA_8550_JP.choices, Profiles.S_ULTRA_8550_JP.notes),
        )
        assertNull(Profiles.resolve("SCG20", "dm3q", "SM8550").profile)
        assertNull(Profiles.resolve("SCG20", "SCG20", "SM8450").profile)
        // 0.4.93: the au S23 (SCG19) the same way: the S23's systems and note; not by the S23's own
        // codename (its ro.product.device is SCG19, only the vendor device is dm1q). The device name
        // is matched in any case, the model number only as the phone writes it.
        assertEquals(Profiles.S_8550_JP, Profiles.resolve("SCG19", "SCG19", "SM8550").profile)
        assertEquals(Profiles.S_8550_JP, Profiles.resolve("SCG19", "scg19", "SM8550").profile)
        assertEquals(
            listOf("s-8550-jp", "Galaxy S23 (au)", FormFactor.BAR),
            listOf(Profiles.S_8550_JP.id, Profiles.S_8550_JP.label, Profiles.S_8550_JP.form),
        )
        assertEquals(
            listOf(Profiles.S_8550.choices, Profiles.S_8550.notes),
            listOf(Profiles.S_8550_JP.choices, Profiles.S_8550_JP.notes),
        )
        assertNull(Profiles.resolve("SCG19", "dm1q", "SM8550").profile)
        assertNull(Profiles.resolve("SCG19", "SCG19", "SM8450").profile)
        // The two au models do not take each other's profile.
        assertNull(Profiles.resolve("SCG20", "SCG19", "SM8550").profile)
        assertNull(Profiles.resolve("SCG19", "SCG20", "SM8550").profile)
        // 0.4.48, from probe reports of phones on One UI 9: the S25 Edge takes the S25's images (untested
        // here), the S24 FE the S24 (Exynos)'s, the A26 the S23s' without HyperOS, the A17 and the A16 5G
        // (Exynos 1330) Infinity-X, like the A07; 0.4.60: Infinity-X tested there, ColorOS (X9U IN) offered too.
        assertEquals(listOf("SM-S937", "psq", "SM8750"), listOf(Profiles.S_EDGE_8750.modelPrefix, Profiles.S_EDGE_8750.codename, Profiles.S_EDGE_8750.socModel))
        assertEquals(Profiles.S_8750.choices.map { it.imageId }, Profiles.S_EDGE_8750.choices.map { it.imageId })
        assertTrue(Profiles.S_EDGE_8750.choices.none { it.tested })
        // 0.4.83: the S24 (Exynos) went on to the S24 Ultra's systems; the FE phones keep these four.
        // 0.5.28: ColorOS (global) and HyperOS 4 Global ran on an S24 FE (reports of 2026-11-20).
        assertEquals(listOf(xin.copy(tested = true), pixel9, ifx, lineage, hyper, hyperHk.copy(tested = true), px, oneui), Profiles.S_FE_9945.choices)
        assertEquals(Profiles.S_FE_9945.choices.map { it.copy(tested = false) }, (Profiles.S_9945.choices - nothing - origin).map { it.copy(tested = false) })
        assertEquals(listOf("SM-S721", "r12s", "s5e9945"), listOf(Profiles.S_FE_9945.modelPrefix, Profiles.S_FE_9945.codename, Profiles.S_FE_9945.socModel))
        assertEquals(listOf(Images.ID_FIND_X9U_IN_1105, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_HYPEROS_LHASA, Images.ID_HYPEROS_HONGKONG, Images.ID_OXYGEN16, Images.ID_NOTHING_ASTEROIDS, Images.ID_PIXELOS_ONYX, Images.ID_ONEUI95), Profiles.A26.choices.map { it.imageId }) // 0.4.57: no Pixel 9 Pro XL; 0.4.66: HyperOS (owner)
        for (p in listOf(Profiles.A17, Profiles.A16, Profiles.A16_4G, Profiles.A07, Profiles.A16_S166, Profiles.A17_5G)) {
            assertEquals(p.id, listOf(Images.ID_FIND_X9U_IN_1105, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_HYPEROS_LHASA, Images.ID_HYPEROS_HONGKONG, Images.ID_OXYGEN16, Images.ID_NOTHING_ASTEROIDS, Images.ID_PIXELOS_ONYX, Images.ID_ONEUI95), p.choices.map { it.imageId })
            // Tested only where a tester's session reached the home screen; that one is preselected.
            val ran = p !in listOf(Profiles.A16_S166, Profiles.A17_5G)
            // 0.5.28: One UI 9.5 ran on an A17 and an A07 (reports of 2026-11-19/20); the A16 4G takes the A17's list.
            val oneUi95Ran = p in listOf(Profiles.A17, Profiles.A16_4G, Profiles.A07)
            assertEquals(p.id, listOf(false, ran, false, false, false, false, false, false, oneUi95Ran), p.choices.map { it.tested })
            if (ran) assertEquals(p.id, Images.ID_INFINITYX, p.recommended?.imageId)
        }
        // 0.4.60: the Galaxy A17 5G (SM-A176B, the A16 5G's Exynos 1330) and the Z Flip7 FE (SM-F761B, Exynos 2400).
        assertEquals(Profiles.A17_5G, Profiles.resolve("SM-A176B", "a17x", "s5e8535").profile)
        assertEquals(listOf(Profiles.A16.notes, Profiles.A16.form), listOf(Profiles.A17_5G.notes, Profiles.A17_5G.form))
        assertEquals(Profiles.FLIP7_FE, Profiles.resolve("SM-F761B", "b7r", "s5e9945").profile)
        assertEquals(listOf(Profiles.S_FE_9945.choices.map { it.copy(tested = false) }.filter { it.imageId != Images.ID_PIXELOS_ONYX }, Profiles.S_9945.notes), listOf(Profiles.FLIP7_FE.choices, Profiles.FLIP7_FE.notes))
        assertEquals(FormFactor.FLIP, Profiles.FLIP7_FE.form)
        assertEquals(Profiles.A17, Profiles.resolve("SM-A175F", "a17", "MT6789").profile)
        // The A16 4G (0.4.55): the A17's chip and image under its own model number and codename.
        assertEquals(Profiles.A16_4G, Profiles.resolve("SM-A165F", "a16", "MT6789").profile)
        assertEquals(listOf("a16-4g", "Galaxy A16 4G"), listOf(Profiles.A16_4G.id, Profiles.A16_4G.label))
        assertEquals(Profiles.A17.choices, Profiles.A16_4G.choices)
        assertEquals(Profiles.A17.notes, Profiles.A16_4G.notes)
        // 0.4.59: the TracFone/Verizon prepaid A16 5G (SM-S166V), the same phone and choices as SM-A166U.
        assertEquals(Profiles.A16_S166, Profiles.resolve("SM-S166V", "a16x", "s5e8535").profile)
        assertEquals(Profiles.A16.notes, Profiles.A16_S166.notes)
        // 0.4.59: the Galaxy A35 5G and A54 5G, the A26's Exynos 1380 and vendor (findings), so its choices and notes.
        assertEquals(Profiles.A35, Profiles.resolve("SM-A356E", "a35x", "s5e8835").profile)
        assertEquals(Profiles.A35, Profiles.resolve("SM-A356U1", "a35x", "s5e8835").profile)
        assertEquals(Profiles.A54, Profiles.resolve("SM-A546E", "a54x", "s5e8835").profile)
        // 0.4.95: the Galaxy M35 5G (SM-M356B, m35x), the same chip and vendor as the A35 5G: the A26's systems and
        // notes; not by another phone's codename or chip.
        assertEquals(Profiles.M35, Profiles.resolve("SM-M356B", "m35x", "s5e8835").profile)
        assertEquals(listOf("m35", "Galaxy M35 5G", FormFactor.BAR), listOf(Profiles.M35.id, Profiles.M35.label, Profiles.M35.form))
        assertNull(Profiles.resolve("SM-M356B", "a35x", "s5e8835").profile)
        assertNull(Profiles.resolve("SM-M356B", "m35x", "SM8450").profile)
        assertNull(Profiles.resolve("SM-A356E", "m35x", "s5e8835").profile)
        // 0.5.35 (PR #327): the Galaxy M36 5G (SM-M366B, m36x), the M35's chip and vendor, so the A26's systems; untested.
        assertEquals(Profiles.M36, Profiles.resolve("SM-M366B", "m36x", "s5e8835").profile)
        assertEquals(listOf("m36", "Galaxy M36 5G", FormFactor.BAR), listOf(Profiles.M36.id, Profiles.M36.label, Profiles.M36.form))
        assertNull(Profiles.resolve("SM-M366B", "m35x", "s5e8835").profile)
        // Galaxy Tab S9 FE Wi-Fi (SM-X510, gts9fewifi, s5e8835; PR #371): the A26's Exynos 1380 systems plus OxygenOS 17 Pad.
        assertEquals(Profiles.TAB_S9_FE, Profiles.resolve("SM-X510", "gts9fewifi", "s5e8835").profile)
        assertEquals(listOf("tab-s9-fe", "Galaxy Tab S9 FE", FormFactor.BAR), listOf(Profiles.TAB_S9_FE.id, Profiles.TAB_S9_FE.label, Profiles.TAB_S9_FE.form))
        assertNull(Profiles.resolve("SM-X510", "gts9fe", "s5e8835").profile)
        assertNull(Profiles.resolve("SM-X510", "gts9fewifi", "SM8450").profile)
        assertNull(Profiles.resolve("SM-X516B", "gts9fewifi", "s5e8835").profile)
        assertTrue(Profiles.TAB_S9_FE in Profiles.TABLETS)
        // 0.5.47: the Tab S9 FE 5G (SM-X516B/N, gts9fe; findings-6d47aeba), the Wi-Fi model's choices and notes.
        assertEquals(Profiles.TAB_S9_FE_5G, Profiles.resolve("SM-X516N", "gts9fe", "s5e8835").profile)
        assertEquals(Profiles.TAB_S9_FE_5G, Profiles.resolve("SM-X516B", "gts9fe", "s5e8835").profile)
        assertEquals(listOf("tab-s9-fe-5g", "Galaxy Tab S9 FE 5G"), listOf(Profiles.TAB_S9_FE_5G.id, Profiles.TAB_S9_FE_5G.label))
        assertEquals(listOf(Profiles.TAB_S9_FE.choices, Profiles.TAB_S9_FE.notes, Profiles.TAB_S9_FE.form),
            listOf(Profiles.TAB_S9_FE_5G.choices, Profiles.TAB_S9_FE_5G.notes, Profiles.TAB_S9_FE_5G.form))
        assertTrue(Profiles.TAB_S9_FE_5G in Profiles.TABLETS)
        // 0.5.48 (owner): the Tab S11 Ultra (SM-X930, gts11uwifi, MT6991; findings-37123bcf), the Tab S11's choices; and
        // One UI 9.5 next to the tablet system on every Tab.
        assertEquals(Profiles.TAB_S11_ULTRA, Profiles.resolve("SM-X930", "gts11uwifi", "MT6991").profile)
        assertEquals(listOf(Profiles.TAB_S11.choices, Profiles.TAB_S11.notes), listOf(Profiles.TAB_S11_ULTRA.choices, Profiles.TAB_S11_ULTRA.notes))
        for (t in Profiles.TABLETS) assertEquals(t.id, listOf(Images.ID_OXYGEN17_PAD, Images.ID_ONEUI95), t.choices.map { it.imageId })
        // Owner (2026-11-25): the tablet system and One UI 9.5 only.
        assertEquals(
            listOf(
                ImageChoice(Images.ID_OXYGEN17_PAD, PackageSets.ID_OXYGEN17_PAD, tested = false),
                ImageChoice(Images.ID_ONEUI95, PackageSets.ID_ONEUI95, tested = false),
            ),
            Profiles.TAB_S9_FE.choices,
        )
        assertEquals(Profiles.A26.notes, Profiles.TAB_S9_FE.notes.filter { it in Profiles.A26.notes })
        // 0.4.59: the Galaxy A27 (SM-A276B), the A36's SM6475 and generation, so its choices and notes.
        assertEquals(Profiles.A27, Profiles.resolve("SM-A276B", "a27xq", "SM6475").profile)
        assertEquals(listOf(Profiles.A36.choices, Profiles.A36.notes), listOf(Profiles.A27.choices, Profiles.A27.notes))
        for (p in listOf(Profiles.A35, Profiles.A54, Profiles.M35, Profiles.M36)) {
            assertEquals(listOf(Profiles.A26.choices, Profiles.A26.notes, Profiles.A26.form), listOf(p.choices, p.notes, p.form))
        }
        // 0.4.68, findings of 2026-11-08: the Galaxy A55 5G (Exynos 1480, the A35's Cortex-A78/A55, so its choices; vendor
        // API 34 and kernel 6.1, so that older-vendor note), the S25 FE (the S24 FE's Exynos 2400, vendor and screen), and
        // the Galaxy S22 with Snapdragon (One UI 8, the S22 Ultra's SM8450: OxygenOS 16 only).
        assertEquals(Profiles.A55, Profiles.resolve("SM-A556B", "a55x", "s5e8845").profile)
        assertEquals(listOf(Profiles.A35.choices, FormFactor.BAR), listOf(Profiles.A55.choices, Profiles.A55.form))
        assertEquals(listOf(Profiles.ID_NOTE_EXYNOS, Profiles.ID_NOTE_OLDER_VENDOR), Profiles.A55.notes.map { it.id })
        assertTrue(Profiles.A55.notes[1].detail.contains("vendor API 34 (Android 14) and kernel 6.1"))
        assertNull(Profiles.A55.choice(Images.ID_PIXEL_KOMODO))
        assertEquals(Profiles.S25_FE, Profiles.resolve("SM-S731B", "r13s", "s5e9945").profile)
        assertNull(Profiles.resolve("SM-S731B", "a56x", "s5e8855").profile) // an A56 renamed
        assertEquals(
            listOf(Profiles.S_FE_9945.choices, Profiles.S_FE_9945.notes, Profiles.S_FE_9945.form),
            listOf(Profiles.S25_FE.choices, Profiles.S25_FE.notes, Profiles.S25_FE.form),
        )
        assertEquals(Profiles.S_8450, Profiles.resolve("SM-S901U", "r0q", "SM8450").profile)
        // 0.4.93: the Exynos S22 (now on One UI 8.0), the S22+'s choice and note; neither S22 by the other's chip.
        assertEquals(Profiles.S_9925, Profiles.resolve("SM-S901B", "r0s", "s5e9925").profile)
        assertEquals(listOf(Profiles.S_PLUS_9925.choices, Profiles.S_PLUS_9925.notes), listOf(Profiles.S_9925.choices, Profiles.S_9925.notes))
        assertNull(Profiles.resolve("SM-S901B", "r0s", "SM8450").profile)
        assertNull(Profiles.resolve("SM-S901B", "r0q", "s5e9925").profile)
        assertEquals(listOf(Profiles.S_ULTRA_8450.choices, Profiles.S_ULTRA_8450.notes), listOf(Profiles.S_8450.choices, Profiles.S_8450.notes))
        // 0.4.70: the Galaxy M55s (SM-M558B), the F55/E55's m55xq and SM7450 on One UI 8.5.
        assertEquals(Profiles.M55S, Profiles.resolve("SM-M558B", "m55xq", "SM7450").profile)
        assertEquals(Profiles.E55, Profiles.resolve("SM-E556B", "m55xq", "SM7450").profile)
        assertEquals(listOf(Profiles.E55.choices, Profiles.E55.notes), listOf(Profiles.M55S.choices, Profiles.M55S.notes))
        assertEquals(Profiles.A16, Profiles.resolve("SM-A166U", "a16x", "s5e8535").profile)
        // The A16 with MediaTek (a16xm) is not the Exynos one. 0.4.93: its own profile, the A07 5G's choice and note.
        assertEquals(Profiles.A16_MTK, Profiles.resolve("SM-A166P", "a16xm", "MT6835").profile)
        assertEquals(listOf(Profiles.A07_5G.choices, Profiles.A07_5G.notes), listOf(Profiles.A16_MTK.choices, Profiles.A16_MTK.notes))
        assertNull(Profiles.resolve("SM-A166P", "a16x", "MT6835").profile)
        assertNull(Profiles.resolve("SM-A166P", "a16xm", "s5e8535").profile)
        // 0.4.95: the A15 5G (SM-A156M, a15x, MT6835) is its own phone, the A07 5G's choice and note; the A15 with
        // the Helio G99 (SM-A155, MT6789) keeps its profile.
        assertEquals(Profiles.A15_5G, Profiles.resolve("SM-A156M", "a15x", "MT6835").profile)
        assertEquals(listOf(Profiles.A07_5G.choices, Profiles.A07_5G.notes), listOf(Profiles.A15_5G.choices, Profiles.A15_5G.notes))
        assertNull(Profiles.resolve("SM-A156M", "a15", "MT6835").profile)
        assertNull(Profiles.resolve("SM-A156M", "a15x", "MT6789").profile)
        assertEquals(Profiles.A15, Profiles.resolve("SM-A155F", "a15", "MT6789").profile)

        // Ids unique; every choice names an image and a set built from that image,
        // each image once per profile; the fold grid with a ColorOS image on the fold
        // form only: the Pixel and Infinity-X sets have none (ColorOS's wallpaper app's;
        // Infinity-X has OPPO's jars but not that app's layout).
        assertEquals(Profiles.BUILT_IN.size, Profiles.BUILT_IN.map { it.id }.toSet().size)
        for (p in Profiles.BUILT_IN) {
            assertTrue(p.id, p.choices.isNotEmpty())
            assertEquals(p.id, p.choices.size, p.choices.map { it.imageId }.toSet().size)
            for (c in p.choices) {
                val image = Images.byId(c.imageId)
                val set = PackageSets.byId(c.packageSetId)
                assertNotNull("${p.id} ${c.imageId}", image)
                assertNotNull("${p.id} ${c.packageSetId}", set)
                assertEquals("${p.id} ${c.imageId}", image!!.id, set!!.imageId)
                val colorOs = image.family == SystemFamily.COLOROS
                assertEquals("${p.id} ${set.id}", p.form == FormFactor.FOLD && colorOs, PackageSets.WALLPAPER_GRID_RRO in set.names)
                assertEquals(c, p.choice(c.imageId))
            }
            assertEquals(p.choices.map { it.imageId }, p.images().map { it.id })
            assertTrue(p.id, p.id.matches(Regex("[a-z0-9][a-z0-9-]{0,31}")))
        }
        assertNull(Profiles.F8U.choice(Images.ID_FIND_X9U_IN_1105))
        // The owner does not want the X9U (CN) image on the Fold: only the N6 and Pixel images there.
        // The Fold7 (0.4.8) takes the N6 image only; the Fold6 (0.4.33) the same.
        assertEquals(listOf(Profiles.F8U, Profiles.FOLD7, Profiles.FOLD8, Profiles.FOLD6, Profiles.FOLD5, Profiles.FOLD4), Profiles.BUILT_IN.filter { it.form == FormFactor.FOLD })
        // The Find X9 Ultra builds run as a phone: the bar phones and (0.4.17) the Z Flip7 on its main screen.
        assertTrue(Profiles.BUILT_IN.filter { it.choice(Images.ID_FIND_X9U_IN_1105) != null }.all { it.form == FormFactor.BAR || it.form == FormFactor.FLIP })
        assertEquals(listOf(Profiles.FLIP7, Profiles.FLIP5, Profiles.FLIP8, Profiles.FLIP6, Profiles.FLIP7_FE), Profiles.BUILT_IN.filter { it.form == FormFactor.FLIP })
        // The Pixel 11 Fold image on the SM8850 folds (it ran on the Fold8 Ultra; 0.4.10 the Z Fold8, untested), with the Fold's set.
        assertEquals(listOf(Profiles.F8U, Profiles.FOLD8), Profiles.BUILT_IN.filter { it.choice(Images.ID_PIXEL_YOGI) != null })
        // The Pixel 11 images only on chips with SVE, which their system code needs: SM8850, and (0.4.17) the
        // Exynos 2600 of the S26+; not the older Snapdragons nor the Flip7's Exynos 2500 (no SME).
        val sve = setOf("SM8850", "s5e9965")
        assertTrue(Profiles.BUILT_IN.filter { it.socModel !in sve }.all { p -> p.images().none { "sve" in it.cpuRequired } })
        // 0.4.22: the Pixel 9 Pro XL image, which needs none, on the SM8750 bar phones and the S24 Ultra; not the
        // Z Fold7 (a bar phone's system on a fold). 0.4.30: also the S23s and the Z Flip5 (Infinity-X started on
        // the S23 with the HIDL marker), the Z Flip7 and the A57; 0.4.31 the A56: every s25 phone, whose APK has its set.
        // 0.4.57: not the A26 and A36 (ARMv8.2: the image's programs stopped on "Illegal instruction" on the A26).
        assertEquals(
            listOf(
                Profiles.S_ULTRA_8750, Profiles.S_8750, Profiles.S_PLUS_8750, Profiles.S_ULTRA_8650, Profiles.S_8650, Profiles.S_8550, Profiles.S_PLUS_8550,
                Profiles.FLIP7, Profiles.A56, Profiles.A57, Profiles.FLIP5,
                Profiles.S_ULTRA_8550, Profiles.FLIP6, Profiles.S_9945, Profiles.S_EDGE_8750, Profiles.S_FE_9945, Profiles.FLIP7_FE,
                Profiles.S25_FE, Profiles.S_PLUS_9945, Profiles.S_ULTRA_8550_JP, Profiles.S_8550_JP, Profiles.S_PLUS_8650,
                Profiles.S26_FE, // 0.5.28: the Z Flip7's systems
            ),
            Profiles.BUILT_IN.filter { it.choice(Images.ID_PIXEL_KOMODO) != null },
        )
        assertEquals(PackageSets.ID_PIXEL_F8U, Profiles.F8U.choice(Images.ID_PIXEL_YOGI)!!.packageSetId)
        // 0.4.11: the IN build listed first wherever it is offered; never on a fold.
        assertEquals(
            Profiles.BUILT_IN.filter { it.choice(Images.ID_FIND_X9U_IN_1105) != null },
            Profiles.BUILT_IN.filter { it.choices.firstOrNull()?.imageId == Images.ID_FIND_X9U_IN_1105 },
        )
        assertTrue(Profiles.BUILT_IN.filter { it.form == FormFactor.FOLD }.all { it.choice(Images.ID_FIND_X9U_IN_1105) == null })
        // The IN build is the preselected one (0.4.51: tested where the retired debloated build was).
        assertEquals(Images.ID_FIND_X9U_IN_1105, Profiles.S_ULTRA_8750.recommended?.imageId)
        assertEquals(Images.ID_FIND_X9U_IN_1105, Profiles.S_PLUS_8750.recommended?.imageId)
        // Every built-in image is some profile's.
        assertEquals(Images.ALL.map { it.id }.toSet(), Profiles.BUILT_IN.flatMap { p -> p.choices.map { it.imageId } }.toSet())
    }

    @Test
    fun allThreeIdsMustMatch() {
        // The probe builds matched model OR codename; build 2 needs all three.
        fun profile(model: String, device: String, soc: String) = Profiles.resolve(model, device, soc).profile

        assertEquals(Profiles.S_ULTRA_8850, profile("SM-S948U", "m3q", "SM8850"))
        assertEquals(Profiles.S_ULTRA_8850, profile("SM-S948B", "M3Q", "sm8850"))
        assertEquals(Profiles.S_ULTRA_8850, profile(" sm-s9480 ", "m3q", "SM8850"))
        assertNull(profile("SM-S948U", "pa3q", "SM8850")) // right model, wrong codename
        assertNull(profile("SM-S948U", "m3q", "SM8750")) // right model and codename, other chip
        assertNull(profile("SM-S948U", "m3q", "s5e9955")) // an Exynos variant
        assertNull(profile("SM-S938B", "m3q", "SM8850")) // S25 model number, S26 codename
        assertNull(profile("SM-F966B", "q8q", "SM8850")) // codename alone matched in the probe builds
        assertNull(profile("SM-F976B", "q8q", "")) // chip unknown: fail closed
        assertEquals(Profiles.S_ULTRA_8650, profile("SM-S928B", "e3q", "SM8650")) // S24 Ultra (0.4.11)
        assertNull(profile("SM-S928B", "e3q", "s5e9945")) // an Exynos S24 Ultra
        // Galaxy S26 (0.4.11): SM-S942 or the Japanese SC-51G, codename m1q, SM8850; not the Exynos S26.
        assertEquals(Profiles.S_8850, profile("SM-S942B", "m1q", "SM8850"))
        assertEquals(Profiles.S_8850_JP, profile("SC-51G", "m1q", "SM8850"))
        assertNull(profile("SM-S942B", "m1q", "s5e9965"))
        // The Exynos S26 (0.4.52): SM-S942, m1s, s5e9965; never with the Snapdragon chip or the S21 a renamed report gave.
        assertEquals(Profiles.S_9965, profile("SM-S942B", "m1s", "s5e9965"))
        assertNull(profile("SM-S942B", "m1s", "SM8850"))
        assertNull(profile("SM-S942B", "m1s", "exynos2100"))
        assertEquals(Profiles.S_8850, profile("SM-S942B", "m1q", "SM8850"))
        assertNull(profile("SM-S948B", "m1q", "SM8850")) // S26 Ultra model number, S26 codename
        // Galaxy S26+ (0.4.12): SM-S947, m2q, SM8850.
        assertEquals(Profiles.S_PLUS_8850, profile("SM-S947U", "m2q", "SM8850"))
        assertEquals(Profiles.S_PLUS_8850, profile("SM-S947B", "m2q", "SM8850"))
        assertNull(profile("SM-S947B", "m2q", "s5e9965")) // Exynos chip, Snapdragon codename
        // The Exynos S26+ and Z Flip7 (0.4.17).
        assertEquals(Profiles.S_PLUS_9965, profile("SM-S947B", "m2s", "s5e9965"))
        assertNull(profile("SM-S947B", "m2s", "SM8850"))
        assertEquals(Profiles.FLIP7, profile("SM-F766U", "b7s", "s5e9955"))
        assertEquals(Profiles.FLIP7, profile("SM-F766B", "B7S", "S5E9955"))
        assertEquals(Profiles.A57, profile("SM-A576B", "a57x", "s5e8865"))
        assertEquals(Profiles.FLIP5, profile("SM-F731B", "b5q", "SM8550"))
        assertNull(profile("SM-F731B", "b5q", "SM8650"))
        assertEquals(Profiles.A56, profile("SM-A566B", "a56x", "s5e8855")) // the A56 (0.4.31)
        assertNull(profile("SM-A566B", "a57x", "s5e8855")) // A56 model number, A57 codename
        // 0.4.33: the Galaxy Z Fold6 (the S24 Ultra's SM8650, a fold) and the Galaxy A07 (MediaTek MT6789).
        assertEquals(Profiles.FOLD6, profile("SM-F956B", "q6q", "SM8650"))
        assertNull(profile("SM-F956B", "q6q", "SM8750"))
        assertEquals(FormFactor.FOLD, Profiles.FOLD6.form)
        assertEquals(listOf(Images.ID_FIND_N6, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_NOTHING_METROID, Images.ID_ONEUI95), Profiles.FOLD6.choices.map { it.imageId })
        // Galaxy Z Fold5 (0.4.35): the Z Flip5's platform as a fold, the Fold6's systems.
        assertEquals(Profiles.FOLD5, profile("SM-F946B", "q5q", "SM8550"))
        assertEquals(FormFactor.FOLD, Profiles.FOLD5.form)
        assertEquals(listOf(Images.ID_FIND_N6, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_ORIGINOS7, Images.ID_ONEUI95), Profiles.FOLD5.choices.map { it.imageId })
        assertEquals(listOf(Profiles.ID_NOTE_OLDER_VENDOR), Profiles.FOLD5.notes.map { it.id })
        // Galaxy Z Fold4 (SM-F936): Snapdragon 8+ Gen 1 (SM8475), One UI 8.0 stock, OxygenOS 16 only (tested).
        assertEquals(Profiles.FOLD4, profile("SM-F936B", "q4q", "SM8475"))
        assertEquals(Profiles.FOLD4, profile("SM-F936N", "q4q", "SM8475"))
        assertEquals(Profiles.FOLD4, profile("SM-F936U", "q4q", "SM8475"))
        assertEquals(FormFactor.FOLD, Profiles.FOLD4.form)
        assertEquals(listOf(Images.ID_OXYGEN16), Profiles.FOLD4.choices.map { it.imageId })
        assertTrue(Profiles.FOLD4.testedWithAnyImage)
        assertEquals(listOf(true), Profiles.FOLD4.choices.map { it.tested })
        assertEquals(listOf(Profiles.ID_NOTE_OLDER_VENDOR, Profiles.ID_NOTE_FOLD4_ISSUES), Profiles.FOLD4.notes.map { it.id })
        assertTrue(Profiles.FOLD4.notes.first().detail.contains("vendor API 31 (Android 12) and kernel 5.10"))
        assertTrue(Profiles.FOLD4.notes.last().detail.contains("camera does not work"))
        assertEquals(Profiles.FOLD4, Profiles.resolve(Bundles.Q4Q.facts).profile)
        assertEquals(FormFactor.FOLD, Bundles.Q4Q.facts.form.form)
        assertEquals(Profiles.A07, profile("SM-A075F", "a07", "MT6789"))
        assertNull(profile("SM-A075F", "a07", "s5e8855"))
        assertEquals(listOf(Images.ID_FIND_X9U_IN_1105, Images.ID_INFINITYX, Images.ID_LINEAGE, Images.ID_HYPEROS_LHASA, Images.ID_HYPEROS_HONGKONG, Images.ID_OXYGEN16, Images.ID_NOTHING_ASTEROIDS, Images.ID_PIXELOS_ONYX, Images.ID_ONEUI95), Profiles.A07.choices.map { it.imageId })
        assertEquals(listOf(Profiles.ID_NOTE_MEDIATEK, Profiles.ID_NOTE_OLDER_VENDOR), Profiles.A07.notes.map { it.id })
        assertNull(profile("SM-F766U", "b7s", "s5e9965"))
        assertNull(profile("SM-S947U", "m3q", "SM8850")) // S26+ model number, S26 Ultra codename
        // Galaxy S23 and S23+ (0.4.11).
        assertEquals(Profiles.S_8550, profile("SM-S911B", "dm1q", "SM8550"))
        assertEquals(Profiles.S_PLUS_8550, profile("SM-S916U", "dm2q", "SM8550"))
        assertNull(profile("SM-S911B", "dm2q", "SM8550"))
        // 0.4.40: the Galaxy S23 Ultra (SM8550 like the S23s), Z Flip6 (SM8650) and S24 (Exynos 2400).
        assertEquals(Profiles.S_ULTRA_8550, profile("SM-S918B", "dm3q", "SM8550"))
        assertEquals(Profiles.S_ULTRA_8550, profile("SM-S918U1", "dm3q", "SM8550"))
        assertNull(profile("SM-S918B", "dm1q", "SM8550")) // S23 Ultra model number, S23 codename
        assertEquals(Profiles.FLIP6, profile("SM-F741B", "b6q", "SM8650"))
        assertEquals(FormFactor.FLIP, Profiles.FLIP6.form)
        assertNull(Profiles.FLIP6.choice(Images.ID_HYPEROS_LHASA)) // as the Z Fold6: HyperOS died on SM8650
        assertEquals(Profiles.S_9945, profile("SM-S921N", "e1s", "s5e9945"))
        assertEquals(Profiles.S_9945, profile("SM-S921B", "e1s", "s5e9945"))
        // 0.4.61: the Snapdragon S24 (SM-S921E probe), apart from the Exynos one by codename and chip.
        assertEquals(Profiles.S_8650, profile("SM-S921E", "e1q", "SM8650"))
        assertNull(profile("SM-S921B", "e1q", "s5e9945"))
        assertEquals(Profiles.S_ULTRA_8650.notes, Profiles.S_8650.notes)
        assertEquals(listOf(Profiles.ID_NOTE_EXYNOS, Profiles.ID_NOTE_OLDER_VENDOR), Profiles.S_9945.notes.map { it.id })
        // 0.4.83: the Exynos S24 and S24+ take the S24 Ultra's systems (Infinity-X untested on them), with their own notes;
        // the S24+ (Exynos) from the owner's SM-S926B probe. A Snapdragon S24+ (e2q) has sent no probe: no profile.
        assertEquals(Profiles.S_ULTRA_8650.choices.map { it.copy(tested = false) }, Profiles.S_9945.choices.map { it.copy(tested = false) })
        assertEquals(Profiles.S_8650.choices.map { it.copy(tested = false) }, Profiles.S_9945.choices.map { it.copy(tested = false) })
        // 0.5.28: One UI 9.5 ran on an Exynos S24 (report of 2026-11-19).
        assertTrue(Profiles.S_9945.choice(Images.ID_ONEUI95)!!.tested)
        assertEquals(Profiles.S_PLUS_9945, profile("SM-S926B", "e2s", "s5e9945"))
        assertEquals(listOf("s-plus-9945", "Galaxy S24+ (Exynos)", FormFactor.BAR), listOf(Profiles.S_PLUS_9945.id, Profiles.S_PLUS_9945.label, Profiles.S_PLUS_9945.form))
        assertEquals(listOf(Profiles.S_9945.choices, Profiles.S_9945.notes), listOf(Profiles.S_PLUS_9945.choices, Profiles.S_PLUS_9945.notes))
        // 0.5.15: the Snapdragon S24+ from an SM-S9260 probe: the Snapdragon S24's systems and note.
        assertEquals(Profiles.S_PLUS_8650, profile("SM-S926U", "e2q", "SM8650"))
        assertEquals(Profiles.S_PLUS_8650, profile("SM-S9260", "e2q", "SM8650"))
        assertEquals(listOf("s-plus-8650", "Galaxy S24+", FormFactor.BAR), listOf(Profiles.S_PLUS_8650.id, Profiles.S_PLUS_8650.label, Profiles.S_PLUS_8650.form))
        assertEquals(listOf(Profiles.S_8650.choices, Profiles.S_8650.notes), listOf(Profiles.S_PLUS_8650.choices, Profiles.S_PLUS_8650.notes))
        assertNull(profile("SM-S926B", "e2q", "s5e9945"))
        assertNull(profile("SM-S926B", "e1s", "s5e9945"))
        // Galaxy S25 (base): all three ids, like the others.
        assertEquals(Profiles.S_8750, profile("SM-S931B", "pa1q", "SM8750"))
        assertEquals(Profiles.S_8750, profile("SM-S931U1", "PA1Q", "sm8750"))
        assertNull(profile("SM-S931B", "pa3q", "SM8750")) // S25 model number, S25 Ultra codename
        assertNull(profile("SM-S938B", "pa1q", "SM8750")) // S25 Ultra model number, S25 codename
        assertNull(profile("SM-S931B", "pa1q", "SM8850")) // another chip
        assertEquals(Profiles.S_PLUS_8750, profile("SM-S936B", "pa2q", "SM8750")) // S25+ (0.4.10)
        assertEquals(Profiles.FOLD8, profile("SM-F971B", "h8q", "SM8850")) // Z Fold8 (0.4.10)
        assertNull(profile("SM-F971B", "h8q", "SM8750"))
        assertNull(profile("SM-F976B", "h8q", "SM8850")) // Fold8 Ultra model number, Fold8 codename
        // Galaxy Z Fold7: all three ids.
        assertEquals(Profiles.FOLD7, profile("SM-F966B", "q7q", "SM8750"))
        assertEquals(Profiles.FOLD7, profile("SM-F966U", "Q7Q", "sm8750"))
        assertNull(profile("SM-F966B", "q7q", "SM8850")) // another chip
        assertNull(profile("SM-F976B", "q7q", "SM8750")) // Fold8 Ultra model number, Fold7 codename
        assertNull(profile("SM-F766B", "b7q", "SM8750")) // Z Flip7: no profile
        assertNull(profile("Pixel 10 Pro Fold", "rango", "Tensor G5"))

        val near = Profiles.resolve("SM-S948U", "pa3q", "SM8750")
        assertNull(near.profile)
        assertEquals(Profiles.S_ULTRA_8850, near.nearest)
        assertEquals(listOf("codename pa3q (profile: m3q)", "chip SM8750 (profile: SM8850)"), near.mismatches)

        assertNull(Profiles.resolve("SM-A566B", "a56x", "s5e8855").nearest)
    }

    @Test
    fun builtInProfilesNeverOverlap() {
        val all = Profiles.BUILT_IN
        for (a in all) {
            for (b in all) {
                if (a === b) continue
                assertFalse("${a.id} vs ${b.id}", a.matches(b.modelPrefix + "X", b.codename, b.socModel))
            }
        }
        // Two profiles matching one phone resolve to nothing (fail closed).
        val twice = Profiles.resolve("SM-F976B", "q8q", "SM8850", listOf(Profiles.F8U, Profiles.F8U.copy(id = "copy")))
        assertNull(twice.profile)
        assertTrue(twice.mismatches.single().startsWith("matches 2 profiles"))
    }

    @Test
    fun socModelFromThePlatformWhenThePropIsEmpty() {
        val f = Fixtures.facts(soc = Fixtures.F8U_SOC.copy(model = ""))
        assertEquals("SM8850", f.soc.model)
        assertEquals(Profiles.F8U, Profiles.resolve(f).profile)
    }

    /** 0.5.06: LineageOS 24 is offered on every phone that offers Infinity-X, right after it, untested; nowhere else. */
    @Test
    fun lineageFollowsInfinityXEverywhere() {
        val offerInfinity = Profiles.BUILT_IN.filter { it.choice(Images.ID_INFINITYX) != null }
        assertTrue(offerInfinity.isNotEmpty())
        for (p in Profiles.BUILT_IN) {
            val ids = p.choices.map { it.imageId }
            if (p in offerInfinity) {
                assertEquals(p.id, ids.indexOf(Images.ID_INFINITYX) + 1, ids.indexOf(Images.ID_LINEAGE))
                // 0.5.15: tested by the team on the Z Fold8 Ultra (the owner's runs).
                assertEquals(p.id, ImageChoice(Images.ID_LINEAGE, PackageSets.ID_LINEAGE, tested = p.id == Profiles.ID_F8U), p.choice(Images.ID_LINEAGE))
            } else {
                assertNull(p.id, p.choice(Images.ID_LINEAGE))
            }
        }
    }

    /**
     * 0.5.22: One UI 9.5 (the Galaxy S26 Ultra build) is last on every phone that offers a system for One UI 9 (an SDK 37
     * image), untested; not on the phones held on One UI 8, whose only system is OxygenOS 16 (SDK 36).
     */
    @Test
    fun oneUi95IsLastOnEveryOneUi9Phone() {
        for (p in Profiles.BUILT_IN) {
            // 0.5.35: the Z Fold8 takes its own set with Josh's Fold8 files (PackageSets.ONEUI95_F8).
            val expected = ImageChoice(Images.ID_ONEUI95, if (p.id == Profiles.ID_FOLD8) PackageSets.ID_ONEUI95_F8 else PackageSets.ID_ONEUI95, tested = false)
            // 0.5.41: a Galaxy Tab has only its tablet system (owner: "Hide all other Heros").
            // Pull request #371: except the Tab S9 FE, which also takes One UI 9.5 (owner, 2026-11-25).
            val onOneUi9 = true && p.images().any { it.sdk == 37 && it.id != Images.ID_ONEUI95 }
            if (onOneUi9) {
                assertEquals(p.id, expected, p.choices.last().copy(tested = false))
                assertEquals(p.id, expected, p.choice(Images.ID_ONEUI95)!!.copy(tested = false))
            } else {
                assertNull(p.id, p.choice(Images.ID_ONEUI95))
            }
        }
        assertEquals(61, Profiles.BUILT_IN.count { it.choice(Images.ID_ONEUI95) != null })
        assertEquals(listOf(Images.ID_OXYGEN16), Profiles.A06.choices.map { it.imageId })
    }
}
