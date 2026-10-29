package com.fahadali.oneos.ui

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.SpannableString
import android.text.Spanned
import android.text.style.TypefaceSpan
import android.view.View
import android.widget.Button
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContract
import androidx.appcompat.app.AlertDialog
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.preference.Preference
import androidx.preference.PreferenceCategory
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.FindingsBuilder
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.probe.ProbeSession
import com.fahadali.oneos.report.ReportSender
import java.io.File
import java.util.concurrent.Executors

/**
 * Findings preview: what will be shared (summary.txt, every file, what was
 * removed), then Share (share sheet through the FileProvider) or Save to
 * Downloads (the system file picker; no storage permission). With
 * [EXTRA_ZIP] it shows a session log bundle (cache/logs/, the full edition's
 * Last session) the same way.
 */
class FindingsActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(if (isLogs) R.string.logs_title else R.string.findings_title)

    /** A log bundle from cache/logs/ ([EXTRA_ZIP]); nothing else can be opened this way. */
    private val logsZip: File? by lazy {
        intent.getStringExtra(EXTRA_ZIP)?.let(::File)?.takeIf { f ->
            f.isFile && f.name.endsWith(".zip") && f.parentFile?.canonicalPath == logsDir(this).canonicalPath
        }
    }

    val isLogs: Boolean get() = logsZip != null

    fun bundleZip(): File? = logsZip ?: if (intent.hasExtra(EXTRA_ZIP)) null else ProbeSession.latestZip(this)

    companion object {
        const val EXTRA_ZIP = "com.fahadali.oneos.extra.ZIP"

        /**
         * cache/logs/: the session log bundles (the full edition's Last session
         * writes them, LogJob); the only folder besides the findings this preview opens.
         */
        // Not the cache: Android may clear it when storage is low (likely right
        // after a 10-22 GB setup), and the logs are kept until the user shares them.
        fun logsDir(ctx: Context) = File(ctx.applicationContext.filesDir, "logs")
    }
    override val layoutRes: Int get() = R.layout.activity_findings

    override fun createFragment(): Fragment = FindingsFragment()

    private lateinit var saveLauncher: ActivityResultLauncher<String>
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        saveLauncher = registerForActivityResult(CreateZipDocument()) { uri -> if (uri != null) saveTo(uri) }
        super.onCreate(savedInstanceState)
        if (isFinishing) return
        val zip = bundleZip()
        val footer = findViewById<View>(R.id.findings_footer)
        if (zip == null) {
            footer.visibility = View.GONE
            return
        }
        setExpandedSubtitle(zip.name)
        findViewById<Button>(R.id.findings_share).setOnClickListener { share(zip) }
        // 0.4.29: straight to the team when this build has the report service; Share and Save stay.
        if (ReportSender.available) {
            findViewById<Button>(R.id.findings_send).apply {
                visibility = View.VISIBLE
                setOnClickListener { startActivity(SendReportActivity.intent(this@FindingsActivity, zip)) }
            }
        }
        findViewById<Button>(R.id.findings_save).setOnClickListener { saveLauncher.launch(zip.name) }
    }

    override fun onDestroy() {
        io.shutdown()
        super.onDestroy()
    }

    private fun share(zip: File) {
        val uri = FileProvider.getUriForFile(this, "${BuildConfig.APPLICATION_ID}.findings", zip)
        val send = Intent(Intent.ACTION_SEND)
            .setType("application/zip")
            .putExtra(Intent.EXTRA_STREAM, uri)
            .putExtra(Intent.EXTRA_SUBJECT, "${getString(if (isLogs) R.string.logs_share_subject else R.string.findings_share_subject)}: ${zip.name}")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        send.clipData = ClipData.newRawUri(zip.name, uri)
        try {
            startActivity(Intent.createChooser(send, getString(if (isLogs) R.string.logs_share_chooser else R.string.findings_share_chooser)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.findings_no_share_app, Toast.LENGTH_SHORT).show()
        }
    }

    private fun saveTo(uri: Uri) {
        val zip = bundleZip() ?: return
        val app = applicationContext
        io.execute {
            val ok = runCatching {
                app.contentResolver.openOutputStream(uri, "w")!!.use { out -> zip.inputStream().use { it.copyTo(out) } }
            }.isSuccess
            main.post {
                Toast.makeText(app, if (ok) R.string.findings_saved else R.string.findings_save_failed, Toast.LENGTH_SHORT).show()
            }
        }
    }

    /** ACTION_CREATE_DOCUMENT for a zip: the user picks where (Downloads by default); no permission needed. */
    private class CreateZipDocument : ActivityResultContract<String, Uri?>() {
        override fun createIntent(context: Context, input: String): Intent =
            Intent(Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/zip")
                .putExtra(Intent.EXTRA_TITLE, input)

        override fun parseResult(resultCode: Int, intent: Intent?): Uri? =
            if (resultCode == Activity.RESULT_OK) intent?.data else null
    }
}

class FindingsFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        val ctx = preferenceManager.context
        preferenceScreen = preferenceManager.createPreferenceScreen(ctx)
        val host = requireActivity() as FindingsActivity
        val logs = host.isLogs
        val zip = host.bundleZip()
        if (zip == null) {
            category(getString(R.string.findings_cat_bundle)).row(getString(R.string.findings_none), null)
            return
        }
        val folder = ProbeSession.folderOf(zip)

        val bundle = category(getString(if (logs) R.string.logs_cat_bundle else R.string.findings_cat_bundle))
        bundle.row(
            getString(if (logs) R.string.logs_send_title else R.string.findings_send_title),
            getString(if (logs) R.string.logs_send_summary else R.string.findings_send_summary),
        )
        bundle.row(zip.name, Units.bytes(zip.length()))

        val summaryFile = File(folder, FindingsBuilder.SUMMARY)
        if (summaryFile.isFile) {
            val cat = category(getString(R.string.findings_cat_summary))
            val p = Preference(ctx)
            p.layoutResource = R.layout.pref_text_block
            p.summary = summaryFile.readText()
            p.isSelectable = false
            cat.addPreference(p)
        }

        val redaction = File(folder, FindingsBuilder.REDACTION)
        if (redaction.isFile) {
            val text = redaction.readText()
            val counts = text.lineSequence().dropWhile { !it.startsWith("Removed values") }.drop(1)
                .takeWhile { it.startsWith("  ") }.map { it.trim().replace(Regex("\\s+"), " ") }.toList()
            category(getString(R.string.findings_cat_privacy)).row(
                text.lineSequence().firstOrNull { it.startsWith("Removed values") }.orEmpty(),
                counts.joinToString("\n").ifEmpty { null },
                onClick = { showFile(FindingsBuilder.REDACTION, redaction) },
            )
        }

        val files = folder.walkTopDown().filter { it.isFile }.map { it.relativeTo(folder).invariantSeparatorsPath }.sorted().toList()
        val cat = category("${getString(R.string.findings_cat_files)} (${files.size})")
        for (rel in files) {
            val f = File(folder, rel)
            val binary = FindingsBuilder.isBinary(rel)
            cat.row(
                rel,
                Units.bytes(f.length()) + if (binary) " · ${getString(R.string.findings_binary)}" else "",
                onClick = if (binary) null else ({ showFile(rel, f) }),
            )
        }

        category("").row(
            getString(if (logs) R.string.logs_delete_title else R.string.findings_delete_title),
            getString(if (logs) R.string.logs_delete_summary else R.string.findings_delete_summary),
            onClick = { confirmDelete(if (logs) zip else null) },
        )
    }

    /** Shows a text file as it will be shared (first 512 kB: every text file a probe writes today). */
    private fun showFile(rel: String, f: File) {
        val bytes = f.inputStream().use { input ->
            val buf = ByteArray(minOf(f.length(), MAX_VIEW.toLong()).toInt())
            var n = 0
            while (n < buf.size) {
                val r = input.read(buf, n, buf.size - n)
                if (r < 0) break
                n += r
            }
            buf.copyOf(n)
        }
        var text = bytes.toString(Charsets.ISO_8859_1)
        if (f.length() > MAX_VIEW) text += "\n… (${Units.bytes(f.length())} in all)"
        val msg = SpannableString(text)
        msg.setSpan(TypefaceSpan("monospace"), 0, msg.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        AlertDialog.Builder(requireContext())
            .setTitle(rel)
            .setMessage(msg)
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }

    /** [logsZip]: a session log bundle (its zip and folder); null: the probe findings. */
    private fun confirmDelete(logsZip: File?) {
        AlertDialog.Builder(requireContext())
            .setTitle(if (logsZip != null) R.string.logs_delete_confirm else R.string.findings_delete_confirm)
            .setMessage(if (logsZip != null) R.string.logs_delete_summary else R.string.findings_delete_summary)
            .setPositiveButton(R.string.delete) { _, _ ->
                if (logsZip != null) {
                    ProbeSession.folderOf(logsZip).deleteRecursively()
                    logsZip.delete()
                } else {
                    ProbeSession.deleteFindings(requireContext())
                }
                activity?.finish()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun category(title: String): PreferenceCategory {
        val c = PreferenceCategory(preferenceManager.context)
        c.title = title
        c.isIconSpaceReserved = false
        preferenceScreen.addPreference(c)
        return c
    }

    private fun PreferenceCategory.row(title: CharSequence, summary: CharSequence?, onClick: (() -> Unit)? = null): Preference {
        val p = Preference(context)
        p.title = title
        p.summary = summary
        p.isIconSpaceReserved = false
        if (onClick == null) {
            p.isSelectable = false
        } else {
            p.setOnPreferenceClickListener { onClick(); true }
        }
        addPreference(p)
        return p
    }

    private companion object {
        const val MAX_VIEW = 512 * 1024
    }
}
