package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BringAppsTest {
    @Test
    fun realUserAppsAreEligible() {
        for (pkg in listOf("org.telegram.messenger", "nekox.messenger", "com.whatsapp", "com.google.android.youtube")) {
            assertTrue(pkg, BringApps.eligible(pkg, system = false, launchable = true))
        }
    }

    @Test
    fun systemAppsAndComponentsAndOursAreNot() {
        // One UI / system apps stay on One UI.
        assertFalse(BringApps.eligible("com.samsung.android.messaging", system = true, launchable = true))
        // No launcher entry (a service/component package): not offered.
        assertFalse(BringApps.eligible("com.google.android.gms", system = false, launchable = false))
        // Our own app, the guest, and root managers are never brought.
        for (pkg in BringApps.NEVER) {
            assertFalse(pkg, BringApps.eligible(pkg, system = false, launchable = true))
        }
    }

    @Test
    fun nonPackageStringsAreRejected() {
        for (bad in listOf("", "telegram", "..", "com..messenger", "1com.app", "com.app/../etc", "com.app;rm")) {
            assertFalse(bad, BringApps.PACKAGE.matches(bad))
            assertFalse(bad, BringApps.eligible(bad, system = false, launchable = true))
        }
    }

    @Test
    fun manifestIsSortedUniqueValidated() {
        val text = BringApps.manifest(listOf("com.whatsapp", "org.telegram.messenger", "com.whatsapp", "not a package"))
        assertEquals("com.whatsapp\norg.telegram.messenger\n", text)
    }

    @Test
    fun parseManifestDropsNoiseAndBadLines() {
        val text = """
            # chosen apps
            org.telegram.messenger

            com.whatsapp
            ../etc/passwd
            org.telegram.messenger
        """.trimIndent()
        assertEquals(listOf("org.telegram.messenger", "com.whatsapp"), BringApps.parseManifest(text))
    }

    @Test
    fun statusLinesBecomeCopiesAndAnythingElseIsDropped() {
        val copies = BringApps.parseStatus(
            listOf(
                "app org.telegram.messenger 1794300000 waiting same",
                "app com.whatsapp 1794300100 installed data",
                "app nekox.messenger 1794300200 failed app",
                "why nekox.messenger INSTALL_FAILED_UPDATE_INCOMPATIBLE: signatures do not match",
                "why com.whatsapp not a failed one",
                "app com.legacy.copy 0 waiting data",
                "app com.gone.app 1794300300 installed gone",
                // Not status lines: all dropped.
                "app ../etc 1 waiting same",
                "app com.bad.stamp -1 waiting same",
                "app com.bad.stamp 12345678901234567890 waiting same",
                "app com.bad.state 1 deleted same",
                "app com.bad.change 1 waiting newer",
                "app com.too.many 1 waiting same extra",
                "brought com.other 12",
            ),
        )
        assertEquals(
            listOf(
                BringApps.Copy("com.gone.app", 1794300300, BringApps.CopyState.INSTALLED, BringApps.Change.GONE),
                BringApps.Copy("com.legacy.copy", 0, BringApps.CopyState.WAITING, BringApps.Change.DATA),
                BringApps.Copy("com.whatsapp", 1794300100, BringApps.CopyState.INSTALLED, BringApps.Change.DATA),
                BringApps.Copy(
                    "nekox.messenger", 1794300200, BringApps.CopyState.FAILED, BringApps.Change.APP,
                    "INSTALL_FAILED_UPDATE_INCOMPATIBLE: signatures do not match",
                ),
                BringApps.Copy("org.telegram.messenger", 1794300000, BringApps.CopyState.WAITING, BringApps.Change.SAME),
            ),
            copies,
        )
        assertTrue(copies.first { it.pkg == "com.whatsapp" }.newer)
        assertFalse(copies.first { it.pkg == "com.gone.app" }.newer)
        assertEquals(emptyList<BringApps.Copy>(), BringApps.parseStatus(emptyList()))
    }

    @Test
    fun aBootBringsAgainOnlyWhatTheGuestHasNotInstalled() {
        fun copy(pkg: String, state: BringApps.CopyState, change: BringApps.Change) = BringApps.Copy(pkg, 1, state, change)
        val again = BringApps.againAtBoot(
            listOf(
                copy("a.waiting.same", BringApps.CopyState.WAITING, BringApps.Change.SAME),
                copy("b.waiting.data", BringApps.CopyState.WAITING, BringApps.Change.DATA),
                copy("c.waiting.app", BringApps.CopyState.WAITING, BringApps.Change.APP),
                copy("d.waiting.gone", BringApps.CopyState.WAITING, BringApps.Change.GONE),
                // Installed in the guest: its data there is the guest's own now, never replaced without a tick.
                copy("e.installed.data", BringApps.CopyState.INSTALLED, BringApps.Change.DATA),
                copy("f.installed.app", BringApps.CopyState.INSTALLED, BringApps.Change.APP),
                // Refused by the guest: again only with another build of the app.
                copy("g.failed.data", BringApps.CopyState.FAILED, BringApps.Change.DATA),
                copy("h.failed.app", BringApps.CopyState.FAILED, BringApps.Change.APP),
            ),
        )
        assertEquals(listOf("b.waiting.data", "c.waiting.app", "h.failed.app"), again)
    }

    @Test
    fun anAppTheSystemHasIsNotBroughtAgainUnasked() {
        fun copy(pkg: String, state: BringApps.CopyState, change: BringApps.Change) = BringApps.Copy(pkg, 1, state, change)
        val copies = listOf(
            copy("a.installed", BringApps.CopyState.INSTALLED, BringApps.Change.SAME),
            copy("b.installed.data", BringApps.CopyState.INSTALLED, BringApps.Change.DATA),
            copy("c.waiting", BringApps.CopyState.WAITING, BringApps.Change.SAME),
            copy("d.failed", BringApps.CopyState.FAILED, BringApps.Change.SAME),
            copy("e.waiting.data", BringApps.CopyState.WAITING, BringApps.Change.DATA),
        )
        // The owner's case: two apps the system has, ticked again, and a third one new.
        val owner = BringApps.split(listOf("z.new", "b.installed.data", "a.installed"), copies)
        assertEquals(listOf("z.new"), owner.fresh)
        assertEquals(listOf("a.installed", "b.installed.data"), owner.there)
        // A copy still waiting or refused is copied like a new one.
        assertEquals(
            BringApps.Ticked(listOf("c.waiting", "d.failed", "z.new"), listOf("a.installed")),
            BringApps.split(listOf("z.new", "d.failed", "c.waiting", "a.installed", "z.new"), copies),
        )
        // Nothing brought yet: every tick is new.
        assertEquals(BringApps.Ticked(listOf("a.one", "b.two"), emptyList()), BringApps.split(listOf("b.two", "a.one"), emptyList()))
        // The stage could not be asked: what was brought before is asked about, not copied unasked.
        assertEquals(
            BringApps.Ticked(listOf("z.new"), listOf("a.installed")),
            BringApps.split(listOf("z.new", "a.installed"), null, setOf("a.installed", "q.other")),
        )
        // A boot: the new one, and the waiting copy that is newer on One UI; the ticked ones it has stay as they are.
        assertEquals(listOf("e.waiting.data", "z.new"), BringApps.atBoot(listOf("z.new", "b.installed.data", "a.installed"), copies))
        assertEquals(listOf("e.waiting.data"), BringApps.atBoot(listOf("a.installed"), copies))
        assertEquals(listOf("z.new"), BringApps.atBoot(listOf("z.new", "a.installed"), null, setOf("a.installed")))
        // The boot screen then counts them as already there.
        assertEquals(
            BringApps.BootCount(coming = 1, there = 2),
            BringApps.bootCount(copies, BringApps.atBoot(listOf("z.new", "b.installed.data", "a.installed"), copies)),
        )
    }

    @Test
    fun bootScreenSaysHowManyAppsComeAlong() {
        fun copy(pkg: String, state: BringApps.CopyState, change: BringApps.Change) = BringApps.Copy(pkg, 1, state, change)
        val copies = listOf(
            copy("a.waiting", BringApps.CopyState.WAITING, BringApps.Change.SAME),
            copy("b.waiting.again", BringApps.CopyState.WAITING, BringApps.Change.DATA),
            copy("c.installed", BringApps.CopyState.INSTALLED, BringApps.Change.SAME),
            copy("d.installed.ticked", BringApps.CopyState.INSTALLED, BringApps.Change.DATA),
            copy("e.failed", BringApps.CopyState.FAILED, BringApps.Change.SAME),
        )
        // What is copied now is not counted twice; a refused copy is in neither number.
        assertEquals(BringApps.BootCount(coming = 1, there = 1), BringApps.bootCount(copies, listOf("b.waiting.again", "d.installed.ticked", "f.new")))
        assertEquals(BringApps.BootCount(coming = 2, there = 2), BringApps.bootCount(copies, emptyList()))
        // The stage could not be asked: nothing is claimed.
        assertEquals(BringApps.BootCount(0, 0), BringApps.bootCount(null, listOf("f.new")))

        assertEquals("Bringing over 3 apps…", BringApps.bootDetail(3))
        assertEquals("Bringing over 1 app…\nXGram (1 of 1)", BringApps.bootDetail(1, 1, "XGram"))
        assertEquals("Bringing over 3 apps · 2 already in ColorOS 17", BringApps.bootLine("ColorOS 17", 3, 2))
        assertEquals("Bringing over 1 app to ColorOS 17", BringApps.bootLine("ColorOS 17", 1, 0))
        // The owner's case (11-10): both apps brought on the Apps screen and installed by an earlier boot.
        assertEquals("Your 2 apps from One UI are already in ColorOS 17", BringApps.bootLine("ColorOS 17", 0, 2))
        assertEquals("Your 1 app from One UI is already in ColorOS 17", BringApps.bootLine("ColorOS 17", 0, 1))
        assertEquals(null, BringApps.bootLine("ColorOS 17", 0, 0))
    }

    @Test
    fun manifestRoundTrips() {
        val pkgs = listOf("com.whatsapp", "nekox.messenger", "org.telegram.messenger")
        assertEquals(pkgs.sorted(), BringApps.parseManifest(BringApps.manifest(pkgs)))
    }
}
