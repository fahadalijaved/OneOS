package com.fahadali.oneos.core.model

import java.io.File
import java.io.OutputStream
import java.util.Properties
import java.util.zip.ZipFile

/** A ZIP is data on the host. Only regular, normalized files reach root.
 * Installation scripts are deferred until the guest namespace exists. */
object GuestModuleBundle {
    data class Info(val id: String, val name: String, val files: Int, val bytes: Long)
    private val idPattern = Regex("^[A-Za-z][A-Za-z0-9._-]{1,63}$")
    private const val LIMIT = 512L * 1024 * 1024

    fun write(zip: File, target: File): Info {
        require(zip.length() in 1..LIMIT) { "Module ZIP must be under 512 MiB" }
        return ZipFile(zip).use { source ->
            val entries = source.entries().asSequence().toList()
            require(entries.size in 1..20_000) { "Too many ZIP entries" }
            val seen = hashSetOf<String>()
            entries.forEach { e ->
                val path = e.name.removeSuffix("/")
                require(path.isNotEmpty() && path.toByteArray().size < 1000 && !path.startsWith("/") &&
                    path.split('/').none { it.isEmpty() || it == "." || it == ".." } &&
                    path.none { it.code < 32 || it == '\\' } && seen.add(path)) { "Unsafe or duplicate ZIP path" }
                require(e.size in 0..LIMIT) { "Invalid ZIP entry size" }
                require(!path.startsWith(".oneos-")) { "Reserved OneOS metadata" }
            }
            val prop = source.getEntry("module.prop") ?: error("Not a root module ZIP: module.prop is missing")
            require(prop.size in 1..16_384) { "Invalid module.prop" }
            val metadata = Properties().apply { source.getInputStream(prop).use(::load) }
            val id = metadata.getProperty("id")?.trim().orEmpty()
            require(idPattern.matches(id) && id !in setOf("vector", "oneos", "zygisksu")) { "Invalid or reserved module id" }
            val framework = source.getEntry("daemon.apk") != null && source.getEntry("daemon") != null &&
                (source.getEntry("framework/lspd.dex") != null || source.getEntry("framework/vector.dex") != null)
            require(source.getEntry("riru") == null && !id.startsWith("riru")) { "Riru requires a separate injection backend; use the Zygisk framework build" }
            var total = zip.length()
            try {
                target.outputStream().buffered().use { out ->
                    out.write("ONEOS1\n".toByteArray())
                    entries.filterNot { it.isDirectory }.sortedBy { it.name }.forEach { e ->
                        total += e.size
                        require(total <= LIMIT) { "Expanded module is larger than 512 MiB" }
                        val executable = e.name.endsWith(".sh") || e.name.startsWith("bin/") || e.name in setOf("daemon", "cli")
                        header(out, e.name, e.size, if (executable) "755" else "644")
                        source.getInputStream(e).use { input ->
                            var remaining = e.size
                            val buffer = ByteArray(65536)
                            while (remaining > 0) {
                                val n = input.read(buffer, 0, minOf(buffer.size.toLong(), remaining).toInt())
                                check(n > 0) { "Truncated ZIP entry" }
                                out.write(buffer, 0, n); remaining -= n
                            }
                            check(input.read() == -1) { "ZIP entry exceeds its declared size" }
                        }
                    }
                    header(out, ".oneos-install.zip", zip.length(), "600")
                    zip.inputStream().use { it.copyTo(out) }
                    if (framework) {
                        val kind = if (source.getEntry("framework/lspd.dex") != null) "lsposed" else "vector"
                        header(out, ".oneos-framework", kind.length.toLong(), "600"); out.write(kind.toByteArray())
                        // Framework distributions contain raw ABI libraries, mapped by their
                        // original installers. Normalize the same layout without executing
                        // those installers or modifying their APK/DEX bytes on the host.
                        val lib = source.getEntry("lib/arm64-v8a/liblspd.so") ?: source.getEntry("lib/arm64-v8a/libzygisk.so")
                        if (source.getEntry("zygisk/arm64-v8a.so") == null && lib != null) {
                            header(out, "zygisk/arm64-v8a.so", lib.size, "644")
                            source.getInputStream(lib).use { it.copyTo(out) }
                        }
                        listOf("arm64-v8a" to "64", "armeabi-v7a" to "32").forEach { (abi, bits) ->
                            listOf("dex2oat" to "dex2oat$bits", "liboat_hook.so" to "liboat_hook$bits.so").forEach { (from, to) ->
                                source.getEntry("bin/$abi/$from")?.takeIf { source.getEntry("bin/$to") == null }?.let { file ->
                                    total += file.size; require(total <= LIMIT) { "Framework exceeds 512 MiB" }
                                    header(out, "bin/$to", file.size, "755"); source.getInputStream(file).use { it.copyTo(out) }
                                }
                            }
                        }
                    } else header(out, ".oneos-pending", 0, "600")
                    out.write("0 0 0\n".toByteArray())
                }
                Info(id, metadata.getProperty("name", id).take(120), entries.count { !it.isDirectory }, target.length())
            } catch (t: Throwable) { target.delete(); throw t }
        }
    }
    private fun header(out: OutputStream, path: String, size: Long, mode: String) {
        val bytes = path.toByteArray(Charsets.UTF_8)
        out.write("${bytes.size} $size $mode\n".toByteArray()); out.write(bytes)
    }
}
