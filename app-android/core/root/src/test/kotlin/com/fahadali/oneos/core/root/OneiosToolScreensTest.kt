package com.fahadali.oneos.core.root

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * What the phone needs of the full edition's manifest for the iOS screens and oneios-tool's flows, read from the
 * sources (no emulator here): every iOS activity the code starts is declared, OneiosService is a dataSync
 * foreground service (Android 14+ refuses a foreground service without a declared type), and the permissions the
 * flows use are there (notifications on Android 13+, the dataSync service, the default network's callback).
 */
class OneiosToolScreensTest {
    private val full = File(Shipped.appSources, "full")
    private val manifest = File(full, "AndroidManifest.xml").readText()

    private fun declared(): Set<String> =
        Regex("""<activity\s+[^>]*android:name="\.ui\.(\w+)"""").findAll(manifest).map { it.groupValues[1] }.toSet()

    @Test
    fun everyIosScreenTheCodeStartsIsDeclared() {
        val started = full.walkTopDown().filter { it.extension == "kt" }
            .flatMap { f -> Regex("""\b(Oneios\w*Activity)::class\.java""").findAll(f.readText()).map { it.groupValues[1] } }.toSet()
        assertTrue("found only $started", "OneiosToolActivity" in started && started.size >= 6)
        assertEquals(emptySet<String>(), started - declared())
    }

    @Test
    fun theServiceAndThePermissionsTheFlowsNeedAreDeclared() {
        val service = Regex("""<service\s+[^>]*android:name="\.session\.OneiosService"[^>]*>""").find(manifest)?.value
        assertTrue("OneiosService: $service", service != null && service.contains("""android:foregroundServiceType="dataSync""""))
        for (p in listOf("FOREGROUND_SERVICE", "FOREGROUND_SERVICE_DATA_SYNC", "POST_NOTIFICATIONS", "ACCESS_NETWORK_STATE", "WAKE_LOCK")) {
            assertTrue("no $p", manifest.contains("""<uses-permission android:name="android.permission.$p" />"""))
        }
        // The tool's screen asks for notifications (Android 13+) before its flow's notification is needed.
        val screen = File(full, "kotlin/com/fahadali/oneos/ui/OneiosToolActivity.kt").readText()
        assertTrue(screen.contains("POST_NOTIFICATIONS") && screen.contains("askNotifications(this, savedInstanceState)"))
    }
}
