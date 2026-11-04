package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.ShaList
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The checked-in package lists the APK is built from (app-android/packages,
 * AA8): each names exactly its set's files, and each set's guards.txt (as
 * built, checked in next to the list) lists exactly the set's guard jars
 * with their hashes, which guest_prepare.sh requires before it binds them.
 */
class PackagesTest {
    private val dir = File(System.getProperty("oneos.packagesDir") ?: "../../packages")

    @Test
    fun listsNameExactlyTheSets() {
        for (s in PackageSets.ALL) {
            val list = File(dir, "${s.id}.sha256").readText()
            assertEquals(s.id, emptyList<String>(), s.check(list))
        }
    }

    @Test
    fun guardsMatchTheirJars() {
        for (s in PackageSets.ALL) {
            val list = File(dir, "${s.id}.sha256").readText()
            val guards = File(dir, "${s.id}.guards.txt")
            // The checked-in guards.txt is the set's own file (same hash as in its list).
            assertEquals(s.id, ShaList.parse(list).entries["guards.txt"], Hashes.sha256(guards.readBytes()))
            assertEquals(s.id, emptyList<String>(), s.checkGuards(guards.readText(), list))
        }
        // Never mixed: the N6 guards do not vouch for the X9U jars.
        val x9u = PackageSets.X9U_IN_SULTRA
        assertTrue(x9u.checkGuards(File(dir, "n6-f8u.guards.txt").readText(), File(dir, "x9u-in-sultra.sha256").readText()).isNotEmpty())
    }

    private val build: String get() = File(Shipped.appAssets, "../../../build.gradle.kts").readText()

    /**
     * app/build.gradle.kts packs each set from the model's folder ([com.fahadali.oneos.core.model.PackageSet.sourceDir])
     * and leaves out exactly the model's omitted files, plus OneOSGuest.apk for a set that does not carry it.
     */
    @Test
    fun buildPacksEachSetFromItsFolder() {
        val rows = Regex("""^\s+"([a-z0-9-]+)" to \(File\(repoRoot, "([^"]+)"\) to listOf\(([^)]*)\)\),?$""", RegexOption.MULTILINE)
            .findAll(build).associate { m -> m.groupValues[1] to (m.groupValues[2] to Regex(""""([^"]+)"""").findAll(m.groupValues[3]).map { it.groupValues[1] }.toList()) }
        assertEquals(PackageSets.ALL.map { it.id }, rows.keys.toList())
        for (s in PackageSets.ALL) {
            val (dir, left) = rows.getValue(s.id)
            assertEquals(s.id, s.sourceDir, dir)
            assertEquals(s.id, (s.omitted + listOfNotNull(PackageSets.GUEST_APP.takeIf { !s.hasReturnApp })).toSet(), left.toSet())
            assertTrue(s.id, left.none { it in s.names })
        }
    }

    /**
     * Root's `receive` takes a set file of at most 256 MiB, and the packaging task refuses a bigger one; the
     * files as built on the server fit (out/ is not in git: checked where it is, e.g. gmssystem_payload.img, 155 MB).
     */
    @Test
    fun everySetFileFitsRootsReceiveLimit() {
        val cap = Regex("""ge (\d+) "\${'$'}bytes" \|\| refuse "\${'$'}name is too large"""").find(Shipped.rootScriptText)!!.groupValues[1].toLong()
        assertEquals(256L shl 20, cap)
        assertTrue(build.contains("private val receiveMax = 268_435_456L"))
        val repo = File(Shipped.switcherAssets, "../..")
        for (s in PackageSets.ALL) {
            val dir = File(repo, s.sourceDir)
            if (!dir.isDirectory) continue
            for (n in s.names) File(dir, n).takeIf { it.isFile }?.let { assertTrue("${s.id} $n: ${it.length()} bytes", it.length() <= cap) }
        }
    }

    /** What app/build.gradle.kts ships from switcher/assets: the session scripts, never the tunnel or 7zz. */
    @Test
    fun switcherAssetsAreShippedOrExcludedOnPurpose() {
        val names = Shipped.switcherAssets.listFiles()!!.filter { it.isFile }.map { it.name }.toSet()
        val shipped = RootScript.SCRIPTS - "host_installd.txt"
        assertEquals(names - setOf("oneos_tunnel.sh", "7zz"), shipped.toSet())
        val build = File(Shipped.appAssets, "../../../build.gradle.kts").readText()
        for (n in shipped) assertTrue("app/build.gradle.kts does not ship $n", build.contains("\"$n\" to File(repoRoot, \"switcher/assets/$n\")"))
        assertTrue(build.contains("val switcherNotShipped = setOf(\"oneos_tunnel.sh\", \"7zz\")"))
    }
}
