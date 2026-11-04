package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AppUpdateTest {
    private val sha = "a".repeat(64)
    private fun json(
        code: String = "58",
        name: String = "\"0.4.42\"",
        apk: String = "\"https://github.com/fahadalijaved/OneOS/releases/download/v0.4.42/OneOS-0.4.42.apk\"",
        bytes: String = "52428800",
        sha256: String = "\"$sha\"",
    ) = """{"versionCode": $code, "versionName": $name, "apk": $apk, "bytes": $bytes, "sha256": $sha256}"""

    @Test
    fun readsTheReleasesUpdate() {
        val u = AppUpdate.parse(json()).getOrThrow()
        assertEquals(AppUpdate(58, "0.4.42", "https://github.com/fahadalijaved/OneOS/releases/download/v0.4.42/OneOS-0.4.42.apk", 52428800L, sha), u)
        assertTrue(u.newerThan(57))
        assertTrue(!u.newerThan(58))
    }

    @Test
    fun notesAndSystemsAreOptional() {
        val plain = AppUpdate.parse(json()).getOrThrow()
        assertEquals(null, plain.notes)
        assertTrue(plain.systems.isEmpty() && !plain.changes("coloros17-findn6"))
        val extra = json().removeSuffix("}") + ", \"notes\": \"Theme Store on the Fold8 ColorOS\", \"systems\": \"coloros17-findn6,hyperos-lhasa\"}"
        val u = AppUpdate.parse(extra).getOrThrow()
        assertEquals("Theme Store on the Fold8 ColorOS", u.notes)
        assertTrue(u.changes("coloros17-findn6") && u.changes("hyperos-lhasa") && !u.changes("pixel11fold-yogi"))
        assertTrue(AppUpdate.parse(json().removeSuffix("}") + ", \"systems\": \"*\"}").getOrThrow().changes("pixel11fold-yogi"))
        assertTrue(AppUpdate.parse(json().removeSuffix("}") + ", \"systems\": \"../x\"}").isFailure)
        assertTrue(AppUpdate.parse(json().removeSuffix("}") + ", \"notes\": \"" + "x".repeat(141) + "\"}").isFailure)
    }

    @Test
    fun driveApksOnlyOnTheTestChannel() {
        val drive = "\"https://drive.usercontent.google.com/download?id=1AbCdEfGhIjKlMnOpQrStUvWxYz012345&export=download&confirm=t\""
        assertTrue(AppUpdate.parse(json(apk = drive)).isFailure)
        assertTrue(AppUpdate.parse(json(apk = drive), test = true).isSuccess)
        assertTrue(AppUpdate.parse(json(apk = "\"https://drive.usercontent.google.com/download?id=x&export=download&confirm=t\""), test = true).isFailure)
        assertTrue(AppUpdate.parse(json(apk = "\"https://evil.example/download?id=1AbCdEfGhIjKlMnOpQrStUvWxYz012345&export=download&confirm=t\""), test = true).isFailure)
        assertTrue(AppUpdate.parse(json(), test = true).isSuccess)
    }

    @Test
    fun refusesAnythingElse() {
        val bad = listOf(
            json(apk = "\"https://example.com/OneOS-0.4.42.apk\""),
            json(apk = "\"https://github.com/fahadalijaved/OneOS/releases/download/v0.4.42/../../x.apk\""),
            json(apk = "\"https://github.com/someone/OneOS/releases/download/v0.4.42/OneOS-0.4.42.apk\""),
            json(code = "0"),
            json(code = "\"58\""),
            json(name = "\"0.4.42; rm\""),
            json(bytes = "0"),
            json(bytes = "999999999999"),
            json(sha256 = "\"ABC\""),
            json() + json(),
            """{"versionCode": 58}""",
        )
        for (b in bad) assertTrue(b, AppUpdate.parse(b).isFailure)
    }
}
