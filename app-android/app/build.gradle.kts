import java.security.MessageDigest
import java.util.Properties
import java.util.zip.ZipFile

plugins {
    alias(libs.plugins.android.application)
}

fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

fun sha256(f: File): String {
    val md = MessageDigest.getInstance("SHA-256")
    f.inputStream().use { input ->
        val buf = ByteArray(1 shl 16)
        while (true) {
            val n = input.read(buf)
            if (n < 0) break
            md.update(buf, 0, n)
        }
    }
    return md.digest().joinToString("") { "%02x".format(it) }
}

// --- What build 2 ships in the APK (AA8, AA9) --------------------------------
// The package sets, as the server built them (out/ is not in git): only the
// files the checked-in app-android/packages/<set>.sha256 names, with exactly
// those hashes, or the build fails. Deduplicated by SHA-256 into
// assets/oneos/files/<sha256>; per-set lists in assets/oneos/sets/.
val repoRoot: File = rootProject.projectDir.parentFile
// Explicit local test payloads can carry a newly built guest without changing release pins.
val testPackagesDir = providers.gradleProperty("oneos.testPackagesDir").orNull
val packagesDir: File = rootProject.file(testPackagesDir ?: "packages")
if (testPackagesDir != null) {
    gradle.taskGraph.whenReady {
        check(allTasks.none { it.name.contains("Release", ignoreCase = true) }) {
            "oneos.testPackagesDir is for local debug builds only; release builds use the checked-in package pins."
        }
    }
}
// Official builds must carry the normally signed guest release artifact, never
// a debug APK or a local system-scan overlay left by device development.
gradle.taskGraph.whenReady {
    if (allTasks.any { it.project.path == ":app" && it.name.contains("FullRelease") }) {
        val releaseGuest = rootProject.file("guest/build/outputs/apk/release/guest-release.apk")
        val stagedGuest = File(repoRoot, "switcher/assets/guest_manager.apk")
        check(releaseGuest.isFile && stagedGuest.isFile && sha256(releaseGuest) == sha256(stagedGuest)) {
            "Build and stage the signed guest release first: scripts/build-guest-manager.sh release"
        }
    }
}
// Every set carries OneOSGuest.apk (app-android/guest, the in-guest "Back to
// One UI" app; the ColorOS sets since their 2026-10-25 rebuild), and
// guest_prepare.sh puts it in the guest's /oem/app.
val packageSets: Map<String, Pair<File, List<String>>> = linkedMapOf(
    "n6-global-f8" to (File(repoRoot, "out/fold8-global-current") to listOf("tethering_payload.img", "OneOSFoldCutout.apk", "OneOSTabletQs.apk")),
    // Find N6 global image (0.4.38), the Z Folds. tethering_payload.img is never mounted.
    "n6-f8u" to (File(repoRoot, "out/overlays_n6g_r15") to listOf("tethering_payload.img")),
    // Find X9 Ultra image, S Ultra: no fold grid either.
    // Find X9 Ultra IN image (0.3.3-0.3.6, again from 0.4.11), the bar phones:
    // the CN set's files (shared by hash) and its cell broadcast module.
    "x9u-in-sultra" to (File(repoRoot, "out/overlays_x9u_in_r70") to listOf("tethering_payload.img", "OneOSWallpapersFoldGrid.apk")),
    // Pixel 11 Fold image (0.3.7), Z Fold (F8U): everything a Pixel session uses,
    // OneOSGuest.apk included, and the fold hinge (scripts/make-fold8-pixel.py --variant f8u).
    "pixel-f8u" to (File(repoRoot, "out/overlays_pixel_f8u_r17") to listOf("tethering_payload.img")),
    // Pixel 11 Pro image (0.4.10), Galaxy S26 Ultra: the same files from that image.
    "pixel-sultra" to (File(repoRoot, "out/overlays_pixel_kodiak_r16") to listOf("tethering_payload.img")),
    "pixel-f8" to (File(repoRoot, "out/overlays_pixel_fold8_r17") to listOf("tethering_payload.img")),
    // Pixel 9 Pro XL image (0.4.22), Galaxy S25 Ultra, S25, S25+ and S24 Ultra: the same files from that image.
    "pixel9-sultra" to (File(repoRoot, "out/overlays_pixel_komodo_r16") to listOf("tethering_payload.img")),
    // Infinity-X image (0.4.27), every phone: one set from that image. Its cellbroadcast module
    // is built from source (0.4.28): the guest keeps One UI's, like tethering.
    "infinityx" to (File(repoRoot, "out/overlays_infinityx_r14") to listOf("tethering_payload.img", "cellbroadcast_payload.img")),
    // HyperOS image (docs/hyperos.md), made for the Z Fold8 Ultra and Z Fold8, on every phone from 0.4.31: Xiaomi's guarded jars,
    // the signal poll and the image's payloads.
    "hyper-f8u" to (File(repoRoot, "out/overlays_hyperos_r25") to listOf("tethering_payload.img")),
    // Nothing OS 5.0 (0.4.33), the Z Fold8 Ultra only: its chips need SVE/SME.
    "nothing-f8u" to (File(repoRoot, "out/overlays_nothing_r32") to listOf("tethering_payload.img")),
    // OxygenOS 16 (0.4.67, experimental), for the phones on One UI 8 (Android 16): no fold overlays, no
    // tethering (One UI's stays), no apex requirement list (no ColorOS set ships one).
    "oxygen16" to (File(repoRoot, "out/overlays_oxygen16_r2") to listOf("tethering_payload.img", "OneOSWallpapersFoldGrid.apk",
        "OneOSFoldCutout.apk", "OneOSTabletQs.apk", "oneos-apex-requires.txt")),
    // OriginOS 7 (0.4.73, experimental): set r17 = r14 plus the vivo fold cutout overlay (the cover's lens).
    "originos" to (File(repoRoot, "out/overlays_originos_cn_r17") to listOf("OneOSWallpapersFoldGrid.apk", "OneOSTabletQs.apk")),
)
// The series downloads (0.4.25): -Poneos.series=<id> packs only the sets that
// app-android/packages/series.txt lists for it (ApkSeries keeps the same lists,
// ApkSeriesTest), the full edition's version name ends in "-<id>" and
// BuildConfig.SERIES names it. Without the property: every set, SERIES "".
val seriesId: String? = (findProperty("oneos.series") as String?)?.trim()?.takeIf { it.isNotEmpty() }
val seriesSets: Map<String, Set<String>> = File(packagesDir, "series.txt").readLines()
    .map { it.trim() }.filter { it.isNotEmpty() && !it.startsWith("#") }
    .associate { l -> l.split(Regex("\\s+")).let { it.first() to it.drop(1).toSet() } }
// 0.4.41 (owner: 1.5 GB APKs are too much): the set files stay out of the APK. It carries
// every set's list and each file's size and Drive id (packages/remote.txt), and the app
// downloads the files its phone's set needs, by hash. -Poneos.packSets=true packs them as
// before (a local test build, no download).
val packSetsInApk: Boolean = (findProperty("oneos.packSets") as String?)?.trim() == "true"
// 0.4.53: each file's sources, comma-separated: "gh:<tag>" (an asset of that release of fahadalijaved/OneOS-files,
// named by its sha256) and Drive ids, copies in OneOS/files and OneOS/files2.. (Drive refuses a file once "too
// many users" downloaded it that day; each copy has its own limit).
val setRemoteIds: Map<String, String> = File(packagesDir, "remote.txt").takeIf { it.isFile }?.readLines()
    ?.map { it.trim() }?.filter { it.isNotEmpty() && !it.startsWith("#") }
    ?.associate { l ->
        // gh:<tag> (GitHub), sf (SourceForge, 0.4.65), or a Drive file id.
        val src = "(gh:(?:[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+:)?[a-z0-9][a-z0-9.-]{0,39}|sf|[A-Za-z0-9_-]{20,80})"
        val m = Regex("^([0-9a-f]{64}) ($src(,$src){0,15})$").matchEntire(l)
            ?: throw GradleException("packages/remote.txt: not a '<sha256> <source>[,<source>...]' line: $l")
        m.groupValues[1] to m.groupValues[2]
    } ?: emptyMap()
val packedSets: Set<String> = if (seriesId == null) {
    packageSets.keys
} else {
    val sets = seriesSets[seriesId] ?: throw GradleException("oneos.series: '$seriesId' is not in packages/series.txt (${seriesSets.keys})")
    (sets - packageSets.keys).takeIf { it.isNotEmpty() }?.let { throw GradleException("packages/series.txt: $seriesId names unknown sets $it") }
    sets
}
// Session scripts copied from switcher/assets at build time (plus the expected
// installd table). oneos_tunnel.sh (the server tunnel) and 7zz are never shipped.
val sessionScripts: Map<String, File> = linkedMapOf(
    "guest_runtime.sh" to File(repoRoot, "switcher/assets/guest_runtime.sh"),
    "guest_root" to File(repoRoot, "switcher/assets/guest_root"),
    "guest_zygiskd" to File(repoRoot, "switcher/assets/guest_zygiskd"),
    "guest_zygisk_ptrace" to File(repoRoot, "switcher/assets/guest_zygisk_ptrace"),
    "guest_zygisk.so" to File(repoRoot, "switcher/assets/guest_zygisk.so"),
    "guest_vector.bundle" to File(repoRoot, "switcher/assets/guest_vector.bundle"),
    "guest_manager.apk" to File(repoRoot, "switcher/assets/guest_manager.apk"),
    "oneos_switch.sh" to File(repoRoot, "switcher/assets/oneos_switch.sh"),
    "oneos_lockstate.sh" to File(repoRoot, "switcher/assets/oneos_lockstate.sh"),
    "boot_status.sh" to File(repoRoot, "switcher/assets/boot_status.sh"),
    "OneOSBootStatus.dex" to File(repoRoot, "switcher/assets/OneOSBootStatus.dex"),
    "oneos_boot_icon.png" to File(repoRoot, "switcher/assets/oneos_boot_icon.png"),
    "guest_prepare.sh" to File(repoRoot, "switcher/assets/guest_prepare.sh"),
    "guest_start.sh" to File(repoRoot, "switcher/assets/guest_start.sh"),
    "guest_props.sh" to File(repoRoot, "switcher/assets/guest_props.sh"),
    "return_to_oneui.sh" to File(repoRoot, "switcher/assets/return_to_oneui.sh"),
    // 0.4.61 (pull request #58): Samsung rild's new-SMS queue bypass for the guest (inbound SMS).
    "libsec-ril-patch.sh" to File(repoRoot, "switcher/assets/libsec-ril-patch.sh"),
    "check_host_apex.sh" to File(repoRoot, "switcher/assets/check_host_apex.sh"),
    "bridges.sh" to File(repoRoot, "switcher/assets/bridges.sh"),
    "fold8_coloros.sh" to File(repoRoot, "switcher/assets/fold8_coloros.sh"),
    "OneOSFold8Geometry.dex" to File(repoRoot, "switcher/assets/OneOSFold8Geometry.dex"),
    "fold8_pixel.sh" to File(repoRoot, "switcher/assets/fold8_pixel.sh"),
    "guest_google.sh" to File(repoRoot, "switcher/assets/guest_google.sh"),
    "zygote_exec" to File(repoRoot, "switcher/assets/zygote_exec"),
    // 0.4.32: the Knox edmnativehelper stand-in (switcher/patches/OneOSEdmStub.java,
    // built by build_edm_stub.sh). It ships with the scripts, not in a package set,
    // so every image gets it without rebuilding one. oneos_switch.sh runs it only
    // when ONEOS_GUEST_EDM_STUB=1.
    "OneOSEdmStub.dex" to File(repoRoot, "switcher/assets/OneOSEdmStub.dex"),
    // 0.4.33: Android's Bluetooth audio factory over Samsung's on the phones that
    // only have Samsung's (switcher/native/oneos_btaudio.cpp, built by build.sh).
    // oneos_switch.sh starts it only on such a phone.
    "oneos_btaudio" to File(repoRoot, "switcher/assets/oneos_btaudio"),
    // 0.4.33: the status bar's dimension overlays on bar phones
    // (switcher/patches/OneOSOverlayDimen.java, build_overlay_dimen.sh).
    "OneOSOverlayDimen.dex" to File(repoRoot, "switcher/assets/OneOSOverlayDimen.dex"),
    "host_installd.txt" to File(repoRoot, "switcher/patches/host_installd.txt"),
    // 0.4.66: One UI 8.5's table, staged as host_installd.txt for SDK 36 (Android 16) images.
    "host_installd_a16.txt" to File(repoRoot, "switcher/patches/host_installd_a16.txt"),
)
val switcherNotShipped = setOf("oneos_tunnel.sh", "7zz")

/** `<sha256>  <name>` lines (`#` comments skipped), as sha256sum writes them. */
fun readShaList(f: File): Map<String, String> {
    val out = linkedMapOf<String, String>()
    f.readLines().filter { it.isNotBlank() && !it.startsWith("#") }.forEach { l ->
        val m = Regex("^([0-9a-f]{64})  ([A-Za-z0-9_][A-Za-z0-9._+-]*)$").matchEntire(l)
            ?: throw GradleException("${f.name}: not a sha256sum line: $l")
        check(out.put(m.groupValues[2], m.groupValues[1]) == null) { "${f.name}: ${m.groupValues[2]} listed twice" }
    }
    return out
}

fun renderShaList(entries: Map<String, String>): String =
    entries.entries.sortedBy { it.key }.joinToString("") { "${it.value}  ${it.key}\n" }

// Guest, Probe and unit-test tasks can run before the generated manager APK
// exists. Every full staging build must have it before any task executes.
val hasGuestManager = sessionScripts.getValue("guest_manager.apk").isFile
if (!hasGuestManager) {
    gradle.taskGraph.whenReady {
        check(allTasks.none { it.path == ":app:oneosFiles" }) {
            "Build the guest APK first with scripts/build-guest-manager.sh."
        }
    }
}
val scriptsList: String = renderShaList(sessionScripts.filterKeys { hasGuestManager || it != "guest_manager.apk" }.mapValues { (n, f) ->
    if (!f.isFile) throw GradleException("session script missing: $f (build the guest APK with scripts/build-guest-manager.sh first)")
    sha256(f)
})
// The root script is the full edition's only (src/full); OneOS Probe has none.
val rootScript: File = file("src/full/assets/root/oneos_root.sh")

/**
 * Imports the package sets and the session scripts into content-addressed
 * assets, and fails when a built file differs from the checked-in list.
 */
abstract class OneOsFilesTask : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val sources: ConfigurableFileCollection

    /** set id -> "source dir|omitted,omitted". */
    @get:Input
    abstract val sets: MapProperty<String, String>

    /** name -> source file. */
    @get:Input
    abstract val scripts: MapProperty<String, String>

    @get:Input
    abstract val notShipped: SetProperty<String>

    /** True: the set files go into the APK (local test builds). False: only their sizes and Drive ids. */
    @get:Input
    abstract val packSets: Property<Boolean>

    /** sha256 -> its sources, comma-separated: gh:<tag> and Drive file ids (packages/remote.txt). */
    @get:Input
    abstract val remoteIds: MapProperty<String, String>

    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val packages: DirectoryProperty

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    private fun sha(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        f.inputStream().use { input ->
            val buf = ByteArray(1 shl 16)
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    private fun list(f: File): Map<String, String> {
        val out = linkedMapOf<String, String>()
        f.readLines().filter { it.isNotBlank() && !it.startsWith("#") }.forEach { l ->
            val m = Regex("^([0-9a-f]{64})  ([A-Za-z0-9_][A-Za-z0-9._+-]*)$").matchEntire(l)
                ?: throw GradleException("${f.name}: not a sha256sum line: $l")
            out[m.groupValues[2]] = m.groupValues[1]
        }
        return out
    }

    /** oneos_root.sh `receive`'s limit for one set file (PackagesTest ties the two). */
    private val receiveMax = 268_435_456L

    private fun render(entries: Map<String, String>) =
        entries.entries.sortedBy { it.key }.joinToString("") { "${it.value}  ${it.key}\n" }

    @TaskAction
    fun run() {
        val out = outputDir.get().asFile
        out.deleteRecursively()
        val files = File(out, "oneos/files").apply { mkdirs() }
        val setsDir = File(out, "oneos/sets").apply { mkdirs() }
        val sizes = sortedMapOf<String, Long>()
        val remote = sortedMapOf<String, String>()
        val ids = remoteIds.get()
        val pack = packSets.get()
        val publishedSizes = File(packages.get().asFile, "sizes.txt").takeIf { it.isFile }?.readLines()
            ?.filter { it.isNotBlank() && !it.startsWith("#") }?.associate { line ->
                val parts = line.split(' ')
                require(parts.size == 2 && Regex("[0-9a-f]{64}").matches(parts[0])) { "invalid published size: $line" }
                val bytes = parts[1].toLong()
                require(bytes in 1..receiveMax) { "invalid published size: $line" }
                parts[0] to bytes
            } ?: emptyMap()
        fun put(src: File, sum: String) {
            val dst = File(files, sum)
            if (!dst.exists()) src.copyTo(dst)
            sizes[sum] = src.length()
        }
        // A set file: in the APK (packSets), else its size and Drive id only.
        fun putSet(src: File, sum: String, problems: MutableList<String>) {
            if (pack) { put(src, sum); return }
            val id = ids[sum]
            if (id == null) { problems += "${src.name} ($sum) is not on Drive: run scripts/release-files.py"; return }
            sizes[sum] = src.length()
            remote[sum] = id
        }
        for ((id, spec) in sets.get()) {
            val dir = File(spec.substringBefore('|'))
            val omitted = spec.substringAfter('|').split(',').filter { it.isNotBlank() }.toSet()
            val listFile = File(packages.get().asFile, "$id.sha256")
            if (!listFile.isFile) throw GradleException("$id: app-android/packages/$id.sha256 is missing")
            if (pack && !dir.isDirectory) throw GradleException("$id: $dir is missing (build the overlays on the server first)")
            val want = list(listFile)
            val present = (dir.listFiles()?.toList() ?: emptyList()).filter { it.isFile }.map { it.name }.toSet()
            val problems = mutableListOf<String>()
            for (n in present - want.keys - omitted) problems += "$n is in $dir but not in packages/$id.sha256"
            for ((n, sum) in want) {
                val f = File(dir, n)
                val publishedBytes = publishedSizes[sum]
                // Remote files are pinned by the set manifest; no OEM build folder is needed
                // (a contributor's checkout). Where the folder exists, it is checked as before.
                if (!pack && !dir.isDirectory && n !in omitted && ids[sum] != null && publishedBytes != null) {
                    sizes[sum] = publishedBytes
                    remote[sum] = ids.getValue(sum)
                    continue
                }
                when {
                    n in omitted -> problems += "$n is listed but left out of $id"
                    !f.isFile -> problems += "$n is missing from $dir"
                    f.length() > receiveMax -> problems += "$n is ${f.length()} bytes, over root's receive limit ($receiveMax)"
                    sha(f) != sum -> problems += "$n differs from packages/$id.sha256 (a rebuilt overlay?)"
                    else -> putSet(f, sum, problems)
                }
            }
            if (problems.isNotEmpty()) throw GradleException("package set $id:\n  " + problems.joinToString("\n  "))
            File(setsDir, "$id.sha256").writeText(render(want))
        }
        val scriptSums = linkedMapOf<String, String>()
        for ((n, path) in scripts.get()) {
            val f = File(path)
            val sum = sha(f)
            put(f, sum)
            scriptSums[n] = sum
        }
        // A new file in switcher/assets is shipped or excluded on purpose, never silently.
        val switcher = File(scripts.get().getValue("oneos_switch.sh")).parentFile
        val unknown = switcher.listFiles()!!.filter { it.isFile }.map { it.name }.toSet() - scripts.get().keys - notShipped.get()
        if (unknown.isNotEmpty()) throw GradleException("switcher/assets has $unknown: add it to sessionScripts or switcherNotShipped in app/build.gradle.kts")
        File(setsDir, "scripts.sha256").writeText(render(scriptSums))
        File(files, "index.txt").writeText(sizes.entries.joinToString("") { "${it.key} ${it.value}\n" })
        File(files, "remote.txt").writeText(remote.entries.joinToString("") { "${it.key} ${it.value}\n" })
        val registryFile = File(packages.get().asFile, "patch-sources.json")
        val registry = groovy.json.JsonSlurper().parse(registryFile) as Map<*, *>
        require(registry["schema"] == 1) { "Unsupported patch source registry" }
        val contributors = registry["contributors"] as List<*>
        val sourceIds = mutableSetOf<String>()
        val rootTable = File(packages.get().asFile, "../app/src/full/assets/root/oneos_root.sh").readText()
        val pairs = Regex("\"([a-z0-9-]+) ([a-z0-9-]+)\"\\) echo ([a-z0-9-]+) ;;")
            .findAll(rootTable).map { it.groupValues.drop(1) }.toSet()
        val imageHashes = Regex("""^\s+([a-z0-9-]+)\) echo "[0-9]+ ([0-9a-f]{64})" ;;$""", RegexOption.MULTILINE)
            .findAll(rootTable).associate { it.groupValues[1] to it.groupValues[2] }
        for (item in contributors) {
            val source = item as Map<*, *>
            val id = source["id"] as String
            require(id != "oneos" && Regex("[a-z0-9][a-z0-9-]{0,39}").matches(id) && sourceIds.add(id)) { "Invalid/duplicate contributor id: $id" }
            require((source["label"] as String).let { it.isNotBlank() && it.length <= 100 })
            require(Regex("[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.-]*").matches(source["repository"] as String))
            require(Regex("[a-z0-9][a-z0-9.-]{0,39}").matches(source["tag"] as String))
            val targets = source["targets"] as List<*>
            require(targets.isNotEmpty() && targets.distinct().size == targets.size)
            for (value in targets) {
                val target = value as Map<*, *>
                require(listOf(target["profile"], target["image"], target["set"]) in pairs) { "Unsupported patch target: $target" }
                val image = target["image"] as String
                val hash = target["imageSha256"] as String
                require(Regex("[0-9a-f]{64}").matches(hash) && imageHashes[image] == hash) { "Patch target image hash differs from this app" }
            }
        }
        File(out, "oneos/patch-sources.json").writeBytes(registryFile.readBytes())
    }
}

val oneosFiles = tasks.register<OneOsFilesTask>("oneosFiles") {
    group = "build"
    description = "Packs the OneOS package sets and session scripts into the APK's assets, checked against app-android/packages."
    for ((dir, _) in packageSets.filterKeys { it in packedSets }.values) sources.from(fileTree(dir))
    for (f in sessionScripts.values) sources.from(f)
    sources.from(rootScript)
    sources.from(fileTree(File(repoRoot, "switcher/assets")))
    sets.set(packageSets.filterKeys { it in packedSets }.mapValues { (_, v) -> "${v.first.path}|${v.second.joinToString(",")}" })
    scripts.set(sessionScripts.mapValues { it.value.path })
    notShipped.set(switcherNotShipped)
    packSets.set(packSetsInApk)
    remoteIds.set(setRemoteIds)
    packages.set(packagesDir)
    outputDir.set(layout.buildDirectory.dir("generated/oneos/assets"))
}

// Release signing key: private to the account that builds releases, never in the
// repo (/srv/projects is shared). Every update must be signed with this same key.
val releaseKeys: Properties? =
    File(System.getProperty("user.home"), ".oneos-release/keystore.properties").takeIf { it.isFile }?.let { f ->
        Properties().apply { f.inputStream().use(::load) }
    }

android {
    sourceSets.getByName("main").kotlin.srcDir(rootProject.file("shared-guest-ui"))
    namespace = "com.fahadali.oneos"
    compileSdk { version = release(37) }

    defaultConfig {
        applicationId = "com.fahadali.oneos"
        minSdk = 31
        targetSdk = 36
        // Friend build 2: the first build that stages and switches (docs/app/DESIGN.md, build 2).
        // 0.3.4: the Galaxy S25 profile, and OneOS Probe as its own app (flavor probe).
        // 0.3.5: Old stages (delete the stages Prepare moved aside).
        // 0.3.7: the Pixel 11 Fold image and its set on the Fold; the Find X9 Ultra IN image is gone.
        // 0.4.24: Pixel guests' camera calls with One UI's transaction codes (framework_patched.jar).
        // 0.4.26: a native-only service fails to start in the guest (Chrome stalled every app start).
        // 0.4.27: the Infinity-X system on every phone.
        // 0.4.28: Infinity-X keeps One UI's cellbroadcast module, sees hwservicemanager on HIDL-only phones.
        // 0.4.29: the Galaxy A57 (Exynos) and Z Flip5, in the s25 series; Send to the OneOS team.
        // 0.4.30: Quick switch between the systems set up on the phone; How's it going? in the guest;
        // the Pixel 9 Pro XL image on every s25 phone.
        // 0.4.31: HyperOS (the Xiaomi lhasa image) for everyone: made for the Z Fold8 Ultra and Z Fold8, the
        // other phones may try it (the cover layout runs as the phone's screen); Samsung's IMS stack in the
        // guest for VoLTE (Infinity-X and HyperOS, where the services.jar carve-out is); the guest's dp
        // scale, cutout, status bar height and corner radius from the phone itself on every image; the
        // Galaxy A56, in the s25 series.
        // 0.4.32: HyperOS starts on the Galaxy S25 Ultra, S25 and S24-era phones again (Xiaomi's
        // auto-installer took the guest's system_server down at boot phase 520); the camera opens
        // without the 5 s Knox wait when Advanced's switch is on (Z Flip5); the composer's panel
        // modes are recorded before the guest's SurfaceFlinger starts, so a display failure says why.
        // 0.4.33: the camera opens without Knox's 5 s wait by default (every 0.4.32
        // camera report), Infinity-X's camera is Aperture (OPPO's needs the Find X9
        // Ultra's camera config) and its status bar keeps off the corners, HyperOS's
        // wallpaper app starts on one-panel phones, the composer capture is written
        // where the logs are collected, and two new phones: Z Fold6, A07.
        // 0.4.34: Infinity-X sound on the S25 series, the Bluetooth audio bridge
        // actually starting, the camera worker stand-in, One UI's brightness curve
        // on every phone (Pixel, HyperOS), HyperOS data apps' libraries.
        // 0.4.35: Nothing OS on the SVE + SME phones with One UI's camera, the Z Flip8
        // and A36, the Pixel 9 Pro XL brightness crash, Samsung's CPU vote released,
        // the ColorOS Fold8 follow-up (pull request #2).
        // 0.4.36: brightness by each panel's own scale (every system), the Z Fold5.
        // 0.4.37: ColorOS's stock UI features on every phone and the Fold8's on every Find N6 fold,
        // One UI's camera codes in the ColorOS IN and Find N6 sets, A2DP offload for ColorOS and Infinity-X.
        // 0.4.38: Magisk's resetprop, HyperOS's mode groups (S23, S24 Ultra, Z Flip5), the camera folder on a
        // first session, diag_samcam.txt; pull request #3: SESL9 redesign, verbose boot/return handoff and
        // interrupted-update recovery.
        // 0.4.39: Samsung IMS registration on ISIM carriers and the SMS service centre's international form
        // (ColorOS), the bar-phone camera's density, HyperOS without SurfaceFlinger's shader pre-warm, ColorOS's
        // first-boot clock reset, the audioserver hand-over only in a crash loop; KernelSU in the guest off.
        // 0.4.40: Galaxy S23 Ultra, Z Flip6 and S24 (Exynos); Samsung IMS's GBA and SIM-slot stand-ins (T-Mobile
        // registration, SMS fallback to CS), HyperOS's DolbyRenderer without Xiaomi's mapper, the camera's 411dp both ways.
        // 0.4.41: one small APK for every phone (the set files downloaded by hash from the owner's Drive) and
        // the app's own update from the latest GitHub release; Samsung Camera folded on bar phones, HyperOS's
        // 64-bit ABI lists on 32-bit-capable phones, a guest's own KernelSU manager removed while guest root is off.
        // 0.4.42: ColorOS's Theme Store on the Find N6 global build (its product config disabled it), setup
        // keeps the stage files that did not change (root keep-files), downloads three files at a time and says
        // when Drive is slow to start one, only the newest log bundle kept, without its unpacked folder.
        // 0.4.43: UX audit (the launch screen shows a new OneOS and sends Welcome back/Restore to Home, one name for
        // each screen in the copy, a light first run, Not available on unsupported systems, Stop asks first, percent and
        // time left, plain setup steps, the blocking check's fix on the pre-boot button, the ways back before the
        // switch, Remove's progress; guest app 0.6: where you are, the ways back incl. the volume keys, How's it going?);
        // report fixes: guest app on Infinity-X, Samsung IMS on the read-only overlay, Exynos UniRender, vendor-ndk.
        // 0.4.44: guest app folders keep the SELinux label the guest gave them (the Theme Store closed on Agree with
        // the bare label every switch put back), the installed update's APK is deleted.
        // 0.4.45: Samsung IMS on every Pixel set (r3: the secims carve-out, its framework members, the SMS centre
        // as an international number, and the wipe-secrets guard the Pixel sets lacked; AT&T Z Fold8 report
        // d4c481b6: no VoLTE, SMS refused); without root the update goes through Android's installer.
        // 0.4.46: the app opens on pull request #3's system carousel again (0.4.43 opened the status Home after a
        // session until Welcome back was its hero, which root off or an update offer could put off for good); One UI's
        // boot-loop check no longer counts a switch and return as a boot loop (it rolled back a Play system update).
        // 0.4.47: ColorOS's Theme Store without its brand check (Find N6 and X9U IN sets: "customised app, not
        // compatible" on every Galaxy); Samsung Camera and the native camera client patch on every Pixel set (r4).
        // 0.4.48: the Theme Store reports OPPO and the Find N6 model to OPPO's server (it sent no themes for samsung);
        // a newer OneOS is a banner with an Update button on the launch screen, not a line of small text.
        // 0.4.49: the Galaxy S25 Edge, S24 FE, A26, A17 and A16 5G (US) from their probe reports (all on One UI 9).
        // A picked file of another system now starts its setup (the card asked for the file again and again).
        // 0.4.50: apps uninstalled in a guest stay uninstalled (their code folders are removed before the next
        // boot); the in-place return names what holds a stage mount when its failsafe reboots.
        // 0.4.51: the debloated Find X9 Ultra ColorOS build retired (never on Drive); the full IN build is every
        // such phone's ColorOS, tested where the debloated one was.
        // 0.4.52: the in-place return no longer reboots for LSPosed's dex2oat wrapper (a bind into ART's APEX it took
        // for One UI's APEX changing; every APEX failsafe in the reports) or for a system_server child not exec'd yet.
        // The Galaxy S26 with Exynos (SM-S942B, m1s) from its probe reports, with the S26+ (Exynos)'s images.
        // 0.4.53: every set file from six Drive copies (OneOS/files, files2..6); a copy Drive refuses ("too many users
        // downloaded this file", 0.4.51 testers) hands over to the next, each phone starting at a copy of its own.
        // 0.4.54: set files from GitHub first (fahadalijaved/OneOS-files, release sets-1: no daily limit), the six
        // Drive copies after (owner: "Drive is still problematic").
        // 0.4.55: Samsung Camera on the bar phones is the Galaxy S26 Ultra's own build, from its firmware, instead of the
        // Z Fold8 Ultra's (whose foldable layouts no shim made right on a bar phone): ColorOS IN r59, Pixel 11 Pro and
        // Pixel 9 Pro XL r5, Infinity-X r4, Nothing OS r22 (samcam_bar.tar for phones). The panel kept at its top rate in
        // Pixel, HyperOS and Nothing OS (it stayed at 24 Hz: 10-15 fps). Infinity-X: Samsung IMS (the carve-out's
        // /system/system_ext path; framework members; SMS centre). The Galaxy A16 4G (SM-A165F).
        versionCode = 119
        versionName = "0.4.90"
        // 0.4.56 (73), TEST CHANNEL ONLY: the Find N6 set's Theme Store logs every OkHttp request and reply (n6g_r7,
        // patches/theme_store_netlog.py) for the owner's "No Data" log; the next public build goes back to n6g_r6.
        // Send to the OneOS team (0.4.29, both editions): the report service's
        // address and its upload-only key, from the team's server (reports/deploy.sh
        // writes them). A build without them shows no Send; Share and Save stay.
        val home = File(System.getProperty("user.home"))
        val reportUrl = File(home, ".oneos-reports-url").takeIf { it.isFile }?.readText()?.trim()
            ?.takeIf { Regex("https://[a-z0-9.-]+").matches(it) }.orEmpty()
        val reportKey = File(home, ".oneos-reports-upload-key").takeIf { it.isFile }?.readText()?.trim()
            ?.takeIf { Regex("[0-9a-f]{32,128}").matches(it) }.orEmpty()
        buildConfigField("String", "REPORT_URL", "\"$reportUrl\"")
        buildConfigField("String", "REPORT_KEY", "\"$reportKey\"")
    }

    // One codebase, two apps (docs/app/DESIGN.md, 0.3.4): "full" is OneOS, the app
    // that switches; "probe" is OneOS Probe, only the device report, the read-only
    // tests and the findings, so anyone can run it and share what it finds. Shared
    // code is in src/main; what only OneOS has is in src/full.
    flavorDimensions += "edition"
    productFlavors {
        create("full") {
            dimension = "edition"
            // Pins for the root path: the launcher runs $STAGE/bin/oneos_root.sh only
            // with this SHA-256, and the app checks every list it ships against these.
            val rootBytes = rootScript.readBytes()
            buildConfigField("String", "ROOT_SCRIPT_SHA256", "\"${sha256(rootBytes)}\"")
            buildConfigField("long", "ROOT_SCRIPT_BYTES", "${rootBytes.size}L")
            buildConfigField("String", "SCRIPTS_SHA256", "\"${sha256(scriptsList.toByteArray())}\"")
            buildConfigField("String", "SERIES", "\"${seriesId.orEmpty()}\"")
            if (seriesId != null) versionNameSuffix = "-$seriesId"
            for ((id, _) in packageSets) {
                val f = File(packagesDir, "$id.sha256")
                val list = if (f.isFile) renderShaList(readShaList(f)) else ""
                buildConfigField("String", "SET_${id.uppercase().replace('-', '_')}_SHA256", "\"${sha256(list.toByteArray())}\"")
            }
        }
        create("probe") {
            dimension = "edition"
            // Its own app next to OneOS (its own root grant), same release key.
            applicationIdSuffix = ".probe"
            versionNameSuffix = "-probe"
        }
    }

    signingConfigs {
        if (releaseKeys != null) {
            create("release") {
                storeFile = file(releaseKeys.getProperty("storeFile"))
                storePassword = releaseKeys.getProperty("storePassword")
                keyAlias = releaseKeys.getProperty("keyAlias")
                keyPassword = releaseKeys.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // What friends get: not debuggable, signed with the OneOS release key.
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    buildFeatures {
        buildConfig = true
    }

    lint {
        abortOnError = true
        // Library modules run their own lintDebug; the app checks its own code.
        checkDependencies = false
    }
}

kotlin {
    jvmToolchain(libs.versions.jvmToolchain.get().toInt())
}

// A release without the key would be an unsigned APK: refuse instead (both editions).
tasks.matching { it.name == "packageFullRelease" || it.name == "packageProbeRelease" }.configureEach {
    val hasKey = releaseKeys != null
    doFirst {
        check(hasKey) { "No release key: ~/.oneos-release/keystore.properties is missing (see app-android/README.md, section Build)." }
    }
}

/**
 * OneOS Probe must stay the read-only app (owner, 0.3.4): checks its packaged
 * APK and merged manifest after every probe build. The app's own assets are
 * the probe runner and its list only (library assets such as SESL's font are
 * fine); nothing of the full edition (the root script, the stage and log
 * lists, the session scripts, the package sets, its code and screens); no
 * text that tells the user to allow "OneOS" for root (OneOS Probe has its own
 * grant, next to OneOS); no permission; under [maxBytes].
 */
abstract class ProbeApkCheckTask : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val apkDir: DirectoryProperty

    @get:Internal
    abstract val loader: Property<com.android.build.api.variant.BuiltArtifactsLoader>

    @get:InputFile
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val manifest: RegularFileProperty

    /** File names that only the full edition may carry (session scripts, root lists, set files). */
    @get:Input
    abstract val forbiddenNames: SetProperty<String>

    @get:Input
    abstract val maxBytes: Property<Long>

    @get:OutputFile
    abstract val report: RegularFileProperty

    @TaskAction
    fun run() {
        val apks = loader.get().load(apkDir.get())?.elements?.map { File(it.outputFile) }.orEmpty()
        if (apks.isEmpty()) throw GradleException("no probe APK in ${apkDir.get().asFile}")
        val problems = mutableListOf<String>()
        val lines = mutableListOf<String>()
        for (apk in apks) {
            if (apk.length() > maxBytes.get()) problems += "${apk.name} is ${apk.length()} B, over ${maxBytes.get()} B"
            ZipFile(apk).use { zip ->
                val names = zip.entries().asSequence().map { it.name }.toList()
                val assets = names.filter { it.startsWith("assets/") }
                for (want in listOf("assets/probe/probe.sh", "assets/probe/commands.list")) {
                    if (want !in names) problems += "${apk.name}: $want is missing"
                }
                for (n in assets) {
                    when {
                        n.startsWith("assets/root/") || n.startsWith("assets/logs/") || n.startsWith("assets/oneos/") ->
                            problems += "${apk.name}: $n is the full edition's"
                        n.startsWith("assets/probe/") && n != "assets/probe/probe.sh" && n != "assets/probe/commands.list" ->
                            problems += "${apk.name}: $n is not the probe runner or its list"
                    }
                }
                // Anywhere in the APK, by name: the session scripts, the lists, the set files.
                for (n in names) {
                    val base = n.substringAfterLast('/')
                    if (base in forbiddenNames.get() || base.endsWith(".guards.txt") || base.endsWith("_payload.img") || base.endsWith("_patched.jar") || base == "surfaceflinger_patched") {
                        problems += "${apk.name}: $n is a full-edition file"
                    }
                }
                // The full edition's code: its session package and its screens.
                val full = listOf("Lcom/fahadali/oneos/session/") + FULL_SCREENS.map { "Lcom/fahadali/oneos/ui/$it;" }
                for (dex in names.filter { Regex("classes[0-9]*\\.dex").matches(it) }) {
                    val text = zip.getInputStream(zip.getEntry(dex)).use { it.readBytes() }.toString(Charsets.ISO_8859_1)
                    for (f in full) if (text.contains(f)) problems += "${apk.name}: $dex has ${f.removePrefix("L").removeSuffix(";")}"
                }
                // The strings it shows (resources.arsc, UTF-8): every root prompt names OneOS Probe.
                // Not the dex: SwitchGates in core/model keeps OneOS's texts, and only OneOS runs it.
                val arsc = zip.getEntry("resources.arsc")?.let { e -> zip.getInputStream(e).use { it.readBytes() }.toString(Charsets.UTF_8) }.orEmpty()
                if (!arsc.contains("OneOS Probe")) problems += "${apk.name}: resources.arsc has no readable app_name"
                for (m in OTHER_APP_ROOT.findAll(arsc)) problems += "${apk.name}: a string says \"${m.value}\" (name OneOS Probe in src/probe)"
                lines += "${apk.name} ${apk.length()} B, assets: ${assets.joinToString(" ")}"
            }
        }
        val m = manifest.get().asFile.readText()
        for (a in FULL_SCREENS) if (m.contains(".ui.$a\"")) problems += "the merged manifest declares $a"
        val permissions = Regex("""<uses-permission\b[^>]*android:name="([^"]+)"""").findAll(m).map { it.groupValues[1] }.toList()
        // 0.4.36 sends reports over HTTPS; AndroidX also protects its private receivers.
        if (permissions.any { it !in setOf("android.permission.INTERNET", "com.fahadali.oneos.probe.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION") }) {
            problems += "the merged manifest asks for an unexpected permission"
        }
        if (problems.isNotEmpty()) throw GradleException("OneOS Probe carries what only OneOS may:\n  " + problems.distinct().joinToString("\n  "))
        report.get().asFile.writeText(lines.joinToString("\n", postfix = "\n"))
    }

    companion object {
        val FULL_SCREENS = listOf("ImageActivity", "PrepareActivity", "SwitchActivity", "LastSessionActivity", "GapSplashActivity")

        /** "Allow OneOS", "for OneOS", "visible to OneOS", not followed by " Probe" (EditionsTest has the same). */
        val OTHER_APP_ROOT = Regex("""(?:[Aa]llow(?:ed for)?|for|visible to) OneOS\b(?! Probe)""")
    }
}

androidComponents {
    onVariants { variant ->
        when (variant.flavorName) {
            // Only OneOS carries the package sets and the session scripts.
            "full" -> {
                variant.sources.assets?.addGeneratedSourceDirectory(oneosFiles, OneOsFilesTask::outputDir)
                val name = variant.name.replaceFirstChar { it.uppercase() }
                val apkDir = variant.artifacts.get(com.android.build.api.artifact.SingleArtifact.APK)
                val loader = variant.artifacts.getBuiltArtifactsLoader()
                val verify = tasks.register("check${name}StagingApk") {
                    group = "verification"
                    description = "Checks compiled staging pins, manifests and payloads in the finished APK."
                    inputs.dir(apkDir)
                    inputs.file(File(repoRoot, "scripts/check-staging-apk.py"))
                    doLast {
                        val apks = loader.load(apkDir.get())?.elements.orEmpty()
                        check(apks.isNotEmpty()) { "No full APK to verify" }
                        for (apk in apks) {
                            // The checker's own words, on failure too (exec otherwise keeps only the exit value).
                            val run = providers.exec {
                                commandLine("python3", "-I", File(repoRoot, "scripts/check-staging-apk.py"), apk.outputFile)
                                isIgnoreExitValue = true
                            }
                            val said = (run.standardOutput.asText.get() + run.standardError.asText.get()).trim()
                            if (run.result.get().exitValue != 0) throw GradleException(said.ifEmpty { "Staging integrity FAILED: ${apk.outputFile}" })
                            logger.lifecycle(said)
                        }
                    }
                }
                // installDebug too: the team installs on the test phone that way, without assemble.
                tasks.matching { it.name == "assemble$name" || it.name == "install$name" }.configureEach { dependsOn(verify) }
            }
            "probe" -> {
                val name = variant.name.replaceFirstChar { it.uppercase() }
                val check = tasks.register<ProbeApkCheckTask>("check${name}Apk") {
                    group = "verification"
                    description = "Checks that the OneOS Probe APK holds only the read-only app."
                    apkDir.set(variant.artifacts.get(com.android.build.api.artifact.SingleArtifact.APK))
                    loader.set(variant.artifacts.getBuiltArtifactsLoader())
                    manifest.set(variant.artifacts.get(com.android.build.api.artifact.SingleArtifact.MERGED_MANIFEST))
                    // The session scripts, the root script and its lists, and every file of the package sets.
                    val setNames = packageSets.keys.flatMap { id -> File(packagesDir, "$id.sha256").takeIf { it.isFile }?.let { readShaList(it).keys }.orEmpty() }
                    forbiddenNames.set(sessionScripts.keys + setOf("oneos_root.sh", "status.list", "installd.list", "collect.list") + setNames)
                    // SESL9 unshrunk debug libraries are ~48 MB. Release is not shrunk either (R8 off):
                    // 0.4.38's release Probe is 38 MB, all of it code (no asset beyond probe/).
                    maxBytes.set((if (variant.buildType == "debug") 60L else 50L) * 1000 * 1000)
                    report.set(layout.buildDirectory.file("reports/probe-apk/${variant.name}.txt"))
                }
                tasks.matching { it.name == "assemble$name" }.configureEach { dependsOn(check) }
            }
        }
    }
}

configurations.configureEach {
    exclude(group = "androidx.core", module = "core")
    exclude(group = "androidx.core", module = "core-ktx")
    exclude(group = "androidx.customview", module = "customview")
    exclude(group = "androidx.coordinatorlayout", module = "coordinatorlayout")
    exclude(group = "androidx.drawerlayout", module = "drawerlayout")
    exclude(group = "androidx.viewpager2", module = "viewpager2")
    exclude(group = "androidx.viewpager", module = "viewpager")
    exclude(group = "androidx.appcompat", module = "appcompat")
    // Play Services pulls stock Fragment, but One UI Design supplies the SESL
    // implementation under the same AndroidX package names.
    exclude(group = "androidx.fragment", module = "fragment")
    // SESL9 Core and Fragment include their Kotlin extensions.
    exclude(group = "sesl.androidx.core", module = "core-ktx")
    exclude(group = "androidx.fragment", module = "fragment-ktx")
    exclude(group = "androidx.preference", module = "preference")
    exclude(group = "androidx.recyclerview", module = "recyclerview")
    exclude(group = "androidx.swiperefreshlayout", module = "swiperefreshlayout")
    exclude(group = "androidx.slidingpanelayout", module = "slidingpanelayout")
    exclude(group = "com.google.android.material", module = "material")
}

dependencies {
    implementation(project(":core:model"))
    implementation(project(":core:device"))
    implementation(project(":core:root"))
    implementation(project(":core:safety"))

    implementation(libs.bundles.sesl9)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.oneui.design) {
        // The design library's optional barcode scanner is unused; keep OneOS offline.
        exclude(group = "com.google.android.gms", module = "play-services-mlkit-barcode-scanning")
        exclude(group = "com.google.mlkit", module = "barcode-scanning-common")
    }
    implementation(libs.oneui.icons)
}
