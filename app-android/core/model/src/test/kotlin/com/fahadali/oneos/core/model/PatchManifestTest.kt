package com.fahadali.oneos.core.model

import org.junit.Assert.assertTrue
import org.junit.Test

class PatchManifestTest {
    private val trusted = setOf("fahadalijaved/OneOS-files", "thatjoshguy67/OneOS-files")
    private val set = PackageSets.N6_GLOBAL_F8
    private val image = Images.FIND_N6
    private val valid = PatchManifest(1, set.id, image.rawSha256, "test-1", set.names.map {
        PatchManifest.File(it, "a".repeat(64), 1024, "gh:thatjoshguy67/OneOS-files:fold8-experimental")
    })

    @Test fun acceptsSupportedImagesAndBothTrustedRepositories() {
        assertTrue(valid.check(set, image, trusted).isEmpty())
        assertTrue(valid.copy(files = valid.files.map { it.copy(source = "gh:fahadalijaved/OneOS-files:sets-1") }).check(set, image, trusted).isEmpty())
        val pixel = PackageSets.PIXEL_F8
        assertTrue(valid.copy(setId = pixel.id, imageSha256 = Images.PIXEL_YOGI.rawSha256,
            files = pixel.names.map { valid.files.first().copy(name = it) }).check(pixel, Images.PIXEL_YOGI, trusted).isEmpty())
    }
    @Test fun rejectsOtherImagesSetsAndUnknownSchemas() {
        assertTrue(valid.copy(imageSha256 = "b".repeat(64)).check(set, image, trusted).isNotEmpty())
        assertTrue(valid.copy(setId = "pixel-f8").check(set, image, trusted).isNotEmpty())
        assertTrue(valid.copy(schema = 2).check(set, image, trusted).isNotEmpty())
    }
    @Test fun rejectsScriptsMissingFilesAndDuplicates() {
        assertTrue(valid.copy(files = valid.files + valid.files.first().copy(name = "guest_start.sh")).check(set, image, trusted).isNotEmpty())
        assertTrue(valid.copy(files = valid.files.drop(1)).check(set, image, trusted).isNotEmpty())
        assertTrue(valid.copy(files = valid.files + valid.files.first()).check(set, image, trusted).isNotEmpty())
    }
    @Test fun rejectsUntrustedSourcesInvalidHashesAndOversizeFiles() {
        for (file in listOf(valid.files.first().copy(source = "gh:someone/Other:latest"),
            valid.files.first().copy(sha256 = "invalid"), valid.files.first().copy(bytes = 0),
            valid.files.first().copy(bytes = 268435457))) {
            assertTrue(valid.copy(files = listOf(file) + valid.files.drop(1)).check(set, image, trusted).isNotEmpty())
        }
    }
}
