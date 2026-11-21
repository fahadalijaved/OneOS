package com.fahadali.oneos.core.model

/**
 * Debloater (0.5.32, owner: "debloat a system before it boots ... one universal solution"). Each system's
 * apps, rated by the research lists (one TSV per system family in docs/debloat, 14 images inventoried one by one): Safe (nothing the
 * user needs goes) or Caution (the system works, a named feature goes). Apps the system or OneOS needs are
 * not listed at all, so they can never be ticked.
 *
 * The list ships as the asset [ASSET] (scripts/debloat/make-app-list.py), one line per app:
 * `<S|C> TAB <package> TAB <label> TAB <KiB> TAB <image ids, comma> TAB <folders, ;> TAB <reason> [TAB m]`; the
 * last column, `m`, marks an app MysticGSI's own debloat removes from that system's builds ([App.mystic]).
 * The ticked apps go to root's `debloat` verb as [listText] before each start; guest_prepare.sh hides their
 * folders (a read-only tmpfs over each) and the image file is never changed. Every folder must pass
 * [pathOk], the rule the root script and guest_prepare.sh check again.
 */
object Debloat {
    const val ASSET = "debloat/apps.tsv"

    /** Lines root's `debloat` verb takes at most. */
    const val MAX_LINES = 600

    enum class Rating { SAFE, CAUTION }

    data class App(
        val rating: Rating,
        val pkg: String,
        val label: String,
        val kib: Long,
        val images: Set<String>,
        val folders: List<String>,
        val reason: String,
        /** MysticGSI's own debloat removes it (the screen's "Same as MysticGSI's debloat"). */
        val mystic: Boolean = false,
    )

    private val PACKAGE = Regex("^[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+$")
    private val CHARS = Regex("^[A-Za-z0-9._/+-]+$")
    private val CONTAINERS = setOf("app", "priv-app", "del-app", "del-app-pre", "data-app")
    /** Top folders that are the running phone's, never the image's apps. */
    private val RUNTIME_TOPS = setOf("data", "dev", "proc", "sys", "mnt", "storage", "apex", "vendor", "odm", "cache", "metadata", "sdcard", "debug_ramdisk")
    private val NOT_LAST = CONTAINERS + setOf(
        "overlay", "framework", "lib", "lib64", "bin", "etc", "apex", "system", "product", "system_ext", "vendor",
    )

    /**
     * Whether [p] names one app's own folder in an image: absolute, plain characters, no `.` part, under an
     * app, priv-app, del-app, del-app-pre or data-app folder and not such a folder itself (never a shared one
     * like product/overlay). The same rule as debloat_path_ok in oneos_root.sh and guest_prepare.sh.
     */
    fun pathOk(p: String): Boolean {
        if (!p.startsWith("/") || p.length > 200 || !CHARS.matches(p)) return false
        if ("//" in p || "/." in p || p.endsWith("/")) return false
        val parts = p.substring(1).split('/')
        if (parts.first() in RUNTIME_TOPS || parts.last() in NOT_LAST) return false
        return parts.dropLast(1).any { it in CONTAINERS }
    }

    /** The asset's apps; a line that does not parse, or names a folder [pathOk] refuses, is left out. */
    fun parse(text: String): List<App> = text.lineSequence().mapNotNull { line ->
        if (line.isBlank() || line.startsWith("#")) return@mapNotNull null
        val c = line.split('\t')
        if (c.size != 7 && c.size != 8) return@mapNotNull null
        val rating = when (c[0]) { "S" -> Rating.SAFE; "C" -> Rating.CAUTION; else -> return@mapNotNull null }
        if (!PACKAGE.matches(c[1])) return@mapNotNull null
        val folders = c[5].split(';').filter { it.isNotEmpty() }
        if (folders.isEmpty() || !folders.all(::pathOk)) return@mapNotNull null
        App(rating, c[1], c[2].ifBlank { c[1] }, c[3].toLongOrNull() ?: 0, c[4].split(',').filter { it.isNotEmpty() }.toSet(), folders, c[6],
            mystic = c.size == 8 && c[7] == "m")
    }.toList()

    /** [image]'s apps, Safe first, each by label. */
    fun forImage(all: List<App>, image: String): List<App> =
        all.filter { image in it.images }.sortedWith(compareBy<App>({ it.rating }, { it.label.lowercase() }, { it.pkg }))

    /** Root's `debloat` stdin for [apps]: one `<package> TAB <folder>` line per folder; empty = hide nothing. */
    fun listText(apps: Collection<App>): String =
        apps.sortedBy { it.pkg }.flatMap { a -> a.folders.map { "${a.pkg}\t$it\n" } }.take(MAX_LINES).joinToString("")

    /** The groups the Debloat screens show apps in, in their order. */
    enum class Group { PARTNER, MAKER, GOOGLE, ANDROID, CHIP }

    private val MAKER_PREFIXES = listOf(
        "com.samsung.", "com.sec.", "com.osp.", "com.wsomacp", "com.oplus.", "com.coloros.", "com.heytap.", "com.nearme.",
        "com.oppo.", "com.oneplus.", "net.oneplus.", "andes.oplus.", "com.finshell.", "com.vivo.", "com.bbk.", "com.iqoo.",
        "com.vos.", "com.miui.", "com.xiaomi.", "com.mi.", "com.mipay.", "com.milink.", "com.miuix.", "com.hyper.",
        "com.nothing.", "com.nothinglondon.", "org.lineageos.", "org.omnirom.", "org.calyxos.", "com.infinity.",
        "com.stevesoltys.", "com.google.android.apps.pixel", "com.google.android.pixel",
    )
    private val CHIP_PREFIXES = listOf("com.qualcomm.", "com.qti.", "vendor.qti.", "com.mediatek.", "com.goodix.", "com.focaltech.")

    /** Which [Group] [pkg] belongs to: the system maker's, Google's, Android's, the chip's, or else a partner's or carrier's. */
    fun group(pkg: String): Group = when {
        MAKER_PREFIXES.any { pkg.startsWith(it) } -> Group.MAKER
        CHIP_PREFIXES.any { pkg.startsWith(it) } -> Group.CHIP
        pkg.startsWith("com.google.") -> Group.GOOGLE
        pkg.startsWith("com.android.") -> Group.ANDROID
        else -> Group.PARTNER
    }

    /** "1.2 GB", "340 MB", "12 KB". */
    fun size(kib: Long): String = when {
        kib >= 1024L * 1024 -> String.format(java.util.Locale.ROOT, "%.1f GB", kib / (1024.0 * 1024))
        kib >= 1024 -> "${kib / 1024} MB"
        else -> "$kib KB"
    }
}
