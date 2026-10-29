package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ReportsTest {
    @Test
    fun zipsGoInPartsAKvValueHolds() {
        assertEquals(0, Reports.parts(0))
        assertEquals(1, Reports.parts(1))
        assertEquals(1, Reports.parts(Reports.PART_BYTES.toLong()))
        assertEquals(2, Reports.parts(Reports.PART_BYTES + 1L))
        // The biggest bundle so far, 27 MB: two parts, each under the 25 MiB a KV value holds.
        assertEquals(2, Reports.parts(27_200_000))
        assertTrue(Reports.PART_BYTES < 25 * 1024 * 1024)
        assertTrue(Reports.MAX_ZIP_BYTES / Reports.PART_BYTES <= 4)
    }

    @Test
    fun reportIdsAreTheSessionsWithASuffix() {
        val id = Reports.reportId("8aea312c31b8821d", "3F2A9b0c")
        assertEquals("8aea312c31b8821d-3f2a9b0c", id)
        assertTrue(Reports.ID_PATTERN.matches(id))
        assertEquals("findingssma576b-beef", Reports.reportId("findings-SM-A576B", "beef"))
        assertTrue(Reports.ID_PATTERN.matches(Reports.reportId("", "abcd")))
        assertFalse(Reports.ID_PATTERN.matches("../etc-abcd"))
        assertFalse(Reports.ID_PATTERN.matches("8aea312c-xyz1"))
        assertTrue(runCatching { Reports.reportId("x", "zz") }.isFailure)
    }

    @Test
    fun freeTextIsCleanedAndCut() {
        assertEquals("black screen at the logo", Reports.cleanText("  black\tscreen   at the\u0007 logo \n", 100))
        assertEquals("a\n\nb", Reports.cleanText("a\n\n\n\nb", 100))
        assertEquals(Reports.NOTE_MAX, Reports.cleanText("x".repeat(2000), Reports.NOTE_MAX).length)
    }

    @Test
    fun checklistAnswers() {
        val c = Checklist(
            start = StartAnswer.HOME,
            works = setOf(CheckItem.WIFI, CheckItem.CALLS, CheckItem.SCREEN),
            problems = setOf(CheckItem.CALLS, CheckItem.BLUETOOTH),
            note = " calls drop after 5 s ",
            contact = "@someone\nelse",
        )
        assertEquals(CheckAnswer.WORKS, c.answer(CheckItem.WIFI))
        // Ticked in both lists: a problem.
        assertEquals(CheckAnswer.PROBLEM, c.answer(CheckItem.CALLS))
        assertEquals(CheckAnswer.NOT_TRIED, c.answer(CheckItem.CAMERA))
        assertTrue(c.wantsFullLogs)
        assertFalse(Checklist(start = StartAnswer.HOME, works = setOf(CheckItem.WIFI)).wantsFullLogs)
        val cleaned = c.cleaned()
        assertEquals(setOf(CheckItem.WIFI, CheckItem.SCREEN), cleaned.works)
        assertEquals("calls drop after 5 s", cleaned.note)
        assertEquals("@someone else", cleaned.contact)
        // The fold item is asked on the Z Folds only.
        assertTrue(CheckItem.FOLD in CheckItem.forForm(FormFactor.FOLD))
        assertFalse(CheckItem.FOLD in CheckItem.forForm(FormFactor.BAR))
        assertFalse(CheckItem.FOLD in CheckItem.forForm(FormFactor.FLIP))
        val items = c.toMap(FormFactor.BAR)["items"] as Map<*, *>
        assertEquals(CheckItem.entries.size - 1, items.size)
        assertEquals("problem", items["calls"])
        assertEquals("not_tried", items["camera"])
        assertTrue(StartAnswer.HOME.started && !StartAnswer.BLACK.started)
        assertEquals(StartAnswer.LOGO, StartAnswer.byId("logo"))
        assertNull(StartAnswer.byId("nope"))
        // Ids are what the service and docs/compatibility.md count by: unique, lower case.
        assertEquals(CheckItem.entries.size, CheckItem.entries.map { it.id }.toSet().size)
        assertTrue(CheckItem.entries.all { it.id.matches(Regex("[a-z]+")) })
    }

    @Test
    fun recordJson() {
        val r = ReportRecord(
            reportId = "8aea312c31b8821d-3f2a",
            createdAt = "2026-10-29T16:40:00+05:30",
            app = AppInfo("com.fahadali.oneos", "0.4.29-s25", 46, "OneOS"),
            series = "s25",
            model = "SM-S911B",
            device = "dm1q",
            profileId = "s-8550",
            phoneLabel = "Galaxy S23",
            imageId = "infinityx41-findx9u",
            imageName = "Infinity-X 4.1",
            sessionId = "8aea312c31b8821d",
            outcomeKind = "GUEST_DEAD",
            afterSeconds = 120,
            checklist = Checklist(start = StartAnswer.BLACK, note = ""),
            form = FormFactor.BAR,
            logs = ReportLogs("session", "oneos-logs-8aea312c31b8821d-short.zip", full = false, bytes = 1_200_000, sha256 = "ab".repeat(32)),
        )
        val m = r.toMap()
        assertEquals(Reports.SCHEMA, m["schema"])
        assertNull(m["note"])
        assertNull(m["contact"])
        assertEquals("black", (m["checklist"] as Map<*, *>)["start"])
        assertEquals(1, (m["logs"] as Map<*, *>)["parts"])
        val json = r.toJson()
        assertTrue(json.contains("\"schema\": \"oneos.report/1\""))
        assertTrue(json.contains("\"series\": \"s25\""))
        assertEquals("Galaxy S23", (m["phone"] as Map<*, *>)["label"])
        assertEquals("Infinity-X 4.1", m["imageName"])
        assertFalse(json.contains("\"fold\""))
        // A probe report: no session, no checklist.
        val probe = r.copy(sessionId = null, outcomeKind = null, afterSeconds = null, checklist = null, logs = null).toMap()
        assertNull(probe["checklist"])
        assertNull(probe["outcome"])
        assertNull(probe["logs"])
    }
}
