package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.StageMarker
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

class GuestRuntimeScriptTest {
    // Fixtures must model the loader's explicit safe modes under any caller umask.
    private fun java.io.File.writePrivate(text: String) {
        writeText(text)
        java.nio.file.Files.setPosixFilePermissions(toPath(),
            java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"))
    }

    private fun fixture(test: (FakeRoot, String) -> Unit) {
        val shells = TestShell.available()
        assumeTrue(shells.isNotEmpty())
        shells.forEach { shell -> FakeRoot(shell).use { fr ->
            val profile = Profiles.S_ULTRA_8850
            val choice = profile.choices.first()
            val begun = fr.run(RootScript.Verb.BEGIN, "new", profile.id, choice.imageId, choice.packageSetId, "4")
            assertEquals(begun.toString(), 0, begun.exit)
            fr.stage.resolve(".oneos_stage").writePrivate(StageMarker(4, profile.id, choice.imageId, choice.packageSetId, 1792000000L).toJson())
            test(fr, choice.imageId)
        } }
    }
    @Test fun statusIsReadOnlyEvenWithMountedGuestTree() = fixture { fr, image ->
        fr.mountinfo(listOf(fr.stage.resolve("rootfs").path))
        val before = fr.snapshot()
        val result = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "status")
        assertEquals(result.toString(), 0, result.exit)
        assertEquals(before, fr.snapshot())
        assertTrue(result.reply.results.contains("disabled"))
    }
    @Test fun enablesAndDisablesOnlyTheIdleGuestsRuntime() = fixture { fr, image ->
        val enabled = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "enable")
        assertEquals(enabled.toString(), 0, enabled.exit)
        assertTrue(fr.stage.resolve("data/oneos_root/enabled").isFile)
        val disabled = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "disable")
        assertEquals(disabled.toString(), 0, disabled.exit)
        assertFalse(fr.stage.resolve("data/oneos_root/enabled").exists())
    }
    @Test fun refusesMutationWhileMountedWithoutChangingAnything() = fixture { fr, image ->
        fr.mountinfo(listOf(fr.stage.resolve("rootfs").path))
        val before = fr.snapshot()
        val result = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "enable")
        assertEquals(result.toString(), 2, result.exit)
        assertEquals(before, fr.snapshot())
    }
    @Test fun moduleStateAndMetadataStayInTheSelectedGuest() = fixture { fr, image ->
        val module = fr.stage.resolve("data/oneos_root/adb/modules_update/test_module")
        module.mkdirs()
        module.resolve("module.prop").writePrivate("id=test_module\nname=Test module\ndescription=Example with spaces\nversion=1\n")
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "off").exit)
        assertTrue(module.resolve("disable").isFile)
        val status = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "status")
        assertTrue(status.reply.results.any { it.startsWith("module-info test_module 0 modules_update module ") && it.contains("54657374206d6f64756c65") })
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "on").exit)
        assertFalse(module.resolve("disable").exists())
        module.resolve(".oneos-framework").writePrivate("lsposed\n")
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "off").exit)
        assertTrue(module.resolve("module.prop").isFile)
        assertFalse(module.resolve("remove").exists())
        assertEquals(2, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "on").exit)
        fr.stage.resolve("data/oneos_root/framework").writePrivate("test_module\n")
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "on").exit)
        assertFalse(module.resolve("disable").exists())
    }
    @Test fun removalIsDeferredAndCanBeCancelled() = fixture { fr, image ->
        val module = fr.stage.resolve("data/oneos_root/adb/modules/test_module")
        module.mkdirs(); module.resolve("module.prop").writePrivate("id=test_module\nname=Test\nauthor=An author\nversion=2\nversionCode=2\n")
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "remove").exit)
        assertTrue(module.resolve("remove").isFile); assertTrue(module.resolve("module.prop").isFile)
        assertEquals(0, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "restore").exit)
        assertFalse(module.resolve("remove").exists())
        val status = fr.run(RootScript.Verb.GUEST_RUNTIME, image, "status")
        assertTrue(status.reply.results.any { it.contains("416e20617574686f72") })
    }
    @Test fun expandedMetadataSurvivesTheReplyParser() = fixture { fr, image ->
        val module=fr.stage.resolve("data/oneos_root/adb/modules/example")
        module.mkdirs();module.resolve("module.prop").writePrivate("id=example\nname=Example\ndescription=${"description ".repeat(70)}\nversion=2\nversionCode=2\nauthor=Author\nupdateJson=https://example.org/update.json\n")
        val row=fr.run(RootScript.Verb.GUEST_RUNTIME,image,"status").reply.results.first { it.startsWith("module-info ") }
        assertTrue(row.length > 500);assertEquals(13,row.split(' ').size)
        assertTrue(row.contains("417574686f72"));assertTrue(row.endsWith("- 0"))
    }
    @Test fun oversizedMetadataCannotBecomeAPartialReply() {
        val reply=RootReply();reply.accept("@@RESULT module-info "+"a".repeat(9000))
        assertTrue(reply.results.isEmpty())
        reply.accept("@@RESULT other "+"b".repeat(9000));assertEquals(500,reply.results.single().length)
    }
    @Test fun selectedFrameworkCannotBeRemoved() = fixture { fr, image ->
        val module = fr.stage.resolve("data/oneos_root/adb/modules/zygisk_vector")
        module.mkdirs(); module.resolve("module.prop").writePrivate("id=zygisk_vector\n")
        assertEquals(2, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "zygisk_vector", "remove").exit)
        assertFalse(module.resolve("remove").exists())
    }
    @Test fun refusesModuleMutationWhileGuestMounted() = fixture { fr, image ->
        fr.mountinfo(listOf(fr.stage.resolve("rootfs").path))
        val before = fr.snapshot()
        assertEquals(2, fr.run(RootScript.Verb.GUEST_MODULE_STATE, image, "test_module", "off").exit)
        assertEquals(before, fr.snapshot())
    }
}
