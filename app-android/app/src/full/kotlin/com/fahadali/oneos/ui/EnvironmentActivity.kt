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
import com.fahadali.oneos.session.GuestRuntimeStore
import com.fahadali.oneos.session.PatchChannels
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
    private var patchBusy = false
    private var rootBusy = false
    private var rootState: GuestRuntimeStore.State? = null
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
            nativeToolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
                roundedCorners = 0
                fillHorizontalPadding = false
            }
            nativeToolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
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
            seslSetFadingEdgeColor(getColor(R.color.preboot_page))
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
        // Only what this page shows of the log save (11-10): it rebuilt every row for each of the 135
        // "Collecting N of M" lines, and "Skip saving logs" rebuilt under the finger lost its tap.
        subscriptions += com.fahadali.oneos.session.LogJob.observeBy({ Triple(it.busy, it.recovering, it.stopping) }) { render() }
        subscriptions += com.fahadali.oneos.session.OldStagesJob.observe { if (!it.busy) Readiness.tick(this); render() }
    }
    override fun onResume() {
        super.onResume()
        if (::image.isInitialized && !preview) {
            Readiness.onResume(this); render()
            if (!rootBusy) {
                rootBusy = true
                GuestRuntimeStore.refresh(this, image.id) { next ->
                    if (!isDestroyed) { rootBusy = false; rootState = next; render() }
                }
            }
        }
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
            val logs = com.fahadali.oneos.session.LogJob.state
            val why = when {
                logs.busy && logs.stopping -> R.string.environment_busy_logs_stopping
                logs.busy -> R.string.environment_busy_logs
                else -> R.string.environment_busy_other
            }
            val busyCard = Cards.section(column, null, rows = true)
            // A card of rows has no padding of its own: without the row's the round corners clipped the text (11-10).
            CardRows.text(busyCard, getString(why), R.style.OneOS_Text_Caption, inList = true).apply {
                setPaddingRelative(paddingStart, dp(12), paddingEnd, dp(12))
            }
            // Skip the log save (owner, 11-08): Boot and Update no longer wait minutes for it.
            // Once tapped the row goes and the text above says "Stopping" (11-10: nothing changed until the save had ended).
            if (logs.busy && !logs.recovering && !logs.stopping) Cards.row(busyCard, R.drawable.ic_oneos_row_last_time, getString(R.string.logs_skip), getString(R.string.logs_skip_summary)) {
                com.fahadali.oneos.session.LogJob.skip()
            }
        }
        val checks = PrebootCards.section(column, gap = false)
        checks.setPadding(dp(10), dp(10), dp(10), dp(10))
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
            checks.addView(row, LinearLayout.LayoutParams(-1, -2).apply { if (rowIndex > 0) topMargin = dp(10) })
            values.forEachIndexed { index, tile ->
                val surface = RoundedLinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    val level = tileLevel(tileGates[rowIndex * 2 + index])
                    val neutral = getColor(R.color.oneos_check_surface)
                    setBackgroundColor(if (level != Level.WARN && level != Level.BLOCK) neutral else
                        androidx.core.graphics.ColorUtils.blendARGB(neutral, Cards.levelColor(this@EnvironmentActivity, level), .16f))
                    roundedCorners = androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_NONE
                    fillHorizontalPadding = false
                    val innerRadius = (resources.getDimension(androidx.appcompat.R.dimen.sesl_rounded_corner_radius) - dp(10)).coerceAtLeast(0f)
                    // Use SESL's own smooth-corner geometry at the inset radius, under the One UI theme.
                    outlineProvider = object : android.view.ViewOutlineProvider() {
                        override fun getOutline(view: View, outline: android.graphics.Outline) {
                            outline.setPath(androidx.appcompat.util.SeslRoundedCorner.getSmoothCornerRectPath(
                                innerRadius, 0f, 0f, view.width.toFloat(), view.height.toFloat()))
                        }
                    }
                    clipToOutline = true
                }
                row.addView(surface, LinearLayout.LayoutParams(0, -1, 1f).apply { if (index > 0) marginStart = dp(10) })
                val content = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = android.view.Gravity.CENTER_VERTICAL
                    minimumHeight = dp(85)
                    setPadding(dp(8), dp(8), dp(8), dp(8))
                    importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
                    contentDescription = "${tile.second}: ${tile.third}"
                }
                content.addView(android.widget.ImageView(this).apply {
                    setImageResource(tile.first)
                    imageTintList = ColorStateList.valueOf(getColor(R.color.oneos_icon))
                    importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                }, LinearLayout.LayoutParams(dp(30), dp(30)).apply { marginEnd = dp(14) })
                val labels = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS
                }
                labels.addView(TextView(this).apply {
                    text = tile.second; textSize = 18f; includeFontPadding = false
                })
                labels.addView(TextView(this).apply {
                    text = tile.third; textSize = 14f; includeFontPadding = false
                    setTextColor(getColor(R.color.preboot_secondary))
                }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(3) })
                content.addView(labels, LinearLayout.LayoutParams(0, -2, 1f))
                surface.addView(content, LinearLayout.LayoutParams(-1, -2))
            }
        }
        val patchProfile = currentFacts?.let { com.fahadali.oneos.core.model.Profiles.resolve(it).profile }
        val patchSources = patchProfile?.let { PatchChannels.sources(this, it.id, image.id) }.orEmpty()
        if (!preview && patchProfile != null && patchSources.isNotEmpty()) {
            val heading = getString(R.string.patch_channel_title, patchProfile.label.removePrefix("Galaxy "))
            val patches = PrebootCards.section(column, "Patches")
            val source = PatchChannels.selected(this, patchProfile.id, image.id)
            val idle = !patchBusy && !Readiness.anyBusy() && !StageCheck.state.busy
            fun label(choice: com.fahadali.oneos.core.model.PatchSource) = if (choice.stable) getString(R.string.patch_channel_stable) else choice.label
            PrebootCards.row(patches, "${label(source)} · ${patchProfile.label.removePrefix("Galaxy ")}",
                getString(if (patchBusy) R.string.patch_channel_checking else R.string.patch_channel_summary), enabled = idle) {
                AlertDialog.Builder(this).setTitle(heading)
                    .setSingleChoiceItems(patchSources.map { label(it) }.toTypedArray(), patchSources.indexOfFirst { it.id == source.id }) { dialog, which ->
                        dialog.dismiss(); choosePatches(patchSources[which].id)
                    }.setNegativeButton(android.R.string.cancel, null).show()
            }
            PrebootCards.row(patches, getString(R.string.patch_channel_refresh),
                PatchChannels.setFor(patchProfile.id, image.id)?.let { set ->
                    if (!source.stable) runCatching { PatchChannels.snapshot(this, set, patchProfile.id)?.revision }.getOrNull()
                    else getString(R.string.patch_channel_stable_version, PatchChannels.stableVersion(this))
                }, enabled = idle) { checkPatches() }
        }
        if (maintenance != null) {
            Cards.row(Cards.section(column, null, rows = true), Icons.drawable.ic_oui_refresh,
                maintenance.title, maintenance.line).apply { isClickable = false; isFocusable = false }
        }
        val root = PrebootCards.section(column, "Root")
        val guest = rootState ?: GuestRuntimeStore.State(image.id)
        val rootIdle = !preview && !rootBusy && !Readiness.anyBusy() && !StageCheck.state.busy
        CardRows.toggle(root, "Enable guest runtime", when {
            rootBusy -> "Reading guest root…"
            guest.error != null -> guest.error
            !guest.ready -> "Update this system to add guest root support"
            else -> null
        }, guest.enabled, enabled = rootIdle && guest.ready) { enabled ->
            changeRoot { done -> GuestRuntimeStore.setEnabled(this, image.id, enabled, done) }
        }.apply {
            minimumHeight = dp(52)
            (this as dev.oneuiproject.oneui.widget.SwitchItemView).separateSwitch = true
        }
        PrebootCards.row(root, getString(R.string.guest_root_shared_kernel_title),
            getString(R.string.guest_root_shared_kernel_summary))
        PrebootCards.row(root, "Xposed framework", guest.providerName(), enabled = rootIdle && guest.ready) {
            val providers = listOf("zygisk_vector") + guest.modules.filter { it.framework != null }.map { it.id }.filter { it != "zygisk_vector" }
            val names = providers.map { guest.providerName(it) } + "Import LSPosed or Vector ZIP…"
            AlertDialog.Builder(this).setTitle("Xposed framework")
                .setSingleChoiceItems(names.toTypedArray(), providers.indexOf(guest.selected)) { dialog, which ->
                    dialog.dismiss()
                    if (which == providers.size) startActivity(Intent(this, GuestRuntimeActivity::class.java)
                        .putExtra("image", image.id).putExtra("import_framework", true))
                    else changeRoot { done -> GuestRuntimeStore.select(this, image.id, providers[which], done) }
                }.setNegativeButton(android.R.string.cancel, null).show()
        }
        PrebootCards.row(root, "Manage guest modules", chevron = true, enabled = !rootBusy) {
            startActivity(Intent(this, GuestRuntimeActivity::class.java).putExtra("image", image.id))
        }
        // Bring apps lives on each system's page, like Root (owner, 11-10); its screen says so when another system is set up now.
        PrebootCards.row(PrebootCards.section(column, getString(R.string.environment_apps)), getString(R.string.bring_title),
            getString(R.string.environment_bring_summary), chevron = true, enabled = !preview) {
            startActivity(BringAppsActivity.intent(this, image))
        }
        PrebootCards.row(PrebootCards.section(column), getString(R.string.environment_report), chevron = true) {
            if (preview) AlertDialog.Builder(this).setTitle(R.string.environment_report).setMessage(R.string.environment_preview).setPositiveButton(android.R.string.ok, null).show()
            else FixActions.run(this, FixAction.SEND_REPORT, image)
        }
        val blocked = report?.gates?.firstOrNull { it.level == Level.BLOCK }
        // What stops the switch, in plain words: the button below offers its fix instead of a Boot that only
        // re-ran the check (0.4.43, UX audit).
        var blockPlain: com.fahadali.oneos.core.model.PlainMessage? = null
        if (!preview && blocked != null && currentFacts != null &&
            (maintenance == null || blocked.finding.reason != report.find(com.fahadali.oneos.core.model.SwitchGates.ID_IMAGE)?.finding?.reason)) {
            val plain = Plain.of(blocked.finding, report, currentFacts)
            // An update in progress keeps its own button, except for the restore after a force
            // restart: that gate blocks the update too, so its button is "Restore now" (11-08).
            if (maintenance == null || plain.action == FixAction.RESTORE) blockPlain = plain
            Cards.row(Cards.section(column, null, rows = true), Cards.badge(Level.BLOCK), plain.title, plain.line) {
                FixActions.run(this, plain.action, image)
            }
        } else if (!preview && !StageCheck.state.busy && StageCheck.state.failure != null) {
            val message = Plain.of(StageCheck.state.failure!!, image, null).line
            CardRows.text(Cards.section(column, null), message, R.style.OneOS_Text_Caption)
        }
        // Any job (0.4.38: the log collection after a return can run for minutes) shows the spinner,
        // not a button whose tap readyToBoot() then ignores.
        val checking = !preview && (patchBusy || StageCheck.state.busy || StageCheck.state.phase == StageCheck.Phase.IDLE ||
            (StageCheck.state.phase != StageCheck.Phase.FAILED && report == null) ||
            Readiness.anyBusy() || com.fahadali.oneos.session.RemoveJob.state.busy)
        findViewById<View>(R.id.environment_action_spinner).visibility = if (checking) View.VISIBLE else View.GONE
        fun readyToBoot(): Boolean = preview || (!patchBusy && StageCheck.state.phase == StageCheck.Phase.DONE &&
            StageCheck.state.result === result && result != null && result.ageMs <= Readiness.CHECK_AGE_MS &&
            report != null && (report.image?.id == image.id || (maintenance != null && ImageMaintenance.identifiedImage(result)?.id == image.id)) &&
            (maintenance != null || !report.blocked) && !Readiness.anyBusy() &&
            !com.fahadali.oneos.session.RemoveJob.state.busy)
        window.decorView.removeCallbacks(recheck)
        if (!preview && !checking && result != null && StageCheck.state.phase == StageCheck.Phase.DONE)
            window.decorView.postDelayed(recheck, (Readiness.CHECK_AGE_MS - result.ageMs).coerceAtLeast(0L) + 500L)
        findViewById<Button>(R.id.environment_boot).apply {
            val fix = blockPlain?.takeIf { !checking }
            // The restore after a force restart comes before an interrupted update's retry,
            // which the same restore gate would only block again (11-08 reports).
            val restoreFirst = fix?.action == FixAction.RESTORE
            text = if (result?.status?.pendingUpdate != null && maintenance != null && !restoreFirst) getString(R.string.retry_update)
                else if (fix != null) fix.actionLabel ?: getString(R.string.environment_what_stops)
                else getString(if (maintenance != null) R.string.environment_update else R.string.environment_boot, image.name)
            // Tappable whenever no check runs: a tap on a check that ran out starts a fresh one (below).
            // Disabled, an expired check left the button dead until the screen was left (0.4.38, F8U).
            isEnabled = !checking
            // Preserve the native button's text measurement while replacing its label
            // visually with the centred SESL spinner during the read-only check.
            setTextColor(if (checking) ColorStateList.valueOf(Color.TRANSPARENT) else actionTextColors)
            contentDescription = if (checking) getString(R.string.environment_checking) else text
            setOnClickListener {
                if (fix != null) {
                    if (fix.actionLabel == null || fix.action == com.fahadali.oneos.core.model.FixAction.NONE ||
                        fix.action == com.fahadali.oneos.core.model.FixAction.ACKNOWLEDGE
                    ) {
                        androidx.appcompat.app.AlertDialog.Builder(this@EnvironmentActivity).setTitle(fix.title).setMessage(fix.line)
                            .setPositiveButton(android.R.string.ok, null).show()
                    } else {
                        FixActions.run(this@EnvironmentActivity, fix.action, image)
                    }
                    return@setOnClickListener
                }
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
    private fun changeRoot(action: ((GuestRuntimeStore.State) -> Unit) -> Unit) {
        if (rootBusy) return
        rootBusy = true; render()
        action { next ->
            if (!isDestroyed) {
                rootBusy = false
                if (next.error == null) rootState = next
                else AlertDialog.Builder(this).setTitle("Guest root").setMessage(next.error).setPositiveButton(android.R.string.ok, null).show()
                render()
            }
        }
    }
    private fun channelProfile() = (StageCheck.state.result?.facts ?: facts)?.let {
        com.fahadali.oneos.core.model.Profiles.resolve(it).profile
    }

    private fun checkPatches() {
        val profile = channelProfile() ?: return
        val source = PatchChannels.selected(this, profile.id, image.id)
        if (!source.stable) { choosePatches(source.id, showResult = true); return }
        if (patchBusy || Readiness.anyBusy()) return
        patchBusy = true; render()
        io.execute {
            val result = runCatching { PatchChannels.stableRelease() }
            runOnUiThread {
                patchBusy = false
                if (!isDestroyed) {
                    val release = result.getOrNull()
                    val message = release?.let {
                        getString(if (it.versionCode > PatchChannels.stableCode(this)) R.string.patch_channel_stable_newer
                            else R.string.patch_channel_stable_current, it.versionName)
                    } ?: result.exceptionOrNull()?.message
                    AlertDialog.Builder(this).setTitle(if (result.isSuccess) R.string.patch_channel_refresh else R.string.patch_channel_failed)
                        .setMessage(message).setPositiveButton(android.R.string.ok, null).show()
                    render()
                }
            }
        }
    }

    private fun choosePatches(sourceId: String, showResult: Boolean = false) {
        if (patchBusy || Readiness.anyBusy()) return
        patchBusy = true; render()
        val selectedImage = image.id
        val profile = channelProfile() ?: run { patchBusy = false; render(); return }
        io.execute {
            val result = runCatching {
                val set = PatchChannels.setFor(profile.id, selectedImage)!!
                val source = PatchChannels.sources(this, profile.id, selectedImage).first { it.id == sourceId }
                if (!source.stable) PatchChannels.refresh(this, set, profile.id, source.id)
                PatchChannels.select(this, profile.id, selectedImage, source.id)
            }
            runOnUiThread {
                patchBusy = false
                if (!isDestroyed) {
                    result.exceptionOrNull()?.let { error ->
                        AlertDialog.Builder(this).setTitle(R.string.patch_channel_failed).setMessage(error.message)
                            .setPositiveButton(android.R.string.ok, null).show()
                    }
                    if (showResult && result.isSuccess) android.widget.Toast.makeText(this, R.string.patch_channel_checked, android.widget.Toast.LENGTH_LONG).show()
                    StageCheck.start(this, StageCheck.Mode.FULL)
                    render()
                }
            }
        }
    }

    private fun environmentToolbar(): Toolbar =
        findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)?.toolbar
            ?: findViewById(R.id.environment_toolbar)

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
