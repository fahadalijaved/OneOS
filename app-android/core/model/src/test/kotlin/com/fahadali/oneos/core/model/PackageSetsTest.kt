package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

class PackageSetsTest {
    private val n6 = PackageSets.N6_F8U
    private val pixel = PackageSets.PIXEL_F8U
    private val xin = PackageSets.X9U_IN_SULTRA

    /** sha256sum of out/overlays_n6g_r3, out/overlays_x9u_r51, out/overlays_x9u_in_r53 (2026-11-03) and out/overlays_pixel_f8u_r2 without the omitted files. */
    private fun shas(set: PackageSet) = Bundles.text("packages/${set.id}.sha256")

    private fun guards(set: PackageSet) = Bundles.text("packages/${set.id}.guards.txt")

    @Test fun fold8StableInheritsEverySharedPayloadAndGuard() {
        val custom = PackageSets.N6_GLOBAL_F8
        assertEquals(n6.files + PackageFile("GlobalVerifiedAddons.tar", FileRole.GUEST_FIX), custom.files)
        assertEquals(guards(n6), guards(custom))
        val sharedHashes = ShaList.parse(shas(n6)).entries
        val customHashes = ShaList.parse(shas(custom)).entries
        assertEquals(emptySet<String>(), sharedHashes.keys.filter {
            sharedHashes[it] != customHashes[it]
        }.toSet())
        assertEquals(setOf("GlobalVerifiedAddons.tar"), customHashes.keys - sharedHashes.keys)
    }

    /** The 15 APEX payloads every set carries. */
    private val commonPayloads = listOf(
        "art", "i18n", "runtime", "sdkext", "crashrecovery", "extservices", "permission", "wifi",
        "appsearch", "mediaprovider", "adservices", "rkpd", "healthfitness", "ondevicepersonalization",
        "configinfrastructure",
    ).map { "${it}_payload.img" }

    @Test
    fun setsAsData() {
        assertEquals(33, n6.files.size) // 0.4.47: + KeKeThemeSpace_patched.apk; 0.4.37: + framework_patched.jar, libcamera_client_patched.so, samcam.tar; 0.4.38 (global): + cellbroadcast, Fold8SystemUI.apk, Fold8AngleRelay.dex; 0.4.39: + telephony-common_patched.jar
        assertEquals(43, pixel.files.size) // 0.4.59: OneOSFoldCutout.apk, yogi-services_patched.jar, libbootanimation_preapex_patched.so, OneOSPixelLauncher.apk, OneOSPixelDoze.apk; 0.4.24: framework_patched.jar (One UI's camera transaction codes); 0.4.45: telephony-common_patched.jar; 0.4.47: libcamera_client_patched.so, samcam.tar
        assertEquals(Images.ID_FIND_N6, n6.imageId)
        assertEquals(Images.ID_PIXEL_YOGI, pixel.imageId)
        assertEquals("out/overlays_n6g_r14", n6.sourceDir)
        assertEquals("out/overlays_x9u_in_r67", xin.sourceDir)
        assertEquals(Images.ID_FIND_X9U_IN, xin.imageId)
        assertEquals("out/overlays_pixel_f8u_r15", pixel.sourceDir)
        assertEquals(
            listOf(PackageSets.N6_GLOBAL_F8, n6, xin, pixel, PackageSets.PIXEL_SULTRA, PackageSets.PIXEL_F8, PackageSets.PIXEL9_SULTRA,
                PackageSets.INFINITYX, PackageSets.HYPER_F8U, PackageSets.NOTHING_F8U),
            PackageSets.ALL,
        )
        // Infinity-X (0.4.27): both guard jars, the camera codes (Java and native), the guest vold, the
        // AOSP signal poll, the IMS backoff, the guest app, the guards and 21 payloads, GmsCore's among them.
        // Not its cellbroadcast module (0.4.28): One UI's stays, as tethering does.
        val ifx = PackageSets.INFINITYX
        assertEquals(Images.ID_INFINITYX, ifx.imageId)
        assertEquals("out/overlays_infinityx_r11", ifx.sourceDir)
        // 0.4.55 (r4): telephony-common_patched.jar (the SMS centre) and samcam.tar (the S26 Ultra's camera).
        assertEquals(36, ifx.files.size)
        // 0.4.33: the status bar's corner padding, as on the Pixel images.
        assertTrue(ifx.file("OneOSPixelStatusBar.apk")?.role == FileRole.RRO)
        assertEquals(21, ifx.files.count { it.role == FileRole.APEX_PAYLOAD })
        assertEquals(listOf(PackageSets.TETHERING, PackageSets.CELLBROADCAST), ifx.omitted)
        assertTrue(ifx.file(PackageSets.CELLBROADCAST) == null)
        assertEquals(
            listOf("services_patched.jar", "oplus-services_patched.jar", "framework_patched.jar", "vold_patched",
                "service.incremental_patched.so", "libcamera_client_patched.so", "telephony-common_patched.jar"),
            ifx.files.filter { it.role in PackageFile.GUARDED }.map { it.name },
        )
        assertTrue(ifx.file(PackageSets.GMS_PAYLOAD) != null && ifx.hasReturnApp)
        // HyperOS (0.4.31 on every phone; made for the Z Fold8 Ultra and Z Fold8): services.jar, Xiaomi's guard jars,
        // framework.jar and the guest vold (r7), the native camera client (r10), the 15 common payloads and bt.
        val hyper = PackageSets.HYPER_F8U
        assertEquals(Images.ID_HYPEROS_LHASA, hyper.imageId)
        assertEquals("out/overlays_hyperos_r21", hyper.sourceDir)
        assertEquals(38, hyper.files.size) // 0.4.38: + libsurfaceflinger_patched.so; 0.4.59: + telephony, two cameras
        assertEquals(listOf("socket_exec", "libaudiohal_aidl_patched.so", "MiWallpaper_patched.apk", "samcam.tar", "samcam_bar.tar"),
            hyper.files.filter { it.role == FileRole.GUEST_FIX }.map { it.name })
        assertEquals(
            listOf("services_patched.jar", "miui-services_patched.jar", "apprecovery.proinstaller_patched.jar", "framework_patched.jar",
                "miui-wifi-service_patched.jar", "miui-telephony-common_patched.jar", "vold_patched", "service.incremental_patched.so",
                "libcamera_client_patched.so", "libsurfaceflinger_patched.so", "telephony-common_patched.jar"),
            hyper.files.filter { it.role in PackageFile.GUARDED }.map { it.name },
        )
        assertTrue(hyper.hasReturnApp && "vold_patched" in hyper.names)
        // Nothing OS (0.4.33), the smallest set: Nothing ships no vendor framework jar, so services.jar and
        // framework.jar carry every guard. The signal-poll injection RRO goes in /oem, after the image's own
        // TelephonyResCommon_Sys.apk in this guest's overlay order (run 10).
        val nothing = PackageSets.NOTHING_F8U
        assertEquals(Images.ID_NOTHING_METROID, nothing.imageId)
        assertEquals("out/overlays_nothing_r29", nothing.sourceDir)
        assertEquals(48, nothing.files.size) // 0.4.55: samcam_bar.tar, the S26 Ultra's camera for the phones
        // r12: Nothing's SystemUI with its quick settings at the screen's own density on the inner panel;
        // r13: its launcher with the drawer's category boxes per row from the width; r17: the ringtone kits
        // the boot animation on both panels and the ringtone generator's device check; 0.4.35: One UI's camera.
        assertEquals(listOf("SystemUI_patched.apk", "NothingLauncher3_patched.apk", "nothing_customringtone.tar",
                "nothing_product_media.tar", "libbootanimation_preapex_patched.so", "NothingGenerateRingtoneService_patched.apk",
                "samcam.tar", "samcam_bar.tar"),
            nothing.files.filter { it.role == FileRole.GUEST_FIX }.map { it.name })
        assertEquals(18, nothing.files.count { it.role == FileRole.APEX_PAYLOAD })
        assertEquals(listOf(PackageSets.TETHERING), nothing.omitted)
        // r2: the guest vold, so the guest registers "gvld" and the return needs no reboot.
        assertEquals(
            listOf("services_patched.jar", "framework_patched.jar", "vold_patched", "service.incremental_patched.so",
                "libcamera_client_patched.so"),
            nothing.files.filter { it.role in PackageFile.GUARDED }.map { it.name },
        )
        // The first non-ColorOS set to carry the SurfaceFlinger patch (the QTI composer skip).
        assertEquals(listOf("surfaceflinger_patched"), nothing.files.filter { it.role == FileRole.SURFACEFLINGER }.map { it.name })
        // Its Google services are hidden by folder, not staged as a payload ([ImageRef.gmsHideable]).
        assertTrue(nothing.file(PackageSets.GMS_PAYLOAD) == null)
        assertTrue(nothing.hasReturnApp && nothing.file(PackageSets.CELLBROADCAST) != null)
        // 0.4.38: no Fold8 set of its own for the Find N6 global image (n6-f8 patched the CN build's
        // SystemUI); the Z Fold8 takes the Folds' n6-f8u.
        assertTrue(PackageSets.ALL.none { it.id == "n6-f8" })
        // The Pixel Fold sets (pull request #1, the F8U's since 0.4.21): the Pixel files, the patched
        // SystemUI, the angle relay and each one's unfold RRO. The bar sets (0.4.59 r12) have only
        // double tap to sleep, from each image's own SystemUI and Pixel Launcher.
        for (bar in listOf(PackageSets.PIXEL_SULTRA, PackageSets.PIXEL9_SULTRA)) {
            assertEquals(listOf("samcam.tar", "OneOSPixelSystemUI.apk", "OneOSPixelLauncher.apk"),
                bar.files.filter { it.role == FileRole.GUEST_FIX }.map { it.name })
        }
        val hinge = listOf("Fold8PixelSystemUI.apk", "Fold8AngleRelay.dex")
        // 0.4.59 (r11): and the boot animation on every panel; r12 the launcher with double tap to sleep.
        val bootanim = listOf("libbootanimation_preapex_patched.so", "OneOSPixelLauncher.apk")
        assertEquals(listOf("samcam.tar") + hinge + "OneOSPixelUnfold.apk" + bootanim, pixel.files.filter { it.role == FileRole.GUEST_FIX }.map { it.name })
        assertEquals(listOf("samcam.tar") + hinge + "Fold8PixelUnfold.apk" + bootanim, PackageSets.PIXEL_F8.files.filter { it.role == FileRole.GUEST_FIX }.map { it.name })
        // 0.4.59: the F8U's also has Nothing OS's per-panel cutout RRO (the cover's camera hole); both
        // Fold sets (r11) the device state policy without tent mode.
        val tent = PackageFile("yogi-services_patched.jar", FileRole.FRAMEWORK_JAR)
        assertEquals(PackageSets.PIXEL_SULTRA.files.filter { it.role != FileRole.GUEST_FIX } + tent + PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            pixel.files.filter { it.role != FileRole.GUEST_FIX })
        assertEquals(PackageSets.PIXEL_SULTRA.files.filter { it.role != FileRole.GUEST_FIX } + tent, PackageSets.PIXEL_F8.files.filter { it.role != FileRole.GUEST_FIX })
        // The Pixel 9 Pro XL's set (0.4.22): the same files, from its own image; 0.4.47 its
        // libcameracompatbilityinfo.so needs One UI's codes too.
        assertEquals(PackageSets.PIXEL_SULTRA.files + PackageFile("libcameracompatbilityinfo_patched.so", FileRole.GUARD_LIBRARY), PackageSets.PIXEL9_SULTRA.files)
        assertEquals(Images.ID_PIXEL_KOMODO, PackageSets.PIXEL9_SULTRA.imageId)
        // One SystemUI build and one relay for both: the APK packs each once.
        val f8uSums = ShaList.parse(shas(pixel)).entries
        val f8Sums = ShaList.parse(shas(PackageSets.PIXEL_F8)).entries
        for (n in hinge) assertEquals(n, f8uSums[n], f8Sums[n])
        // Owner: leave out only dead weight.
        assertEquals(listOf("tethering_payload.img"), n6.omitted)
        assertEquals(listOf("tethering_payload.img"), pixel.omitted)
        // The global builds carry their own cell broadcast module (0.4.38: the Find N6's too).
        for (s in listOf(n6, xin)) assertTrue(s.id, PackageSets.CELLBROADCAST in s.names)
        for (s in PackageSets.ALL) {
            assertEquals(s.names.size, s.names.toSet().size)
            assertTrue(s.omitted.none { it in s.names })
            assertTrue(s.names.none { it == Images.STAGE_NAME })
            assertTrue(s.id, s.names.containsAll(commonPayloads + "guards.txt" + "services_patched.jar"))
            assertEquals(s.id, FileRole.GUARDS, s.file("guards.txt")!!.role)
            // Executable: surfaceflinger_patched and vold_patched only (root's file_mode, deploy-phone.sh's push).
            for (f in s.files) assertEquals("${s.id} ${f.name}", if (f.name in setOf("surfaceflinger_patched", "vold_patched")) "0755" else "0644", f.mode)
            // The guest vold's two binaries: both or none (oneos_switch.sh and guest_prepare.sh refuse one alone).
            assertEquals(s.id, s.file("vold_patched") != null, s.file("service.incremental_patched.so") != null)
            // Back to One UI in the guest exactly when the set stages the in-guest app (guest_prepare.sh installs it).
            assertEquals(s.id, PackageSets.GUEST_APP in s.names, s.hasReturnApp)
        }
        // The ColorOS sets (0.4.8, rebuilt 2026-10-25): both guard jars, the guest vold
        // as gvld (ColorOS 17 CP2A.260605.016) and the in-guest app.
        // 0.4.37: the Find N6 and IN sets with One UI's camera codes too (framework_patched.jar,
        // libcamera_client_patched.so); the CN set's image is not on the server yet.
        // 0.4.39: and the SMS service centre fix in telephony-common_patched.jar (a guard jar, after framework_patched.jar).
        val camera = listOf("framework_patched.jar", "telephony-common_patched.jar", "libcamera_client_patched.so")
        for (s in listOf(n6, xin)) {
            val cam = camera
            assertEquals(listOf("services_patched.jar", "oplus-services_patched.jar") + cam.take(cam.size.coerceAtMost(2)),
                s.files.filter { it.role == FileRole.GUARD_JAR }.map { it.name })
            assertEquals(
                s.id,
                listOf("services_patched.jar", "oplus-services_patched.jar", "vold_patched", "service.incremental_patched.so") + cam,
                s.files.filter { it.role in PackageFile.GUARDED }.map { it.name },
            )
            // 0.4.38: the Find N6 global set carries its cell broadcast module too.
            assertEquals(s.id, 16, s.files.count { it.role == FileRole.APEX_PAYLOAD })
            assertEquals(FileRole.SURFACEFLINGER, s.file("surfaceflinger_patched")!!.role)
            assertEquals(FileRole.GUEST_APP, s.file(PackageSets.GUEST_APP)!!.role)
            assertTrue(s.hasReturnApp)
        }
        // The IN build's set (0.4.11; 0.4.51 the only Find X9 Ultra build): the Find N6 set's files but the
        // fold's (the wallpaper grid, the Fold8 SystemUI and its hinge relay), with its own guest vold as gvld.
        assertEquals((n6.names - PackageSets.WALLPAPER_GRID_RRO - "Fold8SystemUI.apk" - "Fold8AngleRelay.dex").toSet(), xin.names.toSet())
        // 0.4.47: the global builds' Theme Store without its brand check, the same file in both sets.
        assertEquals(ShaList.parse(shas(n6)).entries[PackageSets.THEME_STORE_APK], ShaList.parse(shas(xin)).entries[PackageSets.THEME_STORE_APK])
        assertEquals(FileRole.GUEST_FIX, n6.file(PackageSets.THEME_STORE_APK)?.role)
        assertEquals(listOf(PackageSets.TETHERING, PackageSets.WALLPAPER_GRID_RRO), xin.omitted)
        assertEquals(16, xin.files.count { it.role == FileRole.APEX_PAYLOAD })
        assertEquals(
            listOf("services_patched.jar", "oplus-services_patched.jar", "vold_patched", "service.incremental_patched.so") + camera,
            xin.files.filter { it.role in PackageFile.GUARDED }.map { it.name },
        )
        assertTrue(xin.hasReturnApp)
        assertEquals(FileRole.RRO, n6.file("OneOSWallpapersFoldGrid.apk")!!.role)
        // 0.4.38: the Find N6 global build is the IN build's base, so 22 files are byte-identical with
        // the IN set (16 payloads, surfaceflinger, the guest vold's two binaries, the native camera
        // client, the in-guest app, 0.4.39 telephony-common_patched.jar and 0.4.47 the patched Theme
        // Store).
        val a = ShaList.parse(shas(n6)).entries
        val g = ShaList.parse(shas(xin)).entries
        assertEquals(23, a.count { (n, h) -> g[n] == h })
        for (n in listOf("vold_patched", "service.incremental_patched.so", "surfaceflinger_patched")) assertEquals(n, a[n], g[n])
        // The Pixel set's files are its own but the in-guest app, the same build in every set.
        val c = ShaList.parse(shas(pixel)).entries
        val colorOs = (a.values + g.values).toSet()
        // 0.4.38: and the hinge-angle relay, one build for the Pixel and ColorOS fold sets.
        assertEquals(setOf("Fold8AngleRelay.dex", PackageSets.GUEST_APP), c.filterValues { it in colorOs }.keys)
        assertEquals(c[PackageSets.GUEST_APP], a[PackageSets.GUEST_APP])
    }

    /** 0.3.7: exactly the files a Pixel session uses (guest_prepare.sh), with their roles. */
    @Test
    fun pixelSetIsWhatAPixelSessionUses() {
        val roles = pixel.files.associate { it.name to it.role }
        assertEquals(FileRole.GUARD_JAR, roles["services_patched.jar"])
        assertEquals(FileRole.GUARD_JAR, roles["framework_patched.jar"])
        assertEquals(FileRole.GUARD_EXECUTABLE, roles["vold_patched"])
        assertEquals(FileRole.GUARD_LIBRARY, roles["service.incremental_patched.so"])
        assertEquals(FileRole.INJECTION_JAR, roles["oneos-telephony.jar"])
        assertEquals(FileRole.INJECTION_SHA256, roles["oneos-telephony.sha256"])
        assertEquals(FileRole.RRO, roles["OneOSPhoneInjection.apk"])
        assertEquals(FileRole.RRO, roles["OneOSPixelStatusBar.apk"])
        assertEquals(FileRole.GUEST_APP, roles[PackageSets.GUEST_APP])
        assertEquals(listOf("services_patched.jar", "framework_patched.jar", "telephony-common_patched.jar", "libcamera_client_patched.so", "vold_patched", "service.incremental_patched.so"), pixel.files.filter { it.role in PackageFile.GUARDED }.map { it.name })
        // 0.4.45 (r3): Samsung IMS on every Pixel set, so their guards name the carve-out (guest_prepare.sh stages
        // Samsung IMS only then) and the SMS service centre goes out as an international number.
        for (s in listOf(pixel, PackageSets.PIXEL_F8, PackageSets.PIXEL_SULTRA, PackageSets.PIXEL9_SULTRA)) {
            val head = guards(s).lines().filter { it.startsWith("#") }.joinToString(" ")
            for (w in listOf("secims", "wipesecrets", "ksuappid", "gatekeeper", "pdb", "apexd", "appid15000")) {
                assertTrue("${s.id}: $w", Regex("\\b$w\\b").containsMatchIn(head))
            }
            assertEquals(s.id, FileRole.GUARD_JAR, s.file("telephony-common_patched.jar")?.role)
        }
        assertEquals("0755", pixel.file("vold_patched")!!.mode)
        assertEquals("0644", pixel.file("service.incremental_patched.so")!!.mode)
        // 22 payloads: every set's 15, Google's cellbroadcast/bt/nfcservices, the image's own
        // telephonycore/conscrypt/profiling (no platform framework-telecom.jar) and GmsCore.
        val payloads = pixel.files.filter { it.role == FileRole.APEX_PAYLOAD }.map { it.name }
        assertEquals(22, payloads.size)
        assertEquals(
            (commonPayloads + listOf("cellbroadcast", "bt", "nfcservices", "telephonycore", "conscrypt", "profiling", "gmssystem").map { "${it}_payload.img" }).toSet(),
            payloads.toSet(),
        )
        assertTrue(PackageSets.GMS_PAYLOAD in pixel.names)
        // Never mounted (the host keeps its tethering module): left out.
        assertTrue(PackageSets.TETHERING !in pixel.names)
        // Nothing of ColorOS: no oplus jars, no patched surfaceflinger (Google's is not patched), no fold grid.
        for (n in listOf("oplus-services_patched.jar", "oplus-telephony-common_patched.jar", "ims-ext-common_patched.jar", "surfaceflinger_patched", PackageSets.WALLPAPER_GRID_RRO)) {
            assertTrue(n, n !in pixel.names)
        }
        assertTrue(pixel.hasReturnApp)
        // The free-space gate's number is the files' total (out/overlays_pixel_f8u_r4, 2026-11-04).
        assertEquals(708_239_363L, pixel.approxBytes)
        // Each image presents its Google services exactly when its sets stage GmsCore.
        for (p in Profiles.BUILT_IN) {
            for (choice in p.choices) {
                val image = Images.byId(choice.imageId)!!
                val set = PackageSets.byId(choice.packageSetId)!!
                assertEquals("${p.id} ${set.id}", image.presentsGms, set.file(PackageSets.GMS_PAYLOAD) != null)
            }
        }
    }

    @Test
    fun shaListsNameExactlyTheSetsFiles() {
        for (s in PackageSets.ALL) assertEquals(s.id, emptyList<String>(), s.check(shas(s)))
        // The Pixel list and a ColorOS one are not interchangeable.
        val pixelOnN6 = pixel.check(shas(n6))
        assertTrue(pixelOnN6.contains("pixel-f8u: oneos-telephony.jar missing"))
        assertTrue(pixelOnN6.contains("pixel-f8u: gmssystem_payload.img missing"))
        assertTrue(pixelOnN6.contains("pixel-f8u: oplus-services_patched.jar is not in this set"))
        assertTrue(pixelOnN6.contains("pixel-f8u: OneOSWallpapersFoldGrid.apk is not in this set"))
        val n6OnPixel = n6.check(shas(pixel))
        assertTrue(n6OnPixel.contains("n6-f8u: surfaceflinger_patched missing"))
        assertTrue(n6OnPixel.contains("n6-f8u: oneos-telephony.jar is not in this set"))
        assertTrue(n6OnPixel.contains("n6-f8u: OneOSPixelStatusBar.apk is not in this set"))
        assertTrue(xin.check(shas(pixel)).contains("x9u-in-sultra: OneOSPixelStatusBar.apk is not in this set"))
        val pixelTether = shas(pixel) + "${"a".repeat(64)}  tethering_payload.img\n"
        assertEquals(listOf("pixel-f8u: tethering_payload.img is left out of this set"), pixel.check(pixelTether))
        // Swapped lists fail: the fold grid is not in the S Ultra set.
        assertTrue(xin.check(shas(n6)).contains("x9u-in-sultra: OneOSWallpapersFoldGrid.apk is left out of this set"))
        assertTrue(n6.check(shas(xin)).contains("n6-f8u: OneOSWallpapersFoldGrid.apk missing"))

        val extra = shas(xin) + "${"a".repeat(64)}  OneOSPixelStatusBar.apk\n"
        assertEquals(listOf("x9u-in-sultra: OneOSPixelStatusBar.apk is not in this set"), xin.check(extra))
        val tether = shas(xin) + "${"a".repeat(64)}  tethering_payload.img\n"
        assertEquals(listOf("x9u-in-sultra: tethering_payload.img is left out of this set"), xin.check(tether))
        val dup = shas(xin) + shas(xin).lines().first() + "\n"
        assertEquals(listOf("${shas(xin).lines().first().substringAfter("  ")} listed twice"), xin.check(dup))
    }

    @Test
    fun guardsMatchTheGuardJars() {
        for (s in PackageSets.ALL) assertEquals(s.id, emptyList<String>(), s.checkGuards(guards(s), shas(s)))
        // N6 guards with the X9U jars: never mix builds. The guard jars, (0.4.37) the N6 set's
        // camera files and (0.4.38) the guest vold's two binaries: the Find N6 global build has the
        // IN build's vold and service.incremental.so, not the CN builds'; (0.4.39) its telephony-common_patched.jar.
        val mixed = xin.checkGuards(guards(n6), shas(xin))
        assertTrue(mixed.isNotEmpty())
        assertTrue(mixed.all { it.startsWith("guards.txt: ") })
        assertTrue(mixed.any { it.contains("the set has") })
        // A guards.txt that lists something else, or misses a jar.
        assertTrue(xin.checkGuards(guards(xin) + "${"b".repeat(64)}  OneOSGuest.apk\n", shas(xin)).single().contains("not a guard jar"))
        assertTrue(xin.checkGuards(guards(xin).lines().filterNot { it.endsWith("oplus-services_patched.jar") }.joinToString("\n"), shas(xin)).single().contains("missing"))
        // The ColorOS sets carry the guards Google services need too (rebuilt 2026-10-25).
        for (s in listOf(n6, xin)) for (t in PackageSets.GMS_GUARDS) assertTrue("${s.id} $t", Regex("\\b$t\\b").containsMatchIn(guards(s)))
    }

    /** 0.3.7: the Pixel set's guards.txt pins services_patched.jar and both gvld binaries; comment lines are fine. */
    @Test
    fun pixelGuardsPinTheGuestVoldToo() {
        val g = guards(pixel)
        val sums = shas(pixel)
        assertEquals(setOf("services_patched.jar", "framework_patched.jar", "telephony-common_patched.jar", "libcamera_client_patched.so", "vold_patched", "service.incremental_patched.so"), ShaList.parse(g).entries.keys)
        assertTrue(g.lines().first().startsWith("#"))
        assertEquals(emptyList<String>(), pixel.checkGuards(g, sums))
        // Only one of the two gvld binaries (a half-built set): refused, as the session scripts do.
        for (n in listOf("vold_patched", "service.incremental_patched.so")) {
            val half = g.lines().filterNot { it.endsWith("  $n") }.joinToString("\n")
            assertEquals(n, listOf("guards.txt: $n missing"), pixel.checkGuards(half, sums))
        }
        // A vold_patched that is not the set's.
        val wrong = g.replace(ShaList.parse(g).entries.getValue("vold_patched"), "c".repeat(64))
        assertTrue(pixel.checkGuards(wrong, sums).single().startsWith("guards.txt: vold_patched is cccccccccccc..., the set has "))
        // Something else listed.
        assertTrue(pixel.checkGuards(g + "${"b".repeat(64)}  OneOSGuest.apk\n", sums).single().contains("OneOSGuest.apk is not a guard jar of pixel-f8u"))
        // Without the comment lines naming the Google services guards: each one is missing (a switch would be refused).
        val bare = g.lines().filterNot { it.startsWith("#") }.joinToString("\n")
        assertEquals(PackageSets.GMS_GUARDS.map { "guards.txt does not name the $it guard Google services need" }, pixel.checkGuards(bare, sums))
        assertEquals(1, pixel.checkGuards(g.replace("appid15000", "appid"), sums).size)
        // Never mixed: a ColorOS set's guards do not vouch for the Pixel files, nor the other way round.
        val colorOsOnPixel = pixel.checkGuards(guards(n6), sums)
        assertTrue(colorOsOnPixel.any { it.startsWith("guards.txt: vold_patched is ") })
        assertTrue(colorOsOnPixel.any { it.startsWith("guards.txt: service.incremental_patched.so is ") })
        assertTrue(colorOsOnPixel.contains("guards.txt: oplus-services_patched.jar is not a guard jar of pixel-f8u"))
        assertTrue(colorOsOnPixel.any { it.startsWith("guards.txt: services_patched.jar is ") })
        val pixelOnN6 = n6.checkGuards(g, shas(n6))
        assertTrue(pixelOnN6.any { it.startsWith("guards.txt: vold_patched is ") })
        assertTrue(pixelOnN6.any { it.startsWith("guards.txt: service.incremental_patched.so is ") })
        assertTrue(pixelOnN6.contains("guards.txt: oplus-services_patched.jar missing"))
        assertTrue(xin.checkGuards(g, shas(xin)).isNotEmpty())
    }

    @Test
    fun shaListParsing() {
        val h = "0123456789abcdef".repeat(4)
        val ok = ShaList.parse("# comment\n$h  a.jar\n${h.uppercase()} *b_payload.img\n\n")
        assertEquals(mapOf("a.jar" to h, "b_payload.img" to h), ok.entries)
        assertTrue(ok.problems.isEmpty())
        assertEquals("$h  a.jar\n$h  b_payload.img\n", ShaList.render(ok.entries))

        for (bad in listOf("$h a.jar b", "$h  ../x", "$h  dir/x", "$h  .hidden", "${h.dropLast(1)}  a.jar", "$h\ta.jar")) {
            assertFalse(bad, ShaList.parse(bad).problems.isEmpty())
            assertTrue(bad, ShaList.parse(bad).entries.isEmpty())
        }
    }

    /** B2's checked-in lists (app-android/packages), when they exist, name exactly these sets. */
    @Test
    fun checkedInPackageListsMatchTheSets() {
        val dir = System.getProperty("oneos.packagesDir")?.let(::File)
        assumeTrue("app-android/packages not there yet", dir != null && dir.isDirectory)
        for (s in PackageSets.ALL) {
            val f = File(dir, "${s.id}.sha256")
            assumeTrue("${f.name} not there yet", f.isFile)
            assertEquals(s.id, emptyList<String>(), s.check(f.readText()))
        }
        // The IN sets' lists are gone with the image (0.3.7).
        assertEquals(PackageSets.ALL.map { "${it.id}.sha256" }.toSet(), dir!!.list()!!.filter { it.endsWith(".sha256") }.toSet())
    }

    @Test
    fun spaceToStage() {
        // AA17: about 27.1 GB for the S Ultra (0.4.51: the X9U IN image + its files + 11 GiB).
        val need = SpaceRule.toStage(Images.FIND_X9U_IN, xin)
        assertEquals("27.1 GB", Units.bytes(need))
        // The Pixel image is smaller: its own raw size and files.
        val pixelNeed = SpaceRule.toStage(Images.PIXEL_YOGI, pixel)
        assertEquals(6_559_223_808L + 708_239_363L + 11L * SpaceRule.GIB, pixelNeed)
        assertEquals("19.1 GB", Units.bytes(pixelNeed))
        assertEquals(11L * SpaceRule.GIB, SpaceRule.LAUNCH_BYTES)
        assertEquals(Images.FIND_X9U_IN.rawBytes + SpaceRule.LAUNCH_BYTES, SpaceRule.toStage(Images.FIND_X9U_IN, null))
    }
}
