package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UsageHelloTest {
    private val id = "0123456789abcdef0123456789abcdef"
    private val day1 = 1_794_000_000_000L // 2026-11-06 or so
    private val image = Regex("^[a-z0-9][a-z0-9._-]{0,47}$")
    private val model = Regex("^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,39}$")

    @Test
    fun dayGateSendsOncePerUtcDay() {
        val d = UsageHello.dayOf(day1)
        assertTrue(UsageHello.due(true, null, day1))
        assertFalse(UsageHello.due(true, d, day1))
        assertFalse(UsageHello.due(true, d, day1 + 60_000))
        val midnight = java.time.LocalDate.parse(d).plusDays(1).atStartOfDay(java.time.ZoneOffset.UTC).toInstant().toEpochMilli()
        assertFalse(UsageHello.due(true, d, midnight - 1))
        assertTrue(UsageHello.due(true, d, midnight))
    }

    @Test
    fun offSendsNothing() {
        assertFalse(UsageHello.due(false, null, day1))
        assertFalse(UsageHello.due(false, "2020-01-01", day1))
    }

    @Test
    fun installIdIsRandom32Hex() {
        val a = UsageHello.newInstallId()
        assertTrue(UsageHello.validInstall(a))
        assertTrue(a != UsageHello.newInstallId())
        assertFalse(UsageHello.validInstall("ABCDEF0123456789abcdef0123456789"))
        assertFalse(UsageHello.validInstall(id.dropLast(1)))
    }

    @Test
    fun jsonMatchesTheWorkersValidation() {
        val systems = (1..12).map { "img$it" } + listOf("Bad Id", "img1", "")
        val text = UsageHello.json(id, 142, "SM-F966U1", "f8u", systems, 9999)
        assertTrue(text.contains("\"schema\": \"oneos.hello/1\"") || text.contains("\"schema\":\"oneos.hello/1\""))
        val list = Regex("\"systems\"\\s*:\\s*\\[([^\\]]*)]").find(text)!!.groupValues[1]
        val ids = Regex("\"([^\"]*)\"").findAll(list).map { it.groupValues[1] }.toList()
        assertEquals(8, ids.size)
        assertTrue(ids.all { image.matches(it) })
        assertTrue(Regex("\"switches\"\\s*:\\s*500\\b").containsMatchIn(text))
        assertTrue(Regex("\"versionCode\"\\s*:\\s*142\\b").containsMatchIn(text))
        assertTrue(text.length <= 2048)
    }

    @Test
    fun emptySystemsAndNoProfileAreFine() {
        val text = UsageHello.json(id, 142, "Pixel 9", null, emptyList(), -3)
        assertTrue(Regex("\"profile\"\\s*:\\s*null").containsMatchIn(text))
        assertTrue(Regex("\"systems\"\\s*:\\s*\\[\\s*]").containsMatchIn(text))
        assertTrue(Regex("\"switches\"\\s*:\\s*0\\b").containsMatchIn(text))
    }

    @Test
    fun modelIsMadeAcceptable() {
        for (m in listOf("SM-F966U1", "Pixel 9 Pro", "  ", "", null, "Ünï/code*model", "x".repeat(80), "-lead", "a;b")) {
            assertTrue("'$m'", model.matches(UsageHello.cleanModel(m)))
        }
        assertEquals("SM-F966U1", UsageHello.cleanModel("SM-F966U1"))
        assertEquals("unknown", UsageHello.cleanModel(""))
    }

    @Test
    fun everyShippedImageAndProfileIdIsAcceptedByTheWorker() {
        for (i in Images.ALL) assertTrue(i.id, image.matches(i.id))
        for (p in Profiles.BUILT_IN) assertTrue(p.id, image.matches(p.id))
    }

    @Test(expected = IllegalArgumentException::class)
    fun badInstallIdIsRefused() {
        UsageHello.json("nope", 1, "x", null, emptyList(), 0)
    }
}
