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
import androidx.appcompat.widget.Toolbar
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosReleases
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosToolJob
import dev.oneuiproject.oneui.R as Icons

/**
 * iOS 27 (OneiOS)'s page (docs/oneios.md, "In the app"), as an Android system's page is
 * (EnvironmentActivity, the same activity_environment layout): the artwork, the state of the iOS
 * files on this phone as check tiles (the runtime and its check, the image set and its check, iOS's
 * data, the last check before the switch), the one thing that stops the switch in plain words with
 * its fix, the runtime's and the image set's own rows, the last session and its logs, the tools, and
 * one fixed button that does what comes next: Set up iOS 27, a fix, Back to One UI, or Switch to
 * iOS 27, which asks first (OneiosSwitchConfirm) and shows the way back before One UI closes.
 * Everything it does is a job of [OneiosJob], whose root verbs are the ones before the redesign.
 */
class OneiosActivity : EdgeToEdgeActivity() {
    private lateinit var picker: OneiosPicker
    private lateinit var actionTextColors: ColorStateList
    private var unsubscribe: (() -> Unit)? = null
    private var toolUnsubscribe: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        picker = OneiosPicker(this, savedInstanceState)
        setContentView(R.layout.activity_environment)
        actionTextColors = findViewById<Button>(R.id.environment_boot).textColors
        val nativeToolbar = findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)
        if (nativeToolbar != null) {
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
            nativeToolbar.setTitle(getString(R.string.oneios_title))
        } else findViewById<View>(R.id.environment_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        toolbar().apply {
            setNavigationIcon(Icons.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
        }
        val scroll = findViewById<NestedScrollView>(R.id.environment_scroll)
        scroll.apply {
            isNestedScrollingEnabled = !resources.getBoolean(R.bool.home_two_pane)
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(getColor(R.color.preboot_page))
            seslSetFadingEdgeWindowBottomAlignment(nativeToolbar != null)
            seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        }
        findViewById<View>(R.id.environment_footer).addOnLayoutChangeListener { footer, _, _, _, _, _, _, _, _ ->
            // As on a system's page: the last row scrolls clear of the fixed button.
            val navigation = if (nativeToolbar != null) (footer.layoutParams as? ViewGroup.MarginLayoutParams)?.bottomMargin ?: 0 else 0
            val clearance = footer.height + navigation + dp(16)
            val fadeHeight = footer.height + navigation + dp(24)
            scroll.seslForceBottomFadingEdgeClamped(fadeHeight)
            scroll.invalidate()
            if (scroll.paddingBottom != clearance) {
                scroll.setPadding(scroll.paddingLeft, scroll.paddingTop, scroll.paddingRight, clearance)
                scroll.seslSetFadingEdgeEnabled(true, dp(24), fadeHeight)
            }
        }
        findViewById<OsArtworkView>(R.id.environment_artwork).bindArtwork(R.drawable.os_oneios)
        findViewById<TextView>(R.id.environment_title).text = getString(R.string.oneios_title)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        picker.save(outState)
    }

    override fun onStart() {
        super.onStart()
        // This page shows no byte count (Set up iOS 27 does): rows are built again only when something else changes.
        unsubscribe = OneiosJob.observeBy({ it.copy(done = 0, total = 0, bytesPerSecond = 0, etaSeconds = null, file = null, message = if (it.copying) null else it.message) }) { render(it) }
        // Update the kernel's rows (kernelUpdateRows): its step, pause and end, not its bytes.
        toolUnsubscribe = OneiosToolJob.observeBy({ s ->
            if (s.last != OneiosToolJob.Flow.KERNEL) null
            else listOf(s.flow, s.starting, s.stopping, s.problem, s.kernelPhase, s.view.current, s.view.held, s.view.paused, s.view.netWaiting,
                s.pausedByUser, s.noNetwork, s.canPause, s.plain, s.builtKc)
        }) { render(OneiosJob.state) }
    }

    override fun onResume() {
        super.onResume()
        if (!OneiosJob.state.busy) OneiosJob.refresh(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        toolUnsubscribe?.invoke()
        toolUnsubscribe = null
        super.onStop()
    }

    private fun render(s: OneiosJob.State) {
        if (isDestroyed) return
        val flow = s.flow
        val st = s.status
        val idle = !s.busy
        val column = findViewById<LinearLayout>(R.id.environment_cards)
        column.removeAllViews()

        // What runs now (a system page's busy card): a download or an import has its progress on Set up iOS 27.
        s.job?.let { job ->
            val busy = PrebootCards.section(column)
            CardRows.text(busy, s.message ?: OneiosActions.runningTitle(this, job), R.style.OneOS_Text_Caption, inList = true).apply {
                setPaddingRelative(paddingStart, dp(12), paddingEnd, dp(12))
            }
            if (s.copying) PrebootCards.row(busy, getString(R.string.systems_show_progress), chevron = true) {
                startActivity(OneiosSetupActivity.intent(this))
            }
        }

        // The state of the iOS files on this phone, as a system page's check tiles.
        val checks = PrebootCards.section(column, getString(R.string.oneios_state_title))
        checks.setPadding(dp(10), dp(10), dp(10), dp(10))
        Cards.tileGrid(
            checks,
            listOf(
                Cards.Tile(Icons.drawable.ic_oui_download, getString(R.string.oneios_runtime), tileValue(st?.runtime?.version, flow.runtime, st?.runtime?.placeholder == true), level(flow.runtime)),
                Cards.Tile(Icons.drawable.ic_oui_file_type_zip, getString(R.string.oneios_image), tileValue(st?.image?.let { "iOS ${it.version}" }, flow.image, false), level(flow.image)),
                Cards.Tile(
                    Icons.drawable.ic_oui_folder_outline, getString(R.string.oneios_data),
                    getString(if (st == null) R.string.environment_unknown else if (OneiosFlow.dataNew(st)) R.string.oneios_data_new else R.string.oneios_data_kept),
                    if (st == null) Level.INFO else Level.OK,
                ),
                Cards.Tile(
                    Icons.drawable.ic_oui_security_outline, getString(R.string.oneios_last_check),
                    getString(
                        when (flow.mark(OneiosFlow.Step.READY)) {
                            OneiosFlow.Mark.DONE -> R.string.oneios_last_check_passed
                            OneiosFlow.Mark.FAILED -> R.string.oneios_last_check_refused
                            OneiosFlow.Mark.RUNNING -> R.string.oneios_checking
                            else -> R.string.oneios_last_check_not_yet
                        },
                    ),
                    when (flow.mark(OneiosFlow.Step.READY)) {
                        OneiosFlow.Mark.DONE -> Level.OK
                        OneiosFlow.Mark.FAILED -> Level.BLOCK
                        else -> Level.INFO
                    },
                ),
            ),
        )

        // What to do now, or what stops the switch, in plain words (a system page's "what stops the switch").
        val problem = flow.problem
        when {
            s.offered == false -> PrebootCards.row(PrebootCards.section(column), getString(R.string.oneios_not_this_phone_title), getString(R.string.oneios_not_this_phone))
            problem != null && s.job == null -> {
                val fix = OneiosFlow.Next.of(problem.fix)
                PrebootCards.row(PrebootCards.section(column), problem.title, problem.line, chevron = problem.fix != OneiosFix.NONE, enabled = idle) {
                    if (problem.isNextStep) startActivity(OneiosSetupActivity.intent(this)) else OneiosActions.run(this, fix, picker)
                }
            }
            flow.ready && s.job == null -> PrebootCards.row(PrebootCards.section(column), getString(R.string.oneios_ready), getString(R.string.oneios_ready_line))
        }

        // The runtime: what is staged and its check, then where a runtime comes from.
        val runtime = PrebootCards.section(column, getString(R.string.oneios_runtime))
        PrebootCards.row(
            runtime,
            flow.runtimeLine ?: getString(R.string.oneios_runtime_none_title),
            st?.runtime?.let { getString(R.string.oneios_runtime_details, it.xnuhost, it.sessionAbi, OneiosSystem.SESSION_ABI.toString(), it.imageFormats) }
                ?: getString(R.string.oneios_runtime_none),
        )
        PrebootCards.row(runtime, getString(R.string.oneios_runtime_download), getString(R.string.oneios_runtime_download_line), chevron = true, enabled = idle) {
            OneiosActions.download(this, null)
        }
        PrebootCards.row(runtime, getString(R.string.oneios_runtime_tag), getString(R.string.oneios_runtime_tag_line), chevron = true, enabled = idle) {
            OneiosActions.askTag(this)
        }
        PrebootCards.row(runtime, getString(R.string.oneios_have_file), getString(R.string.oneios_runtime_file_line), chevron = true, enabled = idle) {
            picker.pick(OneiosKind.RUNTIME)
        }

        // The image set: what is staged and its check; it only ever comes from a file.
        val image = PrebootCards.section(column, getString(R.string.oneios_image))
        PrebootCards.row(
            image,
            flow.imageLine ?: getString(R.string.oneios_image_none_title),
            st?.image?.let { getString(R.string.oneios_image_details, it.format, st?.runtime?.imageFormats ?: "?") }
                ?: getString(R.string.oneios_image_none),
        )
        PrebootCards.row(image, getString(R.string.oneios_have_file), getString(R.string.oneios_image_file_line), chevron = true, enabled = idle) {
            picker.pick(OneiosKind.IMAGE)
        }
        PrebootCards.row(image, getString(R.string.oneios_image_how), getString(R.string.oneios_image_how_line), chevron = true) {
            SystemsNav.open(this, "https://github.com/${OneiosReleases.REPO}#readme")
        }
        PrebootCards.row(image, getString(R.string.oneios_data), (flow.dataLine ?: getString(R.string.environment_unknown)) + "\n" + getString(R.string.oneios_data_line))

        // The kernel: what the runtime carries, what the image boots, and Update the kernel (docs/oneios.md,
        // "Kernel updates"). A new kernel never means rebuilding the image set, and needs no PC: the phone fetches
        // Apple's kernelcache from Apple itself (once; it stays cached in the stage), pairs the staged xnu with it
        // and activates the collection atomically.
        if (st?.runtime != null) {
            val kernel = PrebootCards.section(column, getString(R.string.oneios_kernel))
            PrebootCards.row(
                kernel,
                kernelTitle(st),
                kernelDetails(st) + OneiosJob.kernelCheckLine(this)?.let { "\n$it" }.orEmpty(),
            )
            if (st.image != null) {
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_check), getString(R.string.oneios_kernel_check_line), chevron = true, enabled = idle) {
                    OneiosJob.checkKernel(this)
                }
                kernelUpdateRows(kernel, st, idle)
                if (st.imageKernel?.hasFallback == true) {
                    PrebootCards.row(kernel, getString(R.string.oneios_kernel_restore), getString(R.string.oneios_kernel_restore_line), chevron = true, enabled = idle) {
                        OneiosActions.confirmRestoreKernel(this)
                    }
                }
                // Optional, with no download: a kernelcache.macho a PC wrote (checked against the same pin).
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_kernelcache), getString(R.string.oneios_kernel_kernelcache_line), chevron = true, enabled = idle) {
                    picker.pickKernelcache()
                }
            }
        }

        // The return: an open session's way back, and how the last one came back.
        val session = PrebootCards.section(column, getString(R.string.last_title))
        if (st?.sessionOpen == true) {
            PrebootCards.row(session, getString(R.string.oneios_back), getString(R.string.oneios_back_line), chevron = true, enabled = idle) {
                OneiosJob.backToOneUi(this)
            }
        }
        val last = OneiosFlow.lastReturn(st)
        PrebootCards.row(
            session,
            last?.title ?: getString(R.string.last_none),
            last?.line ?: getString(R.string.oneios_last_none_line),
        )
        PrebootCards.row(session, getString(R.string.oneios_logs), getString(R.string.oneios_logs_line), chevron = true) {
            startActivity(OneiosLogsActivity.intent(this))
        }

        // Tools: OneiOS's phone checks beside One UI, and oneios-tool's flows (docs/oneios.md, "oneios-tool in the app").
        val tools = PrebootCards.section(column, getString(R.string.oneios_tools))
        PrebootCards.row(tools, getString(R.string.oneios_checks), getString(R.string.oneios_checks_line), chevron = true) {
            startActivity(OneiosChecksActivity.intent(this))
        }
        if (st?.runtime != null) {
            PrebootCards.row(tools, getString(R.string.oneios_make_image), getString(R.string.oneios_make_image_line), chevron = true,
                enabled = idle || OneiosToolJob.state.busy) { OneiosToolActivity.start(this, OneiosToolJob.Flow.MAKE_IMAGE) }
            PrebootCards.row(tools, getString(R.string.oneios_tool_sums), getString(R.string.oneios_tool_sums_line), chevron = true,
                enabled = idle || OneiosToolJob.state.busy) { OneiosToolActivity.start(this, OneiosToolJob.Flow.SUMS) }
        }

        if (st?.staged == true) {
            PrebootCards.row(PrebootCards.section(column, getString(R.string.oneios_manage)), getString(R.string.oneios_remove), getString(R.string.oneios_remove_line), chevron = true, enabled = idle) {
                OneiosActions.confirmRemove(this)
            }
        }
        bindAction(s, flow)
    }

    /** The fixed button: the one thing to do now, with a spinner while a job runs (as a system page's Boot). */
    private fun bindAction(s: OneiosJob.State, flow: OneiosFlow.View) {
        val waiting = s.busy || (s.status == null && s.failure == null && s.offered != false)
        findViewById<View>(R.id.environment_action_spinner).visibility = if (waiting) View.VISIBLE else View.GONE
        val next = flow.next
        // Not set up yet: Set up iOS 27, as a system's card says Set up; the steps are on that screen.
        val setUp = !waiting && (next == OneiosFlow.Next.GET_RUNTIME || next == OneiosFlow.Next.IMPORT_IMAGE) && flow.problem?.isNextStep != false
        findViewById<Button>(R.id.environment_boot).apply {
            text = when {
                next == OneiosFlow.Next.NOT_THIS_PHONE -> getString(R.string.catalog_not_available)
                setUp -> getString(R.string.oneios_set_up)
                else -> OneiosActions.label(this@OneiosActivity, next) ?: getString(R.string.oneios_switch)
            }
            isEnabled = !waiting && next != OneiosFlow.Next.NOT_THIS_PHONE
            setTextColor(if (waiting) ColorStateList.valueOf(Color.TRANSPARENT) else actionTextColors)
            contentDescription = if (waiting) getString(R.string.oneios_checking) else text
            setOnClickListener {
                val now = OneiosJob.state
                if (now.busy) return@setOnClickListener
                val n = now.flow.next
                if (setUp) startActivity(OneiosSetupActivity.intent(this@OneiosActivity))
                else OneiosActions.run(this@OneiosActivity, n, picker)
            }
        }
    }

    /**
     * Update the kernel on this page (docs/oneios.md, "Kernel updates"): while it runs, what runs now (its step, a
     * pause, the wait for a network) with Pause or Resume, Stop, and its own screen for the bytes and the time left;
     * after it, why it stopped in plain words ([OneiosPlain.kernelUpdate]) or Activate for the kernel it built; and
     * the Update button. This page is built again only when the step, a pause or the end changes, never for a byte
     * count ([onStart]).
     */
    private fun kernelUpdateRows(kernel: LinearLayout, st: OneiosStatus, idle: Boolean) {
        val t = OneiosToolJob.state
        val mine = t.last == OneiosToolJob.Flow.KERNEL
        if (mine && t.busy) {
            val v = t.view
            val running = v.steps.firstOrNull { it.state == OneiosTool.StepState.RUNNING }
            val why = when {
                t.stopping -> getString(R.string.oneios_tool_stopping)
                v.netWaiting != null -> v.netWaiting
                t.noNetwork -> getString(R.string.oneios_tool_no_network)
                v.held || t.pausedByUser -> getString(R.string.oneios_tool_paused)
                else -> v.paused
            }
            PrebootCards.row(
                kernel, t.kernelPhase?.words ?: getString(R.string.oneios_tool_starting),
                listOfNotNull(running?.text, why).joinToString(" · ").ifEmpty { getString(R.string.oneios_kernel_update_progress) }, chevron = true,
            ) { startActivity(OneiosToolActivity.intent(this)) }
            if (t.canPause && !t.stopping) {
                if (t.pausedByUser) PrebootCards.row(kernel, getString(R.string.oneios_tool_resume), getString(R.string.oneios_tool_resume_line)) { OneiosToolJob.resumeByUser() }
                else PrebootCards.row(kernel, getString(R.string.oneios_tool_pause), getString(R.string.oneios_tool_pause_line), enabled = !t.starting) { OneiosToolJob.pauseByUser() }
            }
            PrebootCards.row(kernel, getString(if (t.stopping) R.string.oneios_tool_stopping else R.string.oneios_tool_stop), enabled = !t.stopping) { OneiosToolJob.cancel() }
            return
        }
        if (mine) {
            t.problem?.let { PrebootCards.row(kernel, getString(R.string.oneios_tool_not_started), it, chevron = true) { startActivity(OneiosToolActivity.intent(this)) } }
            t.plain?.let { m -> PrebootCards.row(kernel, m.title, m.line, chevron = true) { startActivity(OneiosToolActivity.intent(this)) } }
            t.builtKc?.let { kc ->
                PrebootCards.row(kernel, getString(R.string.oneios_kernel_activate), getString(R.string.oneios_kernel_activate_line), chevron = true, enabled = idle) {
                    OneiosToolJob.kernelActivating()
                    OneiosJob.activateKernel(this, kc)
                }
            }
        }
        PrebootCards.row(
            kernel, getString(R.string.oneios_kernel_update),
            getString(if (st.kb.kernelcacheSha256 != null) R.string.oneios_kernel_update_cached_line else R.string.oneios_kernel_update_line),
            chevron = true, enabled = idle && OneiosToolJob.canStart(),
        ) { OneiosToolActivity.start(this, OneiosToolJob.Flow.KERNEL) }
    }

    private fun kernelTitle(st: OneiosStatus): String =
        st.runtimeKernel?.let { getString(R.string.oneios_kernel_title, it.buildId) } ?: getString(R.string.oneios_kernel_none)

    private fun kernelDetails(st: OneiosStatus): String {
        val runtime = st.runtimeKernel?.let { "${it.buildId} (${it.xnu})" } ?: getString(R.string.oneios_kernel_kc_none)
        val image = st.imageKernel?.let {
            it.buildId + " (" + it.kcSha256.take(12) + "…)" + if (it.hasFallback) " · ${getString(R.string.oneios_kernel_kc_fallback)}" else ""
        } ?: getString(R.string.oneios_kernel_kc_unknown)
        val inputs = (if (st.kb.inputs == 0) getString(R.string.oneios_kernel_inputs_none)
            else getString(R.string.oneios_kernel_inputs, st.kb.inputs)) + " · " +
            getString(if (st.kb.kernelcacheSha256 != null) R.string.oneios_kernel_cache_yes else R.string.oneios_kernel_cache_no)
        return getString(R.string.oneios_kernel_details, runtime, image, inputs)
    }

    private fun tileValue(version: String?, check: OneiosFlow.Check, placeholder: Boolean): String = when {
        version == null -> getString(R.string.oneios_tile_none)
        placeholder -> getString(R.string.oneios_tile_value, version, getString(R.string.oneios_tile_placeholder))
        else -> getString(
            R.string.oneios_tile_value, version,
            getString(
                when (check) {
                    OneiosFlow.Check.PASSED -> R.string.oneios_tile_checked
                    OneiosFlow.Check.FAILED -> R.string.oneios_tile_check_failed
                    else -> R.string.oneios_tile_not_checked
                },
            ),
        )
    }

    private fun level(check: OneiosFlow.Check): Level = when (check) {
        OneiosFlow.Check.PASSED -> Level.OK
        OneiosFlow.Check.FAILED -> Level.BLOCK
        OneiosFlow.Check.NOT_STAGED -> Level.WARN
        OneiosFlow.Check.NOT_CHECKED -> Level.INFO
    }

    private fun toolbar(): Toolbar =
        findViewById<dev.oneuiproject.oneui.layout.ToolbarLayout>(R.id.environment_toolbar_layout)?.toolbar
            ?: findViewById(R.id.environment_toolbar)

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    companion object {
        fun intent(ctx: android.content.Context): Intent = Intent(ctx, OneiosActivity::class.java)
    }
}
