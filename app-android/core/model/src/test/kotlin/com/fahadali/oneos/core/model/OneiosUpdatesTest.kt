package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Automatic update checks ([OneiosAppReleases], [OneiosUpdates]) and one-tap bug report text ([OneiosBugReport]):
 * docs/oneios.md, 2026-11-28.
 */
class OneiosUpdatesTest {
    private fun releaseJson(
        tag: String = "v0.1.42",
        apk: String = "OneOS-oneios-0.5.121-debug.apk",
        size: Long = 12_345_678L,
        body: String = "OneOS app: versionName **0.5.121**, versionCode **250**",
        includeSha: Boolean = true,
        repo: String = OneiosReleases.REPO,
    ): String {
        val base = "https://github.com/$repo/releases/download/$tag"
        val shaEntry = if (includeSha) """,{"name":"$apk.sha256","size":100,"browser_download_url":"$base/$apk.sha256"}""" else ""
        return """{"tag_name":"$tag","body":"$body","assets":[{"name":"$apk","size":$size,"browser_download_url":"$base/$apk"}$shaEntry]}"""
    }

    @Test
    fun parsesOneiosAppReleaseAndRejectsIncompleteOrForeignAssets() {
        val r = OneiosAppReleases.parse(releaseJson())
        assertNotNull(r)
        assertEquals("v0.1.42", r!!.tag)
        assertEquals("0.5.121", r.versionName)
        assertEquals(250, r.versionCode)
        assertEquals("OneOS-oneios-0.5.121-debug.apk", r.assetName)
        assertEquals(12_345_678L, r.bytes)
        val u = r.update("A".repeat(64))
        assertEquals(250, u.versionCode)
        assertEquals("0.5.121", u.versionName)
        assertEquals("a".repeat(64), u.sha256)
        assertEquals("OneiOS release v0.1.42", u.notes)

        // Missing .sha256, missing versionCode in notes, or foreign repo: refused.
        assertNull(OneiosAppReleases.parse(releaseJson(includeSha = false)))
        assertNull(OneiosAppReleases.parse(releaseJson(body = "no version code here")))
        assertNull(OneiosAppReleases.parse(releaseJson(repo = "other/OneiOS")))
    }

    @Test
    fun combinesRuntimeKernelAndAppUpdatesAndRateLimitsHourly() {
        val apk = OneiosAppReleases.parse(releaseJson())!!
        // All three due (newer runtime implies kernel may need rebuild too).
        val all = OneiosUpdates.of("0.1.41", "0.1.42", null, 249, apk)
        assertTrue(all.any)
        assertTrue(all.needsPage)
        assertEquals("0.1.42", all.runtime)
        assertEquals(OneiosUpdates.KERNEL_NEXT, all.kernel)
        assertEquals("0.5.121", all.app)
        assertTrue(all.line!!, all.line!!.contains("runtime 0.1.42") && all.line!!.contains("kernel") && all.line!!.contains("app 0.5.121"))

        // Only app newer -> does not need iOS page.
        val appOnly = OneiosUpdates.of("0.1.42", "0.1.42", null, 249, apk)
        assertTrue(appOnly.any)
        assertFalse(appOnly.needsPage)
        assertEquals("Update available: app 0.5.121", appOnly.line)

        // Only kernel due.
        val kernelOnly = OneiosUpdates.of("0.1.42", "0.1.42", "xnu-12377", 250, apk)
        assertTrue(kernelOnly.any)
        assertTrue(kernelOnly.needsPage)
        assertEquals("Update available: kernel xnu-12377", kernelOnly.line)

        // Nothing due.
        val none = OneiosUpdates.of("0.1.42", "0.1.42", null, 250, apk)
        assertFalse(none.any)
        assertNull(none.line)

        // Hourly rate limit + 10 min failure backoff.
        val t0 = 10_000_000L
        assertFalse(OneiosUpdates.checkDue(t0 + 59 * 60_000L, t0, 0L))
        assertTrue(OneiosUpdates.checkDue(t0 + OneiosUpdates.CHECK_EVERY_MS, t0, 0L))
        assertFalse(OneiosUpdates.checkDue(t0 + OneiosUpdates.CHECK_EVERY_MS, 0L, t0 + OneiosUpdates.CHECK_EVERY_MS + 1))
        assertTrue(OneiosUpdates.checkDue(t0 + 1000L, t0, t0 + 999_999L, force = true))
    }

    @Test
    fun bugReportFormatsVersionsAndSessionSummaryWithoutPersonalData() {
        val v = OneiosBugReport.Versions(
            appName = "0.5.121",
            appCode = 250,
            phoneModel = "SM-S928B",
            phoneDevice = "e3q",
            androidRelease = "15",
            androidBuild = "AP3A.240905.015",
            runtimeVersion = "0.1.42",
            imageVersion = "27.0.1",
            imageBuild = "24A446",
            imageKernel = "xnu-old",
            runtimeKernel = "xnu-new",
        )
        val lines = OneiosBugReport.versionLines(v)
        assertTrue(lines.any { it.contains("OneOS 0.5.121 (versionCode 250)") })
        assertTrue(lines.any { it.contains("SM-S928B (e3q)") })
        assertTrue(lines.any { it.contains("Runtime: 0.1.42") })
        assertTrue(lines.any { it.contains("Image: iOS 27.0.1 (24A446)") })
        assertTrue(lines.any { it.contains("Kernel: image xnu-old, runtime xnu-new") })

        val summary = OneiosLogs.summarize(listOf("xnuhost: boot ok", "xnuhost: exit 0"))
        val md = OneiosBugReport.issueMarkdown(v, summary, logName = "xnuhost-session.log", iosLogIncluded = true)
        assertTrue(md.contains("### Environment"))
        assertTrue(md.contains("### Last session summary"))
        assertTrue(md.contains("`xnuhost-session.log`"))
        assertTrue(md.contains("ioslog-last-boot.txt"))
    }
}
