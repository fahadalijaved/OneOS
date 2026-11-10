package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** The cases are the reports up to 2026-11-09 (model, bootloader, vendor model, One UI). */
class CustomRomTest {
    private fun check(model: String, bootloader: String, vendor: String, oneUi: String) =
        CustomRomRule.check(CustomRomRule.Signals(model, bootloader, vendor, oneUi))

    @Test
    fun stockPhonesPass() {
        val stock = listOf(
            "SM-A346E" to "A346EXXUGGZJ9", "SM-S908U1" to "S908U1UEU8EXK1", "SM-N986N" to "N986NKSS4HYB1",
            "SM-X110" to "X110XXSB2BYE1", "SM-S901W" to "S901WVLS6FYE1", "SM-A155M" to "A155MUBS6CYG2",
            "SM-F966B" to "F966BXXU1AYG8", "SM-S166V" to "S166VUDS2AYF1", "SM-S9380" to "S9380ZCS3AYH1",
            "SM-W2025" to "W2025ZCU1AYH1", "SC-51F" to "SC51FOMU1BYD1", "SCG35" to "SCG35KDU1AYE3",
        )
        for ((model, bl) in stock) {
            assertNull(model, check(model, bl, model, "90000"))
            // The vendor model may not be readable; the bootloader alone still passes.
            assertNull(model, check(model, bl, "", "90000"))
            // Neither readable: nothing to go by, so nothing is refused.
            assertNull(model, check(model, "unknown", "", "90000"))
        }
    }

    @Test
    fun portsAreRefused() {
        val ports = listOf(
            Triple("SM-S901B", "A217FXXSCDXE2", "SM-A217F"),
            Triple("SM-S901B", "G991BXXSJHZC2", "SM-G991B"),
            Triple("SM-A576B", "A515FXXU8HWI5", "SM-A515F"),
            Triple("SM-A546S", "A515FXXU8HWI5", "SM-A515F"),
            Triple("SM-S926B", "G986BXXSFHWB2", "SM-G986B"),
        )
        for ((model, bl, vendor) in ports) {
            assertEquals(model, CustomRomRule.R_PORT, check(model, bl, vendor, "80000")?.reason)
            assertEquals(model, CustomRomRule.R_PORT, check(model, bl, "", "90000")?.reason)
            assertEquals(model, CustomRomRule.R_PORT, check(model, "unknown", vendor, "90000")?.reason)
            assertEquals(Level.BLOCK, check(model, bl, vendor, "90000")?.level)
        }
        // One UI with a model name that is no Samsung model number.
        assertEquals(CustomRomRule.R_PORT, check("Galaxy S25 Ultra", "A515FXXU8HWI5", "SM-A515F", "90000")?.reason)
    }

    /** 0.4.84: a US phone on the other US firmware (carrier U, unlocked U1) is stock, not a port. */
    @Test
    fun usCarrierAndUnlockedModelsAreOnePhone() {
        val same = listOf(
            // The S26+ of 2026-11-10: U1 phone, U firmware.
            Triple("SM-S947U1", "S947USQU5BZJA", "SM-S947U"),
            // The other way round: U phone, U1 firmware.
            Triple("SM-S947U", "S947U1UEU5BZJA", "SM-S947U1"),
            Triple("SM-S908U1", "S908USQS8EXK1", "SM-S908U"),
            Triple("SM-F966U", "F966U1UEU1AYG8", "SM-F966U1"),
        )
        for ((model, bl, vendor) in same) {
            assertNull(model, check(model, bl, vendor, "90000"))
            assertNull(model, check(model, bl, "", "90000"))
            assertNull(model, check(model, "unknown", vendor, "90000"))
            // Without One UI it is still a custom ROM on that phone.
            assertEquals(model, CustomRomRule.R_NOT_ONE_UI, check(model, bl, vendor, "")?.reason)
        }
        assertEquals("S947U", CustomRomRule.family("S947U1"))
        assertEquals("S947U", CustomRomRule.family("S947U"))
        assertEquals("A346E", CustomRomRule.family("A346E"))
        // Only U and U1 are one phone: another phone's or another region's firmware stays refused.
        for ((model, bl, vendor) in listOf(
            Triple("SM-S947U1", "S942USQU5BZJA", "SM-S942U"),
            Triple("SM-S947U1", "S948USQU5BZJA", "SM-S948U"),
            Triple("SM-S947B", "S947USQU5BZJA", "SM-S947U"),
            Triple("SM-S947U1", "S947BXXU5BZJA", "SM-S947B"),
            Triple("SM-S947W", "S947U1UEU5BZJA", "SM-S947U1"),
            Triple("SM-S947U1", "S947NKSU5BZJA", "SM-S947N"),
        )) {
            assertEquals(model, CustomRomRule.R_PORT, check(model, bl, vendor, "90000")?.reason)
            assertEquals(model, CustomRomRule.R_PORT, check(model, bl, "", "90000")?.reason)
            assertEquals(model, CustomRomRule.R_PORT, check(model, "unknown", vendor, "90000")?.reason)
        }
    }

    @Test
    fun romsWithoutOneUiAreRefused() {
        assertEquals(CustomRomRule.R_NOT_ONE_UI, check("SM-G973F", "G973FXXUFHVJ1", "SM-G973F", "")?.reason)
        assertEquals(CustomRomRule.R_NOT_ONE_UI, check("SM-G973F", "G973FXXUFHVJ1", "", "")?.reason)
    }

    @Test
    fun otherMakersAreRefused() {
        for ((model, bl, vendor) in listOf(
            Triple("motorola one", "0xC40A", "motorola one"),
            Triple("CPH2591", "unknown", "CPH2591"),
            Triple("ALT-LX1", "unknown", "Bengal for arm64"),
        )) {
            assertEquals(model, CustomRomRule.R_NOT_SAMSUNG, check(model, bl, vendor, "")?.reason)
        }
    }

    /** The other systems: their own model, no One UI, on the Samsung vendor and bootloader. */
    @Test
    fun guestSystemsPass() {
        for (model in listOf("PD2609MA", "CPH2745", "Pixel 11 Pro Fold", "2510DPN6CC", "A059")) {
            assertNull(model, check(model, "F971BXXU1AZH5", "SM-F971B", ""))
            assertNull(model, check(model, "F971BXXU1AZH5", "", ""))
            assertNull(model, check(model, "S938BXXS6BYI1", "SM-S938B", ""))
        }
    }

    @Test
    fun factsCarryTheRule() {
        assertEquals("SM-A346E".let(CustomRomRule::code), "A346E")
        assertEquals("SC51F", CustomRomRule.code("SC-51F"))
        assertEquals("", CustomRomRule.code("CPH2591"))
    }
}
