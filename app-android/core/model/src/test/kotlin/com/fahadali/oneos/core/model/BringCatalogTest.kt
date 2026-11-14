package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BringCatalogTest {
    private val png = byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10)

    @Test
    fun labelsAreOneCleanLine() {
        assertEquals("Chat app", BringCatalog.label("  Chat\t\tapp\r\n", "org.example.chat"))
        assertEquals("a b c", BringCatalog.label("a\u0007b c", "org.example.chat"))
        assertEquals("Café ☕", BringCatalog.label("Café ☕", "org.example.chat"))
        assertEquals("org.example.chat", BringCatalog.label(" \t\n ", "org.example.chat"))
        assertEquals(80, BringCatalog.label("x".repeat(200), "org.example.chat").length)
        // 80 characters, not 80 UTF-16 units: a pair is not cut in half.
        val emoji = BringCatalog.label("😀".repeat(100), "org.example.chat")
        assertEquals(80, emoji.codePointCount(0, emoji.length))
    }

    @Test
    fun lineHasThreeTabSeparatedFields() {
        val l = BringCatalog.line(BringCatalog.Entry("org.example.chat", "Chat\tIt", png))!!
        assertTrue(l.endsWith("\n"))
        val f = l.trimEnd('\n').split('\t')
        assertEquals(listOf("org.example.chat", "Chat It"), f.take(2))
        assertEquals(3, f.size)
        assertTrue(f[2].matches(Regex("[A-Za-z0-9+/=]+")))
        assertTrue(java.util.Base64.getDecoder().decode(f[2]).contentEquals(png))
        assertNull(BringCatalog.line(BringCatalog.Entry("not a package", "x", png)))
        assertNull(BringCatalog.line(BringCatalog.Entry("../x.y", "x", png)))
        assertNull(BringCatalog.line(BringCatalog.Entry("org.example.chat", "x", ByteArray(0))))
    }

    @Test
    fun textIsSortedDistinctAndCapped() {
        val t = BringCatalog.text(
            listOf(
                BringCatalog.Entry("org.example.b", "banana", png),
                BringCatalog.Entry("org.example.a", "Apple", png),
                BringCatalog.Entry("org.example.a", "Apple again", png),
                BringCatalog.Entry("bad", "x", png),
            ),
        )
        assertEquals(listOf("org.example.a", "org.example.b"), t.lines().filter { it.isNotEmpty() }.map { it.substringBefore('\t') })
        val many = (1..450).map { BringCatalog.Entry("org.example.app$it", "App $it", png) }
        assertEquals(BringCatalog.MAX_APPS, BringCatalog.text(many).lines().count { it.isNotEmpty() })
        val big = ByteArray(1_000_000) { 7 }
        val bytes = BringCatalog.text((1..10).map { BringCatalog.Entry("org.example.big$it", "Big $it", big) }).toByteArray().size
        assertTrue(bytes <= BringCatalog.MAX_BYTES)
        assertFalse(BringCatalog.text(emptyList()).isNotEmpty())
    }
}
