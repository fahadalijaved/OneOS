package com.fahadali.oneos.core.model

import java.util.Locale

/**
 * One image a profile may run, with the file set staged next to it (built
 * from that image by scripts/make-overlays.sh). The staged image decides the
 * set: never another set with that image, never this set with another image.
 */
data class ImageChoice(
    /** [ImageRef.id]. */
    val imageId: String,
    /** [PackageSet.id] staged next to that image on this phone. */
    val packageSetId: String,
    /** A session has run on this phone with this image; false = the untested tick at Switch. */
    val tested: Boolean,
)

/**
 * A phone this build has OS images and file sets for (build 2, AA3). A
 * phone matches only when its model number starts with [modelPrefix] AND
 * `ro.product.device` is [codename] AND its SoC model is [socModel]. The probe
 * builds matched model OR codename (the old TestedDevice), which would have
 * let an Exynos variant or a renamed model through.
 */
data class PhoneProfile(
    /** Stable id: `ONEOS_PROFILE` in session.env, the stage marker, logs. */
    val id: String,
    /** "Galaxy S26 Ultra". */
    val label: String,
    /** `SM-S948`: every regional variant (U, B, N, W, 0) starts with it. */
    val modelPrefix: String,
    /** `ro.product.device`, e.g. `m3q`. */
    val codename: String,
    /** `ro.soc.model` (or the model of `ro.board.platform` when the prop is empty), e.g. `SM8850`. */
    val socModel: String,
    /** BAR profiles get the phone form in session.env and no fold steps. */
    val form: FormFactor,
    /** The images this phone may run, each with its set (0.3.3: more than one); the first is its usual one. */
    val choices: List<ImageChoice>,
    /** False: known, but this build refuses to switch ([disabledReason] is the BLOCK). */
    val enabled: Boolean = true,
    val disabledReason: String? = null,
    /** Extra switch-time warnings for this phone (no tick needed). */
    val notes: List<Finding> = emptyList(),
) {
    fun matches(model: String, device: String, soc: String): Boolean =
        model.trim().uppercase(Locale.ROOT).startsWith(modelPrefix) &&
            device.trim().equals(codename, ignoreCase = true) &&
            soc.trim().equals(socModel, ignoreCase = true)

    fun matches(f: DeviceFacts): Boolean = matches(f.model, f.device, f.soc.model)

    /** The choice for [imageId]; null = this phone does not take that image. */
    fun choice(imageId: String): ImageChoice? = choices.firstOrNull { it.imageId == imageId }

    /** The images of [choices] this build has, in order. */
    fun images(all: List<ImageRef> = Images.ALL): List<ImageRef> = choices.mapNotNull { Images.byId(it.imageId, all) }

    /** The choice "Choose a system" preselects: the first one that has run on this phone, else the first. */
    val recommended: ImageChoice? get() = choices.firstOrNull { it.tested } ?: choices.firstOrNull()

    /** Some image has run on this phone (the device report's "Tested phone"). */
    val testedWithAnyImage: Boolean get() = choices.any { it.tested }

    /** "SM-S948* / m3q / SM8850". */
    val ids: String get() = "$modelPrefix* / $codename / $socModel"
}

/** [profile] is the one profile all three ids match; null when none (or, fail closed, more than one) does. */
data class ProfileResolution(
    val profile: PhoneProfile?,
    /** When nothing matched: the profile with the same model prefix (else codename), for the message. */
    val nearest: PhoneProfile?,
    /** What differs from [nearest], e.g. "codename pa3q (profile: m3q)". */
    val mismatches: List<String>,
)

/** The phones build 2 knows (PLAN.md "Profiles"). Built in; fix packs take this over later. */
object Profiles {
    const val ID_F8U = "f8u"
    const val ID_S_ULTRA_8850 = "s-ultra-8850"
    const val ID_S_ULTRA_8750 = "s-ultra-8750"
    const val ID_S_8750 = "s-8750"
    const val ID_FOLD7 = "f7"
    const val ID_S_PLUS_8750 = "s-plus-8750"
    const val ID_FOLD8 = "f8"
    const val ID_S_8850 = "s-8850"
    const val ID_S_8850_JP = "s-8850-jp"
    const val ID_S_PLUS_8850 = "s-plus-8850"
    const val ID_S_ULTRA_8650 = "s-ultra-8650"
    const val ID_S_8550 = "s-8550"
    const val ID_S_PLUS_8550 = "s-plus-8550"
    const val ID_S_PLUS_9965 = "s-plus-9965"
    const val ID_S_9965 = "s-9965"
    const val ID_FLIP7 = "flip7"
    const val ID_A56 = "a56"
    const val ID_A57 = "a57"
    const val ID_FLIP5 = "flip5"
    const val ID_FOLD6 = "f6"
    const val ID_A07 = "a07"
    const val ID_A06 = "a06"
    const val ID_A07_5G = "a07-5g"
    const val ID_A15 = "a15"
    const val ID_A24 = "a24"
    const val ID_A25 = "a25"
    const val ID_A33 = "a33"
    const val ID_A34 = "a34"
    const val ID_A53 = "a53"
    const val ID_E55 = "e55"
    const val ID_S_FE_9925 = "s-fe-9925"
    const val ID_S_FE_8450 = "s-fe-8450"
    const val ID_S_PLUS_9925 = "s-plus-9925"
    const val ID_S_ULTRA_9925 = "s-ultra-9925"
    const val ID_S_ULTRA_8450 = "s-ultra-8450"
    const val ID_S_ULTRA_8450_JP = "s-ultra-8450-jp"
    const val ID_FLIP8 = "flip8"
    const val ID_A36 = "a36"
    const val ID_FOLD5 = "f5"
    const val ID_S_ULTRA_8550 = "s-ultra-8550"
    const val ID_FLIP6 = "flip6"
    const val ID_S_9945 = "s-9945"
    const val ID_S_8650 = "s-8650"
    const val ID_S_EDGE_8750 = "s-edge-8750"
    const val ID_S_FE_9945 = "s-fe-9945"
    const val ID_A26 = "a26"
    const val ID_A17 = "a17"
    const val ID_A16_4G = "a16-4g"
    const val ID_A16_S166 = "a16-s166"
    const val ID_A35 = "a35"
    const val ID_A54 = "a54"
    const val ID_A27 = "a27"
    const val ID_A17_5G = "a17-5g"
    const val ID_FLIP7_FE = "flip7-fe"
    const val ID_A16 = "a16"
    const val ID_A55 = "a55"
    const val ID_S25_FE = "s25-fe"
    const val ID_S_8450 = "s-8450"
    const val ID_M55S = "m55s"
    const val ID_S_PLUS_9945 = "s-plus-9945"
    const val ID_S_ULTRA_8550_JP = "s-ultra-8550-jp"
    const val ID_S_9925 = "s-9925"
    const val ID_A16_MTK = "a16-mtk"
    const val ID_S_8550_JP = "s-8550-jp"

    /** The SM8750 and SM8650 phones' note ([PhoneProfile.notes]) and its [Finding.reason]. */
    const val ID_NOTE_OLDER_VENDOR = "profile-vendor-older"
    const val R_OLDER_VENDOR = "older-vendor"

    /** The SM8550 phones' note: the system will most likely not start there. */
    const val ID_NOTE_EXPECT_NO_START = "profile-expect-no-start"
    const val R_EXPECT_NO_START = "expect-no-start"

    /**
     * Both S Ultra profiles and the Galaxy S25: the Find X9 Ultra CN build,
     * tested on all three (owner, 2026-10-25; 0.3.3-0.3.6 also took the IN build,
     * gone in 0.3.7). The set is
     * named for the S Ultra but holds nothing per phone beyond the bar form (no
     * fold grid).
     */
    /**
     * 0.4.11: the Find X9 Ultra IN (global) build on every bar phone that
     * takes the CN build, listed first (owner: "IN build is just better").
     * Untested, so a phone where the CN build has run still preselects that.
     */
    private val X9U_IN_CHOICE = ImageChoice(Images.ID_FIND_X9U_IN, PackageSets.ID_X9U_IN_SULTRA, tested = false)

    /** The same image where a tester's session has reached the home screen (docs/compatibility.md). */
    private val X9U_IN_TESTED = X9U_IN_CHOICE.copy(tested = true)

    // 0.4.51: the full Find X9 Ultra IN build only (the debloated build left the app and was never on Drive);
    // tested where the debloated one was: testers started the IN build on these phones too.
    private val S_ULTRA_CHOICES = listOf(X9U_IN_TESTED)

    /**
     * 0.4.22: the Pixel 9 Pro XL image on the phones without SVE (SM8750, SM8650),
     * untested. Its system code has none (the Pixel 11 images need it), so these
     * phones get a Pixel too.
     */
    private val PIXEL9_CHOICE = ImageChoice(Images.ID_PIXEL_KOMODO, PackageSets.ID_PIXEL9_SULTRA, tested = false)

    /**
     * 0.4.27: Infinity-X (the Find X9 Ultra build) on every phone, untested,
     * listed last so no phone's preselected system changes. Its system code
     * has no SVE, so the SM8750 and older phones take it too; one set for all
     * of them (a fold gets the fold layout from the session scripts).
     */
    private val INFINITYX_CHOICE = ImageChoice(Images.ID_INFINITYX, PackageSets.ID_INFINITYX, tested = false)

    /**
     * 0.4.31: the phones whose testers' sessions reached the home screen on it
     * (reports of 2026-10-29/30, docs/compatibility.md): the Galaxy S26 Ultra,
     * S25 Ultra, S25, S24 Ultra and Z Flip5. Calls and SMS are the open ones
     * there, which is what the IMS work is for.
     */
    private val INFINITYX_TESTED = INFINITYX_CHOICE.copy(tested = true)

    /**
     * HyperOS (0.4.31, owner: "Allow all users to try"), made for the Z Fold8 Ultra
     * and Z Fold8: on every phone, last, after Infinity-X. One set everywhere; on a
     * bar phone its cover-screen layout runs as the phone's screen.
     */
    private val HYPEROS_CHOICE = ImageChoice(Images.ID_HYPEROS_LHASA, PackageSets.ID_HYPER_F8U, tested = false)
    /**
     * OxygenOS 16 (SDK 36) for phones on One UI 8 (0.4.67, experimental; the app offers it only on SDK 36).
     * 0.4.91, at the owner's request (2026-11-11, "add oxygenos to s23 series on oneui8/8.5"): the Galaxy S23,
     * S23+ and S23 Ultra ([S_8550], [S_PLUS_8550], [S_ULTRA_8550]) that are still on One UI 8.0/8.5, untested:
     * no session on an SM8550 phone with an Android 16 One UI yet. The S22 Ultra and S23 FE with Snapdragon
     * (SM8450, the HIDL composer as well) run it. Before OriginOS in their lists, which stays last.
     */
    private val OXYGEN16_CHOICE = ImageChoice(Images.ID_OXYGEN16, PackageSets.ID_OXYGEN16, tested = false)

    /**
     * Nothing OS 5.0 (0.4.33), untested, last: the Z Fold8 Ultra first, where it
     * was made; 0.4.35 the Z Fold8, the S26 family (both chips) and the Z Flip8;
     * 0.4.36 the S25 Ultra, S25, S25+, S24 Ultra, Z Fold7 and Z Fold6 (it needs
     * no SVE after all, Images.NOTHING_METROID). Only phones whose panels share
     * the Fold's brightness scale (brightnessMaximum about 5): its brightness
     * range overlay is the Fold's. 0.4.83, at the owner's request (2026-11-10,
     * "the same supported roms as s24 ultra to plus and base too"): the Exynos
     * S24 and S24+ (brightnessMaximum 5.0 in their One UI 9 probes), like the
     * Exynos S26s before them.
     */
    private val NOTHING_CHOICE = ImageChoice(Images.ID_NOTHING_METROID, PackageSets.ID_NOTHING_F8U, tested = false)
    /**
     * OriginOS 7 (0.4.73, experimental): the Snapdragon S25 and S26 series and the Z Fold7, Fold8 and Fold8 Ultra
     * (each profile names it itself: the shared choice lists also serve Exynos phones). Tested on the
     * Z Fold8 Ultra only (fold mode 1, runs 13-24); the bar phones take vivo's phone layout (session reports of
     * 0.4.73 and 0.4.74 from the S25, S25+, S26 Ultra and Z Fold7: started and returned).
     * 0.4.82, at the owner's request (2026-11-10): also the Snapdragon S24 (S24, S24 Ultra) and S23 (S23, S23+,
     * S23 Ultra) phones, untested: no OriginOS session on vendor API 34 or 33 yet. The session scripts have no
     * OriginOS step that depends on the vendor's generation; the S23s run ColorOS 17, the Pixel 9 Pro XL image and
     * HyperOS, the S24 Ultra the Pixel 9 Pro XL image (reports of 0.4.72-0.4.74). Sound there goes through the HIDL
     * audio HAL and the S23s' display through the HIDL composer, which no OriginOS session has used; the image has
     * both clients (docs/originos.md, the host check).
     * 0.4.83, at the owner's request (2026-11-10, "the same supported roms as s24 ultra to plus and base too"):
     * the Exynos S24 and S24+ ([S_9945], [S_PLUS_9945]), untested and the first Exynos phones with it: no OriginOS
     * session has met Samsung's Exynos vendor (the Xclipse GPU's drivers, Exynos's composer3 and AIDL audio HAL).
     * The session scripts have no OriginOS step that depends on the chip; ColorOS 17 and the Pixel 9 Pro XL image
     * reach the home screen on the Exynos 2400's vendor (reports of 0.4.72-0.4.74 from the S24 (Exynos) and
     * S24 FE). On no other Exynos phone (docs/originos.md, the host check).
     */
    private val ORIGINOS_CHOICE = ImageChoice(Images.ID_ORIGINOS7, PackageSets.ID_ORIGINOS, tested = false)
    private val ORIGINOS_TESTED = ImageChoice(Images.ID_ORIGINOS7, PackageSets.ID_ORIGINOS, tested = true)

    private fun olderVendor(vendorApi: String, kernel: String) = Finding(
        ID_NOTE_OLDER_VENDOR, Level.WARN, "Older vendor software",
        "This phone has vendor API $vendorApi and kernel $kernel; the other systems' display path has only run on " +
            "vendor API 202504 (Snapdragon 8 Elite Gen 5).",
        R_OLDER_VENDOR,
    )

    /** The SM8750 phones (S25 Ultra, S25, S25+, Z Fold7): vendor API 202404 and kernel 6.6. */
    private val OLDER_VENDOR = olderVendor("202404", "6.6")

    /**
     * The SM8550 phones (Galaxy S23, S23+): vendor API 33 (Android 13) and
     * kernel 5.15, and only the HIDL display composer (their probe reports
     * list no android.hardware.graphics.composer3.IComposer, which the S24
     * Ultra and newer have and the guests' SurfaceFlinger talks to).
     * Offered at the owner's request (2026-10-25) so
     * a failed start comes back as logs: the black-screen auto-return
     * (oneos_switch.sh, ONEOS_RETURN_BLACK) brings One UI back.
     */
    private val EXPECT_NO_START = Finding(
        ID_NOTE_EXPECT_NO_START, Level.WARN, "Will most likely not start",
        "This phone has vendor API 33 (Android 13) and kernel 5.15; the other systems have only run on " +
            "vendor API 202404 and newer. If the screen stays black, OneOS returns to One UI by itself; " +
            "share the session logs afterwards.",
        R_EXPECT_NO_START,
    )

    /** The Exynos phones' note: the first sessions on that chip. */
    const val ID_NOTE_EXYNOS = "profile-exynos"
    const val R_EXYNOS = "exynos"

    /**
     * 0.4.17: the first Exynos phones. The guest system takes One UI's vendor
     * through Android's standard interfaces, the same as on Snapdragon, and the
     * session scripts find Samsung's Exynos display composer
     * (vendor.hwcomposer-3) and backlight (/sys/class/backlight/panel)
     * themselves. The S26+ (Exynos) and Z Flip7 sessions of 0.4.17 to 0.4.20
     * brought the Exynos host fixes (docs/exynos-hosts.md: ro.boot.hardware
     * for the Qualcomm-built guests, Samsung's software watchdog); the next
     * Exynos logs show how far a session gets with them.
     */
    private val EXYNOS = Finding(
        ID_NOTE_EXYNOS, Level.WARN, "First runs on Exynos",
        "Exynos phones have had only a few test sessions so far. The screen, phone calls, Wi-Fi or sound may not work; " +
            "if the screen stays black, OneOS returns to One UI by itself. Share the session logs afterwards.",
        R_EXYNOS,
    )

    /** The MediaTek phones' note: the first sessions on that chip (0.4.33, the Galaxy A07). */
    const val ID_NOTE_MEDIATEK = "profile-mediatek"
    const val R_MEDIATEK = "mediatek"

    /**
     * 0.4.33: the first MediaTek phone. The guest system takes One UI's vendor
     * through Android's standard interfaces, as on Snapdragon and Exynos, and
     * the session scripts find the display composer by its init service name
     * (vendor.hwcomposer-3-1 on the A07). Unlike every phone before it there is
     * no /sys/class/backlight panel node, so the brightness slider may do
     * nothing until a session shows how its backlight is driven.
     */
    private val MEDIATEK = Finding(
        ID_NOTE_MEDIATEK, Level.WARN, "First runs on MediaTek",
        "MediaTek phones have not run OneOS before. The screen, brightness, phone calls, Wi-Fi or sound may not work; " +
            "if the screen stays black, OneOS returns to One UI by itself. Share the session logs afterwards.",
        R_MEDIATEK,
    )

    /** The Switch tick for [ID_NOTE_EXPECT_NO_START]. */
    fun expectNoStartAck(system: String = Images.OTHER_SYSTEM): String =
        "I understand $system will most likely not start on this phone, and I'll share the session logs after"

    val F8U = PhoneProfile(
        id = ID_F8U,
        label = "Z Fold (F8U)",
        modelPrefix = "SM-F976",
        codename = "q8q",
        socModel = "SM8850",
        form = FormFactor.FOLD,
        choices = listOf(
            ImageChoice(Images.ID_FIND_N6, PackageSets.ID_N6_F8U, tested = true),
            // 0.3.7: the Pixel 11 Fold image with its set, on this phone only.
            // Tested: runs 41-44 booted it here (staged over adb by
            // scripts/deploy-phone.sh, not yet from the app).
            ImageChoice(Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8U, tested = true),
            INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE,
            ORIGINOS_TESTED,
        ),
    )

    val S_ULTRA_8850 = PhoneProfile(
        id = ID_S_ULTRA_8850,
        label = "Galaxy S26 Ultra",
        modelPrefix = "SM-S948",
        codename = "m3q",
        socModel = "SM8850",
        form = FormFactor.BAR,
        // 0.4.10: the Pixel 11 Pro image too, untested. SM8850 has the SVE that
        // Pixel's system code needs; the SM8750 phones do not.
        choices = S_ULTRA_CHOICES + ImageChoice(Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, tested = false) + INFINITYX_TESTED + HYPEROS_CHOICE +
            NOTHING_CHOICE + ORIGINOS_CHOICE,
    )

    val S_ULTRA_8750 = PhoneProfile(
        id = ID_S_ULTRA_8750,
        label = "Galaxy S25 Ultra",
        modelPrefix = "SM-S938",
        codename = "pa3q",
        socModel = "SM8750",
        form = FormFactor.BAR,
        // Off in 0.3.0 (the S26 Ultra was to go first); on from 0.3.1 (owner: the
        // friend's S25 Ultra is on Android 17 and ready). Untested: ticks as the S26 Ultra.
        choices = S_ULTRA_CHOICES + PIXEL9_CHOICE + INFINITYX_TESTED + HYPEROS_CHOICE + NOTHING_CHOICE + ORIGINOS_CHOICE,
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy S25 (base), from 0.3.4: a friend's probe findings of 2026-10-23
     * (SM-S931B, pa1q, SM8750, One UI 9.0, Android 17, one 1080 x 2340
     * panel, no hinge, installd table identical to switcher/patches/
     * host_installd.txt, 85 methods). Not an S Ultra, so its explicit profile
     * is what puts it in scope
     * ([CompatEvaluator.inScope]); it takes the S Ultra images and sets, untested.
     */
    val S_8750 = PhoneProfile(
        id = ID_S_8750,
        label = "Galaxy S25",
        modelPrefix = "SM-S931",
        codename = "pa1q",
        socModel = "SM8750",
        form = FormFactor.BAR,
        choices = S_ULTRA_CHOICES + PIXEL9_CHOICE + INFINITYX_TESTED + HYPEROS_CHOICE + NOTHING_CHOICE + ORIGINOS_CHOICE,
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy Z Fold7, from 0.4.8: a probe report of 2026-10-25 (SM-F966B, q7q,
     * SM8750, One UI 9.0, Android 17, vendor API 202404, kernel 6.6). Laid
     * out like the Z Fold8 Ultra: inner panel on port 147 and cover on 148
     * (1968 x 2184 and 1080 x 2520, density 420), sec_touchscreen and
     * sec_touchscreen2 on those ports, device states 0 CLOSE and 3 OPEN, a
     * "flip" lid switch, and an installd table identical to
     * switcher/patches/host_installd.txt (85 methods). It takes the Find N6
     * image with the Fold's set, untested. No Pixel image: Pixel's system
     * code uses SVE in every process (RefBase's constructor), which SM8750
     * does not have.
     */
    val FOLD7 = PhoneProfile(
        id = ID_FOLD7,
        label = "Galaxy Z Fold7",
        modelPrefix = "SM-F966",
        codename = "q7q",
        socModel = "SM8750",
        form = FormFactor.FOLD,
        choices = listOf(ImageChoice(Images.ID_FIND_N6, PackageSets.ID_N6_F8U, tested = false), INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE) + ORIGINOS_CHOICE,
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy S25+, from 0.4.10: a probe report of 2026-10-25 (SM-S936B, pa2q,
     * SM8750, One UI 9.0, Android 17, vendor API 202404, one panel on port
     * 147, density 450, installd table identical to
     * switcher/patches/host_installd.txt). The Galaxy S25's images and sets,
     * untested; of the Pixel images only the Pixel 9 Pro XL's (no SVE).
     */
    val S_PLUS_8750 = PhoneProfile(
        id = ID_S_PLUS_8750,
        label = "Galaxy S25+",
        modelPrefix = "SM-S936",
        codename = "pa2q",
        socModel = "SM8750",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE) + ORIGINOS_CHOICE,
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy Z Fold8, from 0.4.10: a probe report of 2026-10-25 (SM-F971B, h8q,
     * SM8850, One UI 9.0, Android 17, vendor API 202504 like the Z Fold8 Ultra,
     * kernel 6.12). The Z Fold8 Ultra's ports and touch screens (inner 147 on
     * sec_touchscreen, cover 148 on sec_touchscreen2), a flip lid switch and an
     * identical installd table; other panels (about 1848 x 2448 and 1248 x
     * 1972, density 420) and one more device state, 1 TENT, which the fold
     * layout now takes from the phone (guest_start.sh). It takes the Fold's
     * images and sets, untested; the Pixel display configs are the Z Fold8
     * Ultra's only, so its Pixel keeps the image's own brightness.
     */
    val FOLD8 = PhoneProfile(
        id = ID_FOLD8,
        label = "Galaxy Z Fold8",
        modelPrefix = "SM-F971",
        codename = "h8q",
        socModel = "SM8850",
        form = FormFactor.FOLD,
        // 0.4.38: the Find N6 global image with the Z Folds' set (n6-f8 of 0.4.14,
        // pull request #1, patched the CN build's SystemUI); not run here yet.
        choices = listOf(
            ImageChoice(Images.ID_FIND_N6, PackageSets.N6_GLOBAL_F8.id, tested = false),
            ImageChoice(Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8, tested = true),
            INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE,
            ORIGINOS_CHOICE,
        ),
    )

    /** The Galaxy S26's images: the S Ultra's, all untested; 0.4.35 Nothing OS too. */
    private val S_8850_CHOICES = listOf(
        X9U_IN_CHOICE,
        ImageChoice(Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, tested = false),
        INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE,
    )

    /**
     * Galaxy S26 (base), from 0.4.11: a probe report of 2026-10-25 from the
     * Japanese carrier model (SC-51G, m1q, SM8850, One UI 9.0, Android 17,
     * vendor API 202504 and kernel 6.12 like the Z Fold8 Ultra, one panel on
     * port 147, density 480, SVE and SME, installd 85 methods). One profile
     * per model number: SM-S942 everywhere else, [S_8850_JP] for SC-51G. The
     * Exynos S26 has another chip and codename: [S_9965].
     */
    val S_8850 = PhoneProfile(
        id = ID_S_8850,
        label = "Galaxy S26",
        modelPrefix = "SM-S942",
        codename = "m1q",
        socModel = "SM8850",
        form = FormFactor.BAR,
        choices = S_8850_CHOICES + ORIGINOS_CHOICE,
    )

    val S_8850_JP = S_8850.copy(id = ID_S_8850_JP, label = "Galaxy S26 (docomo)", modelPrefix = "SC-51G")

    /**
     * Galaxy S26+, from 0.4.12: a probe report of 2026-10-25 (SM-S947U, m2q,
     * SM8850, One UI 9.0, Android 17, vendor API 202504 and kernel 6.12, one
     * 1440 x 3120 panel on port 147 at density 600, a centre camera hole,
     * Android's Bluetooth audio HAL and AIDL composer like the S26 Ultra, SVE
     * and SME, installd 85 methods). The Galaxy S26's images and sets, untested.
     */
    val S_PLUS_8850 = PhoneProfile(
        id = ID_S_PLUS_8850,
        label = "Galaxy S26+",
        modelPrefix = "SM-S947",
        codename = "m2q",
        socModel = "SM8850",
        form = FormFactor.BAR,
        choices = S_8850_CHOICES + ORIGINOS_CHOICE,
    )

    /**
     * Galaxy S24 Ultra, from 0.4.11: a probe report of 2026-10-25 (SM-S928B,
     * e3q, SM8650, One UI 9.0, Android 17, vendor API 34, kernel 6.1, one
     * panel on port 147, density 450, no SVE or SME, installd 85 methods).
     * The S Ultra's images and sets, untested; of the Pixel images only the
     * Pixel 9 Pro XL's (no SVE).
     */
    val S_ULTRA_8650 = PhoneProfile(
        id = ID_S_ULTRA_8650,
        label = "Galaxy S24 Ultra",
        modelPrefix = "SM-S928",
        codename = "e3q",
        socModel = "SM8650",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_TESTED, HYPEROS_CHOICE, NOTHING_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy S23 and S23+, from 0.4.11: probe reports of 2026-10-25
     * (SM-S911B dm1q and SM-S916U dm2q, SM8550, One UI 9.0, Android 17, one
     * panel on port 147, no SVE or SME, installd 85 methods). The S Ultra's
     * image and set with [EXPECT_NO_START]. 0.4.30: also the Pixel 9 Pro XL
     * image (no SVE needed), with the S23s, the Z Flip7, the A57 and the Z
     * Flip5: Infinity-X started on an S23 once the HIDL-only phones got the
     * hwservicemanager marker (guest_prepare.sh), which Pixel lacks as well.
     */
    val S_8550 = PhoneProfile(
        id = ID_S_8550,
        label = "Galaxy S23",
        modelPrefix = "SM-S911",
        codename = "dm1q",
        socModel = "SM8550",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(EXPECT_NO_START),
    )

    val S_PLUS_8550 = PhoneProfile(
        id = ID_S_PLUS_8550,
        label = "Galaxy S23+",
        modelPrefix = "SM-S916",
        codename = "dm2q",
        socModel = "SM8550",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(EXPECT_NO_START),
    )

    /**
     * Galaxy S26+ with Exynos, from 0.4.17: a probe report of 2026-10-25
     * (SM-S947B, m2s, s5e9965 Exynos 2600, One UI 9.0, Android 17 build
     * CP2A.260605.016, one 1440 x 3120 panel on port 129 at density 600,
     * sec_touchscreen, backlight /sys/class/backlight/panel, composer
     * vendor.hwcomposer-3, SVE, SVE2, SME and SME2, installd table identical to
     * switcher/patches/host_installd.txt). The Galaxy S26's images and sets
     * (both Find X9 Ultra builds and the Pixel 11 Pro, whose system code needs
     * the SVE this chip has), untested, with [EXYNOS].
     */
    val S_PLUS_9965 = PhoneProfile(
        id = ID_S_PLUS_9965,
        label = "Galaxy S26+ (Exynos)",
        modelPrefix = "SM-S947",
        codename = "m2s",
        socModel = "s5e9965",
        form = FormFactor.BAR,
        choices = S_8850_CHOICES,
        notes = listOf(EXYNOS),
    )

    /**
     * Galaxy S26 with Exynos, from 0.4.52: probe reports of 2026-11-02 to 11-04
     * (SM-S942B, m1s, s5e9965 Exynos 2600 like the S26+ (Exynos), One UI 9.0,
     * Android 17 build CP2A.260605.016, vendor and board API 202504, first API 36,
     * SVE, SVE2, SME and SME2, installd 85 methods). Its model number is the
     * Snapdragon S26's ([S_8850], m1q), so the codename tells them apart, as for
     * the two S26+. The S26+ (Exynos)'s images and sets, untested, with [EXYNOS].
     * A report naming SM-S942B with an Exynos 2100 (universal2100_r, Cortex-X1)
     * is another phone with a changed model name and is left out.
     */
    val S_9965 = S_PLUS_9965.copy(id = ID_S_9965, label = "Galaxy S26 (Exynos)", modelPrefix = "SM-S942", codename = "m1s")

    /**
     * Galaxy Z Flip7, from 0.4.17: a probe report of 2026-10-25 (SM-F766U, b7s,
     * s5e9955 Exynos 2500, One UI 9.0, Android 17 build CP2A.260605.016, main
     * panel 1080 x 2520 on port 129 at density 480 and a 948 x 1048 cover on
     * 130, sec_touchscreen and sec_touchscreen2, a "flip" lid switch,
     * backlights panel and panel1, composer vendor.hwcomposer-3, SVE and SVE2
     * but no SME, installd table identical to host_installd.txt). It runs the
     * guest as a phone on the main panel (the bar settings; no cover layout
     * yet), with the Find X9 Ultra builds, untested, and [EXYNOS]. The ColorOS
     * images also start on the SM8750 phones, which have no SME either.
     */
    val FLIP7 = PhoneProfile(
        id = ID_FLIP7,
        label = "Galaxy Z Flip7",
        modelPrefix = "SM-F766",
        codename = "b7s",
        socModel = "s5e9955",
        form = FormFactor.FLIP,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(EXYNOS),
    )

    /**
     * Galaxy A57, from 0.4.29: a probe report of 2026-10-29 (SM-A576B, a57x,
     * s5e8865 Exynos, One UI 9.0, Android 17 build CP2A.260605.016, vendor API
     * 202504, kernel 6.12, one 1080 x 2340 panel on port 129 at density 450,
     * sec_touchscreen, backlight /sys/class/backlight/panel (max 9180),
     * composer vendor.hwcomposer-3 and the AIDL audio HAL, init.vendor.sysfw.rc
     * like the S26+ (Exynos), SVE and SVE2 but no SME, installd table identical
     * to host_installd.txt). The first A-series phone and the first mid-range
     * chip: the Z Flip7's images (the Find X9 Ultra builds and Infinity-X, whose
     * system code needs neither SVE nor SME), untested, with [EXYNOS].
     */
    val A57 = PhoneProfile(
        id = ID_A57,
        label = "Galaxy A57",
        modelPrefix = "SM-A576",
        codename = "a57x",
        socModel = "s5e8865",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_TESTED, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(EXYNOS),
    )

    /**
     * Galaxy A56, from 0.4.31: a probe report of 2026-10-30 (SM-A566B, a56x,
     * s5e8855 Exynos, One UI 9.0, Android 17 build CP2A.260605.016, vendor API
     * 202404, one 1080 x 2340 panel at density 450, sec_touchscreen, composer
     * android.hardware.graphics.composer3-service.exynos, SVE and SVE2 but no
     * SME, installd table identical to host_installd.txt). The A57's smaller
     * sibling, one Exynos generation down (s5e8855 against s5e8865) and the same
     * in everything the switch reads, so it takes the A57's images, untested,
     * with [EXYNOS].
     */
    val A56 = PhoneProfile(
        id = ID_A56,
        label = "Galaxy A56",
        modelPrefix = "SM-A566",
        codename = "a56x",
        socModel = "s5e8855",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(EXYNOS),
    )

    /**
     * Galaxy Z Flip5, from 0.4.29: a probe report of 2026-10-28 (SM-F731B, b5q,
     * SM8550 like the Galaxy S23s, One UI 9.0, Android 17 build
     * CP2A.260605.016, vendor API 33 and kernel 5.15, main panel 1080 x 2640 on
     * port 131 at density 480 and a 748 x 720 cover on 132, sec_touchscreen
     * and sec_touchscreen2, a "flip" lid switch, backlights panel0-backlight
     * and panel1-backlight (max 765), the HIDL display composer and audio HAL
     * (no composer3, no audio.core), no SVE, installd table identical to
     * host_installd.txt). The S23s' images (both Find X9 Ultra builds and
     * Infinity-X), run as a phone on the main screen like the Z Flip7 (no
     * cover layout), with their [EXPECT_NO_START] note: the same chip and
     * vendor, which no system has started on yet.
     */
    val FLIP5 = PhoneProfile(
        id = ID_FLIP5,
        label = "Galaxy Z Flip5",
        modelPrefix = "SM-F731",
        codename = "b5q",
        socModel = "SM8550",
        form = FormFactor.FLIP,
        choices = listOf(X9U_IN_TESTED, PIXEL9_CHOICE, INFINITYX_TESTED, HYPEROS_CHOICE),
        notes = listOf(EXPECT_NO_START),
    )

    /**
     * Galaxy Z Fold6, from 0.4.33: a probe report of 2026-10-30 (SM-F956B, q6q,
     * SM8650 like the Galaxy S24 Ultra, One UI 9.0, Android 17 build
     * CP2A.260605.016, vendor API 34 and kernel 6.1, density 420, installd table
     * identical to host_installd.txt; the tester asked for a build). A fold like
     * the Z Fold7: the Find N6 global build (its fold layout) and Infinity-X, untested.
     * Not HyperOS: on the S24 Ultra, the same chip, its SurfaceFlinger aborts at
     * the first display (0.4.32, four sessions), so it would only show black.
     */
    val FOLD6 = PhoneProfile(
        id = ID_FOLD6,
        label = "Galaxy Z Fold6",
        modelPrefix = "SM-F956",
        codename = "q6q",
        socModel = "SM8650",
        form = FormFactor.FOLD,
        choices = listOf(ImageChoice(Images.ID_FIND_N6, PackageSets.ID_N6_F8U, tested = false), INFINITYX_CHOICE, NOTHING_CHOICE),
        notes = listOf(olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy A07, from 0.4.33: a probe report of 2026-10-30 (SM-A075F, a07,
     * MediaTek MT6789, One UI 9.0, Android 17 build CP2A.260605.016, vendor API
     * 31 and kernel 6.12, one 720 x 1600 panel at density 300 (60/90 Hz), touch
     * chipone-tddi, composer3 and audio.core AIDL HALs, Cortex-A55/A76 with no
     * SVE or SME, installd table of 85 methods like every One UI 9 phone). The
     * owner asked for the A series on Infinity-X; this one is on Android 17
     * already, so the version gate allows it. Infinity-X only (its system code
     * needs neither SVE nor SME: the S25 Ultra runs it), untested, with
     * [MEDIATEK]. The A16 and A17 on One UI 8.5 (Android 16) are still refused
     * by the version gate. 0.4.60: Infinity-X reached the home screen here (0.4.58 reports of
     * 2026-11-06), and ColorOS (the Find X9 Ultra IN build) is offered too, untested (owner).
     */
    val A07 = PhoneProfile(
        id = ID_A07,
        label = "Galaxy A07",
        modelPrefix = "SM-A075",
        codename = "a07",
        socModel = "MT6789",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, INFINITYX_TESTED, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK, olderVendor("31 (Android 12)", "6.12")),
    )

    /**
     * Galaxy Z Flip8, from 0.4.35: a probe report of 2026-11-01 (SM-F776B, b8s,
     * s5e9965 Exynos 2600 like the S26+ (Exynos), One UI 9.0, Android 17 build
     * CP2A.260605.016, SVE, SVE2, SME and SME2, installd 85 methods). A flip run
     * as a phone on its main screen like the Z Flip7, with the S26+ (Exynos)'s
     * images (its chip has the SVE and SME the Pixel 11 Pro and Nothing OS need),
     * untested, with [EXYNOS].
     */
    val FLIP8 = PhoneProfile(
        id = ID_FLIP8,
        label = "Galaxy Z Flip8",
        modelPrefix = "SM-F776",
        codename = "b8s",
        socModel = "s5e9965",
        form = FormFactor.FLIP,
        choices = S_8850_CHOICES,
        notes = listOf(EXYNOS),
    )

    /**
     * Galaxy A36, from 0.4.35: a probe report of 2026-10-31 (SM-A366B, a36xq,
     * Snapdragon SM6475 "parrot", One UI 9.0, Android 17 build CP2A.260605.016,
     * vendor API 202404 and kernel 6.6 like the S25s, one panel on port 130,
     * backlight panel0-backlight (max 8670), composer3 and the AIDL audio HAL,
     * Cortex-A55/A78 with no SVE or SME, installd 85 methods). The first
     * mid-range Snapdragon: the S25+'s images (the Find X9 Ultra builds, the
     * Pixel 9 Pro XL, Infinity-X and HyperOS, none of which needs SVE),
     * untested, with the S25s' older-vendor note.
     */
    val A36 = PhoneProfile(
        id = ID_A36,
        label = "Galaxy A36",
        modelPrefix = "SM-A366",
        codename = "a36xq",
        socModel = "SM6475",
        form = FormFactor.BAR,
        // 0.4.57: not the Pixel 9 Pro XL, as on the A26: the same ARMv8.2 CPU features (no ilrcpc, frint, flagm...).
        choices = listOf(X9U_IN_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy Z Fold5, from 0.4.35: a probe report of 2026-11-01 (SM-F946B, q5q,
     * SM8550 like the Z Flip5 and the S23s, One UI 9.0, Android 17, vendor API 33
     * and kernel 5.15, inner 1812 x 2176 and cover 904 x 2316, device states 0
     * CLOSE and 3 OPEN, the HIDL composer and Samsung's Bluetooth audio HAL, no
     * SVE, installd 85 methods). A fold like the Z Fold6: the Find N6 global build (its
     * fold layout) and Infinity-X, which started on the Z Flip5's same platform,
     * untested, with the older-vendor note.
     */
    val FOLD5 = PhoneProfile(
        id = ID_FOLD5,
        label = "Galaxy Z Fold5",
        modelPrefix = "SM-F946",
        codename = "q5q",
        socModel = "SM8550",
        form = FormFactor.FOLD,
        choices = listOf(ImageChoice(Images.ID_FIND_N6, PackageSets.ID_N6_F8U, tested = false), INFINITYX_CHOICE),
        notes = listOf(olderVendor("33 (Android 13)", "5.15")),
    )

    /**
     * Galaxy S23 Ultra, from 0.4.40: probe reports of 2026-10-31 to 11-03 (SM-S918B, SM-S918U and
     * SM-S918U1, dm3q, SM8550 like the S23 and S23+, One UI 9.0, Android 17 build CP2A.260605.016,
     * vendor API 33 and kernel 5.15, no SVE or SME, installd 85 methods). The S23s' images and sets
     * with their [EXPECT_NO_START] note; untested on it.
     */
    val S_ULTRA_8550 = PhoneProfile(
        id = ID_S_ULTRA_8550,
        label = "Galaxy S23 Ultra",
        modelPrefix = "SM-S918",
        codename = "dm3q",
        socModel = "SM8550",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(EXPECT_NO_START),
    )

    /**
     * Galaxy Z Flip6, from 0.4.40: a probe report of 2026-11-02 (SM-F741B, b6q, SM8650 like the
     * Galaxy S24 Ultra and Z Fold6, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 34 and
     * kernel 6.1, no SVE or SME, installd 85 methods). Run as a phone on the main screen like the
     * Z Flip5 and Z Flip7, with the S24 Ultra's images except HyperOS (the Z Fold6's reason: its
     * SurfaceFlinger died on that chip; 0.4.39's fix is untested there); untested on it.
     */
    val FLIP6 = PhoneProfile(
        id = ID_FLIP6,
        label = "Galaxy Z Flip6",
        modelPrefix = "SM-F741",
        codename = "b6q",
        socModel = "SM8650",
        form = FormFactor.FLIP,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE),
        notes = listOf(olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy S24 with Exynos, from 0.4.40: a probe report of 2026-11-03 (SM-S921N, e1s, s5e9945
     * Exynos 2400, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 34 and kernel 6.1,
     * SVE and SVE2 but no SME, installd 85 methods; an SM-S921B probe the same). The S23s' images
     * (both Find X9 Ultra builds, the Pixel 9 Pro XL, Infinity-X and HyperOS), untested, with
     * [EXYNOS]: the first Exynos 2400. 0.4.83, at the owner's request (2026-11-10): the Galaxy S24
     * Ultra's systems, so Nothing OS and OriginOS 7 as well (both untested here; OriginOS has run on
     * no Exynos phone, [ORIGINOS_CHOICE]). The S24 FE, Z Flip7 FE and S25 FE keep their four.
     */
    val S_9945 = PhoneProfile(
        id = ID_S_9945,
        label = "Galaxy S24 (Exynos)",
        modelPrefix = "SM-S921",
        codename = "e1s",
        socModel = "s5e9945",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(EXYNOS, olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy S24+ with Exynos, from 0.4.83: a probe report of 2026-11-10 from the owner (SM-S926B, e2s,
     * s5e9945 Exynos 2400 like the Galaxy S24 (Exynos), One UI 9.0, Android 17 build CP2A.260605.016,
     * vendor API 34 and kernel 6.1, one 1080 x 2340 panel on port 195 at density 450, brightnessMaximum
     * 5.0, sec_touchscreen, composer3 and the AIDL audio HAL, backlight /sys/class/backlight/panel,
     * SVE and SVE2 but no SME, installd 85 methods with the table of switcher/patches/host_installd.txt,
     * KernelSU). The three probes of 2026-11-08 from this model were still One UI 8.5. The S24
     * (Exynos)'s systems, which from this build are the S24 Ultra's, untested, with its notes.
     */
    val S_PLUS_9945 = S_9945.copy(id = ID_S_PLUS_9945, label = "Galaxy S24+ (Exynos)", modelPrefix = "SM-S926", codename = "e2s")

    /**
     * Galaxy S25 Edge, from 0.4.48: a probe report of 2026-11-04 (SM-S937B, psq, SM8750 like the
     * Galaxy S25, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 202404 and kernel 6.6,
     * a 1440 x 3120 panel, sec_touchscreen, composer3 and the AIDL audio HAL, no SVE or SME,
     * installd 85 methods). The S25's platform in a thinner body: the S25's images, untested,
     * with its older-vendor note.
     */
    val S_EDGE_8750 = PhoneProfile(
        id = ID_S_EDGE_8750,
        label = "Galaxy S25 Edge",
        modelPrefix = "SM-S937",
        codename = "psq",
        socModel = "SM8750",
        form = FormFactor.BAR,
        choices = S_ULTRA_CHOICES.map { it.copy(tested = false) } + PIXEL9_CHOICE + INFINITYX_CHOICE + HYPEROS_CHOICE + NOTHING_CHOICE + ORIGINOS_CHOICE,
        notes = listOf(OLDER_VENDOR),
    )

    /**
     * Galaxy S24 with Snapdragon, from 0.4.61: a probe report of 2026-11-07 (SM-S921E, e1q, SM8650
     * like the Galaxy S24 Ultra, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 34 and
     * kernel 6.1, one 1080 x 2340 panel on port 131 at density 480, sec_touchscreen, composer3,
     * no SVE or SME, installd 85 methods). The S24 Ultra's images, untested. Shares SM-S921 with
     * [S_9945]: the codename and the chip tell them apart.
     */
    val S_8650 = PhoneProfile(
        id = ID_S_8650,
        label = "Galaxy S24",
        modelPrefix = "SM-S921",
        codename = "e1q",
        socModel = "SM8650",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, NOTHING_CHOICE, ORIGINOS_CHOICE),
        notes = listOf(olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy S24 FE, from 0.4.48: a probe report of 2026-11-04 (SM-S721B, r12s, s5e9945 Exynos
     * 2400 like the Galaxy S24 (Exynos), One UI 9.0, Android 17, vendor API 34 and kernel 6.1,
     * one 1080 x 2340 panel at density 450, sec_touchscreen, composer3, SVE and SVE2 but no SME,
     * installd 85 methods). The S24 (Exynos)'s images, untested, with [EXYNOS].
     */
    val S_FE_9945 = PhoneProfile(
        id = ID_S_FE_9945,
        label = "Galaxy S24 FE",
        modelPrefix = "SM-S721",
        codename = "r12s",
        socModel = "s5e9945",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(EXYNOS, olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy A26, from 0.4.48: a probe report of 2026-11-03 (SM-A266B, a26x, s5e8835 Exynos 1380,
     * One UI 9.0, Android 17, vendor API 33 and kernel 5.15, one 1080 x 2340 panel at density 450,
     * sec_touchscreen, the HIDL composer, no SVE or SME, installd 85 methods). An older vendor like
     * the Galaxy S23s and Z Flip5: both Find X9 Ultra builds, the Pixel 9 Pro XL and Infinity-X,
     * none of which needs SVE; not HyperOS (it mostly stayed black on vendor 33). Untested, with
     * [EXYNOS].
     */
    val A26 = PhoneProfile(
        id = ID_A26,
        label = "Galaxy A26",
        modelPrefix = "SM-A266",
        codename = "a26x",
        socModel = "s5e8835",
        form = FormFactor.BAR,
        // 0.4.57: not the Pixel 9 Pro XL any more: its own programs stopped on "Illegal instruction" before
        // it started, in every session (0.4.54/0.4.55 reports 9f2307a3, 560a1dcb, c926c955). This ARMv8.2
        // CPU lacks what every phone it runs on has (ilrcpc, frint, flagm, jscvt, fcma, i8mm, bf16...).
        choices = listOf(X9U_IN_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(EXYNOS, olderVendor("33 (Android 13)", "5.15")),
    )

    /**
     * Galaxy A17, from 0.4.48: probe reports from 2026-11-03 on (SM-A175F, a17, MediaTek MT6789
     * like the Galaxy A07, now on One UI 9.0 and Android 17, vendor API 31 and kernel 6.12, one
     * 1080 x 2340 panel, composer3 and the AIDL audio HAL, no SVE or SME, installd 85 methods).
     * Parked while it was on One UI 8.5; the A07's Infinity-X, with [MEDIATEK]. 0.4.60: Infinity-X
     * reached the home screen on the A17 and the A16 4G (reports of 2026-11-05 to 07), and the
     * Find X9 Ultra IN ColorOS is offered too, untested (owner: "allow them to try ColorOS too").
     */
    val A17 = PhoneProfile(
        id = ID_A17,
        label = "Galaxy A17",
        modelPrefix = "SM-A175",
        codename = "a17",
        socModel = "MT6789",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, INFINITYX_TESTED, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK, olderVendor("31 (Android 12)", "6.12")),
    )

    /**
     * Galaxy A16 4G, from 0.4.55: a probe report of 2026-11-05 (SM-A165F, a16, MediaTek MT6789
     * like the A07 and A17, One UI 9.0 and Android 17 build A165FXXUBEZJ7, vendor and board API 31,
     * first API 34, kernel 6.12, no SVE or SME). The A17's Infinity-X, untested, with [MEDIATEK].
     * The A16 5G is another phone ([A16], SM-A166, Exynos 1330).
     */
    val A16_4G = A17.copy(id = ID_A16_4G, label = "Galaxy A16 4G", modelPrefix = "SM-A165", codename = "a16")

    /**
     * Galaxy A16 5G (the US model, Exynos), from 0.4.48: a probe report of 2026-11-03 (SM-A166U,
     * a16x, s5e8535 Exynos 1330, One UI 9.0, Android 17, vendor API 33 and kernel 5.15, one
     * 1080 x 2340 panel, the HIDL composer, no SVE or SME, installd 85 methods). The A16s with
     * MediaTek are other phones ([A16_4G], SM-A165; [A16_MTK], SM-A166P, on One UI 8.5). The
     * weakest chip so far: Infinity-X, with [EXYNOS]. 0.4.60: Infinity-X reached the home screen
     * (a 0.4.58 report of 2026-11-05), and the Find X9 Ultra IN ColorOS is offered too, untested:
     * the A26's ColorOS also runs on a Cortex-A78/A55 Exynos with the HIDL composer.
     */
    val A16 = PhoneProfile(
        id = ID_A16,
        label = "Galaxy A16 5G",
        modelPrefix = "SM-A166",
        codename = "a16x",
        socModel = "s5e8535",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, INFINITYX_TESTED, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(EXYNOS, olderVendor("33 (Android 13)", "5.15")),
    )

    /**
     * Galaxy A16 5G sold by TracFone/Verizon prepaid as SM-S166V, from 0.4.59: a probe report of
     * 2026-11-05 (fearless, SM-S166V, a16x, s5e8535 Exynos 1330, sales code TFV, vendor API 33,
     * kernel 5.15, KernelSU): the same phone as [A16] under a carrier model number. It was still on
     * One UI 8.5 (Android 16, S166VUDS8DZG1), so the version gate holds it until One UI 9.
     */
    val A16_S166 = A16.copy(
        id = ID_A16_S166, label = "Galaxy A16 5G (SM-S166V)", modelPrefix = "SM-S166",
        choices = A16.choices.map { it.copy(tested = false) }, // no session on this model number yet
    )

    /**
     * Galaxy A35 5G, from 0.4.59: findings of 2026-11-05 and 06 (SM-A356E and SM-A356U1, a35x, s5e8835
     * Exynos 1380, One UI 9.0, Android 17, vendor API 33 and kernel 5.15, one 1080 x 2340 panel at
     * density 450, the HIDL composer 2.4 and audio HAL, Mali, no SVE or SME, installd 85 methods): the
     * [A26]'s chip and vendor in every one of those, so its choices and notes. Untested, with [EXYNOS].
     */
    val A35 = A26.copy(id = ID_A35, label = "Galaxy A35 5G", modelPrefix = "SM-A356", codename = "a35x")

    /**
     * Galaxy A54 5G, from 0.4.59: findings of 2026-11-05 (SM-A546E, a54x, s5e8835 Exynos 1380, One UI
     * 9.0, Android 17, vendor API 33 and kernel 5.15, 1080 x 2340 at density 450, the HIDL composer 2.4
     * and audio HAL, Mali, no SVE or SME, installd 85 methods): the [A26]'s chip and vendor, so its
     * choices and notes. Untested, with [EXYNOS].
     */
    val A54 = A26.copy(id = ID_A54, label = "Galaxy A54 5G", modelPrefix = "SM-A546", codename = "a54x")

    /**
     * Galaxy A27, from 0.4.59: findings of 2026-11-07 (SM-A276B, a27xq, Snapdragon SM6475 "parrot",
     * One UI 9.0, Android 17 build CP2A.260605.016, Cortex-A55/A78 with no SVE or SME, KernelSU,
     * installd 85 methods): the [A36]'s chip, CPU and generation, so its choices and notes.
     * Untested.
     */
    val A27 = A36.copy(id = ID_A27, label = "Galaxy A27", modelPrefix = "SM-A276", codename = "a27xq")

    /**
     * Galaxy A17 5G, from 0.4.60: findings of 2026-11-07 (SM-A176B, a17x, s5e8535 Exynos 1330 like
     * the Galaxy A16 5G, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 33 and kernel 5.15,
     * density 450, Mali, Cortex-A55/A78 with no SVE or SME, KernelSU, installd 85 methods): the
     * [A16]'s chip and vendor, so its choices and notes. Untested. The Galaxy A17 4G is [A17].
     */
    val A17_5G = A16.copy(
        id = ID_A17_5G, label = "Galaxy A17 5G", modelPrefix = "SM-A176", codename = "a17x",
        choices = A16.choices.map { it.copy(tested = false) },
    )

    /**
     * Galaxy Z Flip7 FE, from 0.4.60: findings of 2026-11-07 (SM-F761B, b7r, s5e9945 Exynos 2400 like
     * the Galaxy S24 (Exynos) and S24 FE, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 34
     * and kernel 6.1, density 480, SVE and SVE2 but no SME, KernelSU, installd 85 methods). A flip run
     * as a phone on its main screen like the [FLIP7], with the S24 (Exynos)'s images, untested, with
     * [EXYNOS].
     */
    val FLIP7_FE = PhoneProfile(
        id = ID_FLIP7_FE,
        label = "Galaxy Z Flip7 FE",
        modelPrefix = "SM-F761",
        codename = "b7r",
        socModel = "s5e9945",
        form = FormFactor.FLIP,
        choices = listOf(X9U_IN_CHOICE, PIXEL9_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE),
        notes = listOf(EXYNOS, olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * OxygenOS 16 (0.4.67, experimental): the phones still on One UI 8.0/8.5 (Android 16, SDK 36), from
     * their probe reports (model, codename, chip). Only the Android 16 image; untested everywhere. Left
     * out: reports of custom systems (an "S24" with an Exynos 990, a "Note20 Ultra" with an S22 Ultra
     * build, an S10 on Android 16) and the tablets (their layout comes later).
     */
    val A07_5G = PhoneProfile(
        id = ID_A07_5G,
        label = "Galaxy A07 5G",
        modelPrefix = "SM-A076",
        codename = "a07x",
        socModel = "MT6835",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK),
    )

    val A06 = PhoneProfile(
        id = ID_A06,
        label = "Galaxy A06",
        modelPrefix = "SM-A066",
        codename = "a06x",
        socModel = "MT6835",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK),
    )

    /**
     * 0.4.74: One UI 9 (Android 17) reached the A15 (findings of 2026-11-09, SM-A155F,
     * CP2A.260605.016, MT6789, vendor API 31, kernel 6.12), the A07's chip: the A07's systems,
     * untested here. OxygenOS 16 stays for the A15s on One UI 8 and 8.5.
     */
    val A15 = PhoneProfile(
        id = ID_A15,
        label = "Galaxy A15",
        modelPrefix = "SM-A155",
        codename = "a15",
        socModel = "MT6789",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK, olderVendor("31 (Android 12)", "6.12")),
    )

    val A24 = PhoneProfile(
        id = ID_A24,
        label = "Galaxy A24",
        modelPrefix = "SM-A245",
        codename = "a24",
        socModel = "MT6789",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK),
    )

    val A25 = PhoneProfile(
        id = ID_A25,
        label = "Galaxy A25",
        modelPrefix = "SM-A256",
        codename = "a25x",
        socModel = "s5e8825",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    val A33 = PhoneProfile(
        id = ID_A33,
        label = "Galaxy A33 5G",
        modelPrefix = "SM-A336",
        codename = "a33x",
        socModel = "s5e8825",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    /**
     * 0.4.74: One UI 9 (Android 17) reached the A34 (findings report of 2026-11-09, SM-A346E,
     * CP2A.260605.016, vendor API 30, kernel 6.6), so it takes the A07's systems too, all untested
     * here (owner: "can try coloros and hyper etc"). OxygenOS 16 stays for the A34s on One UI 8.
     */
    val A34 = PhoneProfile(
        id = ID_A34,
        label = "Galaxy A34 5G",
        modelPrefix = "SM-A346",
        codename = "a34x",
        socModel = "MT6877",
        form = FormFactor.BAR,
        choices = listOf(X9U_IN_CHOICE, INFINITYX_CHOICE, HYPEROS_CHOICE, OXYGEN16_CHOICE),
        notes = listOf(MEDIATEK, olderVendor("30 (Android 11)", "6.6")),
    )

    val A53 = PhoneProfile(
        id = ID_A53,
        label = "Galaxy A53 5G",
        modelPrefix = "SM-A536",
        codename = "a53x",
        socModel = "s5e8825",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    val E55 = PhoneProfile(
        id = ID_E55,
        label = "Galaxy F55/E55",
        modelPrefix = "SM-E556",
        codename = "m55xq",
        socModel = "SM7450",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
    )

    val S_FE_9925 = PhoneProfile(
        id = ID_S_FE_9925,
        label = "Galaxy S23 FE",
        modelPrefix = "SM-S711",
        codename = "r11s",
        socModel = "s5e9925",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    val S_FE_8450 = PhoneProfile(
        id = ID_S_FE_8450,
        label = "Galaxy S23 FE (Snapdragon)",
        modelPrefix = "SM-S711",
        codename = "r11q",
        socModel = "SM8450",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
    )

    val S_PLUS_9925 = PhoneProfile(
        id = ID_S_PLUS_9925,
        label = "Galaxy S22+",
        modelPrefix = "SM-S906",
        codename = "g0s",
        socModel = "s5e9925",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    val S_ULTRA_9925 = PhoneProfile(
        id = ID_S_ULTRA_9925,
        label = "Galaxy S22 Ultra",
        modelPrefix = "SM-S908",
        codename = "b0s",
        socModel = "s5e9925",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
        notes = listOf(EXYNOS),
    )

    val S_ULTRA_8450 = PhoneProfile(
        id = ID_S_ULTRA_8450,
        label = "Galaxy S22 Ultra (Snapdragon)",
        modelPrefix = "SM-S908",
        codename = "b0q",
        socModel = "SM8450",
        form = FormFactor.BAR,
        choices = listOf(OXYGEN16_CHOICE),
    )

    /**
     * Galaxy A55 5G, from 0.4.68: findings of 2026-11-08 (SM-A556B, a55x, s5e8845 Exynos 1480, One UI
     * 9.0, Android 17 build CP2A.260605.016, vendor API 34 and kernel 6.1, one 1080 x 2340 panel on port
     * 131 at density 450, backlight panel (max 761), sec_touchscreen, composer3, Cortex-A55/A78 with no
     * SVE, SME, BF16 or I8MM, KernelSU, installd 85 methods). Its CPU is the [A35]'s (Cortex-A78/A55,
     * ARMv8.2: no Pixel 9 Pro XL, which stopped on "Illegal instruction" on the A26), so the A35's
     * choices; its vendor is a generation newer (vendor API 34, kernel 6.1, composer3 like the
     * [S_FE_9945]), so that older-vendor note. Untested, with [EXYNOS].
     */
    val A55 = A35.copy(
        id = ID_A55, label = "Galaxy A55 5G", modelPrefix = "SM-A556", codename = "a55x", socModel = "s5e8845",
        notes = listOf(EXYNOS, olderVendor("34 (Android 14)", "6.1")),
    )

    /**
     * Galaxy S25 FE, from 0.4.68: findings of 2026-11-08 (SM-S731B, r13s, s5e9945 Exynos 2400 like the
     * Galaxy S24 FE, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 34 and kernel 6.1, one
     * 1080 x 2340 panel at density 450, backlight panel (max 9180), sec_touchscreen, composer3,
     * Cortex-X4/A720/A520 with SVE and SVE2 but no SME, KernelSU, installd 85 methods): the [S_FE_9945]'s
     * chip, vendor and screen, so its choices and notes. Untested. Not the "SM-S731B" with codename a56x
     * and an s5e8855 (an A56 renamed).
     */
    val S25_FE = S_FE_9945.copy(id = ID_S25_FE, label = "Galaxy S25 FE", modelPrefix = "SM-S731", codename = "r13s")

    /**
     * Galaxy S22 with Snapdragon, from 0.4.68: findings of 2026-11-08 (SM-S901U, r0q, SM8450, One UI 8.0,
     * Android 16 build BP2A.250605.031.A3, vendor and board API 31, kernel 5.10, one 1080 x 2340 panel on
     * port 130 at density 480, backlight panel0-backlight (max 510), the HIDL composer, Cortex-X2/A710/A510
     * with no SVE or SME, KernelSU): the [S_ULTRA_8450]'s chip, vendor and One UI, so its choice, OxygenOS
     * 16 only, untested. The Exynos S22 (SM-S901B, r0s, s5e9925) is [S_9925].
     */
    val S_8450 = S_ULTRA_8450.copy(id = ID_S_8450, label = "Galaxy S22 (Snapdragon)", modelPrefix = "SM-S901", codename = "r0q")

    /**
     * Galaxy M55s, from 0.4.70: findings of 2026-11-08 (SM-M558B, m55xq, Snapdragon 7 Gen 1 SM7450
     * "taro", One UI 8.5, Android 16 build BP4A.251205.006, vendor and board API 31, kernel 5.10
     * android12, one 1080 x 2400 panel on port 130 at density 450, backlight panel0-backlight (max
     * 4095), the HIDL composer, KernelSU): the [E55]'s codename, chip and vendor, so its choice,
     * OxygenOS 16 only, untested.
     */
    val M55S = E55.copy(id = ID_M55S, label = "Galaxy M55s", modelPrefix = "SM-M558")

    /**
     * The au Galaxy S22 Ultra, from 0.4.74: findings of 2026-11-09 (SCG14, ro.product.device SCG14,
     * vendor device b0q, SM8450, One UI 8). The S22 Ultra (Snapdragon)'s OxygenOS 16, untested.
     */
    val S_ULTRA_8450_JP = S_ULTRA_8450.copy(id = ID_S_ULTRA_8450_JP, label = "Galaxy S22 Ultra (au)", modelPrefix = "SCG14", codename = "SCG14")

    /**
     * The au Galaxy S23 Ultra, from 0.4.92: findings of 2026-11-11 (SCG20, ro.product.device SCG20,
     * vendor device dm3q, SM8550, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 33, density
     * 450, KernelSU; its installd table is the 85 methods of host_installd.txt). The [S_ULTRA_8550]'s
     * systems and note, untested.
     */
    val S_ULTRA_8550_JP = S_ULTRA_8550.copy(id = ID_S_ULTRA_8550_JP, label = "Galaxy S23 Ultra (au)", modelPrefix = "SCG20", codename = "SCG20")

    /**
     * Galaxy S22 with Exynos, from 0.4.93: findings of 2026-11-11 (SM-S901B, r0s, s5e9925, now on One UI
     * 8.0 and Android 16, KernelSU, verified boot green; on the waiting list while it was on One UI 7.0).
     * The [S_PLUS_9925]'s chip and One UI, so its choice and note: OxygenOS 16 only, untested. The
     * Snapdragon S22 is [S_8450] (r0q).
     */
    val S_9925 = S_PLUS_9925.copy(id = ID_S_9925, label = "Galaxy S22 (Exynos)", modelPrefix = "SM-S901", codename = "r0s")

    /**
     * Galaxy A16 5G with MediaTek, from 0.4.93: findings of 2026-11-11 (SM-A166P, a16xm, MT6835, One UI
     * 8.5 and Android 16, KernelSU). The [A07_5G]'s chip and One UI, so its choice and note: OxygenOS 16
     * only, untested. The Exynos A16 5G is [A16] (a16x).
     */
    val A16_MTK = A07_5G.copy(id = ID_A16_MTK, label = "Galaxy A16 5G (MediaTek)", modelPrefix = "SM-A166", codename = "a16xm")

    /**
     * The au Galaxy S23, from 0.4.93: findings of 2026-11-11 (SCG19, ro.product.device SCG19, vendor
     * device dm1q, SM8550, One UI 9.0, Android 17 build CP2A.260605.016, vendor API 33, density 480,
     * KernelSU; its installd table is the 85 methods of host_installd.txt). The [S_8550]'s systems and
     * note, untested.
     */
    val S_8550_JP = S_8550.copy(id = ID_S_8550_JP, label = "Galaxy S23 (au)", modelPrefix = "SCG19", codename = "SCG19")

    val BUILT_IN: List<PhoneProfile> = listOf(
        F8U, S_ULTRA_8850, S_ULTRA_8750, S_8750, FOLD7, S_PLUS_8750, FOLD8,
        S_8850, S_8850_JP, S_ULTRA_8650, S_8650, S_8550, S_PLUS_8550, S_PLUS_8850,
        S_PLUS_9965, FLIP7, A56, A57, FLIP5, FOLD6, A07, FLIP8, A36, FOLD5,
        S_ULTRA_8550, FLIP6, S_9945, S_EDGE_8750, S_FE_9945, A26, A17, A16, S_9965, A16_4G, A16_S166, A35, A54, A27, A17_5G, FLIP7_FE,
        A06, A07_5G, A15, A24, A25, A33, A34, A53, E55, S_FE_9925, S_FE_8450, S_PLUS_9925, S_ULTRA_9925, S_ULTRA_8450,
        A55, S25_FE, S_8450, M55S, S_ULTRA_8450_JP, S_PLUS_9945, S_ULTRA_8550_JP, S_9925, A16_MTK, S_8550_JP,
    )

    /** `ro.build.version.oneui` values seen on profiled phones (all One UI 9.0). */
    val ONE_UI_SEEN: Set<Int> = setOf(90000)

    /** One UI versions whose installd tables the app carries for Android 16 systems (One UI 8.0 and 8.5, [InstalldExpected.accepted]). */
    val ONE_UI_SEEN_A16: Set<Int> = setOf(80000, 80500)

    fun byId(id: String, profiles: List<PhoneProfile> = BUILT_IN): PhoneProfile? = profiles.firstOrNull { it.id == id }

    fun resolve(f: DeviceFacts, profiles: List<PhoneProfile> = BUILT_IN): ProfileResolution =
        resolve(f.model, f.device, f.soc.model, profiles)

    fun resolve(model: String, device: String, soc: String, profiles: List<PhoneProfile> = BUILT_IN): ProfileResolution {
        val hits = profiles.filter { it.matches(model, device, soc) }
        if (hits.size == 1) return ProfileResolution(hits.single(), null, emptyList())
        if (hits.size > 1) {
            return ProfileResolution(null, null, listOf("matches ${hits.size} profiles (${hits.joinToString { it.id }})"))
        }
        val m = model.trim().uppercase(Locale.ROOT)
        val nearest = profiles.firstOrNull { m.startsWith(it.modelPrefix) }
            ?: profiles.firstOrNull { device.trim().equals(it.codename, ignoreCase = true) }
            ?: return ProfileResolution(null, null, emptyList())
        val diff = mutableListOf<String>()
        if (!m.startsWith(nearest.modelPrefix)) diff += "model ${model.trim()} (profile: ${nearest.modelPrefix}*)"
        if (!device.trim().equals(nearest.codename, ignoreCase = true)) {
            diff += "codename ${device.trim().ifEmpty { "unknown" }} (profile: ${nearest.codename})"
        }
        if (!soc.trim().equals(nearest.socModel, ignoreCase = true)) {
            diff += "chip ${soc.trim().ifEmpty { "unknown" }} (profile: ${nearest.socModel})"
        }
        return ProfileResolution(null, nearest, diff)
    }
}

/** Android release names for the SDK levels OneOS meets. */
object AndroidRelease {
    fun name(sdk: Int): String = when (sdk) {
        31 -> "12"
        32 -> "12L"
        33 -> "13"
        34 -> "14"
        35 -> "15"
        36 -> "16"
        37 -> "17"
        else -> "SDK $sdk"
    }
}
