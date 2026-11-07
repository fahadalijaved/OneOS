package com.fahadali.oneos.core.model

/** A release may replace known payloads, but cannot change the image or add executable scripts. */
data class PatchManifest(
    val schema: Int,
    val setId: String,
    val imageSha256: String,
    val revision: String,
    val files: List<File>,
    val profileId: String? = null,
) {
    data class File(val name: String, val sha256: String, val bytes: Long, val source: String)

    /**
     * [base] is this app's own list for the set (name -> sha256). Only [REPLACEABLE] files may differ from it:
     * every other file (guards.txt, the guarded jars and binaries, payload images, dex files run as system,
     * archives root unpacks) must be the app's, so a channel can never vouch for its own guards, and a
     * snapshot made for an older app is refused instead of bringing back older payloads.
     */
    fun check(
        set: PackageSet,
        image: ImageRef,
        repositories: Set<String> = setOf(PatchSource.STABLE.repository),
        profile: String? = null,
        base: Map<String, String>,
    ): List<String> = buildList {
        if (profile != null && profileId != profile) add("Patches are for another device")
        if (schema != 1) add("Unsupported patch manifest schema")
        if (setId != set.id || imageSha256 != image.rawSha256) add("Patches are for another system image")
        if (revision.isBlank() || revision.length > 100) add("Invalid patch revision")
        if (files.map { it.name }.toSet() != set.names.toSet() || files.size != set.names.size) add("Patch files do not match this system's file set")
        if (base.keys != set.names.toSet()) add("This app has no complete file list for ${set.id}")
        val hash = Regex("[0-9a-f]{64}")
        val source = Regex("gh:([A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.-]*):[a-z0-9][a-z0-9.-]{0,39}")
        for (file in files) {
            if (!hash.matches(file.sha256)) add("Invalid hash for ${file.name}")
            if (file.bytes !in 1..268_435_456L) add("Invalid size for ${file.name}")
            if (source.matchEntire(file.source)?.groupValues?.get(1) !in repositories) add("Invalid download source for ${file.name}")
            if (file.name !in REPLACEABLE && base[file.name] != file.sha256)
                add("${file.name} is not this app's: a patch channel may only replace ${REPLACEABLE.filter { it in set.names }.joinToString()} (the channel may be for another OneOS version)")
        }
    }

    companion object {
        /**
         * The files a contributor channel may replace (pull request #37 review): the guest's Fold8 SystemUI and
         * the addon archive, whose members fold8_coloros.sh checks before unpacking. Nothing that guards One UI.
         */
        val REPLACEABLE = setOf("Fold8SystemUI.apk", "GlobalVerifiedAddons.tar")
    }
}
