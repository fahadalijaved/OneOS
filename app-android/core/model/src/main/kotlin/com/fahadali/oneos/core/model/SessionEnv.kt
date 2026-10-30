package com.fahadali.oneos.core.model

/**
 * `$STAGE/session.env`, the app's settings for one session (AA5, PLAN.md
 * contract). One `KEY=VALUE` per line, only the keys of [ALLOWED], each with
 * a value its pattern allows, every key present once: the scripts read
 * `${ONEOS_*:-default}`, so a missing key would silently fall back to the
 * Fold defaults (`ONEOS_GUEST_FORM=fold` on an S Ultra). Root runs
 * [validate]'s rules again before it sources the file with `set -a`.
 *
 * Nothing here can turn the way back off: the return knobs (`ONEOS_RETURN_MAX`,
 * `ONEOS_RETURN_KEYS`), `ONEOS_STOCK_SF`, `ONEOS_KEEP_FOLD_LAYOUT`,
 * `ONEOS_PREPARE_ONLY` (only root's dry-run launch sets it) and the tunnel keys
 * are not on the list, and `ONEOS_LOGCAT` may only be 1. The scripts' own
 * defaults apply to them.
 *
 * [RETURN_MODE] (0.4.7) is always `inplace`: Back to One UI restarts One UI's
 * framework on the same boot (run 48, docs/inplace-return.md), and any check
 * that fails there still ends in the full reboot. It cannot select anything
 * else, so it cannot turn a way back off either.
 *
 * [HIDE_GMS] (0.3.3) is the one key a launch changes: Prepare writes 0, and
 * root's `launch` writes the Switch screen's choice for that launch only. 1 is
 * allowed only when the staged image's Google services may be hidden
 * ([ImageRef.gmsHideable]); guest_prepare.sh then hides them for the session.
 * The Pixel image has them but presents its own GmsCore ([ImageRef.presentsGms]),
 * which the session scripts refuse to hide, so 0.3.7 has no image that may.
 *
 * [HEAT_CAP] (0.4.23) is the other: Prepare writes 1, and root's `launch`
 * writes Advanced's Cool down when hot. 1 caps the CPU while the skin is hot
 * (oneos_switch.sh), 0 leaves it at full clock. Neither touches the way back.
 * [SEC_IMS] (0.4.20) is the second key a launch changes: Prepare writes 0, a
 * launch writes the Advanced screen's choice. 1 stages this phone's own Samsung
 * IMS app into the guest for VoLTE (guest_prepare.sh, docs/samsung-ims-in-guest.md);
 * any image, any Samsung phone: the scripts check the phone's files themselves.
 * [EDM_STUB] (0.4.32) is the third: Prepare writes 0, a launch writes Advanced's
 * choice. 1 registers a stand-in for Knox's edmnativehelper while the guest runs
 * (oneos_switch.sh, switcher/patches/OneOSEdmStub.java). One UI's cameraserver is
 * shared with the guest and asks Knox on every camera open; only One UI's
 * system_server registers that name, so the lookup blocks libbinder's full 5 s
 * while the camera app gives up at 3 s (Z Flip5 reports on 0.4.29 and 0.4.31,
 * both images, two different camera apps). Opt-in: the stub answers every code
 * "allowed", and answering wrongly would turn the camera off rather than slow.
 */
object SessionEnv {
    const val FILE_NAME = "session.env"
    const val MAX_BYTES = 4096

    /** The app's gap splash; root starts it with `am start -n` (not exported). */
    const val SPLASH_COMPONENT = "com.fahadali.oneos/.ui.GapSplashActivity"

    /** 1: hide Play services, the Play Store and their helpers in the guest for this session (guest_prepare.sh). */
    const val HIDE_GMS = "ONEOS_GUEST_HIDE_GMS"

    /** 1: cap the CPU from 45 °C skin during the session (oneos_switch.sh); 0: full clock all session. */
    const val HEAT_CAP = "ONEOS_HEAT_CAP"
    /** 1: this phone's Samsung IMS app (VoLTE) staged into the guest for this session (guest_prepare.sh); experimental. */
    const val SEC_IMS = "ONEOS_GUEST_SEC_IMS"
    /** 1: answer Knox's edmnativehelper while the guest runs, so a camera open is not 5 s late (oneos_switch.sh); experimental. */
    const val EDM_STUB = "ONEOS_GUEST_EDM_STUB"

    /** How the return brings One UI back: always in place, with the reboot as its failsafe (return_to_oneui.sh). */
    const val RETURN_MODE = "ONEOS_RETURN_MODE"

    /** Every key the app writes, in file order, with the values it may have. */
    val ALLOWED: Map<String, Regex> = linkedMapOf(
        "ONEOS_APP" to Regex("1"),
        "ONEOS_PROFILE" to Regex("[a-z0-9][a-z0-9-]{0,31}"),
        "ONEOS_SPLASH_COMPONENT" to Regex(Regex.escape(SPLASH_COMPONENT)),
        "ONEOS_WALLPAPER_PROBE" to Regex("0"),
        "ONEOS_RECORD" to Regex("0"),
        "ONEOS_LOGCAT" to Regex("1"),
        "ONEOS_GUEST_FORM" to Regex("fold|phone"),
        "ONEOS_GUEST_FOLD" to Regex("layout|off"),
        "ONEOS_COVER_TSP" to Regex("[01]"),
        "ONEOS_GUEST_FOLD_CONTINUE" to Regex("[01]"),
        "ONEOS_GUEST_UNFOLD_PORTRAIT" to Regex("[01]"),
        "ONEOS_GUEST_COMPACT_WINDOW" to Regex("[01]"),
        "ONEOS_GUEST_WALLPAPER_GRID" to Regex("[01]"),
        HIDE_GMS to Regex("[01]"),
        HEAT_CAP to Regex("[01]"),
        SEC_IMS to Regex("[01]"),
        EDM_STUB to Regex("[01]"),
        RETURN_MODE to Regex("inplace"),
    )

    /** Never written; root refuses a file with any of them, any `ONEOS_TUNNEL_*` key, or any key not in [ALLOWED]. */
    val FORBIDDEN: Map<String, String> = linkedMapOf(
        "ONEOS_RETURN_MAX" to "0 turns off auto-return and the Volume Up+Down return",
        "ONEOS_RETURN_KEYS" to "0 turns off the Volume Up+Down return",
        "ONEOS_STOCK_SF" to "1 runs the guest without the composer patch",
        "ONEOS_KEEP_FOLD_LAYOUT" to "1 keeps the host's fold layout",
        "ONEOS_PREPARE_ONLY" to "only root's dry-run launch sets it",
        "ONEOS_TUNNEL_SERVER" to "server tunnel, not shipped",
        "ONEOS_TUNNEL_PORT" to "server tunnel, not shipped",
    )
    const val FORBIDDEN_PREFIX = "ONEOS_TUNNEL_"

    /** Fold (F8U): the scripts' defaults today, written out. */
    val FOLD_FORM: Map<String, String> = linkedMapOf(
        "ONEOS_GUEST_FORM" to "fold",
        "ONEOS_GUEST_FOLD" to "layout",
        "ONEOS_COVER_TSP" to "1",
        "ONEOS_GUEST_FOLD_CONTINUE" to "1",
        "ONEOS_GUEST_UNFOLD_PORTRAIT" to "1",
        "ONEOS_GUEST_COMPACT_WINDOW" to "1",
        "ONEOS_GUEST_WALLPAPER_GRID" to "1",
    )

    /**
     * Bar (S Ultra): phone form and every fold step off, so the touch-IC
     * writer, the fold layout and the fold grid cannot run (DA1-DA4).
     */
    val BAR_FORM: Map<String, String> = linkedMapOf(
        "ONEOS_GUEST_FORM" to "phone",
        "ONEOS_GUEST_FOLD" to "off",
        "ONEOS_COVER_TSP" to "0",
        "ONEOS_GUEST_FOLD_CONTINUE" to "0",
        "ONEOS_GUEST_UNFOLD_PORTRAIT" to "0",
        "ONEOS_GUEST_COMPACT_WINDOW" to "0",
        "ONEOS_GUEST_WALLPAPER_GRID" to "0",
    )

    /**
     * The values for [profile], in file order (also for a disabled profile, for
     * tests and display). Google services stay on ([HIDE_GMS]=0): owner, once a
     * run with them works they stay on; a launch may turn them off for itself.
     */
    fun values(profile: PhoneProfile): LinkedHashMap<String, String> {
        val form = when (profile.form) {
            FormFactor.FOLD -> FOLD_FORM
            FormFactor.BAR -> BAR_FORM
            // 0.4.17, Galaxy Z Flip7: a phone on the main panel; no cover layout yet.
            FormFactor.FLIP -> BAR_FORM
        }
        val out = linkedMapOf(
            "ONEOS_APP" to "1",
            "ONEOS_PROFILE" to profile.id,
            "ONEOS_SPLASH_COMPONENT" to SPLASH_COMPONENT,
            "ONEOS_WALLPAPER_PROBE" to "0",
            "ONEOS_RECORD" to "0",
            "ONEOS_LOGCAT" to "1",
        )
        out.putAll(form)
        out[HIDE_GMS] = "0"
        out[HEAT_CAP] = "1"
        out[SEC_IMS] = "0"
        out[EDM_STUB] = "0"
        out[RETURN_MODE] = "inplace"
        return out
    }

    /** session.env for [profile]. Refuses a disabled profile and anything [validate] would refuse. */
    fun generate(profile: PhoneProfile, profiles: List<PhoneProfile> = Profiles.BUILT_IN): String {
        require(profile.enabled) { "profile ${profile.id} is disabled: ${profile.disabledReason}" }
        val text = values(profile).entries.joinToString("") { "${it.key}=${it.value}\n" }
        val problems = validate(text, profiles)
        require(problems.isEmpty()) { problems.joinToString("; ") }
        return text
    }

    /**
     * Problems with a session.env text; empty = root may source it. Fails closed
     * on anything unexpected. [image] is the staged image: [HIDE_GMS]=1 only
     * when its Google services may be hidden ([ImageRef.gmsHideable]; null: never).
     */
    fun validate(text: String, profiles: List<PhoneProfile> = Profiles.BUILT_IN, image: ImageRef? = null): List<String> {
        if (text.length > MAX_BYTES) return listOf("over $MAX_BYTES bytes")
        val p = mutableListOf<String>()
        if (!text.endsWith("\n")) p += "must end with a newline"
        val seen = linkedMapOf<String, String>()
        val present = mutableSetOf<String>()
        for ((i, line) in text.removeSuffix("\n").split('\n').withIndex()) {
            val eq = line.indexOf('=')
            if (eq <= 0) {
                p += "line ${i + 1} is not KEY=VALUE"
                continue
            }
            val key = line.substring(0, eq)
            val value = line.substring(eq + 1)
            val rule = ALLOWED[key]
            val again = !present.add(key)
            when {
                key in FORBIDDEN || key.startsWith(FORBIDDEN_PREFIX) -> p += "forbidden key $key"
                rule == null -> p += "key '${key.take(64)}' is not allowed"
                again -> p += "$key set twice"
                !rule.matches(value) -> p += "$key='${value.take(64)}' is not allowed"
                else -> seen[key] = value
            }
        }
        for (k in ALLOWED.keys) if (k !in present) p += "$k missing"
        val id = seen["ONEOS_PROFILE"] ?: return p
        val profile = Profiles.byId(id, profiles)
        when {
            profile == null -> p += "unknown profile $id"
            !profile.enabled -> p += "profile $id is disabled"
            else -> for ((k, v) in values(profile)) {
                val got = seen[k] ?: continue
                when {
                    // Either value is the launch's own choice (the pattern allows only 0 or 1).
                    k == HEAT_CAP -> Unit
                    k == SEC_IMS -> {} // 0 or 1, a launch's choice on any phone and image
                    k == EDM_STUB -> {} // 0 or 1, a launch's choice on any phone and image
                    k != HIDE_GMS -> if (got != v) p += "$k=$got does not match profile $id ($v)"
                    got == "1" && image?.gmsHideable != true -> p += if (image?.googleServices == true) {
                        "$HIDE_GMS=1, but the ${image.shortName} image's sessions present Google services, which cannot be hidden"
                    } else {
                        "$HIDE_GMS=1, but ${image?.let { "the ${it.shortName} image" } ?: "the image"} has no Google services"
                    }
                }
            }
        }
        return p
    }
}
