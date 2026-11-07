package com.fahadali.oneos.session

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.fahadali.oneos.core.root.RootScript
import java.util.concurrent.Executors

/** Serialized access to the selected guest's root state. Never guesses host modules. */
object GuestRuntimeStore {
    data class Module(val id: String, val name: String, val description: String, val enabled: Boolean,
        val pending: Boolean, val framework: String?, val version: String = "", val author: String = "", val versionCode: Long = 0,
        val updateUrl: String = "", val capabilities: Set<String> = emptySet(), val removing: Boolean = false)
    data class State(val image: String, val enabled: Boolean = false, val ready: Boolean = false,
        val selected: String = "zygisk_vector", val modules: List<Module> = emptyList(), val error: String? = null) {
        fun providerName(id: String = selected): String = when {
            id == "zygisk_vector" -> "Vector"
            modules.any { it.id == id && it.framework == "lsposed" } -> "LSPosed"
            modules.any { it.id == id && it.framework == "vector" } -> "Vector"
            else -> modules.firstOrNull { it.id == id }?.name ?: id
        }
    }
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    fun refresh(ctx: Context, image: String, done: (State) -> Unit) = submit(ctx, image, null, done)
    fun setEnabled(ctx: Context, image: String, enabled: Boolean, done: (State) -> Unit) =
        submit(ctx, image, listOf(image, if (enabled) "enable" else "disable"), done)
    fun select(ctx: Context, image: String, provider: String, done: (State) -> Unit) =
        submit(ctx, image, listOf(image, "select-$provider"), done)
    fun setModule(ctx: Context, image: String, id: String, enabled: Boolean, done: (State) -> Unit) {
        changeModule(ctx, image, id, if (enabled) "on" else "off", done)
    }
    fun changeModule(ctx: Context, image: String, id: String, action: String, done: (State) -> Unit) {
        val app = ctx.applicationContext
        io.execute {
            val state = runCatching {
                val reply = RootVerbs.run(app, RootScript.Verb.GUEST_MODULE_STATE, listOf(image, id, action))
                check(reply.ok) { reply.problem ?: "Could not change module" }
                read(app, image)
            }.getOrElse { State(image, error = it.message ?: "Could not read guest modules") }
            main.post { done(state) }
        }
    }
    private fun submit(ctx: Context, image: String, action: List<String>?, done: (State) -> Unit) {
        val app = ctx.applicationContext
        io.execute {
            val state = runCatching {
                if (action != null) {
                    val reply = RootVerbs.run(app, RootScript.Verb.GUEST_RUNTIME, action)
                    check(reply.ok) { reply.problem ?: "Could not change guest root" }
                }
                read(app, image)
            }.getOrElse { State(image, error = it.message ?: "Could not read guest root") }
            main.post { done(state) }
        }
    }
    fun read(ctx: Context, image: String): State {
        val reply = RootVerbs.run(ctx, RootScript.Verb.GUEST_RUNTIME, listOf(image, "status"))
        check(reply.ok) { reply.problem ?: "Could not read guest root" }
        val result = reply.reply.results
        val modules = result.filter { it.startsWith("module-info ") }.mapNotNull { row ->
            val parts = row.split(' ')
            if (parts.size != 8 && parts.size != 13) return@mapNotNull null
            runCatching { Module(parts[1], unhex(parts[6]).ifBlank { parts[1] }, unhex(parts[7]),
                parts[2] == "1", parts[3] == "modules_update", parts[4].takeUnless { it == "module" }, unhex(parts[5]),
                parts.getOrNull(8)?.let(::unhex).orEmpty(), parts.getOrNull(9)?.let(::unhex)?.toLongOrNull() ?: 0,
                parts.getOrNull(10)?.let(::unhex).orEmpty(), parts.getOrNull(11)?.split(',')?.toSet() ?: emptySet(), parts.getOrNull(12) == "1") }.getOrNull()
        }.associateBy { it.id }.values.sortedBy { it.name.lowercase() }
        return State(image, "enabled" in result, "runtime-ready" in result,
            result.firstOrNull { it.startsWith("selected ") }?.removePrefix("selected ") ?: "zygisk_vector", modules)
    }
    private fun unhex(value: String): String {
        if (value == "-") return ""
        require(value.length % 2 == 0 && value.length <= 4096)
        return value.chunked(2).map { it.toInt(16).toByte() }.toByteArray().toString(Charsets.UTF_8)
    }
}
