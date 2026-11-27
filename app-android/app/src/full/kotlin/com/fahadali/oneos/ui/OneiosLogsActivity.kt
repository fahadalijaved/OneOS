package com.fahadali.oneos.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.Toast
import androidx.core.content.FileProvider
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosBugReport
import com.fahadali.oneos.core.model.OneiosLogFile
import com.fahadali.oneos.core.model.OneiosLogs
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosLogsJob
import dev.oneuiproject.oneui.layout.ToolbarLayout
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Session logs of the iOS 27 (OneiOS) system (docs/oneios.md): this session's
 * or the last one's xnuhost log and the five before it, each with the time of
 * its last line, its size and how the session ended, and the switch's, the
 * return's and the helpers' logs. A row opens the log ([OneiosLogActivity]);
 * Share all makes one zip of every log. Root only reads ([OneiosLogsJob]).
 */
class OneiosLogsActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_logs)
        val toolbar = findViewById<ToolbarLayout>(R.id.oneios_logs_toolbar)
        toolbar.setTitle(getString(R.string.oneios_logs))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_logs_scroll)
        applyEdgeToEdgeInsets(toolbar) { bottom -> scroll.setPadding(0, 0, 0, bottom) }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0; fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
    }

    override fun onStart() {
        super.onStart()
        unsubscribe = OneiosLogsJob.observe { render() }
    }

    override fun onResume() {
        super.onResume()
        OneiosLogsJob.refresh(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun render() {
        val s = OneiosLogsJob.state
        s.shared?.let { shared ->
            OneiosLogsJob.taken()
            share(this, shared)
        }
        s.shareProblem?.let {
            OneiosLogsJob.taken()
            Toast.makeText(this, getString(R.string.oneios_logs_share_failed, it), Toast.LENGTH_LONG).show()
        }
        val list = findViewById<LinearLayout>(R.id.oneios_logs_list)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_logs_scroll)
        val at = scroll.scrollY
        list.removeAllViews()
        val idle = !s.listing && s.exporting == null
        PrebootCards.row(PrebootCards.section(list, gap = false), getString(R.string.oneios_logs), getString(R.string.oneios_logs_about))

        // Quick sharing right at the top: one tap for the full bug-report zip (including iOS's last-boot log) or GitHub issue text.
        val found = s.list
        val quick = PrebootCards.section(list)
        if (s.exporting != null) {
            PrebootCards.row(quick, s.exporting)
            PrebootCards.row(quick, getString(R.string.oneios_logs_stop_share)) { OneiosLogsJob.stopShare() }
        } else {
            val hasLogs = found?.files?.isNotEmpty() == true
            PrebootCards.row(
                quick,
                getString(R.string.oneios_logs_share_bug),
                getString(R.string.oneios_logs_share_bug_line),
                chevron = true,
                enabled = idle && hasLogs,
            ) { OneiosLogsJob.shareBugReport(this, header(this), versions(this)) }
            PrebootCards.row(
                quick,
                getString(R.string.oneios_logs_copy_issue),
                getString(R.string.oneios_logs_copy_issue_line),
                chevron = true,
                enabled = idle && !s.noStage,
            ) { copyIssueText(this) }
        }

        val sessions = PrebootCards.section(list, getString(R.string.oneios_logs_sessions))
        when {
            found == null && s.problem == null -> PrebootCards.row(sessions, getString(R.string.oneios_checking))
            s.noStage -> PrebootCards.row(sessions, getString(R.string.oneios_logs_none), getString(R.string.oneios_logs_no_stage))
            found != null && found.sessions.isEmpty() -> PrebootCards.row(sessions, getString(R.string.oneios_logs_none), getString(R.string.oneios_logs_none_line))
        }
        found?.sessions?.forEach { f ->
            val title = when {
                f.id != OneiosLogs.SESSION -> getString(R.string.oneios_logs_earlier)
                found.sessionOpen -> getString(R.string.oneios_logs_current)
                else -> getString(R.string.oneios_logs_last)
            }
            logRow(sessions, f, title, OneiosLogs.endLine(f.tail))
        }
        s.problem?.let { PrebootCards.row(sessions, getString(R.string.oneios_checks_problem), it) }

        if (found != null && found.others.isNotEmpty()) {
            val others = PrebootCards.section(list, getString(R.string.oneios_logs_others))
            for (f in found.others) {
                val title = getString(
                    when (f.id) {
                        "switch" -> R.string.oneios_logs_switch
                        "return" -> R.string.oneios_logs_return
                        "display" -> R.string.oneios_logs_display
                        else -> R.string.oneios_logs_feeder
                    },
                )
                logRow(others, f, title, f.tail.lastOrNull { it.isNotBlank() }?.take(120).orEmpty())
            }
        }

        // oneios-tool reads them too, on the phone (`phone log --analyze`, `ioslog`): its own screen.
        if (found != null && !s.noStage) {
            val tool = PrebootCards.section(list, getString(R.string.oneios_tool_from_tool))
            val busyTool = com.fahadali.oneos.session.OneiosToolJob.state.busy
            PrebootCards.row(tool, getString(R.string.oneios_tool_log), getString(R.string.oneios_tool_log_line), chevron = true, enabled = idle || busyTool) {
                OneiosToolActivity.start(this, com.fahadali.oneos.session.OneiosToolJob.Flow.LOG)
            }
            PrebootCards.row(tool, getString(R.string.oneios_tool_ioslog_boots), getString(R.string.oneios_tool_ioslog_line), chevron = true, enabled = idle || busyTool) {
                OneiosToolActivity.start(this, com.fahadali.oneos.session.OneiosToolJob.Flow.IOSLOG_BOOTS)
            }
            PrebootCards.row(tool, getString(R.string.oneios_tool_ioslog_show), getString(R.string.oneios_tool_ioslog_line), chevron = true, enabled = idle || busyTool) {
                OneiosToolActivity.start(this, com.fahadali.oneos.session.OneiosToolJob.Flow.IOSLOG_SHOW)
            }
        }

        val actions = PrebootCards.section(list)
        PrebootCards.row(actions, getString(R.string.oneios_logs_refresh), enabled = idle) { OneiosLogsJob.refresh(this) }
        scroll.post { scroll.scrollTo(0, at) }
    }

    private fun logRow(card: LinearLayout, f: OneiosLogFile, title: String, end: String) {
        val line = getString(R.string.oneios_logs_row, time(f.modified), Units.bytes(f.bytes), end.ifEmpty { OneiosLogs.fileName(f.id) })
        PrebootCards.row(card, title, line, chevron = true) { startActivity(OneiosLogActivity.intent(this, f.id, title)) }
    }

    companion object {
        fun intent(ctx: Context): Intent = Intent(ctx, OneiosLogsActivity::class.java)

        private val TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

        /** The time of a log's last line, in the phone's time. */
        fun time(epochSeconds: Long): String = TIME.format(Instant.ofEpochSecond(epochSeconds).atZone(ZoneId.systemDefault()))

        fun header(ctx: Context): List<String> = listOf(
            "OneOS ${BuildConfig.VERSION_NAME}, iOS 27 (OneiOS) session logs",
            "${Build.MODEL} (${Build.DEVICE}), Android ${Build.VERSION.RELEASE}, ${Build.DISPLAY}",
            TIME.format(java.time.ZonedDateTime.now()),
        )

        fun versions(ctx: Context): OneiosBugReport.Versions {
            val st = OneiosJob.state.status
            val build = st?.image?.build?.let { com.fahadali.oneos.core.model.OneiosImageChoice.kernelBuildOf(it) }
            val runtimeKernel = if (st != null && build != null) OneiosJob.stagedKernel(ctx, st, build)?.buildId ?: st.runtimeKernel?.buildId else st?.runtimeKernel?.buildId
            return OneiosBugReport.Versions(
                appName = BuildConfig.VERSION_NAME,
                appCode = BuildConfig.VERSION_CODE,
                phoneModel = Build.MODEL.orEmpty(),
                phoneDevice = Build.DEVICE.orEmpty(),
                androidRelease = Build.VERSION.RELEASE.orEmpty(),
                androidBuild = Build.DISPLAY.orEmpty(),
                runtimeVersion = st?.runtime?.version,
                imageVersion = st?.image?.version,
                imageBuild = st?.image?.build,
                imageKernel = st?.imageKernel?.buildId,
                runtimeKernel = runtimeKernel,
            )
        }

        fun copyIssueText(ctx: Context) {
            OneiosLogsJob.buildIssueText(ctx, versions(ctx)) { res ->
                res.onSuccess { text ->
                    val cm = ctx.getSystemService(ClipboardManager::class.java)
                    cm?.setPrimaryClip(ClipData.newPlainText("OneiOS bug report", text))
                    Toast.makeText(ctx, R.string.oneios_logs_issue_copied, Toast.LENGTH_LONG).show()
                }.onFailure { err ->
                    Toast.makeText(ctx, ctx.getString(R.string.oneios_logs_share_failed, err.message ?: err.javaClass.simpleName), Toast.LENGTH_LONG).show()
                }
            }
        }

        /** Hands a file under files/logs to the share sheet, readable by the app that takes it and no other. */
        fun share(ctx: Context, shared: OneiosLogsJob.Shared) {
            val uri = FileProvider.getUriForFile(ctx, "${BuildConfig.APPLICATION_ID}.findings", shared.file)
            val send = Intent(Intent.ACTION_SEND).setType(shared.mime)
                .putExtra(Intent.EXTRA_STREAM, uri)
                .putExtra(Intent.EXTRA_SUBJECT, "OneiOS: ${shared.subject}")
                .putExtra(Intent.EXTRA_TEXT, shared.text.take(20_000))
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            send.clipData = ClipData.newRawUri(shared.file.name, uri)
            try {
                ctx.startActivity(Intent.createChooser(send, ctx.getString(R.string.oneios_checks_share)))
            } catch (_: android.content.ActivityNotFoundException) {
                Toast.makeText(ctx, R.string.fix_no_app, Toast.LENGTH_LONG).show()
            }
        }
    }
}
