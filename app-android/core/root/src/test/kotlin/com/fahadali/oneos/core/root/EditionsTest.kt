package com.fahadali.oneos.core.root

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The two editions of the app (0.3.4): OneOS (flavor full) and OneOS Probe
 * (flavor probe), one codebase. What the probe's APK gets is src/main plus
 * src/probe, so the root script, the stage and log lists, the session scripts
 * and the package sets must live only in src/full or in the full variants'
 * generated assets. The build checks the packaged probe APK as well
 * (`checkProbeReleaseApk`, app/build.gradle.kts); this is the same rule on the
 * source sets, without building an APK.
 */
class EditionsTest {
    private val src = Shipped.appSources

    private fun files(dir: File): Set<String> =
        if (!dir.isDirectory) emptySet() else dir.walkTopDown().filter { it.isFile }.map { it.relativeTo(dir).invariantSeparatorsPath }.toSet()

    @Test
    fun sharedAssetsAreTheProbeRunnerAndItsList() {
        assertEquals(setOf("probe/commands.list", "probe/probe.sh"), files(Shipped.appAssets))
        assertEquals(emptySet<String>(), files(File(src, "probe/assets")))
    }

    @Test
    fun theRootScriptAndTheSessionListsAreTheFullEditions() {
        assertEquals(
            setOf("root/oneos_root.sh", "root/status.list", "root/installd.list", "logs/collect.list"),
            files(Shipped.fullAssets),
        )
        assertTrue(Shipped.rootScript.isFile)
    }

    @Test
    fun onlyTheFullEditionDeclaresTheSwitchingScreens() {
        val screens = listOf("ImageActivity", "PrepareActivity", "SwitchActivity", "LastSessionActivity", "GapSplashActivity")
        val main = File(src, "main/AndroidManifest.xml").readText()
        val full = File(src, "full/AndroidManifest.xml").readText()
        for (a in screens) {
            assertFalse("src/main declares $a", main.contains(".ui.$a\""))
            assertTrue("src/full does not declare $a", full.contains(".ui.$a\""))
            assertTrue("$a.kt is not in src/full", File(src, "full/kotlin/com/fahadali/oneos/ui/$a.kt").isFile)
            assertFalse("$a.kt is in src/main", File(src, "main/kotlin/com/fahadali/oneos/ui/$a.kt").exists())
        }
        assertFalse(File(src, "probe/AndroidManifest.xml").exists())
        // The session code (root verbs, stage check, prepare, launch, logs) is the full edition's.
        assertFalse(File(src, "main/kotlin/com/fahadali/oneos/session").exists())
        assertFalse(File(src, "probe/kotlin/com/fahadali/oneos/session").exists())
        for (f in File(src, "main/kotlin").walkTopDown().filter { it.isFile }) {
            assertFalse("${f.name} uses the full edition's session code", f.readText().contains("import com.fahadali.oneos.session."))
        }
        // The probe shares only the findings, never the session logs.
        assertFalse(File(src, "probe/res/xml/findings_paths.xml").readText().contains("logs/"))
    }

    /**
     * OneOS Probe installs next to OneOS with its own root grant and its own
     * storage: nothing it shows tells the user to allow "OneOS" (the app that
     * switches) or says the results are OneOS's. Its strings are src/main's
     * with src/probe's on top; the shared Kotlin texts take app_name. The build
     * checks the packaged resources as well (`checkProbeReleaseApk`).
     */
    @Test
    fun theProbeNamesItselfForRootAndItsFiles() {
        fun strings(f: File) = Regex("""<string name="(\w+)">(.*?)</string>""", RegexOption.DOT_MATCHES_ALL)
            .findAll(f.readText()).associate { it.groupValues[1] to it.groupValues[2].replace("\\'", "'") }
        val probe = strings(File(src, "main/res/values/strings.xml")) + strings(File(src, "probe/res/values/strings.xml"))
        assertEquals("OneOS Probe", probe["app_name"])
        for ((name, text) in probe) {
            assertFalse("$name: $text", OTHER_APP_ROOT.containsMatchIn(text))
            // The session logs are OneOS's only (FindingsActivity shows them in OneOS).
            if (!name.startsWith("logs_")) assertFalse("$name: $text", OTHER_APP_FILES.containsMatchIn(text))
        }
        val shared = File(src, "main").walkTopDown().filter { it.isFile && (it.extension == "kt" || it.path.contains("/res/xml/")) } +
            File(src, "probe").walkTopDown().filter { it.isFile && it.extension != "png" }
        for (f in shared) {
            val hit = OTHER_APP_ROOT.find(f.readText()) ?: OTHER_APP_FILES.find(f.readText())
            assertEquals("${f.relativeTo(src)}: ${hit?.value}", null, hit)
        }
    }

    /** The package sets and session scripts (task oneosFiles) are added to the full variants only. */
    @Test
    fun onlyTheFullEditionGetsTheOneOsFiles() {
        val build = File(src, "../build.gradle.kts").readText()
        assertEquals(1, Regex("""addGeneratedSourceDirectory\(oneosFiles""").findAll(build).count())
        // Pull request #9: the full variants also check the finished APK (checkFull*StagingApk).
        assertTrue(Regex("""\"full\" -> \{\s*variant\.sources\.assets\?\.addGeneratedSourceDirectory\(oneosFiles, OneOsFilesTask::outputDir\)""")
            .containsMatchIn(build))
        assertTrue(build.contains("applicationIdSuffix = \".probe\""))
    }

    private companion object {
        /** Which app to allow: "Allow OneOS", "for OneOS", "visible to OneOS", not followed by " Probe" (app/build.gradle.kts has the same). */
        val OTHER_APP_ROOT = Regex("""(?:[Aa]llow(?:ed for)?|for|visible to) OneOS\b(?! Probe)""")

        /** Which app holds the results. */
        val OTHER_APP_FILES = Regex("""\b(?:(?:go to|stay in) OneOS\b(?! Probe)|OneOS(?:'s storage| removes| wrote))""")
    }
}
