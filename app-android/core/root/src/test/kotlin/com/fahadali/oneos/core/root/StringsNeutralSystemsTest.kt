package com.fahadali.oneos.core.root

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * StringsNeutralTest for Choose a system and Setting up (the redesign's
 * systems area): their strings, Kotlin and layouts never name a system in
 * fixed text; the name comes from the image table at runtime.
 */
class StringsNeutralSystemsTest {
    private val src = Shipped.appSources

    private val names = Regex("""\b(?:ColorOS|OPPO|Lineage|Pixel|Find N6|Find X9|lineage_stage)\b""")

    @Test
    fun theSystemsStringsNameNoSystem() {
        val f = File(src, "full/res/values/strings_systems.xml")
        assertTrue("${f.name} is missing", f.isFile)
        val strings = Regex("""<string name="(\w+)"[^>]*>(.*?)</string>""", RegexOption.DOT_MATCHES_ALL)
            .findAll(f.readText()).associate { it.groupValues[1] to it.groupValues[2] }
        assertTrue("no strings found", strings.size > 40)
        for ((k, v) in strings) {
            assertEquals("$k: $v", null, names.find(v)?.value)
        }
    }

    @Test
    fun theSystemsCodeAndLayoutsNameNoSystem() {
        val ui = File(src, "full/kotlin/com/fahadali/oneos/ui")
        val layouts = File(src, "full/res/layout")
        val files = listOf("SystemsActivity.kt", "SetupProgressActivity.kt", "SetupRingView.kt", "ChipFlowLayout.kt").map { File(ui, it) } +
            listOf(
                "activity_systems.xml", "systems_screen.xml", "systems_card.xml", "systems_chip.xml",
                "activity_setup_progress.xml", "setup_progress_screen.xml", "setup_step.xml",
            ).map { File(layouts, it) }
        for (f in files) {
            assertTrue("${f.name} is missing", f.isFile)
            // Comments may say what the text was; the code's own strings may not name a system.
            val code = f.readLines().filterNot { l -> l.trimStart().let { it.startsWith("*") || it.startsWith("//") || it.startsWith("/*") || it.startsWith("<!--") } }
            for ((i, l) in code.withIndex()) {
                assertEquals("${f.name}:${i + 1}: $l", null, names.find(l)?.value)
            }
        }
    }
}
