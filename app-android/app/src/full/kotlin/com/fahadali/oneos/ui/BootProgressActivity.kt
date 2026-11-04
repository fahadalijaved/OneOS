package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.session.LaunchJob

/** Visible boot preparation. The debug path never observes, starts or cancels a real launch. */
class BootProgressActivity : EdgeToEdgeActivity() {
    companion object {
        fun intent(ctx: Context, image: ImageRef, preview: Boolean = false) = Intent(ctx, BootProgressActivity::class.java)
            .putExtra("image", image.id).putExtra("preview", preview)
    }
    private var preview = false
    private var cancelled = false
    private var unsubscribe: (() -> Unit)? = null
    private val handler = Handler(Looper.getMainLooper())
    private var shownFailure = false
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ArtworkTransitions.prepare(this)
        val image = intent.getStringExtra("image")?.let(Images::byId) ?: LaunchJob.state.image
        if (image == null) { finish(); return }
        preview = DebugPreview.enabled(this) && intent.getBooleanExtra("preview", false)
        setContentView(R.layout.activity_boot_progress)
        findViewById<View>(R.id.boot_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        findViewById<OsArtworkView>(R.id.boot_artwork).bind(image)
        ArtworkTransitions.bindTarget(this, findViewById(R.id.boot_artwork))
        // The ways back, said once more on the last screen before One UI closes (0.4.43, UX audit).
        findViewById<TextView>(R.id.boot_back).text = getString(R.string.switch_go_dialog_back_app, image.name)
        findViewById<TextView>(R.id.boot_title).apply {
            text = image.name
            if (!resources.getBoolean(R.bool.home_two_pane)) visibility = View.GONE
        }
        findViewById<Toolbar>(R.id.boot_toolbar).apply {
            setNavigationIcon(dev.oneuiproject.oneui.R.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            if (!resources.getBoolean(R.bool.home_two_pane)) title = image.name
            if (preview) subtitle = getString(R.string.environment_preview)
            setNavigationOnClickListener { cancelBoot() }
        }
        findViewById<Button>(R.id.boot_cancel).setOnClickListener { cancelBoot() }
        if (!preview) onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() = cancelBoot()
        })
    }
    override fun onStart() {
        super.onStart()
        if (preview) {
            handler.postDelayed({
                if (!isFinishing && !isDestroyed) AlertDialog.Builder(this).setTitle(R.string.setup_preview_complete)
                    .setMessage(R.string.setup_preview_simulated).setPositiveButton(android.R.string.ok) { _, _ -> finishAfterTransition() }.show()
            }, 8_000L)
        } else unsubscribe = LaunchJob.observe { state ->
            findViewById<Button>(R.id.boot_cancel).apply {
                isEnabled = state.cancellable && !cancelled
                setText(if (cancelled) R.string.environment_boot_cancelling else android.R.string.cancel)
            }
            findViewById<TextView>(R.id.boot_status).text = state.detail ?: getString(R.string.splash_shutdown)
            if (state.phase == LaunchJob.Phase.IDLE) finish()
            if (state.phase == LaunchJob.Phase.FAILED && !shownFailure) {
                shownFailure = true
                AlertDialog.Builder(this).setTitle(state.plain?.title ?: getString(R.string.setup_failed_title))
                    .setMessage(state.plain?.line ?: state.message).setPositiveButton(android.R.string.ok) { _, _ -> LaunchJob.clear(); finish() }.show()
            }
        }
    }
    private fun cancelBoot() {
        if (preview) { handler.removeCallbacksAndMessages(null); finishAfterTransition() }
        else if (LaunchJob.cancel()) {
            cancelled = true
            findViewById<Button>(R.id.boot_cancel).apply { isEnabled = false; setText(R.string.environment_boot_cancelling) }
        }
    }
    override fun onStop() { handler.removeCallbacksAndMessages(null); unsubscribe?.invoke(); unsubscribe = null; super.onStop() }
}
