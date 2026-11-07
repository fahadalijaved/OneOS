package com.fahadali.oneos.core.model

/** Contributor trust and compatibility are declared once, in packages/patch-sources.json. */
data class PatchSource(
    val id: String,
    val label: String,
    val repository: String,
    val tag: String?,
    val targets: List<Target> = emptyList(),
) {
    data class Target(val profile: String, val image: String, val set: String)
    val stable: Boolean get() = id == STABLE_ID
    fun supports(profile: String, image: String, set: String): Boolean =
        stable || Target(profile, image, set) in targets

    fun check(): List<String> = buildList {
        if (!Regex("[a-z0-9][a-z0-9-]{0,39}").matches(id)) add("Invalid patch source id")
        if (label.isBlank() || label.length > 100) add("Invalid patch source label")
        if (!Regex("[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.-]*").matches(repository)) add("Invalid patch repository")
        if (!stable && (tag == null || !Regex("[a-z0-9][a-z0-9.-]{0,39}").matches(tag))) add("Invalid patch release tag")
        if (!stable && targets.isEmpty()) add("A contributor needs explicit device/image targets")
        if (targets.distinct().size != targets.size) add("Duplicate patch target")
        for (target in targets) {
            val profile = Profiles.BUILT_IN.firstOrNull { it.id == target.profile }
            if (profile?.choice(target.image)?.packageSetId != target.set || PackageSets.byId(target.set)?.imageId != target.image)
                add("Patch target is not supported by this app: $target")
            else if (PackageSets.byId(target.set)!!.names.none { it in PatchManifest.REPLACEABLE })
                add("Patch target has no file a channel may replace: $target")
        }
    }

    companion object {
        const val STABLE_ID = "oneos"
        val STABLE = PatchSource(STABLE_ID, "OneOS patches (Stable)", "fahadalijaved/OneOS-files", null)
    }
}
