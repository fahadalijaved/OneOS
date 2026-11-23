package com.fahadali.oneos.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosCheck
import com.fahadali.oneos.core.model.OneiosCheckOutcome
import com.fahadali.oneos.core.model.OneiosChecks
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OneiosChecksJob
import com.fahadali.oneos.session.OneiosJob
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * Hardware checks of the iOS 27 (OneiOS) system (docs/oneios.md): one row per
 * check, each a phone tool of the staged OneiOS runtime that root runs beside
 * One UI ([OneiosChecksJob]). A row shows pass, fail or skipped and the tool's
 * line, has a Run button of its own, and opens the full output, which can be
 * copied and shared. Run all runs the ordinary checks in order; Share all is
 * every log in one text. Without a staged runtime the screen offers the
 * download first. Nothing here starts a session.
 */
class OneiosChecksActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null
    private var unsubscribeSetup: (() -> Unit)? = null
    private var setupWasBusy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_checks)
        val footer = findViewById<View>(R.id.oneios_checks_footer)
        val toolbar = findViewById<ToolbarLayout>(R.id.oneios_checks_toolbar)
        toolbar.setTitle(getString(R.string.oneios_checks))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        applyEdgeToEdgeInsets(toolbar) { bottom -> footer.updateBottomMarginForNavigationBar(0, bottom) }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0; fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
        val scroll = findViewById<NestedScrollView>(R.id.oneios_checks_scroll)
        footer.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            val navigation = (footer.layoutParams as ViewGroup.MarginLayoutParams).bottomMargin
            scroll.setPadding(0, 0, 0, footer.height + navigation + dp(24))
        }
        findViewById<Button>(R.id.oneios_checks_run_all).setOnClickListener { confirmRunAll() }
    }

    override fun onStart() {
        super.onStart()
        unsubscribe = OneiosChecksJob.observe { render() }
        // The download of the runtime is OneiosJob's; when it ends, read what is staged again.
        unsubscribeSetup = OneiosJob.observe { s ->
            if (setupWasBusy && !s.busy) OneiosChecksJob.refresh(this)
            setupWasBusy = s.busy
            render()
        }
    }

    override fun onResume() {
        super.onResume()
        if (!OneiosChecksJob.state.busy && !OneiosJob.state.busy) OneiosChecksJob.refresh(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribeSetup?.invoke()
        unsubscribe = null
        unsubscribeSetup = null
        super.onStop()
    }

    private fun render() {
        val s = OneiosChecksJob.state
        val setup = OneiosJob.state
        val list = findViewById<LinearLayout>(R.id.oneios_checks_list)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_checks_scroll)
        val at = scroll.scrollY
        list.removeAllViews()
        val runtime = s.status?.runtime
        val idle = !s.busy && !setup.busy
        val canRun = idle && runtime != null && s.status?.sessionOpen != true

        PrebootCards.row(PrebootCards.section(list, gap = false), getString(R.string.oneios_checks), getString(R.string.oneios_checks_about))

        val top = PrebootCards.section(list, getString(R.string.oneios_runtime))
        when {
            runtime != null -> PrebootCards.row(top, getString(R.string.oneios_checks_runtime, runtime.version))
            s.status == null && s.problem == null -> PrebootCards.row(top, getString(R.string.oneios_checking))
            else -> {
                // No runtime: the tools come with it, so the download is offered first.
                PrebootCards.row(top, getString(R.string.oneios_checks_no_runtime), getString(R.string.oneios_checks_no_runtime_line))
                PrebootCards.row(top, getString(R.string.oneios_runtime_download), getString(R.string.oneios_checks_download_line), chevron = true, enabled = idle) {
                    OneiosJob.downloadRuntime(this, null)
                }
            }
        }
        if (setup.busy && setup.message != null) {
            val line = if (setup.total > 0) "${Units.bytes(setup.done)} of ${Units.bytes(setup.total)}" else null
            PrebootCards.row(top, setup.message, line)
        } else if (setup.failed && setup.message != null && runtime == null) {
            PrebootCards.row(top, setup.message)
        }
        if (s.status?.sessionOpen == true) PrebootCards.row(top, getString(R.string.oneios_checks_session_open))
        s.problem?.let { PrebootCards.row(top, getString(R.string.oneios_checks_problem), it) }

        if (s.running != null) {
            val card = PrebootCards.section(list)
            val running = OneiosChecks.byId(s.running)
            val name = running?.title.orEmpty()
            // How long it has run of its limit, and the tool's latest line as root passes it on (once a second).
            val seconds = if (s.startedAt > 0) ((android.os.SystemClock.elapsedRealtime() - s.startedAt) / 1000).toInt() else 0
            PrebootCards.row(card, getString(R.string.oneios_checks_running, name),
                listOfNotNull(
                    running?.let { getString(R.string.oneios_checks_elapsed, seconds, it.limitSeconds) },
                    s.liveLine,
                    if (s.queued.isEmpty()) null else getString(R.string.oneios_checks_queued, s.queued.size),
                ).joinToString("\n"))
            PrebootCards.row(card, getString(R.string.oneios_stop), getString(R.string.oneios_checks_stop_line)) { OneiosChecksJob.cancel() }
        }

        val checks = PrebootCards.section(list, getString(R.string.oneios_checks_list))
        OneiosChecks.RUN_ALL.forEach { checkRow(checks, it, s, canRun) }
        val more = PrebootCards.section(list, getString(R.string.oneios_checks_experimental))
        OneiosChecks.ALL.filter { it.experimental }.forEach { checkRow(more, it, s, canRun) }
        // oneios-tool's CPU check (`phone cpu` on the phone itself, read only): its own screen, its own verdict.
        PrebootCards.row(PrebootCards.section(list, getString(R.string.oneios_tool_from_tool)), getString(R.string.oneios_tool_cpu),
            getString(R.string.oneios_tool_cpu_line), chevron = true, enabled = canRun || com.fahadali.oneos.session.OneiosToolJob.state.busy) {
            OneiosToolActivity.start(this, com.fahadali.oneos.session.OneiosToolJob.Flow.CPU)
        }

        val share = PrebootCards.section(list)
        PrebootCards.row(share, getString(R.string.oneios_checks_share_all), getString(R.string.oneios_checks_share_all_line), chevron = true,
            enabled = s.rows.isNotEmpty()) { share(getString(R.string.oneios_checks), OneiosChecksJob.report(header())) }
        PrebootCards.row(share, getString(R.string.oneios_checks_copy_all), enabled = s.rows.isNotEmpty()) { copy(OneiosChecksJob.report(header())) }

        findViewById<Button>(R.id.oneios_checks_run_all).isEnabled = canRun
        scroll.post { scroll.scrollTo(0, at) }
    }

    /** A check's row: its name, the verdict and the tool's line; the row opens the details, the button runs it. */
    private fun checkRow(card: LinearLayout, check: OneiosCheck, s: OneiosChecksJob.State, canRun: Boolean) {
        val row = s.rows[check.id]
        val result = row?.result
        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(24), dp(12), dp(16), dp(12))
            minimumHeight = dp(73)
            val out = android.util.TypedValue()
            theme.resolveAttribute(android.R.attr.selectableItemBackground, out, true)
            setBackgroundResource(out.resourceId)
            isClickable = true
            setOnClickListener { details(check) }
        }
        val text = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        text.addView(TextView(this).apply {
            this.text = check.title
            textSize = 18f
            setTextColor(getColor(R.color.oneios_check_title))
        })
        val (word, colour) = when {
            s.running == check.id -> getString(R.string.oneios_checks_state_running) to R.color.preboot_primary
            check.id in s.queued -> getString(R.string.oneios_checks_state_queued) to R.color.preboot_secondary
            result == null -> getString(R.string.oneios_checks_state_none) to R.color.preboot_secondary
            result.outcome == OneiosCheckOutcome.PASS -> getString(R.string.oneios_checks_state_pass) to R.color.oneios_check_pass
            result.outcome == OneiosCheckOutcome.FAIL -> getString(R.string.oneios_checks_state_fail) to R.color.oneios_check_fail
            else -> getString(R.string.oneios_checks_state_skipped) to R.color.oneios_check_skipped
        }
        text.addView(TextView(this).apply {
            this.text = word
            textSize = 14f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(getColor(colour))
        })
        (result?.line ?: check.notice)?.let { summary ->
            text.addView(TextView(this).apply {
                this.text = summary
                textSize = 14f
                maxLines = 4
                ellipsize = android.text.TextUtils.TruncateAt.END
                setTextColor(getColor(R.color.preboot_secondary))
            })
        }
        line.addView(text, LinearLayout.LayoutParams(0, -2, 1f))
        line.addView(Button(this).apply {
            this.text = getString(R.string.oneios_checks_run)
            contentDescription = getString(R.string.oneios_checks_run) + " " + check.title
            isEnabled = canRun
            setOnClickListener { confirmRun(check) }
        }, LinearLayout.LayoutParams(-2, -2).apply { marginStart = dp(8) })
        if (card.childCount > 0) {
            card.addView(View(this).apply { setBackgroundColor(getColor(R.color.oneios_check_divider)) },
                LinearLayout.LayoutParams(-1, 1).apply { marginStart = dp(24); marginEnd = dp(24) })
        }
        card.addView(line, LinearLayout.LayoutParams(-1, -2))
    }

    // --- What has to hold before a check runs ---------------------------------------

    private fun bluetoothOn(): Boolean = runCatching {
        getSystemService(android.bluetooth.BluetoothManager::class.java)?.adapter?.isEnabled == true
    }.getOrDefault(false)

    private fun adaptiveBrightnessOn(): Boolean = runCatching {
        Settings.System.getInt(contentResolver, Settings.System.SCREEN_BRIGHTNESS_MODE) == Settings.System.SCREEN_BRIGHTNESS_MODE_AUTOMATIC
    }.getOrDefault(false)

    /** Why [check] cannot run as the phone is now; null when it can. */
    private fun unmet(check: OneiosCheck): String? = when {
        check.id == OneiosChecks.BLUETOOTH && bluetoothOn() -> getString(R.string.oneios_checks_bt_on)
        check.id == OneiosChecks.LEVELS && adaptiveBrightnessOn() -> getString(R.string.oneios_checks_adaptive_on)
        else -> null
    }

    private fun confirmRun(check: OneiosCheck) {
        if (!OneiosChecksJob.canStart()) return
        val unmet = unmet(check)
        if (unmet != null) {
            AlertDialog.Builder(this).setTitle(check.title).setMessage(unmet).setPositiveButton(android.R.string.ok, null).show()
            return
        }
        if (check.notice == null) {
            OneiosChecksJob.run(this, listOf(check.id))
            return
        }
        AlertDialog.Builder(this).setTitle(check.title).setMessage(check.notice)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_checks_run) { _, _ -> OneiosChecksJob.run(this, listOf(check.id)) }.show()
    }

    private fun confirmRunAll() {
        if (!OneiosChecksJob.canStart()) return
        val skip = OneiosChecks.RUN_ALL.mapNotNull { c -> unmet(c)?.let { c.id to it } }.toMap()
        val text = buildString {
            append(getString(R.string.oneios_checks_run_all_intro)).append("\n")
            for (c in OneiosChecks.RUN_ALL) c.notice?.let { append("\n• ").append(c.title).append(": ").append(it) }
            if (skip.isNotEmpty()) {
                append("\n\n").append(getString(R.string.oneios_checks_will_skip))
                for ((id, why) in skip) append("\n• ").append(OneiosChecks.byId(id)?.title).append(": ").append(why)
            }
        }
        AlertDialog.Builder(this).setTitle(R.string.oneios_checks_run_all).setMessage(text)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_checks_run_all) { _, _ ->
                // Read again: the owner may have changed a setting while the dialog was open.
                val now = OneiosChecks.RUN_ALL.mapNotNull { c -> unmet(c)?.let { c.id to it } }.toMap()
                OneiosChecksJob.run(this, OneiosChecks.RUN_ALL.map { it.id }, now)
            }.show()
    }

    // --- Details, copy, share ----------------------------------------------------------

    private fun details(check: OneiosCheck) {
        val row = OneiosChecksJob.state.rows[check.id]
        val log = OneiosChecks.log(check, row?.result, row?.output.orEmpty())
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(8), dp(24), 0)
        }
        if (row == null) {
            box.addView(TextView(this).apply {
                text = listOfNotNull(getString(R.string.oneios_checks_not_run_yet), check.notice).joinToString("\n\n")
                textSize = 15f
            })
        }
        row?.picture?.takeIf { it.isFile }?.let { file ->
            runCatching { BitmapFactory.decodeFile(file.path) }.getOrNull()?.let { bitmap ->
                box.addView(ImageView(this).apply {
                    setImageBitmap(bitmap)
                    adjustViewBounds = true
                    contentDescription = getString(R.string.oneios_checks_picture)
                }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
            }
        }
        box.addView(TextView(this).apply {
            text = log
            textSize = 12f
            typeface = Typeface.MONOSPACE
            setTextIsSelectable(true)
        })
        val dialog = AlertDialog.Builder(this).setTitle(check.title)
            .setView(ScrollView(this).apply { addView(box) })
            .setNegativeButton(R.string.oneios_checks_close, null)
            .setNeutralButton(R.string.oneios_checks_copy) { _, _ -> copy(log) }
            .setPositiveButton(R.string.oneios_checks_share) { _, _ -> share(check.title, header().joinToString("\n") + "\n\n" + log) }
            .create()
        dialog.show()
    }

    private fun header(): List<String> = listOf(
        "OneOS ${BuildConfig.VERSION_NAME}, OneiOS runtime ${OneiosChecksJob.state.status?.runtime?.version ?: "none"}",
        "${Build.MODEL} (${Build.DEVICE}), Android ${Build.VERSION.RELEASE}, ${Build.DISPLAY}",
        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.US).format(java.util.Date()),
    )

    private fun copy(text: String) {
        getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText(getString(R.string.oneios_checks), text.take(SHARE_MAX)))
        Toast.makeText(this, R.string.oneios_checks_copied, Toast.LENGTH_SHORT).show()
    }

    private fun share(subject: String, text: String) {
        val send = Intent(Intent.ACTION_SEND).setType("text/plain")
            .putExtra(Intent.EXTRA_SUBJECT, "OneiOS: $subject")
            .putExtra(Intent.EXTRA_TEXT, text.take(SHARE_MAX))
        try {
            startActivity(Intent.createChooser(send, getString(R.string.oneios_checks_share)))
        } catch (_: android.content.ActivityNotFoundException) {
            Toast.makeText(this, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density + .5f).toInt()

    companion object {
        // An intent's extras travel in one binder transaction (1 MiB for the whole process).
        private const val SHARE_MAX = 200_000

        fun intent(ctx: Context): Intent = Intent(ctx, OneiosChecksActivity::class.java)
    }
}
