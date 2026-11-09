package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class GuestModuleBundleTest {
    private fun bundle(extra: String, id: String = "example") = Files.createTempDirectory("module-test").toFile().let { dir ->
        try {
            val zip = dir.resolve("module.zip")
            ZipOutputStream(zip.outputStream()).use { out ->
                listOf("module.prop" to "id=$id\nname=Example\n", extra to "payload").forEach { (path, value) ->
                    out.putNextEntry(ZipEntry(path)); out.write(value.toByteArray()); out.closeEntry()
                }
            }
            val output = dir.resolve("bundle")
            GuestModuleBundle.write(zip, output) to output.readBytes()
        } finally { dir.deleteRecursively() }
    }
    @Test fun packagesModuleWithoutExecutingItsInstaller() {
        val (info, bytes) = bundle("customize.sh")
        assertEquals("example", info.id)
        assertTrue(bytes.toString(Charsets.ISO_8859_1).contains(".oneos-pending"))
        assertTrue(bytes.takeLast(6).toByteArray().contentEquals("0 0 0\n".toByteArray()))
    }
    @Test fun rejectsTraversalAndAbsolutePaths() {
        listOf("../escape", "system/../../escape", "/data/adb/escape", "system/./file", "a\\b").forEach { path ->
            assertThrows(IllegalArgumentException::class.java) { bundle(path) }
        }
    }
    @Test fun protectsRuntimeProviderIds() {
        listOf("vector", "oneos", "zygisksu", "../bad").forEach { id ->
            assertThrows(IllegalArgumentException::class.java) { bundle("system/example", id) }
        }
    }
}
