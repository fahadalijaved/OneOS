package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test

class PatchSourceTest {
    private val target = PatchSource.Target(Profiles.FOLD7.id, Images.ID_FIND_N6, PackageSets.ID_N6_F8U)
    private val source = PatchSource("another-contributor", "Another contributor's patches", "another-contributor/patches", "testing", listOf(target))

    @Test fun additionalContributorAndDeviceNeedOnlyADeclaration() {
        assertTrue(source.check().isEmpty())
        assertTrue(source.supports(target.profile, target.image, target.set))
        assertFalse(source.supports(Profiles.FOLD8.id, target.image, target.set))
        assertFalse(source.supports(target.profile, Images.PIXEL_YOGI.id, target.set))
        assertFalse(source.supports(target.profile, target.image, PackageSets.PIXEL_F8.id))
    }
    @Test fun requiresExplicitSupportedDeviceImageAndSet() {
        assertTrue(source.copy(targets = emptyList()).check().isNotEmpty())
        assertTrue(source.copy(targets = listOf(target.copy(profile = "unknown"))).check().isNotEmpty())
        assertTrue(source.copy(targets = listOf(target.copy(set = PackageSets.PIXEL_F8.id))).check().isNotEmpty())
        assertTrue(source.copy(targets = listOf(target, target)).check().isNotEmpty())
        // A set with nothing a channel may replace (PatchManifest.REPLACEABLE) cannot be a target.
        assertTrue(source.copy(targets = listOf(PatchSource.Target(Profiles.FOLD8.id, Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8))).check().isNotEmpty())
    }
    @Test fun repositoriesAndReleaseTagsCannotInjectUrlsOrPaths() {
        assertTrue(source.copy(repository = "https://example.com/patches").check().isNotEmpty())
        assertTrue(source.copy(repository = "../patches").check().isNotEmpty())
        assertTrue(source.copy(tag = "../../other").check().isNotEmpty())
    }
    @Test fun manifestTrustBelongsToTheSelectedContributor() {
        val set = PackageSets.N6_F8U
        val manifest = PatchManifest(1, set.id, Images.FIND_N6.rawSha256, "test", set.names.map {
            PatchManifest.File(it, "a".repeat(64), 1, "gh:${source.repository}:${source.tag}")
        })
        val base = set.names.associateWith { "a".repeat(64) }
        assertTrue(manifest.check(set, Images.FIND_N6, base = base).isNotEmpty())
        assertTrue(manifest.check(set, Images.FIND_N6, setOf(source.repository), base = base).isEmpty())
        val scoped = manifest.copy(profileId = Profiles.FOLD7.id)
        assertTrue(scoped.check(set, Images.FIND_N6, setOf(source.repository), Profiles.FOLD7.id, base = base).isEmpty())
        assertTrue(scoped.check(set, Images.FIND_N6, setOf(source.repository), Profiles.FOLD8.id, base = base).isNotEmpty())
    }
}
