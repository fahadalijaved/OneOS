package com.fahadali.oneos.ui

import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.GuestModuleBundle
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell
import com.fahadali.oneos.session.GuestRuntimeStore
import com.fahadali.oneos.session.RootVerbs
import dev.oneuiproject.oneui.layout.ToolbarLayout
import java.io.File
import java.util.concurrent.Executors

/** Native module list and fixed import action from the supplied Figma design. */
class GuestRuntimeActivity : EdgeToEdgeActivity() {
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var image: String
    private lateinit var state: GuestRuntimeStore.State
    private var busy = false
    private var loaded = false
    private var importFramework = false
    private val picker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null && !busy) importModule { com.fahadali.oneos.shared.ModuleUpdates.copyDocument(this,uri) }
    }
    private fun importModule(source: () -> File) {
            busy = true; render()
            io.execute {
                val result = runCatching {
                    val zip = source()
                    val bundle = File.createTempFile("guest-module-", ".bundle", cacheDir)
                    try {
                        val info = GuestModuleBundle.write(zip, bundle)
                        val md = java.security.MessageDigest.getInstance("SHA-256")
                        bundle.inputStream().use { input ->
                            val buffer = ByteArray(65536)
                            while (true) { val n = input.read(buffer); if (n < 0) break; md.update(buffer, 0, n) }
                        }
                        val sum = md.digest().joinToString("") { "%02x".format(it) }
                        val reply = RootVerbs.run(applicationContext, RootScript.Verb.GUEST_MODULE,
                            listOf(image, info.id, bundle.length().toString(), sum),
                            RootShell.Feed { out -> bundle.inputStream().use { it.copyTo(out) } })
                        check(reply.ok) { reply.problem ?: "Module import failed" }
                        GuestRuntimeStore.read(applicationContext, image) to info.name
                    } finally { zip.delete(); bundle.delete() }
                }
                runOnUiThread {
                    if (isDestroyed) return@runOnUiThread
                    busy = false
                    result.onSuccess { (next, name) -> state = next; Toast.makeText(this, "$name staged for the next boot", Toast.LENGTH_LONG).show() }
                        .onFailure { showError(it.message ?: "Could not import module") }
                    render()
                }
            }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        image = intent.getStringExtra("image") ?: run { finish(); return }
        state = GuestRuntimeStore.State(image)
        importFramework = intent.getBooleanExtra("import_framework", false)
        setContentView(R.layout.activity_guest_modules)
        val footer = findViewById<View>(R.id.guest_modules_footer)
        val toolbar = findViewById<ToolbarLayout>(R.id.guest_modules_toolbar)
        toolbar.setTitle("Manage guest modules")
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        applyEdgeToEdgeInsets(toolbar) { bottom -> footer.updateBottomMarginForNavigationBar(0, bottom) }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0; fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
        val scroll = findViewById<NestedScrollView>(R.id.guest_modules_scroll)
        scroll.seslSetFadingEdgeEnabled(true)
        scroll.seslSetFadingEdgeColor(getColor(R.color.preboot_page))
        scroll.seslSetFadingEdgeWindowBottomAlignment(true)
        scroll.seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        footer.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            val navigation = (footer.layoutParams as ViewGroup.MarginLayoutParams).bottomMargin
            val space = footer.height + navigation + dp(24)
            scroll.setPadding(0, 0, 0, space)
            scroll.seslForceBottomFadingEdgeClamped(space)
        }
        findViewById<Button>(R.id.guest_modules_import).setOnClickListener {
            picker.launch(arrayOf("application/zip", "application/octet-stream", "application/x-zip-compressed"))
        }
        render()
    }
    override fun onResume() {
        super.onResume()
        if (!::state.isInitialized || busy) return
        busy = true; render()
        GuestRuntimeStore.refresh(this, image) { next ->
            if (isDestroyed) return@refresh
            busy = false; loaded = true
            state = if (next.error == null) next else state.copy(error = next.error)
            render()
            if (importFramework && state.ready) {
                importFramework = false
                picker.launch(arrayOf("application/zip", "application/octet-stream", "application/x-zip-compressed"))
            }
        }
    }
    override fun onDestroy() { io.shutdown(); super.onDestroy() }
    private fun render() {
        if (!::state.isInitialized) return
        val list = findViewById<LinearLayout>(R.id.guest_modules_list)
        list.removeAllViews()
        when {
            !loaded -> empty(list, "Reading guest modules…", null)
            state.error != null -> empty(list, "Couldn’t read guest modules", state.error)
            state.modules.isEmpty() -> empty(list, "No guest modules yet", if (state.ready)
                "Import a module ZIP to add it to this system." else "Update this system on the pre-boot page to add guest module support.")
            else -> state.modules.forEach { module ->
                com.fahadali.oneos.shared.ModuleCards.add(list, module.name, module.description,
                    module.enabled, !busy && state.ready, getColor(R.color.preboot_card),
                    version = module.version.ifBlank { module.versionCode.takeIf { it > 0 }?.toString().orEmpty() }, author = module.author,
                    status = if(module.removing) "Uninstall pending · Next guest restart" else if(module.pending) "Staged for next guest restart" else null,
                    toggleEnabled = !module.removing && (module.framework == null || module.id == state.selected),
                    options = moduleOptions(module)) { value ->
                    busy = true; render()
                    GuestRuntimeStore.setModule(this, image, module.id, value) { next ->
                        if (isDestroyed) return@setModule
                        busy = false
                        if (next.error != null) showError(next.error) else state = next
                        render()
                    }
                }
            }
        }
        findViewById<Button>(R.id.guest_modules_import).isEnabled = loaded && state.ready && !busy
    }
    private fun moduleOptions(module: GuestRuntimeStore.Module): List<Pair<String, () -> Unit>> = buildList {
        if ("webui" in module.capabilities) add("WebUI · Open inside guest" to { showError("Open this module's WebUI from OneOS inside the guest.") })
        if ("action" in module.capabilities) add("Action · Run inside guest" to { showError("Run this module's action from OneOS inside the guest.") })
        if (module.updateUrl.isNotBlank() && !module.pending && !module.removing) add("Check for updates" to {
            busy=true; render()
            com.fahadali.oneos.shared.ModuleUpdates.check(this@GuestRuntimeActivity,module.name,module.id,module.versionCode,module.updateUrl) { zip ->
                busy=false; render(); if(zip != null) importModule { zip }
            }
        })
        add((if(module.removing) "Cancel uninstall" else "Uninstall ${module.name}") to {
            AlertDialog.Builder(this@GuestRuntimeActivity).setTitle(if(module.removing) "Cancel uninstall?" else "Uninstall ${module.name}?")
                .setMessage("This change applies at the next guest restart. Module cleanup scripts run only inside the guest.")
                .setNegativeButton(android.R.string.cancel,null).setPositiveButton(android.R.string.ok) { _,_ ->
                    busy=true; render()
                    GuestRuntimeStore.changeModule(this@GuestRuntimeActivity,image,module.id,if(module.removing) "restore" else "remove") { next ->
                        busy=false; if(next.error != null) showError(next.error) else state=next; render()
                    }
                }.show()
        })
    }
    private fun empty(list: LinearLayout, title: String, line: String?) {
        PrebootCards.row(PrebootCards.section(list, gap = false), title, line)
    }
    private fun showError(message: String) {
        AlertDialog.Builder(this).setTitle("Guest modules").setMessage(message).setPositiveButton(android.R.string.ok, null).show()
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density + .5f).toInt()
}
