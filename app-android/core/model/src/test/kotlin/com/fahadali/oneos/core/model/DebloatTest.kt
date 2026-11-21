package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class DebloatTest {
    @Test
    fun onlyAnAppsOwnFolder() {
        for (ok in listOf(
            "/system/app/BookmarkProvider",
            "/system/system_ext/priv-app/ConnectivityThermalPowerManagerNextgen",
            "/my_product/apps_extension/1147_Bell/SimSwitchFirstTime/app/Crave_v6.70.2_SDK35_1147",
            "/my_stock/del-app/OplusDocumentsReader",
            "/system/system_ext/app/NfcEngineerTest/NfcEngineerTest",
            "/product/data-app/WPSforPad",
        )) assertTrue(ok, Debloat.pathOk(ok))
        for (bad in listOf(
            "", "system/app/X", "/system/app", "/system/app/", "/product/overlay", "/system/product/overlay",
            "/my_product/priv-app", "/my_product/apps_extension/Rogers/SimSwitchFirstTime/del-app",
            "/product/prebuilts/com.android.deskclocklib", "/system/app/../priv-app/X", "/system/app/.hidden",
            "/system//app/X", "/system/app/X Y", "/system/app/X;rm", "/system/app/" + "x".repeat(200),
            "/system/app/framework", "/data/app/X",
        )) assertFalse(bad, Debloat.pathOk(bad))
    }

    @Test
    fun parsesAndWritesTheRootList() {
        val text = """
            # header
            S	org.example.ads	Ads	2048	img-a,img-b	/system/app/Ads	Ad service
            C	org.example.cloud	Cloud	1048576	img-a	/system/priv-app/Cloud;/product/app/CloudStub	Cloud sync	m
            C	org.example.bad	Bad	1	img-a	/product/overlay	shared folder: dropped
            X	org.example.rating	Bad	1	img-a	/system/app/R	unknown rating: dropped
            S	notapackage	Bad	1	img-a	/system/app/N	dropped
        """.trimIndent()
        val all = Debloat.parse(text)
        assertEquals(listOf("org.example.ads", "org.example.cloud"), all.map { it.pkg })
        assertEquals(listOf(false, true), all.map { it.mystic })
        assertEquals(listOf("org.example.ads"), Debloat.forImage(all, "img-b").map { it.pkg })
        assertEquals(Debloat.Rating.SAFE, Debloat.forImage(all, "img-a").first().rating)
        assertEquals(
            "org.example.ads\t/system/app/Ads\norg.example.cloud\t/system/priv-app/Cloud\norg.example.cloud\t/product/app/CloudStub\n",
            Debloat.listText(all),
        )
        assertEquals("", Debloat.listText(emptyList()))
        assertEquals("1.0 GB", Debloat.size(1048576))
        assertEquals("2 MB", Debloat.size(2048))
    }

    @Test
    fun groupsByWhoMadeTheApp() {
        assertEquals(Debloat.Group.MAKER, Debloat.group("com.miui.player"))
        assertEquals(Debloat.Group.MAKER, Debloat.group("com.sec.android.app.voicenote"))
        assertEquals(Debloat.Group.MAKER, Debloat.group("com.google.android.apps.pixel.dcservice"))
        assertEquals(Debloat.Group.GOOGLE, Debloat.group("com.google.android.youtube"))
        assertEquals(Debloat.Group.ANDROID, Debloat.group("com.android.bookmarkprovider"))
        assertEquals(Debloat.Group.CHIP, Debloat.group("com.qualcomm.qti.xrcb"))
        assertEquals(Debloat.Group.PARTNER, Debloat.group("com.facebook.services"))
        assertEquals(Debloat.Group.PARTNER, Debloat.group("android.autoinstalls.config.Xiaomi.model"))
    }

    /** The asset the app ships: every app line parses, every folder passes the rule, and each image's list fits root's limit. */
    @Test
    fun shippedListIsSound() {
        val f = File("../../app/src/full/assets/debloat/apps.tsv")
        val lines = f.readLines().filter { it.isNotBlank() && !it.startsWith("#") }
        val all = Debloat.parse(f.readText())
        assertEquals(lines.size, all.size)
        assertTrue(all.size > 100)
        for (image in Images.ALL.map { it.id }) {
            val apps = Debloat.forImage(all, image)
            assertTrue("$image: ${apps.sumOf { it.folders.size }} folders", apps.sumOf { it.folders.size } <= Debloat.MAX_LINES)
            assertEquals("$image repeats a package", apps.size, apps.map { it.pkg }.toSet().size)
        }
        // Never offered: what a system or OneOS needs.
        val never = setOf(
            "com.google.android.gms", "com.android.vending", "com.android.systemui", "com.android.settings", "com.android.phone",
            "com.android.providers.media.module", "com.google.android.webview", "com.android.permissioncontroller",
            "com.samsung.android.kgclient", "com.sec.imsservice", "com.android.launcher3",
            "com.oplus.aod", "com.oplus.camera", // OneOS's AOD work and the lock screen fingerprint circle; OneOS manages the camera
        )
        assertEquals(emptyList<String>(), all.map { it.pkg }.filter { it in never })
        // MysticGSI's ColorOS debloat is offered whole on the ColorOS image, OPPO's camera aside (OneOS manages it).
        val x9u = Debloat.forImage(all, "coloros17-findx9u-in-1105")
        assertTrue(x9u.count { it.mystic } > 50)
        assertFalse(x9u.any { it.pkg == "com.oplus.camera" })
    }
}
