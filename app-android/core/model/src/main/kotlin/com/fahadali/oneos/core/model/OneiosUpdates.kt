package com.fahadali.oneos.core.model

/**
 * The OneOS APK of a OneiOS release (OneiOS `oneos/interface.md` section 1, `docs/releases.md`): the asset
 * `OneOS-oneios-<versionName>-debug.apk` with `<that name>.sha256` beside it, signed with the OneiOS debug key, and the
 * release notes naming its versionName and versionCode (`versionName **0.5.120**, versionCode **249**`). The app's own
 * update comes from here (2026-11-28): upstream's update.json names APKs signed with another key, which never install
 * over a fork build ([AppUpdate]'s certificate check refuses them).
 */
data class OneiosAppRelease(
    val tag: String,
    val versionName: String,
    val versionCode: Int,
    val assetName: String,
    val url: String,
    val bytes: Long,
    val sha256Url: String,
) {
    /** The [AppUpdate] the updater downloads and checks, once the `.sha256` file was read. */
    fun update(sha256: String): AppUpdate = AppUpdate(versionCode, versionName, url, bytes, sha256.lowercase(), notes = "OneiOS release $tag")
}

object OneiosAppReleases {
    private const val DOWNLOAD_PREFIX = "https://github.com/${OneiosReleases.REPO}/releases/download/"
    val ASSET = Regex("^OneOS-oneios-([0-9]{1,3}(?:\\.[0-9]{1,4}){1,3})-debug\\.apk$")
    private val CODE = Regex("versionCode \\*\\*([0-9]{1,9})\\*\\*")

    /**
     * The OneOS APK in GitHub's release JSON [text], or null when the release has none (a runtime-only release), or
     * its notes name no versionCode (then nothing is offered: the code is what says newer). Only assets of OneiOS's
     * own releases are taken.
     */
    fun parse(text: String): OneiosAppRelease? = runCatching {
        val root = JsonRead.parse(text) as? Map<*, *> ?: return null
        val tag = (root["tag_name"] as? String)?.takeIf { OneiosReleases.validTag(it) } ?: return null
        val assets = (root["assets"] as? List<*>).orEmpty().mapNotNull { it as? Map<*, *> }
        fun url(a: Map<*, *>): String? = (a["browser_download_url"] as? String)?.takeIf { it.startsWith(DOWNLOAD_PREFIX) }
        val apks = assets.filter { a -> (a["name"] as? String)?.let(ASSET::matches) == true }
        val a = apks.singleOrNull() ?: return null
        val name = a["name"] as String
        val bytes = (a["size"] as? Long)?.takeIf { it in 1..AppUpdate.MAX_BYTES } ?: return null
        val assetUrl = url(a) ?: return null
        val sha = assets.firstOrNull { it["name"] == "$name.sha256" }?.let(::url) ?: return null
        val code = CODE.find(root["body"] as? String ?: "")?.groupValues?.get(1)?.toIntOrNull() ?: return null
        OneiosAppRelease(tag, ASSET.matchEntire(name)!!.groupValues[1], code, name, assetUrl, bytes, sha)
    }.getOrNull()
}

/**
 * What the app can update (the owner, 2026-11-28: "Updates should be checked automatically: the runtime, the kernel
 * and the app itself"): one line for the main screen and iOS 27's page, "Update available: runtime 0.1.42 · kernel
 * (built for it) · app 0.5.121", and one tap that runs all of them in order (the runtime, then the kernel built from
 * it, then the app, whose install restarts it).
 */
object OneiosUpdates {
    data class Available(
        /** The newer release's runtime version; null: the staged one is the newest (or none is staged). */
        val runtime: String? = null,
        /** The kernel build id due ([KERNEL_NEXT] when a newer runtime brings its own); null: kernel.kc is current. */
        val kernel: String? = null,
        /** The newer OneOS versionName; null: this one is the newest. */
        val app: String? = null,
    ) {
        val any: Boolean get() = runtime != null || kernel != null || app != null

        /** Whether the tap needs iOS 27's page (the runtime and the kernel run there); false: only the app. */
        val needsPage: Boolean get() = runtime != null || kernel != null

        /** "Update available: runtime 0.1.42 · kernel (rebuilt if the new runtime's differs) · app 0.5.121"; null when nothing is. */
        val line: String?
            get() = if (!any) null else "Update available: " + parts.joinToString(" · ")

        val parts: List<String>
            get() = listOfNotNull(
                runtime?.let { "runtime $it" },
                kernel?.let { if (it == KERNEL_NEXT) "kernel (rebuilt if the new runtime's differs)" else "kernel $it" },
                app?.let { "app $it" },
            )
    }

    const val KERNEL_NEXT = "next"

    /**
     * [stagedRuntime]: the staged runtime's version (null: none staged, so no runtime update: the first one is the
     * user's choice); [latestRuntime]: the newest release's; [kernelDue]: the runtime's kernel build id when the image's
     * kernel.kc is not it (null: current, or not known); [appCode]: this OneOS's versionCode; [app]: the newest
     * release's OneOS APK.
     */
    fun of(stagedRuntime: String?, latestRuntime: String?, kernelDue: String?, appCode: Int, app: OneiosAppRelease?): Available {
        val runtime = latestRuntime?.takeIf {
            stagedRuntime != null && it != stagedRuntime && OneiosManifests.versionAtLeast(it, stagedRuntime)
        }
        // A newer runtime may bring another kernel: Update the kernel runs after it when its kernel.kc differs.
        val kernel = if (runtime != null) KERNEL_NEXT else kernelDue
        return Available(runtime, kernel, app?.takeIf { it.versionCode > appCode }?.versionName)
    }

    /** How often the app looks for a newer release by itself: at most once an hour (no loop: at app start and a screen's resume). */
    const val CHECK_EVERY_MS = 60L * 60 * 1000

    /** After a look that got no answer (offline, GitHub refused), the next one in 10 minutes. */
    const val RETRY_MS = 10L * 60 * 1000

    /** Whether a look is due now: [lastOkAt] the last answered look, [nextTryAt] the retry time after one with no answer. */
    fun checkDue(now: Long, lastOkAt: Long, nextTryAt: Long, force: Boolean = false): Boolean =
        force || (now >= nextTryAt && now - lastOkAt >= CHECK_EVERY_MS)
}
