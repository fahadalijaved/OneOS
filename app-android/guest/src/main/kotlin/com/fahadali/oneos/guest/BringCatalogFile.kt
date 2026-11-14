package com.fahadali.oneos.guest

import java.util.Base64

/**
 * What the OneOS app on One UI left for this system's Bring apps screen: the
 * catalog at /data/oneos_bring_catalog/catalog.tsv (one `package TAB label TAB
 * base64 PNG icon` line per app), and the request / status files of one request
 * under /data/oneos_bring_requests. Pure parsing, no Android classes.
 */
object BringCatalogFile {
    const val CATALOG = "/data/oneos_bring_catalog/catalog.tsv"
    const val REQUESTS = "/data/oneos_bring_requests"

    private val PACKAGE = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+$")

    class Item(val pkg: String, val label: String, val png: ByteArray)

    /** The apps of the catalog text; a line that is not exactly three well-formed fields is skipped. */
    fun parse(text: String): List<Item> {
        val out = LinkedHashMap<String, Item>()
        for (line in text.lineSequence()) {
            val f = line.split('\t')
            if (f.size != 3 || !PACKAGE.matches(f[0]) || f[1].isBlank()) continue
            val png = runCatching { Base64.getDecoder().decode(f[2]) }.getOrNull() ?: continue
            if (f[0] !in out) out[f[0]] = Item(f[0], f[1], png)
        }
        return out.values.sortedBy { it.label.lowercase() }
    }

    /** One request's progress, from the first line of `<pkg>.status`. */
    sealed class Progress {
        object Sent : Progress()
        object Copying : Progress()
        object Installing : Progress()
        object Done : Progress()
        class Failed(val why: String) : Progress()
    }

    /** [line] null or unknown: still [Progress.Sent]. */
    fun progress(line: String?): Progress {
        val l = line?.trim().orEmpty()
        return when {
            l == "copying" -> Progress.Copying
            l == "installing" -> Progress.Installing
            l == "done" -> Progress.Done
            l.startsWith("failed") -> Progress.Failed(l.removePrefix("failed").removePrefix(":").trim().ifEmpty { "no reason given" }.take(200))
            else -> Progress.Sent
        }
    }
}
