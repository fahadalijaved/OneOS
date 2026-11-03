package com.fahadali.oneos.ui

import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.DeviceFacts
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.session.LaunchJob
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.Readiness
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.widget.CardItemView
import dev.oneuiproject.oneui.widget.RoundedLinearLayout
import dev.oneuiproject.oneui.R as Icons

/** Read-only environment checks. Boot still goes through SwitchConfirm and LaunchJob's fresh gates. */
class EnvironmentActivity : EdgeToEdgeActivity() {
    private lateinit var image: ImageRef
    private var preview = false
    private lateinit var actionTextColors: ColorStateList
    private var facts: DeviceFacts? = null
    private val subscriptions = mutableListOf<() -> Unit>()
    private val io = java.util.concurrent.Executors.newSingleThreadExecutor()
    // A check is good for Readiness.CHECK_AGE_MS: when it runs out on this screen, check again by itself.
    private val recheck = Runnable { if (!isDestroyed && !preview) { Readiness.tick(this); render() } }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ArtworkTransitions.prepare(this)
        val selected = intent.getStringExtra("image")?.let(Images::byId) ?: EnvironmentNavigation.image(this)
        if (selected == null) { catalogue(); return }
        image = selected
        preview = DebugPreview.enabled(this) && intent.getBooleanExtra("preview", false)
        setContentView(R.layout.activity_environment)
        actionTextColors = findViewById<Button>(R.id.environment_boot).textColors
        val nativeToolbar = findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)
        if (nativeToolbar != null) {
            // Same fixed-height ToolbarLayout and native SESL floating bridge as Twidget.
            applyEdgeToEdgeInsets(nativeToolbar, onNavigationBarInset = {})
            findViewById<View>(R.id.environment_window).setOnApplyWindowInsetsListener { _, insets ->
                val bottom = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout()).bottom
                findViewById<View>(R.id.environment_footer).updateBottomMarginForNavigationBar(0, bottom)
                insets
            }
            nativeToolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
            nativeToolbar.setEdgeInsetHorizontal(0f)
            findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
                roundedCorners = 0
                fillHorizontalPadding = false
            }
            findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
        } else findViewById<View>(R.id.environment_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        environmentToolbar().apply {
            setNavigationIcon(Icons.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
            if (preview) subtitle = getString(R.string.environment_preview)
        }
        findViewById<NestedScrollView>(R.id.environment_scroll).apply {
            isNestedScrollingEnabled = !resources.getBoolean(R.bool.home_two_pane)
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(getColor(R.color.oneos_page_background))
            seslSetFadingEdgeWindowBottomAlignment(nativeToolbar != null)
            seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        }
        val scroll = findViewById<NestedScrollView>(R.id.environment_scroll)
        findViewById<View>(R.id.environment_footer).addOnLayoutChangeListener { footer, _, _, _, _, _, _, _, _ ->
            // The native fade belongs to the scrolling content behind the fixed action.
            // Bottom padding lets the final row scroll fully clear of the button.
            val navigation = if (nativeToolbar != null) (footer.layoutParams as? ViewGroup.MarginLayoutParams)?.bottomMargin ?: 0 else 0
            val clearance = footer.height + navigation + dp(16)
            val fadeHeight = footer.height + navigation + dp(24)
            // Keep the fixed action backed by the native fade even with short or
            // temporarily incomplete checking content, not just when scrollable.
            scroll.seslForceBottomFadingEdgeClamped(fadeHeight)
            scroll.invalidate()
            if (scroll.paddingBottom != clearance) {
                scroll.setPadding(scroll.paddingLeft, scroll.paddingTop, scroll.paddingRight, clearance)
                scroll.seslSetFadingEdgeEnabled(true, dp(24), fadeHeight)
            }
        }
        render()
        ArtworkTransitions.bindTarget(this, findViewById(R.id.environment_artwork))
        if (!preview) io.execute {
            val collected = runCatching { FactProbe(applicationContext).collect(RootProbe(applicationContext).signals()) }.getOrNull()
            runOnUiThread { if (!isDestroyed && !isFinishing) { facts = collected; render() } }
        }
    }

    override fun onStart() {
        super.onStart()
        if (!::image.isInitialized || preview) return
        subscriptions += StageCheck.observe { if (!it.busy) Readiness.tick(this); render() }
        subscriptions += PrepareJob.observe { render() }
        subscriptions += LaunchJob.observe { render() }
        subscriptions += com.fahadali.oneos.session.LogJob.observe { render() }
        subscriptions += com.fahadali.oneos.session.OldStagesJob.observe { if (!it.busy) Readiness.tick(this); render() }
    }
    override fun onResume() {
        super.onResume()
        if (::image.isInitialized && !preview) { Readiness.onResume(this); render() }
    }
    override fun onStop() {
        window.decorView.removeCallbacks(recheck)
        subscriptions.forEach { it() }; subscriptions.clear(); super.onStop()
    }
    override fun onDestroy() { io.shutdownNow(); super.onDestroy() }

    private fun catalogue() {
        startActivity(Intent(this, LauncherActivity::class.java).putExtra("browse_systems", true).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        finish()
    }

    private fun render() {
        if (!::image.isInitialized || isDestroyed) return
        val result = StageCheck.state.result
        val currentFacts = if (!preview) result?.facts?.let { FactProbe(this).refresh(it) } ?: facts else null
        val report = if (!preview && result?.installd != null && currentFacts != null)
            StageCheck.gates(this, result, GatePhase.SWITCH, screenLock = currentFacts.screenLockSet, facts = currentFacts) else null
        if (!preview && result?.status?.ours == true) result.status.marker?.imageId?.let(Images::byId)?.let {
            if (it.id == image.id) EnvironmentNavigation.remember(this, it, false)
        }
        val maintenance = if (!preview) ImageMaintenance.message(this, image, result, report) else null
        findViewById<OsArtworkView>(R.id.environment_artwork).bind(image)
        findViewById<TextView>(R.id.environment_title).text = image.name
        val wide = resources.getBoolean(R.bool.home_two_pane)
        if (!wide) findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout).setTitle(image.name)
        val column = findViewById<LinearLayout>(R.id.environment_cards)
        column.removeAllViews()
        // 0.4.38: say what is running, so a waiting button is never a silent one (top: the fixed action covers the bottom).
        if (!preview && !StageCheck.state.busy && (Readiness.anyBusy() || com.fahadali.oneos.session.RemoveJob.state.busy)) {
            val why = if (com.fahadali.oneos.session.LogJob.state.busy) R.string.environment_busy_logs else R.string.environment_busy_other
            CardRows.text(Cards.section(column, null), getString(why), R.style.OneOS_Text_Caption)
        }
        val checks = Cards.section(column, null)
        checks.setPadding(dp(8), dp(8), dp(8), dp(8))
        val rootValue = if (preview) "KernelSU active" else currentFacts?.rootKind?.takeUnless { it == com.fahadali.oneos.core.model.RootKind.NONE }?.label?.let { getString(R.string.environment_active, it) }
            ?: getString(R.string.environment_no_root)
        val storageValue = if (preview) "51.2 GB free" else currentFacts?.storage?.let { getString(R.string.environment_free, Units.bytes(it.freeBytes)) } ?: getString(R.string.environment_unknown)
        val batteryValue = if (preview) "98% Charging · 28°C" else currentFacts?.battery?.let {
            "${it.levelPercent}%" + (if (it.charging) " · Charging" else "") + (it.temperatureC?.let { t -> " · ${t.toInt()}°C" } ?: "")
        } ?: getString(R.string.environment_unknown)
        val lockValue = if (preview) getString(R.string.environment_lock_off) else getString(when (currentFacts?.screenLockSet) {
            false -> R.string.environment_lock_off
            true -> R.string.environment_lock_on
            null -> R.string.environment_unknown
        })
        val tileReport = report ?: if (!preview && result != null && currentFacts != null)
            StageCheck.gates(this, result, GatePhase.SWITCH, screenLock = currentFacts.screenLockSet, facts = currentFacts) else null
        fun tileLevel(id: String): Level = when {
            preview -> Level.OK
            StageCheck.state.busy -> Level.INFO
            StageCheck.state.failure?.id == id -> StageCheck.state.failure!!.level
            StageCheck.state.phase == StageCheck.Phase.DONE -> tileReport?.find(id)?.level ?: Level.INFO
            else -> Level.INFO
        }
        val tileGates = listOf(
            com.fahadali.oneos.core.model.SwitchGates.ID_ROOT,
            com.fahadali.oneos.core.model.SwitchGates.ID_SPACE,
            com.fahadali.oneos.core.model.SwitchGates.ID_BATTERY,
            com.fahadali.oneos.core.model.SwitchGates.ID_SCREEN_LOCK,
        )
        val tiles = listOf(
            Triple(Icons.drawable.ic_oui_security, getString(R.string.environment_root), rootValue),
            Triple(Icons.drawable.ic_oui_manage_storage, getString(R.string.environment_storage), storageValue),
            Triple(Icons.drawable.ic_oui_battery_filled, getString(R.string.environment_battery), batteryValue),
            Triple(Icons.drawable.ic_oui_page_lock, getString(R.string.environment_lock), lockValue),
        )
        tiles.chunked(2).forEachIndexed { rowIndex, values ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; isBaselineAligned = false }
            checks.addView(row, LinearLayout.LayoutParams(-1, -2).apply { if (rowIndex > 0) topMargin = dp(8) })
            values.forEachIndexed { index, tile ->
                val surface = RoundedLinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    val level = tileLevel(tileGates[rowIndex * 2 + index])
                    val neutral = getColor(R.color.oneos_check_surface)
                    setBackgroundColor(if (level == Level.INFO) neutral else
                        androidx.core.graphics.ColorUtils.blendARGB(neutral, Cards.levelColor(this@EnvironmentActivity, level), .16f))
                    roundedCorners = androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_NONE
                    fillHorizontalPadding = false
                    val innerRadius = (resources.getDimension(androidx.appcompat.R.dimen.sesl_rounded_corner_radius) - dp(8)).coerceAtLeast(0f)
                    // Use SESL's own smooth-corner geometry at the inset radius, under the One UI theme.
                    outlineProvider = object : android.view.ViewOutlineProvider() {
                        override fun getOutline(view: View, outline: android.graphics.Outline) {
                            outline.setPath(androidx.appcompat.util.SeslRoundedCorner.getSmoothCornerRectPath(
                                innerRadius, 0f, 0f, view.width.toFloat(), view.height.toFloat()))
                        }
                    }
                    clipToOutline = true
                }
                row.addView(surface, LinearLayout.LayoutParams(0, -1, 1f).apply { if (index > 0) marginStart = dp(8) })
                surface.addView(CardItemView(this).apply {
                    title = tile.second; summary = tile.third
                    icon = androidx.appcompat.content.res.AppCompatResources.getDrawable(context, tile.first)
                    iconSize = dp(24)
                    minimumHeight = dp(if (wide) 88 else 104)
                    gravity = android.view.Gravity.CENTER_VERTICAL
                    getIconImageView().imageTintList = ColorStateList.valueOf(getColor(R.color.oneos_icon))
                    // Compact the stock card row for a two-column fact tile; it has no badge or end widget.
                    (getTitleView().parent as View).setPadding(dp(12), 0, dp(12), 0)
                    (getIconImageView().parent as View).setPadding(0, 0, dp(12), 0)
                    getTitleView().apply {
                        textSize = 16f
                        (layoutParams as? ViewGroup.MarginLayoutParams)?.let { it.marginEnd = 0; layoutParams = it }
                    }
                    getSummaryView().apply {
                        textSize = 13f
                        (layoutParams as? ViewGroup.MarginLayoutParams)?.let { it.marginEnd = 0; layoutParams = it }
                    }
                    isClickable = false; isFocusable = false
                }, LinearLayout.LayoutParams(-1, -2))
            }
        }
        if (maintenance != null) {
            Cards.row(Cards.section(column, null, rows = true), Icons.drawable.ic_oui_refresh,
                maintenance.title, maintenance.line).apply { isClickable = false; isFocusable = false }
        }
        Cards.row(Cards.section(column, null, rows = true), 0, getString(R.string.environment_guest_root),
            getString(R.string.environment_guest_root_status))
        Cards.row(Cards.section(column, null, rows = true), 0, getString(R.string.environment_report)) {
            if (preview) AlertDialog.Builder(this).setTitle(R.string.environment_report).setMessage(R.string.environment_preview).setPositiveButton(android.R.string.ok, null).show()
            else FixActions.run(this, FixAction.SEND_REPORT, image)
        }.also { Cards.setRowEnd(it, Icons.drawable.ic_oui_keyboard_arrow_right) }
        val blocked = report?.gates?.firstOrNull { it.level == Level.BLOCK }
        if (!preview && blocked != null && currentFacts != null &&
            (maintenance == null || blocked.finding.reason != report.find(com.fahadali.oneos.core.model.SwitchGates.ID_IMAGE)?.finding?.reason)) {
            val plain = Plain.of(blocked.finding, report, currentFacts)
            Cards.row(Cards.section(column, null, rows = true), Cards.badge(Level.BLOCK), plain.title, plain.line) {
                FixActions.run(this, plain.action, image)
            }
        } else if (!preview && !StageCheck.state.busy && StageCheck.state.failure != null) {
            val message = Plain.of(StageCheck.state.failure!!, image, null).line
            CardRows.text(Cards.section(column, null), message, R.style.OneOS_Text_Caption)
        }
        // Any job (0.4.38: the log collection after a return can run for minutes) shows the spinner,
        // not a button whose tap readyToBoot() then ignores.
        val checking = !preview && (StageCheck.state.busy || StageCheck.state.phase == StageCheck.Phase.IDLE ||
            (StageCheck.state.phase != StageCheck.Phase.FAILED && report == null) ||
            Readiness.anyBusy() || com.fahadali.oneos.session.RemoveJob.state.busy)
        findViewById<View>(R.id.environment_action_spinner).visibility = if (checking) View.VISIBLE else View.GONE
        fun readyToBoot(): Boolean = preview || (StageCheck.state.phase == StageCheck.Phase.DONE &&
            StageCheck.state.result === result && result != null && result.ageMs <= Readiness.CHECK_AGE_MS &&
            report != null && (report.image?.id == image.id || (maintenance != null && ImageMaintenance.identifiedImage(result)?.id == image.id)) &&
            (maintenance != null || !report.blocked) && !Readiness.anyBusy() &&
            !com.fahadali.oneos.session.RemoveJob.state.busy)
        window.decorView.removeCallbacks(recheck)
        if (!preview && !checking && result != null && StageCheck.state.phase == StageCheck.Phase.DONE)
            window.decorView.postDelayed(recheck, (Readiness.CHECK_AGE_MS - result.ageMs).coerceAtLeast(0L) + 500L)
        findViewById<Button>(R.id.environment_boot).apply {
            text = if (result?.status?.pendingUpdate != null && maintenance != null) getString(R.string.retry_update)
                else getString(if (maintenance != null) R.string.environment_update else R.string.environment_boot, image.name)
            // Tappable whenever no check runs: a tap on a check that ran out starts a fresh one (below).
            // Disabled, an expired check left the button dead until the screen was left (0.4.38, F8U).
            isEnabled = !checking
            // Preserve the native button's text measurement while replacing its label
            // visually with the centred SESL spinner during the read-only check.
            setTextColor(if (checking) ColorStateList.valueOf(Color.TRANSPARENT) else actionTextColors)
            contentDescription = if (checking) getString(R.string.environment_checking) else text
            setOnClickListener {
                if (!readyToBoot()) {
                    Readiness.tick(this@EnvironmentActivity)
                    render()
                    return@setOnClickListener
                }
                if (maintenance != null) {
                    FixActions.run(this@EnvironmentActivity, maintenance.action, image)
                    return@setOnClickListener
                }
                if (preview) ArtworkTransitions.start(this@EnvironmentActivity,
                    BootProgressActivity.intent(this@EnvironmentActivity, image, true), findViewById(R.id.environment_artwork))
                else SwitchConfirm.show(this@EnvironmentActivity)
            }
        }
    }
    private fun environmentToolbar(): Toolbar =
        findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)?.toolbar
            ?: findViewById(R.id.environment_toolbar)

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
