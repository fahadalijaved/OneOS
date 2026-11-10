package com.fahadali.oneos.core.model

/**
 * Custom ROMs (0.4.74, owner: "customrom reports need to be rejected ... in the app itself",
 * "otherwise it will keep on filling our findings"): no switching and no reports of any kind.
 *
 * A port keeps the real phone in two places a ROM does not rewrite: the bootloader's version
 * (`ro.bootloader`, [android.os.Build.BOOTLOADER], always starts with the model code, e.g.
 * A346EXXUGGZJ9 on the SM-A346E) and the vendor partition (`ro.product.vendor.model`). Reports
 * up to 2026-11-09: the stock phones of every report with properties (about 150, A, S, Z, E, M,
 * Tab, US U1, Korean N, Japanese-style codes) matched both; the ports did not: "SM-S901B" on an
 * A21s (A217F) and an S21 (G991B), "SM-A576B" and "SM-A546S" on an A51 (A515F), "SM-S926B" on an
 * S20+ (G986B).
 *
 * 0.4.84, the US carrier (U) and unlocked (U1) models (owner, 2026-11-10: "This isnt custom its U/U1
 * variant change for US devices. Allow this"): they are one phone and take each other's stock
 * firmware, and the model name stays the phone's own while the bootloader and the vendor partition
 * are the firmware's. A Galaxy S26+ that says SM-S947U1 on the U firmware (bootloader S947USQU5BZJA,
 * vendor SM-S947U) was refused as a port. The two count as the same model ([family]); every other
 * letter still has to match.
 *
 * The other systems never trip it: they have no `ro.build.version.oneui` (so never [R_PORT]),
 * their model is another maker's (so never [R_NOT_ONE_UI]), and they run on the Samsung
 * vendor and bootloader (so never [R_NOT_SAMSUNG]).
 */
object CustomRomRule {
    const val ID = "custom-rom"

    /** One UI from another phone: the model differs from the bootloader's or the vendor's. */
    const val R_PORT = "port"

    /** A Samsung phone without One UI (LineageOS and the like). */
    const val R_NOT_ONE_UI = "not-one-ui"

    /** Not Samsung hardware at all (Motorola, OnePlus, Huawei, ...). */
    const val R_NOT_SAMSUNG = "not-samsung-hardware"

    data class Signals(
        /** `ro.product.model`. */
        val model: String,
        /** `ro.bootloader` ([android.os.Build.BOOTLOADER]). */
        val bootloader: String,
        /** `ro.product.vendor.model`; empty when it could not be read. */
        val vendorModel: String,
        /** `ro.build.version.oneui`. */
        val oneUiRaw: String,
    )

    private val SAMSUNG_BOOTLOADER = Regex("[A-Z]{1,3}[0-9]{3,4}[A-Z0-9]{0,3}[A-Z]{2,3}[A-Z0-9]{4,8}")
    private val SAMSUNG_CODE = Regex("(?:[A-Z]{1,2}[0-9]{3,4}[A-Z0-9]{0,3}|SC[0-9]{2}[A-Z]|SCG[0-9]{2})")

    /** "SM-A346E" -> "A346E", "SC-51F" -> "SC51F", "SCG35" -> "SCG35"; "" when it is not a Samsung model number. */
    fun code(model: String): String {
        val m = model.trim().uppercase()
        val c = when {
            m.startsWith("SM-") -> m.substring(3)
            m.startsWith("SC-") || m.startsWith("SCG") -> m.replace("-", "")
            else -> return ""
        }
        return if (SAMSUNG_CODE.matches(c)) c else ""
    }

    private val US_UNLOCKED = Regex("[A-Z]{1,2}[0-9]{3,4}U1")

    /** The US unlocked model's code without its "1": "S947U1" -> "S947U" (the carrier model's); others as they are. */
    fun family(code: String): String = if (US_UNLOCKED.matches(code)) code.dropLast(1) else code

    /** A Samsung bootloader version (not "unknown", not another maker's). */
    fun samsungBootloader(bootloader: String): Boolean = SAMSUNG_BOOTLOADER.matches(bootloader.trim().uppercase())

    fun check(s: Signals): Finding? {
        val oneUi = s.oneUiRaw.isNotBlank()
        val bl = s.bootloader.trim().uppercase()
        val blSamsung = samsungBootloader(bl)
        val modelCode = code(s.model)
        val vendorCode = code(s.vendorModel)
        // U and U1 are one phone: compared without the "1" (a U1 bootloader starts with the U code too).
        val modelFamily = family(modelCode)
        val vendorFamily = family(vendorCode)
        val samsungHardware = blSamsung || vendorCode.isNotEmpty()
        // The phone itself, as far as the bootloader and the vendor partition tell.
        val real = vendorCode.ifEmpty { if (blSamsung) bl.take(modelCode.length.coerceAtLeast(5)) else "" }

        val port = oneUi && samsungHardware && (
            modelCode.isEmpty() ||
                (blSamsung && !bl.startsWith(modelFamily)) ||
                (vendorCode.isNotEmpty() && vendorFamily != modelFamily)
            )
        if (port) {
            return finding(
                R_PORT, "Custom ROM: One UI from another phone",
                "This phone says it is ${s.model.ifBlank { "?" }}, but its bootloader (${s.bootloader.ifBlank { "?" }})" +
                    (if (s.vendorModel.isNotBlank()) " and vendor (${s.vendorModel})" else "") +
                    " say it is ${if (real.isNotEmpty()) "the SM-$real" else "another phone"}. OneOS runs on stock One UI " +
                    "only, so it does not switch or send reports here. If this is stock firmware, turn off any module " +
                    "that changes the model name and restart.",
            )
        }
        val sameModel = modelCode.isNotEmpty() && ((blSamsung && bl.startsWith(modelFamily)) || vendorFamily == modelFamily)
        if (!oneUi && sameModel) {
            return finding(
                R_NOT_ONE_UI, "Custom ROM: not One UI",
                "This ${s.model} runs a system without One UI (no ro.build.version.oneui). OneOS runs next to stock " +
                    "One UI only, so it does not switch or send reports here.",
            )
        }
        if (!oneUi && !samsungHardware && modelCode.isEmpty()) {
            return finding(
                R_NOT_SAMSUNG, "Not a Samsung phone",
                "${s.model.ifBlank { "This phone" }} is not a Samsung phone (bootloader '${s.bootloader.ifBlank { "?" }}'). " +
                    "OneOS runs next to stock One UI only, so it does not switch or send reports here.",
            )
        }
        return null
    }

    private fun finding(reason: String, title: String, detail: String) = Finding(ID, Level.BLOCK, title, detail, reason)
}
