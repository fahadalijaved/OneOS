package com.fahadali.oneos.core.model

/**
 * The device report ("Check this phone") from the facts an app can read
 * without root. Rules follow docs/app/DESIGN.md section 4.5 and
 * compat-safety-logs.md section 1.9 (worst finding wins). It is advisory:
 * what only refuses at switch time is a WARN here and a BLOCK in
 * [SwitchGates] (profile not enabled, Android version, screen lock).
 *
 * BLOCK: not Samsung; no arm64; not a target model (owner: Samsung flagships
 * Z Fold / Z Flip / S Ultra, and from 0.3.4 any phone with an explicit
 * profile, the Galaxy S25: [inScope]); Exynos; root probe ran and failed; free
 * space short for this phone's image (or a typical one).
 * WARN: phone has a profile but no session ran on it (S26 Ultra), or the
 * profile is off in this build (S25 Ultra); in-scope model without a profile;
 * unknown chip; form factor vs model prefix (or vs the profile) disagree; One
 * UI version not in a profile (tested: 9.0 = 90000); Android version differs
 * from the OneOS images (both are Android 17, SDK 37); CPU rule of the
 * phone's image ([CpuRules.forImage]); VoLTE-only carrier ([CarrierRules]);
 * no root manager found; root probe timed out; screen lock set or unknown
 * ([ScreenLockRule]); free space unknown.
 */
object CompatEvaluator {
    /** "Has run on: ColorOS 17 · Find N6 build on the Z Fold (F8U); Pixel 11 Fold on the Z Fold (F8U).", from the profiles' tested choices (the image table names the systems). */
    val TESTED_SCOPE: String get() = testedScope()

    fun testedScope(profiles: List<PhoneProfile> = Profiles.BUILT_IN, images: List<ImageRef> = Images.ALL): String {
        val runs = profiles.flatMap { p ->
            p.choices.filter { it.tested }.mapNotNull { c -> Images.byId(c.imageId, images)?.let { "${it.nameWithVariant} on the ${p.label}" } }
        }
        return if (runs.isEmpty()) "No session has run yet." else "Has run on: ${runs.joinToString("; ")}."
    }
    const val ID_ANDROID_DIFFERS = "android-version-differs"
    const val ID_ANDROID_MATCHES = "sdk-package"
    const val ID_PROFILE_DISABLED = "profile-disabled"
    const val ID_NO_PROFILE = "no-profile"
    const val ID_CARRIER = "carrier-volte"
    const val ID_OUT_OF_SCOPE = "model-out-of-scope"

    /**
     * The owner's scope: a Z Fold, Z Flip or S Ultra by model number, or a
     * phone that matches an explicit profile (all three ids, [Profiles]), such
     * as the Galaxy S25. Any other S-series model stays out of scope.
     */
    fun inScope(family: ModelFamily, profile: PhoneProfile?): Boolean = family.inScope || profile != null

    /**
     * [app] is the app that asks for root ("OneOS", or "OneOS Probe" in the
     * probe edition): the root findings tell the user which app to allow.
     */
    fun evaluate(
        f: DeviceFacts,
        profiles: List<PhoneProfile> = Profiles.BUILT_IN,
        images: List<ImageRef> = Images.ALL,
        sets: List<PackageSet> = PackageSets.ALL,
        app: String = "OneOS",
    ): CompatReport {
        val out = mutableListOf<Finding>()
        val family = f.family
        val profile = Profiles.resolve(f, profiles).profile
        // The profile's usual image (its first choice) for the CPU rule and free
        // space; Prepare and Switch use the image actually picked or staged.
        val choice = profile?.choices?.firstOrNull()
        val image = choice?.let { Images.byId(it.imageId, images) }
        val set = choice?.let { PackageSets.byId(it.packageSetId, sets) }

        // Brand, ABI, model scope (G11 and the owner's target list).
        if (!f.isSamsung) {
            out += Finding(
                "not-samsung", Level.BLOCK, "Not a Samsung phone",
                "OneOS runs next to One UI, so it needs a Samsung phone " +
                    "(brand '${f.brand}', maker '${f.manufacturer}').",
            )
        }
        if ("arm64-v8a" !in f.abis64) {
            out += Finding(
                "not-arm64", Level.BLOCK, "No 64-bit ARM support",
                "OS packages are arm64-v8a only; this phone reports " +
                    "'${f.abis64.joinToString().ifEmpty { "none" }}'.",
            )
        }
        if (f.isSamsung && !inScope(family, profile)) {
            val extra = profiles.filter { !ModelFamily.of(it.modelPrefix).inScope }
            out += Finding(
                ID_OUT_OF_SCOPE, Level.BLOCK, "Not a supported model",
                "OneOS supports Samsung flagships only: Galaxy Z Fold, Z Flip and S Ultra" +
                    extra.joinToString("") { ", and the ${it.label} (${it.ids})" } +
                    ". ${f.model} (${f.device.ifEmpty { "?" }}, ${f.soc.model.ifEmpty { "?" }}) is not one of them.",
            )
        }

        // Profile: model prefix AND codename AND SoC (Profiles).
        when {
            profile != null && !profile.enabled -> out += Finding(
                ID_PROFILE_DISABLED, Level.WARN, profile.disabledReason ?: "Not enabled in this build",
                "${profile.label} (${profile.ids}) has a profile, but this build does not switch on it.",
            )
            profile != null && profile.testedWithAnyImage -> out += Finding(
                "tested-model", Level.OK, "Tested phone",
                "Has run on the ${profile.label}: " +
                    profile.choices.filter { it.tested }.joinToString("; ") { c -> Images.byId(c.imageId, images)?.nameWithVariant ?: c.imageId } + ".",
            )
            profile != null -> out += Finding(
                "untested-model", Level.WARN, "Not tested on this model yet",
                "${testedScope(profiles, images)} A ${profile.label} (${f.model}) should behave the same way, " +
                    "but no session has run on one yet. You can continue after reading the warnings.",
            )
            f.isSamsung && family.inScope -> out += Finding(
                ID_NO_PROFILE, Level.WARN, "No OneOS package for this model yet",
                "${testedScope(profiles, images)} This build switches only on " +
                    profiles.filter { it.enabled }.joinToString(", ") { it.label } +
                    ". A ${family.label} (${f.model}, ${f.device.ifEmpty { "?" }}, ${f.soc.model.ifEmpty { "?" }}) " +
                    "needs its own profile; the tests and findings help make one.",
            )
        }
        if (profile != null && f.form.form != profile.form) {
            out += Finding(
                "profile-form-mismatch", Level.WARN, "Form factor differs from the profile",
                "The hardware says ${f.form.form.label}, the ${profile.label} profile is ${profile.form.label}. " +
                    "Switching refuses this.",
            )
        }

        // SoC.
        when (f.soc.vendor) {
            SocVendor.QUALCOMM -> out += Finding(
                "soc-snapdragon", Level.OK, "Snapdragon",
                "${f.soc.display}: the display path OneOS knows.",
            )
            // 0.4.17: an Exynos phone with its own profile (Galaxy S26+ Exynos, Z
            // Flip7, from 0.4.29 the A57) is a first run, not a block; any other stays blocked.
            SocVendor.EXYNOS -> out += if (profile != null) Finding(
                "soc-exynos", Level.WARN, "Exynos: first runs",
                "${f.soc.display}. Exynos phones have had only a few test sessions so far; the ${profile.label} profile " +
                    "is for its first sessions.",
            ) else Finding(
                "soc-exynos", Level.BLOCK, "Exynos is not supported yet",
                "${f.soc.display}. Only the Snapdragon display path is known; Exynos stays " +
                    "blocked until an Exynos profile exists.",
            )
            SocVendor.MEDIATEK, SocVendor.UNKNOWN -> out += Finding(
                "soc-unknown", Level.WARN, "Chip not recognised",
                "${f.soc.display}. Only Snapdragon has been tested.",
            )
        }

        // Form factor vs model number.
        if (f.form.mismatch) {
            val hw = f.form.hardwareForm?.label ?: "foldable"
            out += Finding(
                "form-prefix-mismatch", Level.WARN, "Form factor unclear",
                "The hardware says $hw, the model number ${f.model} says " +
                    "${f.form.prefixForm?.label}. OneOS goes by the hardware: ${f.form.form.label}.",
            )
        }

        // One UI version.
        val oneUi = f.oneUi
        if (oneUi == null) {
            if (f.isSamsung) {
                out += Finding(
                    "oneui-missing", Level.WARN, "One UI version not found",
                    "ro.build.version.oneui is '${f.oneUiRaw}'. OneOS has only run next to One UI.",
                )
            }
        } else if (oneUi.raw !in Profiles.ONE_UI_SEEN) {
            val seen = Profiles.ONE_UI_SEEN.sorted().mapNotNull { OneUiVersion.parse(it.toString()) }
            out += Finding(
                "oneui-unseen", Level.WARN, "One UI $oneUi not seen yet",
                "Profiles so far are from One UI ${seen.joinToString()}.",
            )
        }

        // Android version vs the OneOS images (a guest must match the host SDK).
        // WARN here; switching refuses a different version (BLOCK at switch time).
        val matching = images.filter { it.sdk == f.sdk }
        if (matching.isEmpty()) {
            val sdks = images.map { it.sdk }.distinct().sorted()
            val releases = sdks.joinToString(", ") { AndroidRelease.name(it) }
            out += Finding(
                ID_ANDROID_DIFFERS, Level.WARN,
                "Android version differs from the OneOS images ($releases); switching may not work",
                "This phone runs Android ${f.androidRelease.ifEmpty { AndroidRelease.name(f.sdk) }} (SDK ${f.sdk}); " +
                    "the OneOS images are Android $releases (SDK ${sdks.joinToString()}). A guest OS shares " +
                    "One UI's system services, so it must have the same Android version. Switching will " +
                    "refuse this phone until there is an image for its Android version.",
            )
        } else {
            out += Finding(
                ID_ANDROID_MATCHES, Level.OK, "Packages for Android SDK ${f.sdk}",
                matching.joinToString("; ") { p ->
                    p.label + if (p.testedOn != null) " (tested on ${p.testedOn})" else " (untested)"
                },
            )
        }

        // CPU: the rule of this phone's image; without a profile the Find N6
        // rule (SVE2, SME; MOPS has a fallback).
        out += if (image != null) CpuRules.forImage(image, f.cpu) else CpuRules.finding(f.cpu)

        // Calls in the guest (VoLTE-only carriers): a WARN here, a tick at Switch.
        f.carrier?.let { c ->
            val carrier = CarrierRules.finding(c)
            if (carrier.level == Level.WARN) out += carrier.copy(id = ID_CARRIER)
        }

        out += rootFinding(f, app)

        // Screen lock (G16): WARN here; SwitchGates refuses it at switch time.
        out += ScreenLockRule.finding(f.screenLockSet)

        // Free space (G9) for this phone's image and files, else a typical image.
        val storage = f.storage
        val need = if (image != null) SpaceRule.toStage(image, set) else SpaceRule.required()
        val session = if (image != null) "the ${image.shortName} image" else "a typical image"
        val parts = if (image != null) {
            "${Units.bytes(image.rawBytes)} image + files + 8 GB staged data + 1 GB logs + 2 GB margin"
        } else {
            "${Units.bytes(SpaceRule.TYPICAL_IMAGE_BYTES)} image + 8 GB staged data + 1 GB logs + 2 GB margin"
        }
        when {
            storage == null -> out += Finding(
                "free-space-unknown", Level.WARN, "Free space unknown",
                "Could not read free space on /data. A session with $session needs about ${Units.bytes(need)}.",
            )
            storage.freeBytes < need -> out += Finding(
                "free-space-short", Level.BLOCK, "Not enough free space",
                "${Units.bytes(storage.freeBytes)} free on /data; a session with $session needs about " +
                    "${Units.bytes(need)} ($parts).",
            )
            else -> out += Finding(
                "free-space", Level.OK, "Enough free space",
                "${Units.bytes(storage.freeBytes)} free on /data; about ${Units.bytes(need)} needed.",
            )
        }

        // Battery (G10) is a session gate, not compatibility: only a note.
        val b = f.battery
        if (b != null && ((b.levelPercent < 30 && !b.charging) || (b.temperatureC ?: 0f) >= 42f)) {
            out += Finding(
                "battery-now", Level.INFO, "Battery would stop a session right now",
                "Before a session the battery must be at 30% or charging, and under 42 °C.",
            )
        }

        return CompatReport(out)
    }

    private fun rootFinding(f: DeviceFacts, app: String): Finding {
        val kind = f.rootKind
        val probe = f.root.probe
        return when {
            probe?.state == SuState.GRANTED -> Finding(
                "root-ok", Level.OK, "Root works",
                "su -c id answered uid 0" +
                    (probe.context?.let { " ($it)" } ?: "") +
                    if (kind != RootKind.NONE && kind != RootKind.OTHER) ", ${kind.label}." else ".",
            )
            probe?.state == SuState.TIMEOUT -> Finding(
                "root-timeout", Level.WARN, "Root did not answer in time",
                "Allow $app in your root manager, then check root again.",
            )
            probe != null -> Finding(
                "root-missing", Level.BLOCK, "Root does not work for $app",
                "su -c id: ${probe.state.name.lowercase().replace('_', ' ')}" +
                    (probe.uid?.let { " (uid $it)" } ?: "") +
                    ". $app needs root from KernelSU, Magisk or APatch, allowed for $app.",
            )
            kind != RootKind.NONE -> Finding(
                "root-unchecked", Level.INFO, "Root manager found: ${kind.label}",
                "Tap Check root to confirm that su works for $app.",
            )
            else -> Finding(
                "root-not-found", Level.WARN, "No root manager found",
                "$app needs root (KernelSU, Magisk or APatch). KernelSU hides su from apps it " +
                    "has not allowed: allow $app in KernelSU first, then tap Check root.",
            )
        }
    }
}
