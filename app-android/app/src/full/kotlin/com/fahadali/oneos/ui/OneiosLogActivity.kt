package com.fahadali.oneos.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Typeface
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosLogFilter
import com.fahadali.oneos.core.model.OneiosLogs
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OneiosLogsJob
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * One session log of the iOS 27 (OneiOS) system (docs/oneios.md, "Session
 * logs"). The end of the log is read and shown first; earlier chunks follow by
 * themselves up to 4 MiB, and "Load earlier lines" reads more. Above the lines:
 * for an xnuhost log its summary (how far the boot got, the kernel panic, the
 * processes that died, how the session ended; a tap shows all of it), a search
 * field and the chips E, !!, panic and guest. Copy takes the lines shown;
 * Share takes the whole log as a file. A long press copies one line.
 */
class OneiosLogActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null
    private lateinit var id: String
    private val chosen = HashSet<OneiosLogFilter>()
    private var query = ""
    private var summaryOpen = false

    /** What the list shows, and what it was made from. */
    private var shown: List<String> = emptyList()
    private var shownOf: List<String>? = null
    private var shownKey = ""
    private var atEnd = true
    private val adapter = Lines()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        id = intent.getStringExtra(EXTRA_ID).orEmpty()
        if (!OneiosLogs.validId(id)) {
            finish()
            return
        }
        setContentView(R.layout.activity_oneios_log)
        val toolbar = findViewById<ToolbarLayout>(R.id.oneios_log_toolbar)
        toolbar.setTitle(intent.getStringExtra(EXTRA_TITLE) ?: getString(R.string.oneios_logs))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)
        val lines = findViewById<ListView>(R.id.oneios_log_lines)
        applyEdgeToEdgeInsets(toolbar) { bottom -> lines.setPadding(0, 0, 0, bottom) }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0; fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE

        // "Load earlier lines", above the first line, while there is more of the log to read.
        val earlier = Button(this, null, android.R.attr.borderlessButtonStyle).apply {
            text = getString(R.string.oneios_logs_earlier_lines)
            setOnClickListener { OneiosLogsJob.more(this@OneiosLogActivity) }
        }
        val head = LinearLayout(this).apply { addView(earlier, LinearLayout.LayoutParams(-1, -2)) }
        lines.addHeaderView(head, null, false)
        earlierButton = earlier
        lines.adapter = adapter
        lines.setOnItemLongClickListener { _, _, position, _ ->
            val line = shown.getOrNull(position - lines.headerViewsCount) ?: return@setOnItemLongClickListener false
            getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText(getString(R.string.oneios_logs), line))
            Toast.makeText(this, R.string.oneios_logs_line_copied, Toast.LENGTH_SHORT).show()
            true
        }

        val chips = findViewById<LinearLayout>(R.id.oneios_log_chips)
        for (f in OneiosLogFilter.entries) {
            chips.addView(TextView(this).apply {
                text = f.label
                textSize = 14f
                typeface = Typeface.MONOSPACE
                setTextColor(getColorStateList(R.color.oneios_chip_text))
                setBackgroundResource(R.drawable.oneios_chip)
                setPadding(dp(14), dp(6), dp(14), dp(6))
                isClickable = true
                isFocusable = true
                contentDescription = "Filter: ${f.label}"
                setOnClickListener {
                    if (!chosen.add(f)) chosen.remove(f)
                    isActivated = f in chosen
                    render()
                }
            }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(8) })
        }
        findViewById<EditText>(R.id.oneios_log_search).addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: Editable?) {
                query = s?.toString()?.trim().orEmpty()
                render()
            }
        })
        findViewById<TextView>(R.id.oneios_log_summary).setOnClickListener {
            summaryOpen = !summaryOpen
            render()
        }
        findViewById<Button>(R.id.oneios_log_copy).setOnClickListener { copy() }
        findViewById<Button>(R.id.oneios_log_share).setOnClickListener { OneiosLogsJob.shareOne(this, id, OneiosLogsActivity.header(this)) }
    }

    private var earlierButton: Button? = null

    override fun onStart() {
        super.onStart()
        if (!::id.isInitialized || !OneiosLogs.validId(id)) return
        if (OneiosLogsJob.state.open?.id != id) OneiosLogsJob.open(this, id)
        unsubscribe = OneiosLogsJob.observe { render() }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    override fun onDestroy() {
        if (isFinishing && ::id.isInitialized) OneiosLogsJob.close(id)
        super.onDestroy()
    }

    private fun render() {
        val s = OneiosLogsJob.state
        s.shared?.let { shared ->
            OneiosLogsJob.taken()
            OneiosLogsActivity.share(this, shared)
        }
        s.shareProblem?.let {
            OneiosLogsJob.taken()
            Toast.makeText(this, getString(R.string.oneios_logs_share_failed, it), Toast.LENGTH_LONG).show()
        }
        val o = s.open?.takeIf { it.id == id } ?: return
        val lines = findViewById<ListView>(R.id.oneios_log_lines)

        findViewById<TextView>(R.id.oneios_log_summary).apply {
            val summary = o.summary
            visibility = if (summary == null) View.GONE else View.VISIBLE
            if (summary != null) {
                text = OneiosLogs.summaryLines(summary).joinToString("\n")
                maxLines = if (summaryOpen) 60 else 5
            }
        }

        // The lines shown: made again only when the log, the chips or the search changed.
        val key = chosen.sortedBy { it.ordinal }.joinToString(",") + "|" + query
        if (shownOf !== o.lines || shownKey != key) {
            val first = lines.firstVisiblePosition
            val top = lines.getChildAt(0)?.top ?: 0
            val before = shown.size
            val sameView = shownKey == key && shownOf != null
            shown = if (chosen.isEmpty() && query.isEmpty()) o.lines else o.lines.filter { OneiosLogs.shown(it, chosen, query) }
            shownOf = o.lines
            shownKey = key
            adapter.notifyDataSetChanged()
            when {
                // The first lines of a log, or a new filter: its end.
                atEnd || !sameView -> lines.post { lines.setSelection(adapter.count + lines.headerViewsCount - 1) }
                // Earlier lines arrived above: stay on the line that was at the top.
                else -> lines.setSelectionFromTop(first + (shown.size - before), top)
            }
            if (o.lines.isNotEmpty()) atEnd = false
        }

        val more = !o.complete && o.start >= 0 && o.lines.size < OneiosLogsJob.MAX_SHOWN_LINES
        earlierButton?.apply {
            visibility = if (more) View.VISIBLE else View.GONE
            isEnabled = !o.loading
            text = getString(if (o.loading) R.string.oneios_logs_loading else R.string.oneios_logs_earlier_lines)
        }
        findViewById<TextView>(R.id.oneios_log_status).text = buildString {
            when {
                o.problem != null -> append(o.problem)
                o.start < 0 -> append(getString(R.string.oneios_logs_loading))
                o.complete -> append(getString(R.string.oneios_logs_status_all, o.lines.size, Units.bytes(o.size)))
                else -> append(getString(R.string.oneios_logs_status_part, o.lines.size, Units.bytes(o.size - o.start), Units.bytes(o.size)))
            }
            if (o.problem == null && o.loading && o.start >= 0) append(" · ").append(getString(R.string.oneios_logs_loading))
            if (shown.size != o.lines.size) append(" · ").append(getString(R.string.oneios_logs_status_shown, shown.size, o.lines.size))
            if (shown.isEmpty() && o.lines.isNotEmpty()) append(" · ").append(getString(R.string.oneios_logs_empty))
            s.exporting?.let { append(" · ").append(it) }
        }
        findViewById<Button>(R.id.oneios_log_share).isEnabled = s.exporting == null
        findViewById<Button>(R.id.oneios_log_copy).isEnabled = shown.isNotEmpty()
    }

    /** The lines shown, with the summary first; the clipboard takes the last 200,000 characters. */
    private fun copy() {
        val o = OneiosLogsJob.state.open?.takeIf { it.id == id } ?: return
        val head = o.summary?.let { OneiosLogs.summaryLines(it).joinToString("\n") + "\n\n" }.orEmpty()
        // From the end: as many whole lines as fit.
        var from = shown.size
        var size = head.length
        while (from > 0 && size + shown[from - 1].length + 1 <= COPY_MAX) {
            from--
            size += shown[from].length + 1
        }
        val cut = from > 0
        val body = StringBuilder(size)
        for (i in from until shown.size) body.append(shown[i]).append('\n')
        getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText(getString(R.string.oneios_logs), head + body))
        Toast.makeText(this, if (cut) R.string.oneios_logs_copied_part else R.string.oneios_checks_copied, Toast.LENGTH_SHORT).show()
    }

    private inner class Lines : BaseAdapter() {
        override fun getCount(): Int = shown.size
        override fun getItem(position: Int): String = shown[position]
        override fun getItemId(position: Int): Long = position.toLong()

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val view = (convertView as? TextView) ?: TextView(this@OneiosLogActivity).apply {
                textSize = 11f
                typeface = Typeface.MONOSPACE
                setPadding(dp(12), dp(1), dp(12), dp(1))
            }
            val line = shown[position]
            view.text = line
            view.setTextColor(
                getColor(
                    when (OneiosLogs.source(line)) {
                        OneiosLogs.Source.HOST_ERROR, OneiosLogs.Source.SIGNAL -> R.color.oneios_check_fail
                        OneiosLogs.Source.HOST_INFO, OneiosLogs.Source.HOST_DEBUG -> R.color.preboot_primary
                        OneiosLogs.Source.GUEST -> if (OneiosLogs.matches(line, OneiosLogFilter.PANIC)) R.color.oneios_check_fail else R.color.oneios_check_title
                        OneiosLogs.Source.OTHER -> R.color.preboot_secondary
                    },
                ),
            )
            return view
        }
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density + .5f).toInt()

    companion object {
        private const val EXTRA_ID = "id"
        private const val EXTRA_TITLE = "title"

        // The clipboard's data travels in one binder transaction (1 MiB for the whole process).
        private const val COPY_MAX = 200_000

        fun intent(ctx: Context, id: String, title: String): Intent =
            Intent(ctx, OneiosLogActivity::class.java).putExtra(EXTRA_ID, id).putExtra(EXTRA_TITLE, title)
    }
}
