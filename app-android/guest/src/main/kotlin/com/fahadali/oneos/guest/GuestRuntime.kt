package com.fahadali.oneos.guest

import android.content.Context
import android.content.Intent
import android.content.ComponentName
import android.os.Handler
import android.os.Looper
import java.util.concurrent.Executors

object GuestRuntime {
    data class Module(val id: String, val name: String, val description: String, val enabled: Boolean, val pending: Boolean, val framework: Boolean, val version: String = "", val author: String = "", val versionCode: Long = 0,
        val updateUrl: String = "", val capabilities: Set<String> = emptySet(), val removing: Boolean = false)
    data class State(val root: Boolean = false, val provider: String = "none", val active: Boolean = false,
        val modules: List<Module> = emptyList(), val error: String? = null, val selected: String = "") {
        val providerName get() = when(provider) { "vector" -> "Vector"; "lsposed" -> "LSPosed"; else -> "None" }
    }
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    fun command(vararg args: String): Pair<Int, String> {
        val p = ProcessBuilder(listOf("/system/xbin/su") + args).redirectErrorStream(true).start()
        val out = boundedOutput(p.inputStream)
        return p.waitFor() to out
    }
    fun boundedOutput(input: java.io.InputStream, limit: Int = 1048576): String = input.use {
        val out=java.io.ByteArrayOutputStream();val buffer=ByteArray(16384);var truncated=false
        while(true){val n=it.read(buffer);if(n<0)break;val keep=minOf(n,limit-out.size());if(keep>0)out.write(buffer,0,keep);if(keep<n)truncated=true}
        out.toString("UTF-8") + if(truncated) "\n[Output truncated]" else ""
    }
    fun shell(script: String): String {
        val result = command("-c", script)
        check(result.first == 0) { result.second.ifBlank { "Guest root command failed (${result.first})" } }
        return result.second
    }
    fun quote(s: String) = "'" + s.replace("'", "'\\''") + "'"
    fun control(vararg args: String) = shell("/system/bin/sh /data/oneos_runtime.sh control " + args.joinToString(" ") { quote(it) })
    fun read(ctx: Context): State {
        check(java.io.File("/data/adb/oneos/run/su.sock").exists()) { "Guest root runtime is inactive" }
        val info = command("--oneos-info")
        check(info.first == 0 && info.second.trim() == "OneOS guest root API 1 manager=${ctx.packageName}") { "Guest root runtime is inactive or needs an update" }
        val lines = control("status").lineSequence().map { it.removePrefix("@@RESULT ") }.toList()
        val framework = lines.firstOrNull { it.startsWith("framework-status ") }?.split(' ')
        val modules = lines.filter { it.startsWith("module-info ") }.mapNotNull {
            val p = it.split(' '); if (p.size != 8 && p.size != 13) null else runCatching {
                Module(p[1], unhex(p[6]).ifBlank { p[1] }, unhex(p[7]), p[2] == "1", p[3] == "modules_update", p[4] != "module", unhex(p[5]),
                    p.getOrNull(8)?.let(::unhex).orEmpty(), p.getOrNull(9)?.let(::unhex)?.toLongOrNull() ?: 0,
                    p.getOrNull(10)?.let(::unhex).orEmpty(), p.getOrNull(11)?.split(',')?.toSet() ?: emptySet(), p.getOrNull(12) == "1")
            }.getOrNull()
        }.associateBy { it.id }.values.sortedBy { it.name.lowercase() }
        return State("root active" in lines, framework?.getOrNull(2) ?: "none", framework?.getOrNull(3) == "1", modules, selected = framework?.getOrNull(1) ?: "")
    }
    fun refresh(ctx: Context, done: (State) -> Unit) = work({ read(ctx.applicationContext) }, done)
    fun work(action: () -> State, done: (State) -> Unit) {
        io.execute { val result = runCatching(action).getOrElse { State(error = it.message ?: "Could not read guest root") }; main.post { done(result) } }
    }
    fun openFramework(ctx: Context, state: State) {
        check(state.active) { "No active Xposed framework" }
        val pkg = when(state.provider) { "vector" -> "org.matrix.vector.manager"; "lsposed" -> "org.lsposed.manager"; else -> error("Unsupported framework") }
        val installed = ctx.packageManager.getLaunchIntentForPackage(pkg)
        if (installed != null) ctx.startActivity(installed.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        else shell("am start -a android.intent.action.MAIN -n com.android.shell/.BugreportWarningActivity -c " + quote("$pkg.LAUNCH_MANAGER"))
    }

    private fun unhex(s: String): String {
        if (s == "-") return ""
        require(s.length % 2 == 0 && s.length <= 4096)
        return s.chunked(2).map { it.toInt(16).toByte() }.toByteArray().toString(Charsets.UTF_8)
    }
}
