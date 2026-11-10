package com.fahadali.oneos.core.model

/**
 * Bring apps (0.4.75, owner: "a way to select our 3rd party apps we want to
 * bring over with us to guest OS with its data ... so we dont have to keep
 * logging in"): copy a user app the phone already has on One UI, with its
 * login (its `/data`), into the guest the first time the guest runs, so it
 * starts signed in. One way, host -> guest, at the moment the owner picks it;
 * nothing in the guest is written back to One UI (the guest never touches the
 * phone's real data, [guest-never-touches-host-data]).
 *
 * The phone's real data is only ever **read** here: the app enumerates the
 * candidates with the package manager (no root), the owner ticks the ones to
 * bring, and the root verb `bring-collect` copies each app's APKs and its
 * `/data` into the guest's data tree (`$STAGE/data/oneos_bring/<pkg>`, which
 * the guest reads at `/data/oneos_bring`), reading One UI's copy and writing
 * only under the stage. The guest's restore step (guest_start.sh) installs
 * them in the guest at boot and lays the saved data over the fresh install
 * with the guest's own uid.
 *
 * This object is the part with no Android in it: which packages may be brought,
 * and the `selected.list` the app writes and the scripts read.
 */
object BringApps {
    /** Where `bring-collect` writes under the guest's data; the guest reads it at /data/[DIR]. */
    const val DIR = "oneos_bring"

    /** The list of chosen packages, one per line, the app sends and the scripts read. */
    const val LIST = "selected.list"

    /**
     * A real Android package name: dot-separated segments, each starting with a
     * letter. Both the app and the root script hold a copy of this check, so a
     * line that is not a package name never reaches a path.
     */
    val PACKAGE = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+$")

    /** OneOS's own packages and the known root managers: never offered, never brought. */
    val NEVER = setOf(
        "com.fahadali.oneos",
        "com.fahadali.oneos.guest",
        "com.fahadali.oneos.probe",
        // KernelSU / its forks' managers (root stays on One UI; the guest has its own).
        "me.weishu.kernelsu",
        "com.rifsxd.ksunext",
        "com.sukisu.ultra",
        "app.kitsusu.manager",
        // Magisk, in case it is side by side.
        "com.topjohnwu.magisk",
    )

    /**
     * May this package be brought into the guest? A plain user app that is not
     * one of ours. [system] is the app's FLAG_SYSTEM / updated-system-app state
     * (One UI's own apps stay on One UI; the guest has its own). [launchable]
     * is whether it has a launcher entry — the apps the owner means ("XGram
     * etc") all do, and it keeps service-only and component packages out.
     */
    fun eligible(pkg: String, system: Boolean, launchable: Boolean): Boolean =
        PACKAGE.matches(pkg) && !system && launchable && pkg !in NEVER

    /** The `selected.list` text for a set of packages (sorted, one per line, trailing newline). */
    fun manifest(packages: Collection<String>): String =
        packages.filter(PACKAGE::matches).distinct().sorted().joinToString("") { "$it\n" }

    /** What became of one copy in the stage, as the root verb `bring-status` tells it. */
    enum class CopyState { WAITING, INSTALLED, FAILED }

    /** What One UI has now that the copy does not: nothing, newer data, another build of the app, or the app is gone. */
    enum class Change { SAME, DATA, APP, GONE }

    /**
     * One brought app in the stage (build 104). [stamp]: when its copy was
     * finished, in epoch seconds (0 for a copy made before build 104).
     * [why]: the guest's own words when it could not install it.
     */
    data class Copy(val pkg: String, val stamp: Long, val state: CopyState, val change: Change, val why: String? = null) {
        /** One UI's app or its data changed after the copy was made. */
        val newer: Boolean get() = change == Change.DATA || change == Change.APP
    }

    /**
     * The `app <pkg> <stamp> <state> <change>` and `why <pkg> <reason>` result
     * lines of `bring-status`, by package. A line that is not exactly that is
     * dropped, so nothing the stage holds can name a state the app does not know.
     */
    fun parseStatus(results: List<String>): List<Copy> {
        val why = HashMap<String, String>()
        for (line in results) {
            val p = line.split(' ', limit = 3)
            if (p.size == 3 && p[0] == "why" && PACKAGE.matches(p[1])) why[p[1]] = p[2].trim()
        }
        val out = LinkedHashMap<String, Copy>()
        for (line in results) {
            val p = line.split(' ')
            if (p.size != 5 || p[0] != "app" || !PACKAGE.matches(p[1])) continue
            val stamp = p[2].takeIf { it.length <= 12 }?.toLongOrNull()?.takeIf { it >= 0 } ?: continue
            val state = CopyState.entries.firstOrNull { it.name.lowercase() == p[3] } ?: continue
            val change = Change.entries.firstOrNull { it.name.lowercase() == p[4] } ?: continue
            out[p[1]] = Copy(p[1], stamp, state, change, why[p[1]]?.takeIf { state == CopyState.FAILED && it.isNotEmpty() })
        }
        return out.values.sortedBy { it.pkg }
    }

    /**
     * The copies a boot brings again on its own, without a tick: the guest has
     * not installed it yet and One UI's is newer, or the guest refused it and
     * the app itself changed since (another build may install). A copy the
     * guest already installed is never replaced unasked: the app's data there
     * may be newer than One UI's, so that takes the owner's tick.
     */
    fun againAtBoot(copies: List<Copy>): List<String> =
        copies.filter { (it.state == CopyState.WAITING && it.newer) || (it.state == CopyState.FAILED && it.change == Change.APP) }
            .map { it.pkg }

    /** The ticked apps: [fresh] the system does not have yet, [there] it has installed already. */
    data class Ticked(val fresh: List<String>, val there: List<String>)

    /**
     * Splits the ticked apps (build 109, owner: "if 2 apps are already present
     * and selected, when i select a 3rd one why it starts to add the previous 2
     * again too ... it should ask me if i want to recheck data of old apps").
     * [Ticked.there]: the system installed its copy; bringing it again replaces
     * its data there, so that is done only when the owner says so (Bring now
     * asks). [Ticked.fresh]: everything else, a copy still waiting or refused
     * included. [copies] null (the stage could not be asked): what was
     * [brought] before counts as there, asked about rather than copied unasked.
     */
    fun split(ticked: Collection<String>, copies: List<Copy>?, brought: Collection<String> = emptyList()): Ticked {
        val has = copies?.filter { it.state == CopyState.INSTALLED }?.map { it.pkg }?.toSet() ?: brought.toSet()
        val (there, fresh) = ticked.distinct().sorted().partition { it in has }
        return Ticked(fresh, there)
    }

    /**
     * What a boot copies: the ticked apps the system does not have yet
     * ([split]) and [againAtBoot]. A ticked app it has already is left for
     * Bring now, where the owner is asked; its tick is kept.
     */
    fun atBoot(ticked: Collection<String>, copies: List<Copy>?, brought: Collection<String> = emptyList()): List<String> =
        (split(ticked, copies, brought).fresh + againAtBoot(copies.orEmpty())).distinct().sorted()

    /** For the boot screen: [coming] copies wait in the stage for the system to install, [there] it installed before. */
    data class BootCount(val coming: Int, val there: Int)

    /**
     * The copies a boot does not copy again ([chosen] are the ones it does),
     * counted for the boot screen. A copy the guest refused is in neither
     * number. [copies] null (the stage could not be asked): nothing is claimed.
     */
    fun bootCount(copies: List<Copy>?, chosen: Collection<String>): BootCount {
        val now = chosen.toSet()
        val rest = copies.orEmpty().filter { it.pkg !in now }
        return BootCount(rest.count { it.state == CopyState.WAITING }, rest.count { it.state == CopyState.INSTALLED })
    }

    private fun apps(n: Int) = if (n == 1) "1 app" else "$n apps"

    /** The boot screen's status while [n] apps are copied: the count, then the one being copied ([at] of [n]). */
    fun bootDetail(n: Int, at: Int = 0, label: String? = null): String =
        "Bringing over ${apps(n)}…" + if (at > 0 && label != null) "\n$label ($at of $n)" else ""

    /**
     * The boot screen's own line about the brought apps (build 108, owner: "the
     * app still doesnt say during the launch page that its bringing over apps
     * too and how many"): it stays under the status until One UI closes.
     * [coming]: copied at this boot or waiting in the stage, the system installs
     * them when it is up. [there]: it installed them before. Null: none.
     */
    fun bootLine(system: String, coming: Int, there: Int): String? = when {
        coming > 0 && there > 0 -> "Bringing over ${apps(coming)} · $there already in $system"
        coming > 0 -> "Bringing over ${apps(coming)} to $system"
        there > 0 -> "Your ${apps(there)} from One UI ${if (there == 1) "is" else "are"} already in $system"
        else -> null
    }

    /** The packages in a `selected.list`, dropping blanks, comments and anything not a package name. */
    fun parseManifest(text: String): List<String> =
        text.lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") }
            .filter(PACKAGE::matches)
            .distinct()
            .toList()
}
