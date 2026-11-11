package com.fahadali.oneos.core.model

import java.util.Locale

/** What a staged file is for; decides its mode and how the scripts use it (guest_prepare.sh). */
enum class FileRole {
    /** services / oplus-services: carry the storage, installd, sysrq and the other guards; pinned by guards.txt. */
    GUARD_JAR,
    /**
     * `vold_patched`: the guest's own vold registered as "gvld" (run 44,
     * docs/inplace-return.md), bound over the guest's /system/bin/vold; pinned
     * by guards.txt together with [GUARD_LIBRARY] and the guarded services.jar
     * (both binaries or none); executable.
     */
    GUARD_EXECUTABLE,
    /** `service.incremental_patched.so`: looks up "gvld"; pinned by guards.txt with [GUARD_EXECUTABLE]. */
    GUARD_LIBRARY,
    /** Other patched framework jars (bound over the guest's). */
    FRAMEWORK_JAR,
    /** `guards.txt`: SHA-256 of the guard files, checked by guest_prepare.sh before anything is bound. */
    GUARDS,
    /** The guest surfaceflinger with the QTI composer skip; executable. */
    SURFACEFLINGER,
    /** An APEX payload loop-mounted read-only for the guest. */
    APEX_PAYLOAD,
    /** A resource overlay copied into the guest (its /oem/overlay). */
    RRO,
    /** `OneOSGuest.apk` (app-android/guest): OneOS inside the guest, Back to One UI; copied into the guest's /oem/app. */
    GUEST_APP,
    /**
     * `oneos-telephony.jar`: the signal poll TeleService's own
     * TelephonyComponentFactory injection loads, from a read-only overlay layer
     * on the guest's system_ext (docs/pixel-guest.md, "Signal bars").
     */
    INJECTION_JAR,
    /**
     * `oneos-telephony.sha256`: the guest's telephony-common.jar and
     * TeleService.apk the jar was built and checked against; guest_prepare.sh
     * uses the jar only while both still match.
     */
    INJECTION_SHA256,
    /**
     * A Galaxy Z Fold8 fix for the Find N6 image (n6-f8, 0.4.14, ported from
     * pull request #1): the patched SystemUI bound over the image's, the
     * hinge-angle relay dex, and OPPO's AOD, UMS and Instant APKs from the
     * same firmware, installed in the guest (switcher/assets/fold8_coloros.sh).
     * In hyper-f8u: socket_exec (guest_start.sh starts hyos_spawner with it)
     * and libaudiohal_aidl_patched.so (bound over the image's). Never run in
     * One UI.
     */
    GUEST_FIX,
}

/** One file of a set, by its flat name in `$STAGE`. */
data class PackageFile(val name: String, val role: FileRole) {
    /**
     * Mode in `$STAGE`: surfaceflinger_patched and vold_patched are executable
     * (as scripts/deploy-phone.sh pushes them; guest_prepare.sh binds them over
     * the guest's binaries), everything else 0644. Root's `file_mode` agrees.
     */
    val mode: String get() = if (role in EXECUTABLE) "0755" else "0644"

    companion object {
        private val EXECUTABLE = setOf(FileRole.SURFACEFLINGER, FileRole.GUARD_EXECUTABLE)

        /** What guards.txt pins: the guard jars and the guest vold's two binaries. */
        val GUARDED: Set<FileRole> = setOf(FileRole.GUARD_JAR, FileRole.GUARD_EXECUTABLE, FileRole.GUARD_LIBRARY)
    }
}

/**
 * The patched files staged next to one image (AA6), as data: flat names and
 * roles only. The SHA-256 of each file is in the checked-in
 * `app-android/packages/<id>.sha256` (the packaging task fails when a built
 * file differs), so this list and that file must name the same files; see
 * [check].
 */
data class PackageSet(
    val id: String,
    /** [ImageRef.id] the overlays were built from; never mix sets and images. */
    val imageId: String,
    /** Server folder the packaging task imports, relative to the repo root. */
    val sourceDir: String,
    val files: List<PackageFile>,
    /** Files in [sourceDir] this set leaves out on purpose. */
    val omitted: List<String>,
    /** Total bytes of [files] (the Pixel set of 2026-10-24, the ColorOS sets of 2026-10-25), for the free-space gate. */
    val approxBytes: Long,
    /**
     * The set stages OneOS's in-guest app (Back to One UI in the other
     * system), so the Switch dialog may say so: guest_prepare.sh copies a
     * staged `OneOSGuest.apk` into the guest's /oem/app (`ONEOS_GUEST_APP`,
     * default on, which session.env cannot set) and oneos_switch.sh's watcher
     * takes its request. True exactly when the set carries
     * [PackageSets.GUEST_APP] (the Pixel set since 0.3.7, the ColorOS sets since 0.4.8).
     */
    val hasReturnApp: Boolean = false,
) {
    val names: List<String> get() = files.map { it.name }

    fun file(name: String): PackageFile? = files.firstOrNull { it.name == name }

    /**
     * Problems with a `<sha256>  <name>` list for this set (the checked-in
     * packages/<id>.sha256 or a built folder's sha256sum); empty = it names
     * exactly [files], once each, with well-formed hashes.
     */
    fun check(shaList: String): List<String> {
        val parsed = ShaList.parse(shaList)
        val p = parsed.problems.toMutableList()
        val listed = parsed.entries.keys
        for (n in names) if (n !in listed) p += "$id: $n missing"
        for (n in listed) {
            when {
                n in omitted -> p += "$id: $n is left out of this set"
                file(n) == null -> p += "$id: $n is not in this set"
            }
        }
        return p
    }

    /**
     * Problems with this set's guards.txt against the set's own hashes: it
     * must list every guard file ([PackageFile.GUARDED]: the guard jars and
     * the guest vold's vold_patched and service.incremental_patched.so),
     * nothing else, with the file's SHA-256
     * (what oneos_switch.sh and guest_prepare.sh check before binding them).
     * A set with the GmsCore payload also needs guards.txt's comment lines to
     * name the guards Google services need ([PackageSets.GMS_GUARDS]), or
     * every switch with it would be refused.
     */
    fun checkGuards(guardsText: String, shaList: String): List<String> {
        val guards = ShaList.parse(guardsText)
        val shas = ShaList.parse(shaList).entries
        val p = guards.problems.map { "guards.txt: $it" }.toMutableList()
        val jars = files.filter { it.role in PackageFile.GUARDED }.map { it.name }
        for (j in jars) {
            val g = guards.entries[j]
            when {
                g == null -> p += "guards.txt: $j missing"
                shas[j] == null -> p += "$j has no hash in the set list"
                g != shas[j] -> p += "guards.txt: $j is ${g.take(12)}..., the set has ${shas[j]!!.take(12)}..."
            }
        }
        for (n in guards.entries.keys) if (n !in jars) p += "guards.txt: $n is not a guard jar of $id"
        if (file(PackageSets.GMS_PAYLOAD) != null) {
            // As the scripts read them: any comment line, whole words (grep -w).
            val words = guardsText.lineSequence().map { it.removeSuffix("\r") }.filter { it.startsWith("#") }
                .flatMap { it.split(Regex("[^A-Za-z0-9_]+")) }.toSet()
            for (t in PackageSets.GMS_GUARDS) if (t !in words) p += "guards.txt does not name the $t guard Google services need"
        }
        return p
    }
}

object PackageSets {
    const val ID_N6_F8U = "n6-f8u"
    const val ID_X9U_IN_SULTRA = "x9u-in-sultra"
    const val ID_PIXEL_F8U = "pixel-f8u"
    const val ID_PIXEL_F8 = "pixel-f8"
    const val ID_PIXEL_SULTRA = "pixel-sultra"
    const val ID_HYPER_F8U = "hyper-f8u"
    const val ID_PIXEL9_SULTRA = "pixel9-sultra"
    const val ID_INFINITYX = "infinityx"
    const val ID_NOTHING_F8U = "nothing-f8u"
    const val ID_OXYGEN16 = "oxygen16"
    const val ID_ORIGINOS = "originos"

    /** Never mounted (guest_prepare.sh only keeps the host module); left out of every set. */
    const val TETHERING = "tethering_payload.img"

    /** Fold-only wallpaper grid (guest_prepare.sh binds it only for the fold form). */
    const val WALLPAPER_GRID_RRO = "OneOSWallpapersFoldGrid.apk"

    /**
     * The ColorOS images' Theme Store with its brand check answering yes (0.4.47), reporting OPPO and the
     * Find N6 model to OPPO's theme server (0.4.48: an empty store for brand samsung); guest_prepare.sh binds it.
     */
    const val THEME_STORE_APK = "KeKeThemeSpace_patched.apk"
    /** 0.4.63: OPPO's AI engine (libaiboost.so and delegates) from the Find X9 Ultra's odm, laid over the guest's /odm. */
    const val ODM_AI = "oplus_odm_ai.tar"

    /**
     * Google's mainline cellbroadcast module (the Pixel image; the CN builds have
     * CellBroadcastService as an app and no payload). guest_prepare.sh mounts it
     * when it is staged, and refuses an app session whose image has the module
     * but no staged payload, except a module built from source
     * (com.android.cellbroadcast.*, Infinity-X): One UI's stays then, the
     * android.uid.networkstack group has One UI's signer ([PackageSets.INFINITYX]).
     */
    const val CELLBROADCAST = "cellbroadcast_payload.img"

    /** The Pixel image's GmsCore (its product gmssystem APEX); guest_prepare.sh presents it ([ImageRef.presentsGms]). */
    const val GMS_PAYLOAD = "gmssystem_payload.img"

    /** OneOS inside the guest (app-android/guest): Back to One UI from its screen or tile ([PackageSet.hasReturnApp]). */
    const val GUEST_APP = "OneOSGuest.apk"

    /**
     * The guards guards.txt's comment lines must name before a session
     * presents Google services (guest_prepare.sh and oneos_switch.sh refuse
     * otherwise): the phone's gatekeeper, FRP partition and apexd stay One
     * UI's, and guest apps get app ids from 15000.
     */
    val GMS_GUARDS: List<String> = listOf("gatekeeper", "pdb", "apexd", "appid15000")

    /** The APEX payloads every set carries (guest_prepare.sh mounts each one). */
    private val COMMON_PAYLOADS: List<String> = listOf(
        "art", "i18n", "runtime", "sdkext", "crashrecovery", "extservices", "permission", "wifi",
        "appsearch", "mediaprovider", "adservices", "rkpd", "healthfitness", "ondevicepersonalization",
        "configinfrastructure",
    )

    /**
     * The ColorOS sets' files (root's SET_COMMON). Since 0.4.8 (rebuilt
     * 2026-10-25 with every guard the Pixel set has) also the guest vold as
     * "gvld" for ColorOS 17 CP2A.260605.016 (vold_patched,
     * service.incremental_patched.so; oplus-services_patched.jar looks up
     * gvld too) and OneOS's in-guest app. 0.4.57: oplus-services_patched.jar keeps ColorOS's
     * resolution switch off on a panel without ColorOS's density tables (patches/oplus_resolution_tables.py).
     */
    private val COMMON: List<PackageFile> = listOf(
        PackageFile("services_patched.jar", FileRole.GUARD_JAR),
        PackageFile("oplus-services_patched.jar", FileRole.GUARD_JAR),
        PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
        PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
        PackageFile(GUEST_APP, FileRole.GUEST_APP),
        PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
        PackageFile("oplus-telephony-common_patched.jar", FileRole.FRAMEWORK_JAR),
        PackageFile("surfaceflinger_patched", FileRole.SURFACEFLINGER),
        PackageFile("guards.txt", FileRole.GUARDS),
    ) + COMMON_PAYLOADS.map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) }

    val N6_F8U = PackageSet(
        id = ID_N6_F8U,
        imageId = Images.ID_FIND_N6,
        // 0.4.38: the Find N6 global image (CPH2765 EX01), on every Z Fold; the Z Fold8 too, whose
        // n6-f8 (pull request #1) patched the CN build's SystemUI. Its cell broadcast module, as the
        // other global build's (x9u-in-sultra).
        sourceDir = "out/overlays_n6g_r15",
        // 0.4.37: One UI's camera transaction codes (ColorOS's ICameraDeviceUser is one code off).
        files = COMMON + PackageFile(WALLPAPER_GRID_RRO, FileRole.RRO) + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD) +
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR) +
            // 0.4.39: the SMS service centre as an international number (guest_smsc_international.py).
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR) +
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY) +
            // 0.4.37: One UI's camera, rewritten for the Find N6 image (scripts/samsung-camera/build-cached.sh);
            // 0.4.57 (r8) with the system's camera icon in its notifications (fix_notification_icon.py).
            PackageFile("samcam.tar", FileRole.GUEST_FIX) +
            // 0.4.38: pull request #1's Fold8 SystemUI and hinge-angle relay, re-applied to the global
            // build (scripts/make-fold8-coloros.py --into); used on the Z Fold8 and Z Fold8 Ultra only.
            PackageFile("Fold8SystemUI.apk", FileRole.GUEST_FIX) + PackageFile("Fold8AngleRelay.dex", FileRole.GUEST_FIX) +
            // 0.4.47: the image's Theme Store without its brand check (DeviceChecker refused the Galaxy's brand).
            PackageFile(THEME_STORE_APK, FileRole.GUEST_FIX) +
            // 0.4.63: OPPO's AI engine for the guest's /odm (lock screen depth effect, AI features).
            PackageFile(ODM_AI, FileRole.GUEST_FIX),
        omitted = listOf(TETHERING),
        approxBytes = 763_750_051L,
        hasReturnApp = true,
    )

    /** The upstream Find N6 set plus a no-op addon slot for opt-in contributor overlays. */
    val N6_GLOBAL_F8 = PackageSet(
        id = "n6-global-f8",
        imageId = Images.ID_FIND_N6,
        sourceDir = "out/fold8-global-current",
        files = N6_F8U.files + PackageFile("GlobalVerifiedAddons.tar", FileRole.GUEST_FIX),
        omitted = listOf(TETHERING, "OneOSFoldCutout.apk", "OneOSTabletQs.apk"),
        // n6-f8u's files and the 10 KB empty addon archive (a channel's archive is larger, but optional).
        approxBytes = N6_F8U.approxBytes + 10_240L,
        hasReturnApp = true,
    )

    /**
     * Find X9 Ultra IN image, the bar phones (0.4.11): the CN set's files and its cell broadcast module;
     * 0.4.37 One UI's camera transaction codes (framework_patched.jar, libcamera_client_patched.so): ColorOS's
     * ICameraDeviceUser is one code off from One UI's, and every camera open was refused ("access restricted").
     */
    val X9U_IN_SULTRA = PackageSet(
        id = ID_X9U_IN_SULTRA,
        imageId = Images.ID_FIND_X9U_IN,
        sourceDir = "out/overlays_x9u_in_r70",
        files = COMMON + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD) + PackageFile("framework_patched.jar", FileRole.GUARD_JAR) +
            // 0.4.39: the SMS service centre as an international number (guest_smsc_international.py).
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR) +
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY) +
            // 0.4.37: One UI's camera, rewritten for this image (scripts/samsung-camera); 0.4.55 (r59) the
            // Galaxy S26 Ultra's own camera, a bar phone's, instead of the Z Fold8 Ultra's; 0.4.57 (r61) with
            // the system's camera icon in its notifications (fix_notification_icon.py).
            PackageFile("samcam.tar", FileRole.GUEST_FIX) +
            // 0.4.47: the Theme Store without its brand check (the Find N6 global build's APK).
            PackageFile(THEME_STORE_APK, FileRole.GUEST_FIX) +
            // 0.4.63: OPPO's AI engine for the guest's /odm (lock screen depth effect, AI features).
            PackageFile(ODM_AI, FileRole.GUEST_FIX) +
            // OneOS: the ColorOS SystemUI with the fingerprint glyph at wake and the
            // unlock wave (switcher/patches/systemui-fingerprint-wave). The set
            // carries the patched classes3.dex and the repacker; the phone appends
            // it to the image's stock SystemUI instead of downloading 127 MB.
            PackageFile("SystemUI_wave.dex", FileRole.GUEST_FIX) +
            PackageFile("OneOSWaveRepack.dex", FileRole.GUEST_FIX),
        omitted = listOf(TETHERING, WALLPAPER_GRID_RRO),
        approxBytes = 644_525_755L,
        hasReturnApp = true,
    )

    /** The Pixel sets' files (root's SET_PIXEL): the same for every Pixel image. */
    private val PIXEL_FILES: List<PackageFile> = listOf(
        PackageFile("services_patched.jar", FileRole.GUARD_JAR),
        // 0.4.24: the image's framework.jar with One UI's camera transaction codes (pixel_camera_abi.py);
        // 0.4.45 (r3) also Samsung IMS's framework members (guest_secims_members.py).
        PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
        // 0.4.45 (r3): the SMS service centre as an international number (guest_smsc_international.py),
        // with Samsung IMS (the secims carve-out in services_patched.jar): AT&T on a Z Fold8 had no IMS,
        // so no VoLTE and SMS refused (report d4c481b6).
        PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
        // 0.4.47 (r4): the image's native camera client with One UI's transaction codes (pixel_camera_native.py).
        PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
        PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
        PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
        PackageFile("guards.txt", FileRole.GUARDS),
        PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
        PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
        PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
        PackageFile("OneOSPixelStatusBar.apk", FileRole.RRO),
        // 0.4.59 (r11/r12): AOD, Pixel's doze service in a static framework overlay (switcher/overlays/pixel_doze).
        PackageFile("OneOSPixelDoze.apk", FileRole.RRO),
        PackageFile(GUEST_APP, FileRole.GUEST_APP),
        // 0.4.47 (r4): One UI's camera, rewritten for the image (scripts/samsung-camera/build-cached.sh);
        // 0.4.57 with the system's camera icon in its notifications (fix_notification_icon.py).
        PackageFile("samcam.tar", FileRole.GUEST_FIX),
    ) + (COMMON_PAYLOADS + listOf("cellbroadcast", "bt", "nfcservices", "telephonycore", "conscrypt", "profiling", "gmssystem"))
        .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) }

    /**
     * The fold hinge for a Pixel 11 Fold guest (pull request #1): Pixel's
     * SystemUIGoogle with the adapter that reads Samsung's folding-angle sensor
     * through the system-UID relay (fold8_pixel.sh), the relay, and an RRO
     * turning on the unfold transition and its hinge-angle gate.
     */
    /**
     * Double tap to sleep on the bar Pixel images (0.4.59): the image's own SystemUIGoogle with the
     * two hooks (switcher/patches/pixel-bar/build-systemui-bar.py) and its own Pixel Launcher
     * (pixel-launcher/build-launcher.py), bound by fold8_pixel.sh over the exact donors only.
     */
    private val PIXEL_DT2S: List<PackageFile> = listOf(
        PackageFile("OneOSPixelSystemUI.apk", FileRole.GUEST_FIX),
        PackageFile("OneOSPixelLauncher.apk", FileRole.GUEST_FIX),
    )

    private fun pixelHinge(unfoldRro: String): List<PackageFile> =
        listOf("Fold8PixelSystemUI.apk", "Fold8AngleRelay.dex", unfoldRro).map { PackageFile(it, FileRole.GUEST_FIX) } +
            // 0.4.59 (r11): the device state policy without tent mode (scripts/patch-yogi-tent.py: the inner
            // panel came on only fully open) and the boot animation on every panel
            // (scripts/patch-bootanim-multidisplay.py: folded, the cover stayed black).
            PackageFile("yogi-services_patched.jar", FileRole.FRAMEWORK_JAR) +
            PackageFile("libbootanimation_preapex_patched.so", FileRole.GUEST_FIX) +
            // 0.4.59 (r12): Pixel Launcher with double tap to sleep on the home screen
            // (switcher/patches/pixel-launcher; the lock screen's is in Fold8PixelSystemUI.apk).
            PackageFile("OneOSPixelLauncher.apk", FileRole.GUEST_FIX)

    /**
     * Pixel 11 Fold image, Z Fold (F8U) (0.3.7), from out/overlays_pixel_f8u
     * (out/overlays_pixel_yogi plus the hinge, scripts/make-fold8-pixel.py --variant f8u):
     * exactly what a Pixel session uses (guest_prepare.sh). Guarded:
     * services_patched.jar with the guest vold as "gvld" (vold_patched,
     * service.incremental_patched.so). The signal poll (oneos-telephony.jar,
     * its .sha256 and OneOSPhoneInjection.apk), Pixel's status bar padding RRO
     * and OneOSGuest.apk. 22 APEX payloads: the 15 of every set, Google's
     * cellbroadcast, bt and nfcservices modules, the image's own telephonycore,
     * conscrypt and profiling (it has no platform framework-telecom.jar), and
     * GmsCore. No oplus jars, surfaceflinger or fold grid: the image has no
     * oplus-services.jar, Google's surfaceflinger is not patched, the grid is
     * for ColorOS's wallpaper app.
     */
    val PIXEL_F8U = PackageSet(
        id = ID_PIXEL_F8U,
        imageId = Images.ID_PIXEL_YOGI,
        sourceDir = "out/overlays_pixel_f8u_r17",
        // 0.4.59 (r7): Nothing OS's per-panel cutout for this phone (switcher/overlays/fold_display_cutout):
        // without it Pixel's cover had no cutout, its icons in the camera band and app headers under it.
        files = PIXEL_FILES + pixelHinge("OneOSPixelUnfold.apk") + PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
        omitted = listOf(TETHERING),
        approxBytes = 708_239_363L,
        hasReturnApp = true,
    )

    /**
     * Pixel 11 Pro image, Galaxy S26 Ultra (0.4.10), from out/overlays_pixel_kodiak:
     * the Pixel set's files, built from that image (all the guards, the guest
     * vold as gvld, the signal poll, the status bar padding RRO, GmsCore).
     */
    val PIXEL_SULTRA = PackageSet(
        id = ID_PIXEL_SULTRA,
        imageId = Images.ID_PIXEL_KODIAK,
        sourceDir = "out/overlays_pixel_kodiak_r16",
        files = PIXEL_FILES + PIXEL_DT2S,
        omitted = listOf(TETHERING),
        approxBytes = 695_159_961L,
        hasReturnApp = true,
    )

    /** Pixel's base payloads plus the hinge, with the Fold8's unfold RRO (its measured 48dp bar and AOD too). */
    val PIXEL_F8 = PackageSet(
        id = ID_PIXEL_F8,
        imageId = Images.ID_PIXEL_YOGI,
        sourceDir = "out/overlays_pixel_fold8_r17",
        files = PIXEL_FILES + pixelHinge("Fold8PixelUnfold.apk"),
        omitted = listOf(TETHERING),
        approxBytes = 708_230_732L,
        hasReturnApp = true,
    )

    /**
     * Pixel 9 Pro XL image, Galaxy S25 Ultra, S25, S25+ and S24 Ultra (0.4.22), from
     * out/overlays_pixel_komodo: the Pixel set's files, built from that image (all
     * the guards, the guest vold as gvld, the signal poll, the status bar padding
     * RRO, GmsCore). Its services.jar keeps the OneOS classes in a dex of their
     * own (scripts/make-overlays.sh: classes2 was past 65536 method references).
     */
    val PIXEL9_SULTRA = PackageSet(
        id = ID_PIXEL9_SULTRA,
        imageId = Images.ID_PIXEL_KOMODO,
        sourceDir = "out/overlays_pixel_komodo_r16",
        // 0.4.47: this image's libcameracompatbilityinfo.so needs One UI's codes too (the Pixel 11 images' agree).
        files = PIXEL_FILES + PIXEL_DT2S + PackageFile("libcameracompatbilityinfo_patched.so", FileRole.GUARD_LIBRARY),
        omitted = listOf(TETHERING),
        approxBytes = 703_551_633L,
        hasReturnApp = true,
    )

    /**
     * Infinity-X 4.1, the Find X9 Ultra build, on every phone (0.4.27), from
     * out/overlays_infinityx: an AOSP-built system with OPPO's framework jars, so
     * it takes from both sides. Guarded: services_patched.jar and
     * oplus-services_patched.jar with every guard (and the wipe guard, which its
     * duress-PIN wipe needs), the guest vold as gvld for its own vold build, and
     * One UI's camera transaction codes in framework_patched.jar and
     * libcamera_client_patched.so. The AOSP signal poll (no
     * oplus-telephony-common.jar), the IMS extension backoff, OneOSGuest.apk and
     * 21 APEX payloads: the 15 of every set, its bt and nfcservices modules, its
     * telephonycore, conscrypt and profiling (no platform framework-telecom.jar,
     * as Pixel) and GmsCore (its gmssystem APEX, Pixel's layout). No
     * surfaceflinger (no QTI composer client in it). Its cellbroadcast module is
     * left out (0.4.28): built from source, it is signed with the build's
     * networkstack key, and with One UI's tethering and NetworkStack in the
     * guest system_server died on "Signature mismatch on system package
     * com.android.cellbroadcastservice for shared user android.uid.networkstack"
     * (S25 Ultra session 26ea59af). The guest keeps One UI's, as for tethering.
     */
    val INFINITYX = PackageSet(
        id = ID_INFINITYX,
        imageId = Images.ID_INFINITYX,
        sourceDir = "out/overlays_infinityx_r14",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("oplus-services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            // 0.4.55 (r4): the SMS service centre as an international number (guest_smsc_international.py).
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            // 0.4.33: the status bar's corner padding, as on the Pixel images (r2).
            PackageFile("OneOSPixelStatusBar.apk", FileRole.RRO),
            // 0.4.55 (r4): One UI's camera, the Galaxy S26 Ultra's, rewritten for this image; 0.4.57 (r5)
            // with the system's camera icon in its notifications (fix_notification_icon.py).
            PackageFile("samcam.tar", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "telephonycore", "conscrypt", "profiling", "gmssystem"))
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        omitted = listOf(TETHERING, CELLBROADCAST),
        approxBytes = 616_237_045L,
        hasReturnApp = true,
    )

    /**
     * HyperOS image (docs/hyperos.md), made for the Z Fold (F8U) and from 0.4.31 on every phone, from
     * out/overlays_hyperos_r10: services_patched.jar and Xiaomi's two guarded
     * jars (miui-services, apprecovery.proinstaller), framework.jar with One
     * UI's camera status format, miui-wifi-service.jar with checked HAL
     * extension casts, miui-telephony-common.jar without an IMS phone, the signal poll, the QTI IMS bind backoff,
     * socket_exec (starts hyos_spawner, which runs the launcher; r9: with --seqpacket, unused since run 12),
     * libaudiohal_aidl_patched.so (the guest audioserver without an audio
     * HAL adapter vendor extension), OneOSGuest.apk and the 16 APEX payloads
     * guest_prepare.sh mounts from this image (the 15 of every set and bt).
     * r7: the guest vold as "gvld" (vold_patched, service.incremental_patched.so;
     * services and miui-services look up gvld), so Back to One UI returns in place.
     * r8: services.jar's second built-in panel (the fold's cover) neither private nor
     * own-content-only (patches/qti_builtin_display_public.py).
     * r10 (0.4.31): One UI's camera transaction codes in framework_patched.jar
     * (patches/pixel_camera_abi.py) and libcamera_client_patched.so, the native
     * camera client with them (patches/pixel_camera_native.py); OneOSGuest.apk 0.2.
     */
    val HYPER_F8U = PackageSet(
        id = ID_HYPER_F8U,
        imageId = Images.ID_HYPEROS_LHASA,
        sourceDir = "out/overlays_hyperos_r25",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("apprecovery.proinstaller_patched.jar", FileRole.GUARD_JAR),
            // 0.4.57 (r15): also Samsung IMS's framework members (guest_secims_members.py).
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-wifi-service_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            // 0.4.37: SurfaceFlinger with the mode group read whole (patches/hyperos_sf_group.py).
            PackageFile("libsurfaceflinger_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("socket_exec", FileRole.GUEST_FIX),
            PackageFile("libaudiohal_aidl_patched.so", FileRole.GUEST_FIX),
            // 0.4.33: the wallpaper app starts on a one-panel phone (r11).
            PackageFile("MiWallpaper_patched.apk", FileRole.GUEST_FIX),
            // 0.4.59 (r16): the SMS fixes every other system has (guest_smsc_international.py,
            // guest_sms_invalid_response.py), and Samsung Camera: the Z Fold8 Ultra's for the folds,
            // the Galaxy S26 Ultra's for the bar phones (guest_prepare.sh picks it by form).
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("samcam.tar", FileRole.GUEST_FIX),
            PackageFile("samcam_bar.tar", FileRole.GUEST_FIX),
            // 0.4.70 (r25): Xiaomi's VendorRIL takes a HIDL radio (patches/hyperos_hidl_radio.py; the
            // MediaTek A phones had no SIM, waiting for Xiaomi's AIDL rild).
            PackageFile("xiaomi-opt-telephony_patched.jar", FileRole.FRAMEWORK_JAR),
        ) + (COMMON_PAYLOADS + "bt").map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        omitted = listOf(TETHERING),
        approxBytes = 628_211_783L,
        hasReturnApp = true,
    )

    /**
     * Nothing OS 5.0 (0.4.33), out/overlays_nothing_r11. The smallest set so far:
     * Nothing's system is close enough to AOSP that only services.jar and
     * framework.jar need the guards. It does have a vendor framework jar,
     * nt-services.jar (system_server's class path, first run 2026-10-30), but
     * unlike oplus-services.jar and miui-services.jar nothing in it reaches
     * storage directly: its only "vold" is the property prefix "persist.vold."
     * in NtOnlineConfigHelper, and its one StorageManager use is the framework
     * API (checkPermissionReadImages in the lock-screen wallpaper), which goes
     * through the guarded StorageManagerService. So it is left as it is.
     * r2 adds the guest vold:
     * its build is in make-overlays.sh's table from 0.4.33, so the guest
     * registers "gvld" and Back to One UI returns in place, without a reboot.
     *
     * Not in it, each for a reason make-overlays.sh reported rather than failed on:
     * - gmssystem_payload.img: its GmsCore is an ordinary priv-app, not an APEX
     *   to present, so Google services are hideable ([ImageRef.gmsHideable]).
     * It is the first set to carry surfaceflinger_patched for a non-ColorOS image.
     */
    val NOTHING_F8U = PackageSet(
        id = ID_NOTHING_F8U,
        imageId = Images.ID_NOTHING_METROID,
        sourceDir = "out/overlays_nothing_r32",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            // 0.4.57 (r23): also Samsung IMS's framework members (guest_secims_members.py).
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("surfaceflinger_patched", FileRole.SURFACEFLINGER),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("nt-telephony-common_patched.jar", FileRole.FRAMEWORK_JAR),
            // The split shade in portrait on a tablet-width panel, which this
            // image only has a landscape value for, and the two panels' own
            // cutouts (the inner one has none on this phone).
            PackageFile("OneOSTabletQs.apk", FileRole.RRO),
            // Quick settings at the screen's own density on the inner panel
            // (r12): Nothing draws them as if every screen were 420 dp wide,
            // 859 dpi there, and half the panel was off the screen.
            PackageFile("SystemUI_patched.apk", FileRole.GUEST_FIX),
            // The app drawer's category boxes per row from the width (r13): two
            // per row on any screen made boxes of about 1000 x 1100 px there.
            PackageFile("NothingLauncher3_patched.apk", FileRole.GUEST_FIX),
            // Nothing's ringtone kits from its own vendor image (r17): the
            // ringtone generator composes every ringtone from them.
            PackageFile("nothing_customringtone.tar", FileRole.GUEST_FIX),
            // Nothing's own sounds (ringtones, notifications, alarms, UI) from
            // its vendor image's product/media (r17); its haptic patterns are in
            // the ringtone kit tar.
            PackageFile("nothing_product_media.tar", FileRole.GUEST_FIX),
            // The boot animation on both panels (r17): built for the first
            // display only, it played on the inner panel with the phone folded.
            PackageFile("libbootanimation_preapex_patched.so", FileRole.GUEST_FIX),
            // The ringtone generator's haptic library reading an OneOS prop for
            // its Nothing device check (r17): the Fold's own name stopped it.
            PackageFile("NothingGenerateRingtoneService_patched.apk", FileRole.GUEST_FIX),
            // The signal poll (r11): Samsung's RIL sends no signal strength
            // indication, so the bar stayed at its first reading. The RRO goes
            // in /oem, the last in this guest's overlay order (run 10), where it
            // outranks the image's own product/overlay/TelephonyResCommon_Sys.apk
            // injection config (Qualcomm's factory, which crash-looped the phone).
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            // About phone with the phone's own hardware, cameras and picture (r17).
            PackageFile("OneOSNtAbout.apk", FileRole.RRO),
            // The same on the other Nothing phones (0.4.35): their own pictures and lenses.
            PackageFile("OneOSNtAboutFold8.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutPhone.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutS26U.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutFlip.apk", FileRole.RRO),
            // Essential Space on a double press of power (no Essential key here).
            PackageFile("OneOSNtEssentialKey.apk", FileRole.RRO),
            // One UI's brightness range for the slider (Nothing's reached 2600 nits).
            PackageFile("OneOSBrightnessRange.apk", FileRole.RRO),
            // One UI's camera, rewritten for this image (scripts/samsung-camera,
            // 0.4.35): guest_prepare.sh unpacks it into the stage's samcam_build.
            PackageFile("samcam.tar", FileRole.GUEST_FIX),
            // 0.4.55: the Galaxy S26 Ultra's camera for the bar phones and flips (guest_prepare.sh picks it by form).
            // 0.4.57 (r23): both with the system's camera icon in their notifications (fix_notification_icon.py).
            PackageFile("samcam_bar.tar", FileRole.GUEST_FIX),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) }
            + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD),
        omitted = listOf(TETHERING),
        approxBytes = 908_819_304L,
        hasReturnApp = true,
    )

    /**
     * OxygenOS 16 for One UI 8 phones (0.4.67, experimental): ColorOS's common files (the image has
     * oplus-services.jar; make-overlays.sh with ONEOS_NO_CAMERA_ABI=1 and One UI 8.5's installd table),
     * the conscrypt and profiling payloads it carries, no camera bridge yet (no One UI 8 camera tables
     * on the server). r2 (0.4.69): the guest vold as "gvld" (vold_patched, service.incremental_patched.so,
     * the gvld lookups in both guard jars; make-overlays.sh pins the CPH2745 binaries), so the return no
     * longer reboots on "vold is not registered" (0.4.67 S22 Ultra 96977dcc, A34 deb8690c).
     */
    val OXYGEN16 = PackageSet(
        id = ID_OXYGEN16,
        imageId = Images.ID_OXYGEN16,
        sourceDir = "out/overlays_oxygen16_r2",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("oplus-services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("oplus-telephony-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("surfaceflinger_patched", FileRole.SURFACEFLINGER),
            PackageFile("guards.txt", FileRole.GUARDS),
        ) + (COMMON_PAYLOADS + listOf("cellbroadcast", "conscrypt", "profiling")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        omitted = listOf(TETHERING, WALLPAPER_GRID_RRO, "OneOSFoldCutout.apk", "OneOSTabletQs.apk", "oneos-apex-requires.txt"),
        approxBytes = 335_237_611L,
        hasReturnApp = true,
    )

    /**
     * OriginOS 7 (0.4.73, experimental): vivo's CN PD2609MA build on the Snapdragon S25/S26 series and the
     * Z Fold7/8 phones (0.4.82: also the Snapdragon S24 and S23 phones, 0.4.83 the Exynos S24 and S24+, the same set). Set r17 (out/overlays_originos_cn_r17: make-overlays.sh with the CN vendor's
     * vivo_config.ini; vivo_guards.py, vivo_brightness.py and the other vivo patches; the fold cutout overlay
     * with the cover's lens): its own services, vivo-services, framework and telephony jars, the guest vold as
     * gvld, vivo's display/input/Bluetooth/composer libraries, the patched launcher, vivo's feature list, the
     * signal poll, the image's own APEX payloads (gmssystem: Play services) and the camera client.
     */
    val ORIGINOS = PackageSet(
        id = ID_ORIGINOS,
        imageId = Images.ID_ORIGINOS7,
        sourceDir = "out/overlays_originos_cn_r17",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vivo-services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vivo-telephony-common-platform-ex_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework-adapter_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("vivo-framework_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("vivo-service-wifi_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("vivo-service-wifi-ex-impl_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("framework-wifi_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("surfaceflinger_patched", FileRole.SURFACEFLINGER),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("BBKLauncher2_patched.apk", FileRole.GUEST_FIX),
            PackageFile("BBKLauncher2_patched.apk.src_sha256", FileRole.GUEST_FIX),
            PackageFile("oneos-vivo-features.txt", FileRole.GUEST_FIX),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
            PackageFile("libandroid_servers_patched.so", FileRole.GUEST_FIX),
            PackageFile("libbluetooth_jni_patched.so", FileRole.GUEST_FIX),
            PackageFile("libcomposer_ext_patched.so", FileRole.GUEST_FIX),
            PackageFile("libinputflinger_patched.so", FileRole.GUEST_FIX),
            PackageFile("libinputservice_patched.so", FileRole.GUEST_FIX),
            PackageFile("libsensorservice_patched.so", FileRole.GUEST_FIX),
            PackageFile(GMS_PAYLOAD, FileRole.APEX_PAYLOAD),
            PackageFile(TETHERING, FileRole.APEX_PAYLOAD),
        ) + (COMMON_PAYLOADS + listOf("bt", "conscrypt", "crashrecovery", "profiling", "telephonycore", "wifi")).distinct()
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        omitted = listOf(WALLPAPER_GRID_RRO, "OneOSTabletQs.apk"),
        approxBytes = 875_233_991L,
        hasReturnApp = true,
    )

    val ALL: List<PackageSet> = listOf(N6_GLOBAL_F8, N6_F8U, X9U_IN_SULTRA, PIXEL_F8U, PIXEL_SULTRA, PIXEL_F8, PIXEL9_SULTRA, INFINITYX, HYPER_F8U, NOTHING_F8U, OXYGEN16, ORIGINOS)

    fun byId(id: String, sets: List<PackageSet> = ALL): PackageSet? = sets.firstOrNull { it.id == id }
}

/**
 * `<sha256>  <name>` lines, as sha256sum prints them (a `*` before the name,
 * binary mode, is accepted). Used for packages/<set>.sha256, guards.txt and
 * `$STAGE/files.sha256`. Lines starting with `#` are comments; names are flat
 * (no `/`, no leading `.`, no spaces).
 */
object ShaList {
    data class Parsed(val entries: Map<String, String>, val problems: List<String>)

    private val LINE = Regex("""^([0-9a-fA-F]{64}) [ *](\S+)$""")
    private val NAME = Regex("""^[A-Za-z0-9_][A-Za-z0-9._+-]*$""")

    fun parse(text: String): Parsed {
        val entries = linkedMapOf<String, String>()
        val problems = mutableListOf<String>()
        text.lineSequence().forEachIndexed { i, raw ->
            val line = raw.removeSuffix("\r")
            if (line.isBlank() || line.startsWith("#")) return@forEachIndexed
            val m = LINE.matchEntire(line)
            if (m == null) {
                problems += "line ${i + 1} is not '<sha256>  <name>'"
                return@forEachIndexed
            }
            val name = m.groupValues[2]
            if (!NAME.matches(name)) {
                problems += "line ${i + 1}: '$name' is not a flat file name"
                return@forEachIndexed
            }
            if (name in entries) problems += "$name listed twice"
            entries[name] = m.groupValues[1].lowercase(Locale.ROOT)
        }
        return Parsed(entries, problems)
    }

    /** sha256sum layout, sorted by name, one trailing newline. */
    fun render(entries: Map<String, String>): String =
        entries.entries.sortedBy { it.key }.joinToString("") { "${it.value}  ${it.key}\n" }
}
