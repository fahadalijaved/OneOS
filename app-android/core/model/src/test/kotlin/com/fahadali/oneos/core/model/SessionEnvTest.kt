package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

class SessionEnvTest {
    @Test
    fun goldenF8u() {
        assertEquals(
            """
            ONEOS_APP=1
            ONEOS_PROFILE=f8u
            ONEOS_SPLASH_COMPONENT=com.fahadali.oneos/.ui.GapSplashActivity
            ONEOS_WALLPAPER_PROBE=0
            ONEOS_RECORD=0
            ONEOS_LOGCAT=1
            ONEOS_GUEST_FORM=fold
            ONEOS_GUEST_FOLD=layout
            ONEOS_COVER_TSP=1
            ONEOS_GUEST_FOLD_CONTINUE=1
            ONEOS_GUEST_UNFOLD_PORTRAIT=1
            ONEOS_GUEST_COMPACT_WINDOW=1
            ONEOS_GUEST_WALLPAPER_GRID=1
            ONEOS_GUEST_HIDE_GMS=0
            ONEOS_HEAT_CAP=1
            ONEOS_GUEST_SEC_IMS=0
            ONEOS_GUEST_EDM_STUB=0
            ONEOS_RETURN_MODE=inplace

            """.trimIndent(),
            SessionEnv.generate(Profiles.F8U),
        )
    }

    @Test
    fun goldenS26Ultra() {
        assertEquals(
            """
            ONEOS_APP=1
            ONEOS_PROFILE=s-ultra-8850
            ONEOS_SPLASH_COMPONENT=com.fahadali.oneos/.ui.GapSplashActivity
            ONEOS_WALLPAPER_PROBE=0
            ONEOS_RECORD=0
            ONEOS_LOGCAT=1
            ONEOS_GUEST_FORM=phone
            ONEOS_GUEST_FOLD=off
            ONEOS_COVER_TSP=0
            ONEOS_GUEST_FOLD_CONTINUE=0
            ONEOS_GUEST_UNFOLD_PORTRAIT=0
            ONEOS_GUEST_COMPACT_WINDOW=0
            ONEOS_GUEST_WALLPAPER_GRID=0
            ONEOS_GUEST_HIDE_GMS=0
            ONEOS_HEAT_CAP=1
            ONEOS_GUEST_SEC_IMS=0
            ONEOS_GUEST_EDM_STUB=0
            ONEOS_RETURN_MODE=inplace

            """.trimIndent(),
            SessionEnv.generate(Profiles.S_ULTRA_8850),
        )
    }

    @Test
    fun s25UltraGetsTheBarSet() {
        val text = SessionEnv.generate(Profiles.S_ULTRA_8750)
        val v = SessionEnv.values(Profiles.S_ULTRA_8750)
        assertEquals("s-ultra-8750", v["ONEOS_PROFILE"])
        assertEquals(SessionEnv.BAR_FORM, v.filterKeys { it in SessionEnv.BAR_FORM })
        assertEquals(emptyList<String>(), SessionEnv.validate(text))
    }

    @Test
    fun galaxyS25GetsTheBarSet() {
        val text = SessionEnv.generate(Profiles.S_8750)
        val v = SessionEnv.values(Profiles.S_8750)
        assertEquals("s-8750", v["ONEOS_PROFILE"])
        assertEquals(SessionEnv.BAR_FORM, v.filterKeys { it in SessionEnv.BAR_FORM })
        assertEquals(emptyList<String>(), SessionEnv.validate(text))
    }

    @Test
    fun forbiddenKeysAreNeverEmitted() {
        for (p in Profiles.BUILT_IN.filter { it.enabled }) {
            val text = SessionEnv.generate(p)
            val keys = text.lines().filter { it.isNotEmpty() }.map { it.substringBefore('=') }
            assertEquals(SessionEnv.ALLOWED.keys.toList(), keys)
            for (k in SessionEnv.FORBIDDEN.keys) assertFalse("${p.id} $k", text.contains(k))
            assertFalse(text.contains(SessionEnv.FORBIDDEN_PREFIX))
            assertFalse(text.contains("ONEOS_LOGCAT=0"))
            // The only return key: in place, never MAX/KEYS (0.4.7).
            assertEquals(listOf("ONEOS_RETURN_MODE=inplace"), text.lines().filter { "RETURN" in it })
            assertFalse(text.contains("PREPARE_ONLY"))
            // Only characters that need no quoting when root sources the file.
            assertTrue(text.all { it == '\n' || it.isLetterOrDigit() || it in "=_./-" })
        }
    }

    @Test
    fun allowListValuesCannotTurnTheWayBackOff() {
        val allowed = SessionEnv.ALLOWED
        assertFalse(allowed.containsKey("ONEOS_RETURN_MAX"))
        assertFalse(allowed.containsKey("ONEOS_RETURN_KEYS"))
        assertFalse(allowed.getValue("ONEOS_RETURN_MODE").matches("reboot"))
        assertFalse(allowed.getValue("ONEOS_LOGCAT").matches("0"))
        assertFalse(allowed.getValue("ONEOS_GUEST_FORM").matches("tablet"))
        assertFalse(allowed.getValue("ONEOS_SPLASH_COMPONENT").matches("com.wewaffles.onelineage/.SplashActivity"))
        assertTrue(SessionEnv.FORBIDDEN.keys.none { it in allowed })
    }

    @Test
    fun validateFailsClosed() {
        val good = SessionEnv.generate(Profiles.S_ULTRA_8850)
        assertEquals(emptyList<String>(), SessionEnv.validate(good))
        assertEquals(emptyList<String>(), SessionEnv.validate(SessionEnv.generate(Profiles.F8U)))

        fun problems(text: String) = SessionEnv.validate(text)

        assertTrue(problems(good + "ONEOS_RETURN_MAX=0\n").contains("forbidden key ONEOS_RETURN_MAX"))
        // 0.4.23: Cool down when hot is the launch's choice, 0 or 1 only.
        assertTrue(good.contains("ONEOS_HEAT_CAP=1\n"))
        assertEquals(emptyList<String>(), problems(good.replace("ONEOS_HEAT_CAP=1", "ONEOS_HEAT_CAP=0")))
        assertTrue(problems(good.replace("ONEOS_HEAT_CAP=1", "ONEOS_HEAT_CAP=2")).isNotEmpty())
        assertTrue(problems(good + "ONEOS_RETURN_KEYS=0\n").contains("forbidden key ONEOS_RETURN_KEYS"))
        // 0.4.7: the return is always in place (a failed check reboots); nothing else may be asked for.
        assertTrue(good.contains("ONEOS_RETURN_MODE=inplace\n"))
        assertTrue(problems(good.replace("ONEOS_RETURN_MODE=inplace", "ONEOS_RETURN_MODE=reboot")).isNotEmpty())
        assertTrue(problems(good.replace("ONEOS_RETURN_MODE=inplace\n", "")).contains("ONEOS_RETURN_MODE missing"))
        assertTrue(problems(good + "ONEOS_STOCK_SF=1\n").contains("forbidden key ONEOS_STOCK_SF"))
        assertTrue(problems(good + "ONEOS_KEEP_FOLD_LAYOUT=1\n").contains("forbidden key ONEOS_KEEP_FOLD_LAYOUT"))
        assertTrue(problems(good + "ONEOS_PREPARE_ONLY=1\n").contains("forbidden key ONEOS_PREPARE_ONLY"))
        assertTrue(problems(good + "ONEOS_TUNNEL_HOST=x\n").contains("forbidden key ONEOS_TUNNEL_HOST"))
        assertTrue(problems(good + "ONEOS_GUEST_5G=1\n").contains("key 'ONEOS_GUEST_5G' is not allowed"))
        assertTrue(problems(good.replace("ONEOS_LOGCAT=1", "ONEOS_LOGCAT=0")).contains("ONEOS_LOGCAT='0' is not allowed"))
        assertTrue(problems(good + "ONEOS_RECORD=0\n").contains("ONEOS_RECORD set twice"))
        assertTrue(problems(good.replace("ONEOS_GUEST_FORM=phone\n", "")).contains("ONEOS_GUEST_FORM missing"))
        assertTrue(problems(good.removeSuffix("\n")).contains("must end with a newline"))
        assertTrue(problems(good.replace("\n", "\r\n")).isNotEmpty())
        assertTrue(problems("# comment\n$good").contains("line 1 is not KEY=VALUE"))
        assertTrue(problems("$good\n").contains("line 19 is not KEY=VALUE"))
        assertTrue(problems(good.replace("ONEOS_APP=1", "export ONEOS_APP=1")).isNotEmpty())
        assertTrue(problems(good.replace("ONEOS_GUEST_FOLD=off", "ONEOS_GUEST_FOLD=\$(reboot)")).isNotEmpty())
        // A fold value in an S Ultra file: the profile decides the form.
        assertTrue(problems(good.replace("ONEOS_COVER_TSP=0", "ONEOS_COVER_TSP=1")).contains("ONEOS_COVER_TSP=1 does not match profile s-ultra-8850 (0)"))
        assertTrue(problems(good.replace("ONEOS_GUEST_FORM=phone", "ONEOS_GUEST_FORM=fold")).isNotEmpty())
        assertTrue(problems(good.replace("s-ultra-8850", "s-ultra-9999")).contains("unknown profile s-ultra-9999"))
        assertTrue(problems("").isNotEmpty())
        assertTrue(problems("A".repeat(SessionEnv.MAX_BYTES + 1)).isNotEmpty())
    }

    /**
     * ONEOS_GUEST_HIDE_GMS: 0 from Prepare; 1 (a launch's choice) only with an
     * image whose Google services may be hidden. 0.3.7 has none: the CN builds
     * have no Google services, and the Pixel image's sessions present them
     * (oneos_switch.sh refuses to hide a staged GmsCore). A Google image
     * whose sessions do not present them (not built in) may.
     */
    @Test
    fun googleServicesMayBeHiddenOnlyWhereASessionCanHideThem() {
        val hideable = Images.PIXEL_YOGI.copy(id = "google-hideable", shortName = "Hideable", presentsGms = false)
        for (p in Profiles.BUILT_IN.filter { it.enabled }) {
            val text = SessionEnv.generate(p)
            assertTrue(p.id, text.lines().contains("${SessionEnv.HIDE_GMS}=0"))
            val hidden = text.replace("${SessionEnv.HIDE_GMS}=0", "${SessionEnv.HIDE_GMS}=1")
            for (i in Images.ALL + hideable) {
                assertEquals("${p.id} ${i.id}", emptyList<String>(), SessionEnv.validate(text, image = i))
                val v = SessionEnv.validate(hidden, image = i)
                when {
                    i.gmsHideable -> assertEquals("${p.id} ${i.id}", emptyList<String>(), v)
                    i.googleServices -> assertEquals(
                        listOf("${SessionEnv.HIDE_GMS}=1, but the ${i.shortName} image's sessions present Google services, which cannot be hidden"),
                        v,
                    )
                    else -> assertEquals(listOf("${SessionEnv.HIDE_GMS}=1, but the ${i.shortName} image has no Google services"), v)
                }
            }
            assertTrue(SessionEnv.validate(hidden, image = Images.PIXEL_YOGI).single().contains("cannot be hidden"))
            assertEquals(emptyList<String>(), SessionEnv.validate(hidden, image = hideable))
            // No image known: never.
            assertEquals(1, SessionEnv.validate(hidden).size)
            for (bad in listOf("2", "", "yes")) {
                assertTrue(bad, SessionEnv.validate(text.replace("${SessionEnv.HIDE_GMS}=0", "${SessionEnv.HIDE_GMS}=$bad"), image = hideable).isNotEmpty())
            }
            assertTrue(SessionEnv.validate(text.replace("${SessionEnv.HIDE_GMS}=0\n", ""), image = hideable).contains("${SessionEnv.HIDE_GMS} missing"))
        }
        // 0.4.11: the Find X9 Ultra IN build's Google services (in the image, not presented) may be hidden.
        assertEquals(listOf(Images.FIND_X9U_IN), Images.ALL.filter { it.gmsHideable })
        assertEquals(
            listOf("ONEOS_GUEST_HIDE_GMS", "ONEOS_HEAT_CAP", "ONEOS_GUEST_SEC_IMS", "ONEOS_GUEST_EDM_STUB", "ONEOS_RETURN_MODE"),
            SessionEnv.ALLOWED.keys.toList().takeLast(5),
        )
        assertEquals("ONEOS_GUEST_EDM_STUB", SessionEnv.ALLOWED.keys.toList().dropLast(1).last())
        for (p in Profiles.BUILT_IN.filter { it.enabled }) {
            val text = SessionEnv.generate(p)
            assertTrue(p.id, text.lines().contains("${SessionEnv.SEC_IMS}=0"))
            for (i in Images.ALL) assertEquals(emptyList<String>(), SessionEnv.validate(text.replace("${SessionEnv.SEC_IMS}=0", "${SessionEnv.SEC_IMS}=1"), image = i))
            assertEquals(emptyList<String>(), SessionEnv.validate(text.replace("${SessionEnv.SEC_IMS}=0", "${SessionEnv.SEC_IMS}=1")))
            for (bad in listOf("2", "", "on")) assertTrue(bad, SessionEnv.validate(text.replace("${SessionEnv.SEC_IMS}=0", "${SessionEnv.SEC_IMS}=$bad")).isNotEmpty())
            assertTrue(SessionEnv.validate(text.replace("${SessionEnv.SEC_IMS}=0\n", "")).contains("${SessionEnv.SEC_IMS} missing"))
            // 0.4.32: the Knox edm stub, a launch's choice on any phone and image, the same way.
            assertTrue(p.id, text.lines().contains("${SessionEnv.EDM_STUB}=0"))
            assertEquals(emptyList<String>(), SessionEnv.validate(text.replace("${SessionEnv.EDM_STUB}=0", "${SessionEnv.EDM_STUB}=1")))
            for (bad in listOf("2", "", "on")) assertTrue(bad, SessionEnv.validate(text.replace("${SessionEnv.EDM_STUB}=0", "${SessionEnv.EDM_STUB}=$bad")).isNotEmpty())
            assertTrue(SessionEnv.validate(text.replace("${SessionEnv.EDM_STUB}=0\n", "")).contains("${SessionEnv.EDM_STUB} missing"))
        }
    }

    /** Every knob the file sets is read by the session scripts under that exact name. */
    @Test
    fun knobNamesMatchTheScripts() {
        val dir = System.getProperty("oneos.switcherAssets")?.let(::File)
        assumeTrue("switcher/assets not found", dir != null && dir.isDirectory)
        val scripts = dir!!.listFiles { f -> f.name.endsWith(".sh") }!!.joinToString("\n") { it.readText() }
        for (k in SessionEnv.ALLOWED.keys) {
            assertTrue("$k not read by switcher/assets/*.sh", Regex("""\$\{$k:-""").containsMatchIn(scripts))
        }
        // The scripts' default splash is the app's.
        assertTrue(scripts.contains("\${ONEOS_SPLASH_COMPONENT:-${SessionEnv.SPLASH_COMPONENT}}"))
        // The form defaults the FOLD set writes out are the scripts' own defaults.
        for ((k, v) in SessionEnv.FOLD_FORM) {
            assertTrue("$k default is not $v", scripts.contains("\${$k:-$v}"))
        }
    }
}
