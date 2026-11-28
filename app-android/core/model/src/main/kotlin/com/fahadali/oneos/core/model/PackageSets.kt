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
    /** 0.5.37: One UI 9.5 phones' camera codes (host_camera_oneui95.txt), bound in place of the One UI 9.0 ones there. */
    private val CAM95: List<PackageFile> = listOf(
        PackageFile("framework_patched_oneui95.jar", FileRole.GUARD_JAR),
        PackageFile("libcamera_client_patched_oneui95.so", FileRole.GUARD_LIBRARY),
    )
    private val CAM95_FW: List<PackageFile> = CAM95.take(1)

    const val ID_N6_F8U = "n6-f8u"
    const val ID_X9U_IN_SULTRA = "x9u-in-sultra"
    const val ID_X9U_IN_1105_SULTRA = "x9u-in-1105-sultra"
    const val ID_X9U_IN_1105_A16 = "x9u-in-1105-a16"
    const val ID_PIXEL_F8U = "pixel-f8u"
    const val ID_PIXEL_F8 = "pixel-f8"
    const val ID_PIXEL_SULTRA = "pixel-sultra"
    const val ID_HYPER_F8U = "hyper-f8u"
    const val ID_HYPER_HK = "hyper-hk"
    const val ID_PIXEL9_SULTRA = "pixel9-sultra"
    const val ID_INFINITYX = "infinityx"
    const val ID_NOTHING_F8U = "nothing-f8u"
    const val ID_NOTHING_A = "nothing-a"
    const val ID_OXYGEN16 = "oxygen16"
    const val ID_ORIGINOS = "originos"
    const val ID_LINEAGE = "lineage"
    const val ID_ONEUI95 = "oneui95"
    const val ID_ONEUI95_F8 = "oneui95-f8"
    const val ID_ONEUI95_A16 = "oneui95-a16"
    const val ID_OXYGEN17_PAD = "oxygen17pad"
    const val ID_PIXELOS = "pixelos"

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
    /**
     * 0.5.05: oplus-framework.jar with outgoing calls over IMS where the carrier asks for VoLTE
     * provisioning (patches/oplus_ims_provision.py; Samsung's IMS answers 0 and ColorOS dialled GSM:
     * Z Fold8 Spectrum 295249c3). The Find N6 sets and the November X9U set only (owner: not the
     * older X9U build, not OxygenOS).
     */
    private val OPLUS_FRAMEWORK_IMS = PackageFile("oplus-framework_patched.jar", FileRole.GUARD_JAR)

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
        sourceDir = "out/overlays_n6g_r23",
        // 0.4.37: One UI's camera transaction codes (ColorOS's ICameraDeviceUser is one code off).
        files = COMMON + OPLUS_FRAMEWORK_IMS +
            PackageFile(WALLPAPER_GRID_RRO, FileRole.RRO) + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD) +
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
            // 0.4.98 (r18): the Folds without the Fold8 rules (Fold7, Fold6, Fold5) get AOD and wallpaper AOD
            // through this SystemUI (guest_prepare.sh binds it; the Fold8s keep Fold8SystemUI.apk).
            PackageFile("ColorPanoramicSystemUI.apk", FileRole.GUEST_FIX) +
            // 0.4.47: the image's Theme Store without its brand check (DeviceChecker refused the Galaxy's brand).
            PackageFile(THEME_STORE_APK, FileRole.GUEST_FIX) +
            // 0.4.63: OPPO's AI engine for the guest's /odm (lock screen depth effect, AI features).
            PackageFile(ODM_AI, FileRole.GUEST_FIX),
        omitted = listOf(TETHERING),
        approxBytes = 763_750_051L + 12_338_345L,
        hasReturnApp = true,
    )

    /** The upstream Find N6 set plus a no-op addon slot for opt-in contributor overlays. */
    val N6_GLOBAL_F8 = PackageSet(
        id = "n6-global-f8",
        imageId = Images.ID_FIND_N6,
        sourceDir = "out/fold8-global-r0531",
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
    // 0.5.10: retired with its image (Images.RETIRED); kept as the base the 1105 set is copied from.
    val X9U_IN_SULTRA = PackageSet(
        id = ID_X9U_IN_SULTRA,
        imageId = Images.ID_FIND_X9U_IN,
        sourceDir = "out/overlays_x9u_in_r75",
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
            // 0.4.97 (r72): the image's SystemUI with wallpaper AOD without OPPO's display-panel HAL
            // (scripts/make-coloros-panoramic-aod.py; bound by guest_prepare.sh).
            PackageFile("ColorPanoramicSystemUI.apk", FileRole.GUEST_FIX),
        omitted = listOf(TETHERING, WALLPAPER_GRID_RRO),
        approxBytes = 634_332_311L + 116_537_002L,
        hasReturnApp = true,
    )

    /**
     * 0.5.02: the newer Find X9 Ultra IN build ([Images.FIND_X9U_IN_1105]): the same files as
     * [X9U_IN_SULTRA], built from that image (out/overlays_x9u_in_1105_r1: its own surfaceflinger and
     * vold pins, SystemUI and OPPO AI libraries; samcam.tar and the Theme Store are the older set's files).
     */
    val X9U_IN_1105_SULTRA = X9U_IN_SULTRA.copy(
        id = ID_X9U_IN_1105_SULTRA,
        imageId = Images.ID_FIND_X9U_IN_1105,
        // 0.5.20 (r3): fingerprint from One UI (services_patched.jar: removal guard, AIDL sensor, its place,
        // Samsung's touch request) and samcam_a.tar (the Galaxy A36's camera for this image, A and M phones).
        // 0.5.32 r8: OplusGestureUI_patched.apk, raise to wake from a Galaxy's pick-up sensor (coloros_lift_wake.py).
        // 0.5.33 r9: samcam.tar with fix_sensor_crop_tables.py (S24 FE front camera: no sensor crop table entry).
        sourceDir = "out/overlays_x9u_in_1105_r13", // 0.5.51 r13: vdcoolok's fingerprint wave in ColorPanoramicSystemUI (ultrasonic only); 0.5.21 r5: video rotation in samcam_a; 0.5.20 r4: OneOSFpTouch
        // 0.5.05 (r2): oplus-framework_patched.jar right after the common files, as root's set_files lists it.
        files = COMMON + OPLUS_FRAMEWORK_IMS + X9U_IN_SULTRA.files.drop(COMMON.size) +
            PackageFile("samcam_a.tar", FileRole.GUEST_FIX) +
            PackageFile("OplusGestureUI_patched.apk", FileRole.GUEST_FIX) +
            PackageFile("OplusGestureUI_patched.apk.src_sha256", FileRole.GUEST_FIX) + CAM95,
        approxBytes = X9U_IN_SULTRA.approxBytes + 12_546_637L + 80_261_120L + 33_762_343L + 53123975L,
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
        sourceDir = "out/overlays_pixel_f8u_r21",
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
        sourceDir = "out/overlays_pixel_kodiak_r23",
        files = PIXEL_FILES + PIXEL_DT2S + CAM95,
        omitted = listOf(TETHERING),
        approxBytes = 695_159_961L + 49701625L,
        hasReturnApp = true,
    )

    /** Pixel's base payloads plus the hinge, with the Fold8's unfold RRO (its measured 48dp bar and AOD too). */
    val PIXEL_F8 = PackageSet(
        id = ID_PIXEL_F8,
        imageId = Images.ID_PIXEL_YOGI,
        sourceDir = "out/overlays_pixel_fold8_r21",
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
        sourceDir = "out/overlays_pixel_komodo_r20",
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
        sourceDir = "out/overlays_infinityx_r23",
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
            // 0.5.52 (r22): the lock screen fingerprint ring (vdcoolok's pull request #152; OneOSGlyphView placed from
            // ro.oneos.fp_glyph) in the image's SystemUI, and services_patched.jar with the biometric removal guard.
            PackageFile("SystemUI_glyph.apk", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "telephonycore", "conscrypt", "profiling", "gmssystem"))
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } + CAM95,
        omitted = listOf(TETHERING, CELLBROADCAST),
        approxBytes = 616_237_045L + 45904223L + 66_685_890L,
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
        sourceDir = "out/overlays_hyperos_r33",
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
        ) + (COMMON_PAYLOADS + "bt").map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } + CAM95,
        omitted = listOf(TETHERING),
        approxBytes = 628_211_783L + 52133799L,
        hasReturnApp = true,
    )

    /**
     * HyperOS 4 Global (0.5.27), out/overlays_hyperos_hk_r2: [Images.HYPEROS_HONGKONG], Xiaomi's OS4.0.5.0.XFRMIXM.
     * The HyperOS guards as in [HYPER_F8U] plus miui-framework.jar (DisplayFeatureManager without Xiaomi's
     * displayfeature service), the guest vold as gvld, SurfaceFlinger with the mode group read whole, One UI's
     * camera for the phones (samcam.tar, samcam_a.tar for the A and M phones, samcam_bar.tar) and its stub
     * app (OneOSCameraProcessingStub.apk), the fold cutout overlay, the apex requirement list, and the 18 APEX
     * payloads (the 15 of every set, bt, cellbroadcast and gmssystem: GmsCore, presented as on the One UI 9.5
     * image). Tethering never mounts.
     */
    val HYPER_HK = PackageSet(
        id = ID_HYPER_HK,
        imageId = Images.ID_HYPEROS_HONGKONG,
        sourceDir = "out/overlays_hyperos_hk_r7",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("apprecovery.proinstaller_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-wifi-service_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("miui-framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libsurfaceflinger_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("socket_exec", FileRole.GUEST_FIX),
            PackageFile("libaudiohal_aidl_patched.so", FileRole.GUEST_FIX),
            PackageFile("OneOSCameraProcessingStub.apk", FileRole.GUEST_FIX),
            PackageFile("samcam.tar", FileRole.GUEST_FIX),
            PackageFile("samcam_a.tar", FileRole.GUEST_FIX),
            PackageFile("samcam_bar.tar", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "cellbroadcast", "gmssystem")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } + CAM95,
        omitted = listOf(TETHERING),
        approxBytes = 866_589_706L + 52343413L,
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
        sourceDir = "out/overlays_nothing_r43", // 0.5.17 r36: fingerprint from One UI, removal guard
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
            + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD) + CAM95,
        omitted = listOf(TETHERING),
        approxBytes = 908_819_304L + 50399950L,
        hasReturnApp = true,
    )

    /**
     * Nothing OS 5.0 for the Galaxy A series (0.5.15, untested): [Images.NOTHING_ASTEROIDS], the Phone
     * (3a) build. make-overlays.sh on that image (vold and SurfaceFlinger pinned for it; its
     * service.incremental.so and crashrecovery APEX are Metroid's), the same Nothing fixes as
     * [NOTHING_F8U] (SystemUI, launcher, About pages, signal poll, Essential key), and:
     * - no ringtone generator or kits: this build has no NothingGenerateRingtoneService; Nothing's
     *   sounds come from nothing_product_media.tar (Metroid's vendor product/media, the same family);
     * - OneOSBrightnessRange34.apk, the slider's range for panels at One UI brightnessMaximum about 3.4
     *   (guest_prepare.sh picks it from One UI's value; the Fold's range topped out at two thirds);
     * - samcam_a.tar, the Galaxy A36's own camera rewritten for this image (video without
     *   libmediaresourcehelper);
     * - GmsCore from its gmssystem APEX, presented as on the Pixel images.
     */
    val NOTHING_A = PackageSet(
        id = ID_NOTHING_A,
        imageId = Images.ID_NOTHING_ASTEROIDS,
        sourceDir = "out/overlays_nothing_a_r8", // 0.5.21 r6: video rotation in samcam_a; 0.5.18 r5: OneOSSehTouch (TEST, not uploaded yet); 0.5.17 r2: fingerprint from One UI, removal guard
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("surfaceflinger_patched", FileRole.SURFACEFLINGER),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("nt-telephony-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("OneOSTabletQs.apk", FileRole.RRO),
            PackageFile("SystemUI_patched.apk", FileRole.GUEST_FIX),
            PackageFile("NothingLauncher3_patched.apk", FileRole.GUEST_FIX),
            PackageFile("nothing_product_media.tar", FileRole.GUEST_FIX),
            PackageFile("libbootanimation_preapex_patched.so", FileRole.GUEST_FIX),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("OneOSNtAbout.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutFold8.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutPhone.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutS26U.apk", FileRole.RRO),
            PackageFile("OneOSNtAboutFlip.apk", FileRole.RRO),
            PackageFile("OneOSNtEssentialKey.apk", FileRole.RRO),
            PackageFile("OneOSBrightnessRange.apk", FileRole.RRO),
            PackageFile("OneOSBrightnessRange34.apk", FileRole.RRO),
            PackageFile("samcam_a.tar", FileRole.GUEST_FIX),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "gmssystem")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) }
            + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD),
        omitted = listOf(TETHERING),
        approxBytes = 924_702_781L,
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
        sourceDir = "out/overlays_oxygen16_r3",
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
     * OxygenOS 17 for tablets (0.5.41, testing; [Images.OXYGEN17_PAD], the Galaxy Tab profiles only): make-overlays.sh on
     * the OnePlus Pad 4 image (out/overlays_oxygen17pad_r1: the guard jars, the guest vold as gvld (the Find X9 Ultra IN
     * layout), SurfaceFlinger without the QTI composer client, One UI's camera codes, the SMS centre, OPPO's IMS
     * provisioning, raise to wake from a Galaxy's pick-up sensor, the OneOS app and 16 APEX payloads).
     */
    val OXYGEN17_PAD = PackageSet(
        id = ID_OXYGEN17_PAD,
        imageId = Images.ID_OXYGEN17_PAD,
        sourceDir = "out/overlays_oxygen17pad_r1",
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
            OPLUS_FRAMEWORK_IMS,
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("OplusGestureUI_patched.apk", FileRole.GUEST_FIX),
            PackageFile("OplusGestureUI_patched.apk.src_sha256", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("cellbroadcast")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        omitted = listOf(TETHERING, WALLPAPER_GRID_RRO, "OneOSFoldCutout.apk", "OneOSTabletQs.apk", "oneos-apex-requires.txt"),
        approxBytes = 442_258_204L,
        hasReturnApp = true,
    )

    /**
     * OriginOS 7 (0.4.73, experimental): vivo's CN PD2609MA build on the Snapdragon S25/S26 series and the
     * Z Fold7/8 phones (0.4.82: also the Snapdragon S24 and S23 phones, 0.4.83 the Exynos S24 and S24+, the same set). Set r18 (out/overlays_originos_cn_r18, 0.4.95: r17 with the guest's own screen lock in services_patched.jar; r17: make-overlays.sh with the CN vendor's
     * vivo_config.ini; vivo_guards.py, vivo_brightness.py and the other vivo patches; the fold cutout overlay
     * with the cover's lens): its own services, vivo-services, framework and telephony jars, the guest vold as
     * gvld, vivo's display/input/Bluetooth/composer libraries, the patched launcher, vivo's feature list, the
     * signal poll, the image's own APEX payloads (gmssystem: Play services) and the camera client.
     */
    val ORIGINOS = PackageSet(
        id = ID_ORIGINOS,
        imageId = Images.ID_ORIGINOS7,
        sourceDir = "out/overlays_originos_cn_r26",
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
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } + CAM95,
        omitted = listOf(WALLPAPER_GRID_RRO, "OneOSTabletQs.apk"),
        approxBytes = 875_233_991L + 56044939L,
        hasReturnApp = true,
    )

    /**
     * LineageOS 24 (0.5.06, experimental), the OnePlus 15 (infiniti) nightly of 2026-11-11, on every phone that offers
     * it, from out/overlays_lineage_r1: a source-built AOSP system like Infinity-X, but without OPPO's jars (no
     * oplus-services_patched.jar) and with no samcam.tar. services_patched.jar and framework_patched.jar with
     * the guards and One UI's camera codes (libcamera_client_patched.so), the guest vold as gvld, the IMS extension
     * backoff, the AOSP signal poll, OneOSGuest.apk, the fold and tablet overlays and 20 APEX payloads (the
     * 15 of every set and the bt, nfcservices, telephonycore, conscrypt and profiling modules). No gmssystem
     * payload: the image has no Google apps, so guest_google.sh (FULL mode, keyed on this set's id) lays One UI's
     * Play services, Play Store and Services Framework over the guest's product partition at session time.
     * Neither tethering nor the cellbroadcast module (source-built, signed with the build's networkstack key; One UI's
     * stays, as for Infinity-X).
     */
    val LINEAGE = PackageSet(
        id = ID_LINEAGE,
        imageId = Images.ID_LINEAGE,
        sourceDir = "out/overlays_lineage_r14", // 0.5.21 r8: video rotation in samcam_a and samcam_bar
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("OneOSPixelStatusBar.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("OneOSTabletQs.apk", FileRole.RRO),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "telephonycore", "conscrypt", "profiling"))
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } +
            // 0.5.06 r2: AOD (SystemUI's doze service at boot), the Pixel sets' overlay.
            PackageFile("OneOSPixelDoze.apk", FileRole.RRO) +
            // 0.5.07 r3: the boot animation on every panel (patch-bootanim-multidisplay.py, Lineage's form).
            PackageFile("libbootanimation_preapex_patched.so", FileRole.GUEST_FIX) +
            // 0.5.14 r6: Samsung Camera (guest_prepare.sh picks one per phone): the Galaxy A36's own for the A and M
            // phones (samcam_a.tar), the S26 Ultra's for the bar phones (samcam_bar.tar); and the current guest app,
            // which knows LineageOS (r5's showed the ColorOS artwork).
            PackageFile("samcam_a.tar", FileRole.GUEST_FIX) +
            PackageFile("samcam_bar.tar", FileRole.GUEST_FIX) + CAM95,
        omitted = listOf(TETHERING, CELLBROADCAST),
        approxBytes = 387_175_398L + 8_538L + 118_120L + 80_261_120L + 78_120_960L + 45756789L,
        hasReturnApp = true,
    )

    /**
     * One UI 9.5 for the phones on One UI 9 (0.5.22, untested): [Images.ONEUI95], the Galaxy S26 Ultra build
     * (S948BXXU6ZZKN). make-overlays.sh on that image (r1): the guard jars and One UI's camera codes, the
     * signal poll, OneOSGuest.apk, the 22 APEX payloads (the 15 of every set and bt, nfcservices, gmssystem,
     * npumanager, telephonycore, webapp and the cellbroadcast module), and oneui_floating_add.txt, the image's
     * software floating features for guest_prepare.sh's merge. No guest vold or SurfaceFlinger patch in
     * this set. Tethering never mounts. r2 (0.5.23): framework_patched.jar with Privacy Display off
     * (patches/oneui_no_privacy_display.py; the S26 Ultra panel feature, on in the image at build time).
     * r4: framework_patched.jar also turns the engmode client off where the phone's VINTF lacks
     * ISehEngmode/default (patches/oneui_engmode_undeclared.py; the S23 family waited forever for it).
     * r9 (0.5.32): samcam_a_oneui.tar, the Galaxy A36's own Samsung Camera (and the five libraries the image
     * lacks), bound by guest_prepare.sh over the image's S26 Ultra camera on Galaxy A and M phones (A17: the
     * S26 Ultra's camera died at launch in its resolution table).
     * r10 (0.5.33): the guest vold as "gvld" (vold_patched, service.incremental_patched.so, services_patched.jar
     * and framework_patched.jar through patches/guest_own_vold.py, --framework for Samsung's AppLockPolicy), so
     * One UI's vold keeps its names all session: every One UI 9.5 return had rebooted ("vold is not registered
     * now", 13 reports).
     */
    val ONEUI95 = PackageSet(
        id = ID_ONEUI95,
        imageId = Images.ID_ONEUI95,
        sourceDir = "out/overlays_oneui95_r12",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcameracompatbilityinfo_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
            PackageFile("oneui_floating_add.txt", FileRole.GUEST_FIX),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("OneOSPixelStatusBar.apk", FileRole.RRO),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            PackageFile("samcam_a_oneui.tar", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "gmssystem", "npumanager", "telephonycore", "webapp")).map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) }
            + PackageFile(CELLBROADCAST, FileRole.APEX_PAYLOAD) + CAM95_FW,
        omitted = listOf(TETHERING),
        approxBytes = 584_720_823L + 77_086_720L + 1_542_200L + 1_813_456L + 58981151L,
        hasReturnApp = true,
    )

    /**
     * One UI 9.5 on the Galaxy Z Fold8 only (0.5.35, Josh's pull request #328, r24): [ONEUI95]'s files with his Fold8
     * framework resources (Fold8OneUI95Framework.apk), SystemUI, Settings, Home and services.jar for the Fold8's two
     * panels, his framework_patched.jar (the Fold8's PDI fallback, gated on its model) and his guest app; the other
     * phones keep [ONEUI95] and never download these 333 MB (owner: "keep fold8 fixes fold8 only"). guest_prepare.sh
     * uses them only on profile f8 with the pinned donor. Built from the r10 folder plus the files of release
     * thatjoshguy67/OneOS-files fold8-oneui95-r24, each checked against the pull request's pins.
     */
    val ONEUI95_F8 = ONEUI95.copy(
        id = ID_ONEUI95_F8,
        sourceDir = "out/overlays_oneui95_f8_r3",
        files = listOf(
            PackageFile("Fold8OneUI95Framework.apk", FileRole.RRO),
            PackageFile("Fold8OneUI95SystemUI.apk", FileRole.GUEST_FIX),
            PackageFile("Fold8OneUI95Services.jar", FileRole.GUEST_FIX),
            PackageFile("Fold8OneUI95Settings.apk", FileRole.GUEST_FIX),
            PackageFile("Fold8OneUI95Home.apk", FileRole.GUEST_FIX),
        ) + (ONEUI95.files - CAM95_FW.toSet()),
        approxBytes = ONEUI95.approxBytes + 333_304_867L - 58981151L,
    )

    /**
     * The image's own modules a One UI 8 phone (Android 16) cannot lend an Android 17 guest ([ONEUI95_A16]):
     * the S22's guest zygote died preloading libandroid.so on One UI 8's tethering module
     * ("cannot locate symbol AConnectivityNative_getNetworkBlockedReason", 0827ba2a), and the framework calls
     * the newer APIs of the others. oneui8test4: uprobestats too (bff57950: the zygote died in
     * SystemServiceRegistry on UprobestatsFrameworkInitializer, which only the image's module has on the boot class
     * path; the image's statsd needs its libuprobestats_client.so). One UI's adbd, virt and VNDK stay.
     * oneui8test5: not tethering. Its BPF maps are One UI's (One UI 8's module loaded them at boot; netd runs on
     * them), and the image's Android 17 train reads another layout: system_server died creating NetworkStatsService
     * on both S22s ("Cannot open ingress discard map", ValueSize, 21540664 and efae874f). One UI's module stays, with
     * [A17_CONNECTIVITY_NATIVE] for the one symbol the image's libandroid.so needs from it.
     */
    val A16_EXTRA_PAYLOADS: List<String> = listOf(
        "conscrypt", "profiling", "os.statsd", "media", "media.swcodec", "resolv", "ipsec", "uwb",
        "devicelock", "scheduling", "neuralnetworks", "tzdata", "uprobestats",
    )

    /**
     * Samsung's own system modules of the image for [ONEUI95_A16] (oneui8test4), staged as
     * samsung.<name>_payload.img and mounted on com.samsung.android.<name>: lifeguard and shell put One UI's jars on
     * the boot and system server class paths, the others are native libraries and linker configs built against
     * the image's system (imagecodec, spqr: the image's ART libraries). One UI 8's are One UI 8 builds.
     */
    /**
     * The image's libcom.android.tethering.connectivity_native.so for [ONEUI95_A16] (oneui8test5), bound over One UI's
     * in the guest's view of One UI's tethering module: the image's libandroid.so needs
     * AConnectivityNative_getNetworkBlockedReason, which One UI 8's module (360743340 on the S22s) does not have
     * (0827ba2a, and the A35 34c9856c). It needs only libc, libm, libdl, libbinder_ndk and the module's libc++.
     */
    const val A17_CONNECTIVITY_NATIVE = "tethering_connectivity_native_a17.so"

    val A16_SAMSUNG_PAYLOADS: List<String> = listOf(
        "lifeguard", "shell", "media.imagecodec.system", "spqr", "media.extractor", "media.swcodec.system",
        "mediacontextanalyzer",
    )

    /**
     * Tester builds only (-Poneos.a17OnA16=true, oneui8test3, r2 in oneui8test4, r3 in oneui8test5, r4 in oneui8test7: the image's
     * services, framework and telephony-common guard jars also patched by a16_connectivity_compat.py): One UI 9.5 on the phones held on One UI 8.0/8.5
     * ([Profiles.withOneUi95OnA16]). [ONEUI95]'s files plus the image's own [A16_EXTRA_PAYLOADS], which
     * guest_prepare.sh mounts only in such a session (A17_ON_A16): One UI 8's are Android 16 builds. Tethering
     * too, against the One UI 9 rule (its BPF maps are One UI's loader's), as the experiment.
     */
    /** Sets only a tester build's profiles offer (no APK series packs them; a tester build packs every set). */
    val TESTER_ONLY: Set<String> = setOf(ID_ONEUI95_A16, ID_X9U_IN_1105_A16)

    val ONEUI95_A16 = ONEUI95.copy(
        id = ID_ONEUI95_A16,
        sourceDir = "out/overlays_oneui95_a16_r9",
        // No One UI 9.5 camera codes (0.5.37's CAM95_FW): they are for One UI 9.5 phones. r7 (0.5.39): One UI 8's,
        // read on the S22 Ultra (host_camera_oneui8.txt, patches/a16_camera.py), which turn the camera on there.
        // r9 (0.5.45): One UI 8.5's (host_camera_oneui85.txt, read on the S23 FE): its cameraserver takes One UI 9.0's
        // CameraCompatibilityInfo where One UI 8 has an int; the One UI 8 jar's calls all failed there.
        files = (ONEUI95.files - CAM95_FW.toSet()) + A16_EXTRA_PAYLOADS.map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } +
            A16_SAMSUNG_PAYLOADS.map { PackageFile("samsung.${it}_payload.img", FileRole.APEX_PAYLOAD) } +
            PackageFile(A17_CONNECTIVITY_NATIVE, FileRole.GUEST_FIX) + PackageFile("framework_patched_oneui8.jar", FileRole.GUARD_JAR) +
            PackageFile("framework_patched_oneui85.jar", FileRole.GUARD_JAR),
        omitted = listOf(TETHERING),
        approxBytes = ONEUI95.approxBytes - 58981151L + 98672640L - 29175808L + 20684800L + 68848L + 58981599L + 58981391L,
    )

    /**
     * ColorOS 17 (Find X9 Ultra IN) on the S22s held on One UI 8 (0.5.51, owner: "Since S22 can boot One UI 9.5 now, lets try
     * ColorOS 17 for them"; [Profiles.withColorOsOnA16]), as [ONEUI95_A16] does for One UI 9.5: [X9U_IN_1105_SULTRA]'s files
     * without One UI 9.5's camera codes, its services, framework and telephony-common guard jars also patched by
     * a16_connectivity_compat.py, the image's own [A16_EXTRA_PAYLOADS], its connectivity_native ([A17_CONNECTIVITY_NATIVE],
     * from its tethering module) and its framework with One UI 8's and One UI 8.5's camera codes (a16_camera.py).
     * guest_prepare.sh runs it as A17_ON_A16 (uprobestats_payload.img staged). Tethering stays One UI's (its BPF maps).
     */
    val X9U_A16_OWN_PAYLOADS: List<String> = listOf("nfcservices", "npumanager", "telephonycore", "webapp")

    /** Filled in when the set is built (out/overlays_x9u_in_1105_a16_r7). */
    private const val X9U_A16_APPROX_BYTES = 1_086_796_720L

    val X9U_IN_1105_A16 = X9U_IN_1105_SULTRA.copy(
        id = ID_X9U_IN_1105_A16,
        sourceDir = "out/overlays_x9u_in_1105_a16_r7",
        files = (X9U_IN_1105_SULTRA.files - CAM95.toSet()) +
            A16_EXTRA_PAYLOADS.map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } +
            PackageFile(A17_CONNECTIVITY_NATIVE, FileRole.GUEST_FIX) + PackageFile("framework_patched_oneui8.jar", FileRole.GUARD_JAR) +
            PackageFile("framework_patched_oneui85.jar", FileRole.GUARD_JAR) +
            // r2: Android's NFC and NPU manager modules (oneui95_a16_r9's): ColorOS's SystemServiceRegistry calls their
            // initializers unguarded and One UI 8 has neither (both S22 testers: zygote died, NoClassDefFoundError).
            // r3: ColorOS's own telephonycore and webapp too (TelephonyServicesInitializer, WebAppFrameworkInitializer behind
            // flags ColorOS turns on; One UI 8 has neither module; abhera on coloros22test3: zygote still died).
            X9U_A16_OWN_PAYLOADS.map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) },
        approxBytes = X9U_A16_APPROX_BYTES,
    )

    /**
     * PixelOS 17 for the Galaxy A series (0.5.35, untested): [Images.PIXELOS_ONYX], the POCO F7 / Redmi Turbo 4 Pro build,
     * a source-built AOSP system with Google's apps that the ARMv8.2 A-series CPUs can run (Google's Pixel 9 Pro XL
     * build cannot: PAuth and RCpc2 in its linker). make-overlays.sh on that image (r1): the guard jars, the guest vold
     * as "gvld" (vold_patched, service.incremental_patched.so), One UI's camera codes, the signal poll, OneOSGuest.apk
     * and 21 APEX payloads, its gmssystem among them (presented, as on the Pixel images). Neither tethering nor the
     * cellbroadcast module (source-built, as for LineageOS). No Samsung Camera tar yet.
     */
    val PIXELOS = PackageSet(
        id = ID_PIXELOS,
        imageId = Images.ID_PIXELOS_ONYX,
        sourceDir = "out/overlays_pixelos_onyx_r7",
        files = listOf(
            PackageFile("services_patched.jar", FileRole.GUARD_JAR),
            PackageFile("framework_patched.jar", FileRole.GUARD_JAR),
            PackageFile("vold_patched", FileRole.GUARD_EXECUTABLE),
            PackageFile("service.incremental_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("libcamera_client_patched.so", FileRole.GUARD_LIBRARY),
            PackageFile("telephony-common_patched.jar", FileRole.GUARD_JAR),
            PackageFile("guards.txt", FileRole.GUARDS),
            PackageFile("ims-ext-common_patched.jar", FileRole.FRAMEWORK_JAR),
            PackageFile("oneos-telephony.jar", FileRole.INJECTION_JAR),
            PackageFile("oneos-telephony.sha256", FileRole.INJECTION_SHA256),
            PackageFile("OneOSPhoneInjection.apk", FileRole.RRO),
            PackageFile(GUEST_APP, FileRole.GUEST_APP),
            // 0.5.35 r2: AOD (owner, A36, 11-21: "AOD doesnt work"; getDozeComponent()=null), as for LineageOS.
            PackageFile("OneOSPixelDoze.apk", FileRole.RRO),
            // 0.5.35 r4: One UI's slider range (owner, A36: "Lowest brightness is still not very low"), as for Nothing OS.
            PackageFile("OneOSBrightnessRange.apk", FileRole.RRO),
            PackageFile("OneOSBrightnessRange34.apk", FileRole.RRO),
            PackageFile("OneOSPixelStatusBar.apk", FileRole.RRO),
            PackageFile("OneOSFoldCutout.apk", FileRole.RRO),
            PackageFile("OneOSTabletQs.apk", FileRole.RRO),
            PackageFile("oneos-apex-requires.txt", FileRole.GUEST_FIX),
        ) + (COMMON_PAYLOADS + listOf("bt", "nfcservices", "telephonycore", "conscrypt", "profiling", "gmssystem"))
            .map { PackageFile("${it}_payload.img", FileRole.APEX_PAYLOAD) } + CAM95,
        omitted = listOf(TETHERING, CELLBROADCAST),
        approxBytes = 515_455_466L + 3 * 8_538L + 46155307L,
        hasReturnApp = true,
    )

    val ALL: List<PackageSet> = listOf(N6_GLOBAL_F8, N6_F8U, X9U_IN_1105_SULTRA, PIXEL_F8U, PIXEL_SULTRA, PIXEL_F8, PIXEL9_SULTRA, INFINITYX, HYPER_F8U, HYPER_HK, NOTHING_F8U, NOTHING_A, OXYGEN16, OXYGEN17_PAD, ORIGINOS, LINEAGE, ONEUI95, ONEUI95_F8, ONEUI95_A16, X9U_IN_1105_A16, PIXELOS)

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
