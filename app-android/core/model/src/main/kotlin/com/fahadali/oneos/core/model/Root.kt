package com.fahadali.oneos.core.model

enum class RootKind(val label: String) {
    KERNELSU("KernelSU"),
    MAGISK("Magisk"),
    APATCH("APatch"),
    OTHER("su (unknown manager)"),
    NONE("None found"),
}

enum class SuState { GRANTED, DENIED, NOT_FOUND, TIMEOUT, ERROR }

/** Result of the one optional `su -c id` probe. */
data class SuProbeResult(
    val state: SuState,
    val uid: Int?,
    /** SELinux context `id` printed, e.g. `u:r:su:s0`. */
    val context: String?,
    /** What su printed (trimmed, at most 500 chars). */
    val output: String,
)

/** Everything known about root without running anything as root. */
data class RootSignals(
    /** Installed root-manager apps (package names). */
    val managerPackages: List<String> = emptyList(),
    /** `su` binaries visible to the app (KernelSU hides its su from apps it has not allowed). */
    val suPaths: List<String> = emptyList(),
    /** The `su -c id` probe, null until the user runs it. */
    val probe: SuProbeResult? = null,
)

/**
 * Root manager (docs/app/compat-safety-logs.md section 1.4). Detected from the
 * manager apps and su binaries, then confirmed with one `su -c id` that the user
 * starts. The markers under /data/adb are not readable without root, so M1 does
 * not use them.
 */
object RootRules {
    /** Keep in sync with the `<queries>` list in core/root/src/main/AndroidManifest.xml. */
    val MANAGER_PACKAGES: Map<String, RootKind> = linkedMapOf(
        "me.weishu.kernelsu" to RootKind.KERNELSU,
        "com.rifsxd.ksunext" to RootKind.KERNELSU,
        "com.sukisu.ultra" to RootKind.KERNELSU,
        // A friend's KernelSU fork (0.4.38 tester: "su (unknown manager)" though it roots fine).
        "app.kitsusu.manager" to RootKind.KERNELSU,
        "com.topjohnwu.magisk" to RootKind.MAGISK,
        "io.github.vvb2060.magisk" to RootKind.MAGISK,
        "io.github.huskydg.magisk" to RootKind.MAGISK,
        "me.bmax.apatch" to RootKind.APATCH,
    )

    fun kind(s: RootSignals): RootKind {
        s.managerPackages.firstNotNullOfOrNull { MANAGER_PACKAGES[it] }?.let { return it }
        if (s.probe?.context.orEmpty().contains(":magisk:")) return RootKind.MAGISK
        if (s.probe?.state == SuState.GRANTED || s.suPaths.isNotEmpty()) return RootKind.OTHER
        return RootKind.NONE
    }

    private val UID_RE = Regex("""\buid=(\d+)""")
    private val CONTEXT_RE = Regex("""\bcontext=(\S+)""")

    /** Parses what `su -c id` printed and its exit code. Root = exit 0 and uid 0. */
    fun parseIdOutput(output: String, exitCode: Int): SuProbeResult {
        val uid = UID_RE.find(output)?.groupValues?.get(1)?.toIntOrNull()
        val context = CONTEXT_RE.find(output)?.groupValues?.get(1)
        val state = if (exitCode == 0 && uid == 0) SuState.GRANTED else SuState.DENIED
        return SuProbeResult(state, uid, context, output.trim().take(500))
    }
}
