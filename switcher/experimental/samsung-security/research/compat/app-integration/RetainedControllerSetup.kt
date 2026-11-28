package com.fahadali.oneos.session

import android.content.Context
import android.os.Looper
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell
import java.util.concurrent.atomic.AtomicBoolean

/** Full-flavor installation only. Returning does not spawn or admit a native session. */
object RetainedControllerSetup {
    private const val ASSET = "root/oneos_retained_root_session"
    private const val ACK = "closed-controller-installed"
    private val lock = Any()
    private var attempted: Attempt? = null

    private class Attempt {
        var nativeBytes: ByteArray? = null
        var result: RootVerbs.Reply? = null
        var failure: Throwable? = null
        val feedDone = AtomicBoolean(false)
    }

    /** Called once by the actual approved BEGIN worker, before the real session factory. */
    @JvmStatic
    fun ensureInstalled(context: Context, expectedNativeSha256: String, expectedNativeBytes: Long) {
        val owner = synchronized(lock) {
            check(attempted == null) { "closed controller setup already attempted" }
            Attempt().also { attempted = it }
        }
        try {
            val main = Looper.getMainLooper()
            check(main != null && Looper.myLooper() !== main) { "closed controller setup requires a worker" }
            val hash = BuildConfig.RETAINED_CONTROLLER_SHA256
            val size = BuildConfig.RETAINED_CONTROLLER_BYTES
            check(Regex("^[0-9a-f]{64}$").matches(hash) && size in 1L..2_097_152L) {
                "this app does not carry a closed controller"
            }
            check(hash == expectedNativeSha256 && size == expectedNativeBytes) {
                "closed controller build differs from the approved request"
            }
            check(BuildConfig.ROOT_SCRIPT_BYTES in 1L..1_048_576L) { "root script size differs" }
            val app = context.applicationContext
            check(app.packageName == BuildConfig.APPLICATION_ID) { "actual app Context required" }
            val bytes = ByteArray(size.toInt())
            owner.nativeBytes = bytes
            app.assets.open(ASSET).use { input ->
                var offset = 0
                while (offset < bytes.size) {
                    val count = input.read(bytes, offset, bytes.size - offset)
                    check(count > 0) { "closed controller asset is short" }
                    offset += count
                }
                check(input.read() == -1) { "closed controller asset has extra bytes" }
            }
            check(Hashes.sha256(bytes) == hash) { "closed controller asset hash differs" }
            val feed = RootShell.Feed { out ->
                out.write(bytes)
                out.flush()
                owner.feedDone.set(true)
            }
            val result = RootVerbs.run(
                app, RootScript.Verb.INSTALL_CLOSED_CONTROLLER, listOf(size.toString(), hash), feed,
                silenceMs = 30_000L, totalMs = 120_000L,
            )
            owner.result = result
            val end = result.end
            check(result.ok && end.exitCode == RootScript.EXIT_OK && end.error == null &&
                !end.cancelled && !end.killed && owner.feedDone.get() &&
                result.controllerInstall == RootVerbs.ControllerInstallResult.FILE_ACKNOWLEDGED &&
                end.written == BuildConfig.ROOT_SCRIPT_BYTES + size &&
                result.reply.ok == ACK && result.reply.okCount == 1 &&
                result.reply.failed == null && result.reply.refused == null) {
                "closed controller installation is unavailable or uncertain"
            }
            // The installer only commits a fixed file. The real begin factory
            // must still open/verify that image and capture its actual peer/pidfd.
        } catch (problem: Throwable) {
            owner.failure = problem
            throw problem
        }
    }
}
