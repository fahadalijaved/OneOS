package com.fahadali.oneos.guest

import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.graphics.drawable.BitmapDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatActivity
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.guest.BringCatalogFile.Progress
import com.fahadali.oneos.shared.NativeCards
import dev.oneuiproject.oneui.layout.ToolbarLayout
import dev.oneuiproject.oneui.utils.applyEdgeToEdge
import dev.oneuiproject.oneui.widget.CardItemView
import java.io.File

/**
 * Bring apps from One UI, from inside this system: lists the apps the OneOS app
 * offered at this start (the catalog it left, [BringCatalogFile.CATALOG]) that are
 * not installed here. A tap creates the empty file `/data/oneos_bring_requests/<pkg>`;
 * the host session's watcher copies that app (with its login) and installs it, and
 * writes one line to `<pkg>.status` (`copying`, `installing`, `done`, `failed: why`),
 * read here every 2 seconds. No root is used here, and nothing is written to One UI.
 */
class BringAppsActivity : AppCompatActivity() {
    private class App(val item: BringCatalogFile.Item, val icon: android.graphics.Bitmap?)

    private val handler = Handler(Looper.getMainLooper())
    private var apps: List<App> = emptyList()
    private var loaded = false
    private var missing = false

    /** pkg -> when it was asked for (ms): a status file older than that is an earlier request's. */
    private val asked = LinkedHashMap<String, Long>()

    /** The progress shown, to redraw only when something changed. */
    private var shown = ""
    private val poll = object : Runnable {
        override fun run() {
            if (asked.isNotEmpty() && snapshot() != shown) render()
            handler.postDelayed(this, 2000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
        setContentView(R.layout.activity_guest_bring)
        val toolbar = findViewById<ToolbarLayout>(R.id.guest_bring_toolbar)
        toolbar.setTitle(getString(R.string.bring_title))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        val scroll = findViewById<NestedScrollView>(R.id.guest_bring_scroll)
        toolbar.setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(bars.left, bars.top, bars.right, 0)
            scroll.setPadding(0, 0, 0, bars.bottom)
            insets
        }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply { roundedCorners = 0; fillHorizontalPadding = false }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
        render()
    }

    override fun onResume() {
        super.onResume()
        load()
        handler.postDelayed(poll, 2000)
    }

    override fun onPause() {
        handler.removeCallbacks(poll)
        super.onPause()
    }

    /** Reads the catalog off the main thread; the apps installed here by now are left out (but the ones asked for in this visit stay, to show their progress). */
    private fun load() {
        Thread {
            val file = File(BringCatalogFile.CATALOG)
            val text = runCatching { if (file.isFile) file.readText() else null }.getOrNull()
            val list = text?.let { BringCatalogFile.parse(it) }.orEmpty().map { item ->
                App(item, item.png.let { runCatching { BitmapFactory.decodeByteArray(it, 0, it.size) }.getOrNull() })
            }
            runOnUiThread {
                if (isDestroyed) return@runOnUiThread
                apps = list
                missing = text == null
                loaded = true
                render()
            }
        }.start()
    }

    private fun installed(pkg: String): Boolean =
        try {
            packageManager.getApplicationInfo(pkg, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }

    private fun requestsWritable(): Boolean = File(BringCatalogFile.REQUESTS).let { it.isDirectory && it.canWrite() }

    /** The request's progress, or null when none was made in this visit. A status file from before this request does not count. */
    private fun progress(pkg: String): Progress? {
        val at = asked[pkg] ?: return null
        val f = File(BringCatalogFile.REQUESTS, "$pkg.status")
        val line = runCatching { if (f.isFile && f.lastModified() >= at - 2000) f.useLines { it.firstOrNull() } else null }.getOrNull()
        return BringCatalogFile.progress(line)
    }

    private fun snapshot(): String = asked.keys.joinToString(",") { pkg ->
        pkg + "=" + when (val p = progress(pkg)) {
            null -> ""
            is Progress.Failed -> "failed:" + p.why
            else -> p.javaClass.simpleName
        } + (if (installed(pkg)) "+i" else "")
    }

    private fun render() {
        val list = findViewById<LinearLayout>(R.id.guest_bring_list)
        list.removeAllViews()
        shown = snapshot()
        val color = getColor(R.color.preboot_card)
        if (!loaded) {
            NativeCards.row(NativeCards.section(list, null, color), getString(R.string.bring_reading))
            return
        }
        if (missing) {
            NativeCards.row(NativeCards.section(list, null, color), getString(R.string.bring_no_catalog))
            return
        }
        val shownApps = apps.filter { !installed(it.item.pkg) || it.item.pkg in asked }
        if (shownApps.isEmpty()) {
            NativeCards.row(NativeCards.section(list, null, color), getString(R.string.bring_none))
            return
        }
        val writable = requestsWritable()
        val card = NativeCards.section(list, getString(R.string.bring_intro), color)
        if (!writable) NativeCards.row(card, getString(R.string.bring_not_writable))
        for (app in shownApps) {
            val pkg = app.item.pkg
            val p = progress(pkg)
            val ready = p is Progress.Done || (p != null && installed(pkg) && p !is Progress.Failed)
            val summary = when {
                p == null -> pkg
                ready -> getString(R.string.bring_ready)
                p is Progress.Failed -> getString(R.string.bring_failed_tap, p.why)
                p is Progress.Installing -> getString(R.string.bring_installing)
                p is Progress.Copying -> getString(R.string.bring_copying)
                else -> getString(R.string.bring_sent)
            }
            // A tap asks for the app (again, after a failure); not while it is on its way or ready.
            val idle = p == null || p is Progress.Failed
            val row: CardItemView = NativeCards.row(card, app.item.label, summary, if (idle && writable) ({ request(pkg) }) else null)
            app.icon?.let { bmp ->
                row.getIconImageView()?.apply {
                    setImageDrawable(BitmapDrawable(resources, bmp))
                    imageTintList = null
                    visibility = View.VISIBLE
                }
            }
            if (ready) {
                val open = LayoutInflater.from(this).inflate(R.layout.item_bring_open, card, false) as Button
                open.setOnClickListener {
                    packageManager.getLaunchIntentForPackage(pkg)?.let { startActivity(it) }
                }
                card.addView(open, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { gravity = android.view.Gravity.END })
            }
        }
    }

    /** The request is an empty file named after the package; an older one (and its status) is replaced so the watcher sees a new one. */
    private fun request(pkg: String) {
        val dir = File(BringCatalogFile.REQUESTS)
        val ok = runCatching {
            File(dir, "$pkg.status").delete()
            File(dir, pkg).delete()
            File(dir, pkg).createNewFile()
        }.getOrDefault(false)
        if (ok) asked[pkg] = System.currentTimeMillis()
        else android.widget.Toast.makeText(this, R.string.bring_not_writable, android.widget.Toast.LENGTH_LONG).show()
        render()
    }
}
