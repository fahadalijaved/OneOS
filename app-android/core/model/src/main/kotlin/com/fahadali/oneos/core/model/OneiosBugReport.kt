package com.fahadali.oneos.core.model

/**
 * Plain bug-report text for sharing OneiOS session logs or pasting into a GitHub issue (the owner, 2026-11-28:
 * "sharing of logs needs to be better and simpler"). Carries only versions, phone model/build and the session summary:
 * no email address, no serial/IMEI, no personal data and nothing from Apple's files.
 */
object OneiosBugReport {
    data class Versions(
        val appName: String,
        val appCode: Int,
        val phoneModel: String,
        val phoneDevice: String,
        val androidRelease: String,
        val androidBuild: String,
        val runtimeVersion: String? = null,
        val imageVersion: String? = null,
        val imageBuild: String? = null,
        val imageKernel: String? = null,
        val runtimeKernel: String? = null,
    )

    /** Short version lines for the zip's `summary.txt` and share-sheet body. */
    fun versionLines(v: Versions): List<String> = buildList {
        add("App: OneOS ${v.appName} (versionCode ${v.appCode})")
        add("Phone: ${v.phoneModel} (${v.phoneDevice}), Android ${v.androidRelease}, ${v.androidBuild}")
        add("Runtime: ${v.runtimeVersion ?: "not staged"}")
        val img = when {
            v.imageVersion != null && v.imageBuild != null -> "iOS ${v.imageVersion} (${v.imageBuild})"
            v.imageVersion != null -> "iOS ${v.imageVersion}"
            else -> "not staged"
        }
        add("Image: $img")
        if (v.imageKernel != null || v.runtimeKernel != null) {
            add("Kernel: image ${v.imageKernel ?: "unknown"}, runtime ${v.runtimeKernel ?: "none"}")
        }
    }

    /** Ready-to-paste Markdown summary for a GitHub issue (versions + last session summary). */
    fun issueMarkdown(v: Versions, summary: OneiosLogs.Summary?, logName: String? = null, iosLogIncluded: Boolean = false): String = buildString {
        appendLine("### Environment")
        for (line in versionLines(v)) appendLine("- $line")
        appendLine()
        appendLine("### Last session summary")
        if (summary != null) {
            logName?.let { appendLine("- Log: `$it`") }
            for (line in OneiosLogs.summaryLines(summary)) appendLine("- $line")
        } else {
            appendLine("- No xnuhost session log was found on this phone.")
        }
        if (iosLogIncluded) appendLine("- iOS unified log (`ioslog-last-boot.txt`) is included in the zip.")
    }.trimEnd()
}
