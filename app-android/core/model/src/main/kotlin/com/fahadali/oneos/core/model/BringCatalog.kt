package com.fahadali.oneos.core.model

/**
 * The catalog of apps One UI offers to bring, for the guest's own "Bring apps
 * from One UI" screen. The app builds it at every start from the same candidates
 * the Bring apps screen lists ([BringApps.eligible]) and the root verb
 * `bring-catalog` writes it to `$STAGE/data/oneos_bring_catalog/catalog.tsv`
 * (the guest reads it at `/data/oneos_bring_catalog/catalog.tsv`, not secret:
 * names and icons only). One line per app, tab separated:
 * `<package> TAB <label> TAB <base64 of a 96x96 PNG icon, no line breaks>`.
 * The root script checks every line again before it writes anything.
 */
object BringCatalog {
    /** Where `bring-catalog` writes under the guest's data; the guest reads it at /data/[DIR]/[FILE]. */
    const val DIR = "oneos_bring_catalog"
    const val FILE = "catalog.tsv"

    /** At most this many lines, and this many bytes in all (the root script refuses more). */
    const val MAX_APPS = 400
    const val MAX_BYTES = 4 * 1024 * 1024
    const val MAX_LABEL = 80

    /** One app of the catalog: [png] is its icon, 96x96. */
    class Entry(val pkg: String, val label: String, val png: ByteArray)

    /**
     * [raw] as one line of text: tabs, line breaks and other control characters
     * become spaces, runs of spaces one, at most [MAX_LABEL] characters; the
     * package name when nothing is left.
     */
    fun label(raw: String, pkg: String): String {
        val sb = StringBuilder()
        var space = true
        raw.codePoints().forEach { cp ->
            val blank = Character.isISOControl(cp) || Character.isWhitespace(cp) || Character.isSpaceChar(cp)
            if (blank) {
                if (!space) sb.append(' ')
                space = true
            } else {
                sb.appendCodePoint(cp)
                space = false
            }
        }
        val s = sb.toString().trim()
        val cut = if (s.codePointCount(0, s.length) > MAX_LABEL) s.substring(0, s.offsetByCodePoints(0, MAX_LABEL)).trim() else s
        return cut.ifEmpty { pkg }
    }

    /** The line for [e], or null when its package is not a package name. */
    fun line(e: Entry): String? {
        if (!BringApps.PACKAGE.matches(e.pkg) || e.png.isEmpty()) return null
        val icon = java.util.Base64.getEncoder().encodeToString(e.png)
        return "${e.pkg}\t${label(e.label, e.pkg)}\t$icon\n"
    }

    /**
     * The catalog text: by label, each package once, at most [MAX_APPS] lines
     * and [MAX_BYTES] bytes (the apps that do not fit are left out, the
     * last ones in label order).
     */
    fun text(entries: Collection<Entry>): String {
        val sb = StringBuilder()
        var bytes = 0
        var n = 0
        val seen = HashSet<String>()
        for (e in entries.sortedWith(compareBy({ label(it.label, it.pkg).lowercase() }, { it.pkg }))) {
            if (n >= MAX_APPS) break
            if (e.pkg in seen) continue
            val l = line(e) ?: continue
            val size = l.toByteArray().size
            if (bytes + size > MAX_BYTES) continue
            seen += e.pkg
            sb.append(l)
            bytes += size
            n++
        }
        return sb.toString()
    }
}
