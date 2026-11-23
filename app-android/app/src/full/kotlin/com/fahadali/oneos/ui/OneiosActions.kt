package com.fahadali.oneos.ui

import android.os.Bundle
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosToolJob

/**
 * The system picker for a runtime package or the image set, registered by the activity that shows the
 * iOS flow (before it starts, as ActivityResult wants). The kind asked for survives recreation.
 */
internal class OneiosPicker(private val a: AppCompatActivity, saved: Bundle?) {
    private var kind: OneiosKind =
        if (saved?.getString(KEY_KIND) == OneiosKind.RUNTIME.word) OneiosKind.RUNTIME else OneiosKind.IMAGE
    private var kernelcache: Boolean = saved?.getBoolean(KEY_KERNELCACHE) == true

    private val launcher: ActivityResultLauncher<Array<String>> =
        a.registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            if (uri != null) {
                if (kernelcache) OneiosJob.importKernelcache(a, uri) else OneiosJob.importFile(a, kind, uri)
                OneiosActions.showProgress(a)
            }
        }

    fun save(out: Bundle) {
        out.putString(KEY_KIND, kind.word)
        out.putBoolean(KEY_KERNELCACHE, kernelcache)
    }

    fun pick(what: OneiosKind) {
        if (OneiosJob.state.busy) return
        kind = what
        kernelcache = false
        try {
            launcher.launch(arrayOf("application/zstd", "application/octet-stream", "*/*"))
        } catch (_: android.content.ActivityNotFoundException) {
            Toast.makeText(a, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    /** Apple's decoded kernelcache for a phone-built kernel (any file: it is checked against the profile's pin). */
    fun pickKernelcache() {
        if (OneiosJob.state.busy) return
        kernelcache = true
        try {
            launcher.launch(arrayOf("application/octet-stream", "*/*"))
        } catch (_: android.content.ActivityNotFoundException) {
            Toast.makeText(a, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    private companion object {
        const val KEY_KIND = "oneios_pick_kind"
        const val KEY_KERNELCACHE = "oneios_pick_kernelcache"
    }
}

/**
 * What the iOS screens' buttons do ([OneiosFlow.Next]), as FixActions is the Android guests': each one
 * starts one job of [OneiosJob] (the root verbs as before) or asks first. A download or an import shows
 * its progress on Set up iOS 27 (OneiosSetupActivity), as an Android system's setup does on Setting up.
 */
internal object OneiosActions {
    /** The button text for [next]; null when there is no button. */
    fun label(a: AppCompatActivity, next: OneiosFlow.Next): String? = when (next) {
        OneiosFlow.Next.WAIT, OneiosFlow.Next.NOT_THIS_PHONE -> null
        OneiosFlow.Next.SWITCH -> a.getString(R.string.oneios_switch)
        OneiosFlow.Next.CHECK_AGAIN -> OneiosPlain.label(OneiosFix.CHECK_AGAIN)
        OneiosFlow.Next.GET_RUNTIME -> OneiosPlain.label(OneiosFix.GET_RUNTIME)
        OneiosFlow.Next.DOWNLOAD_RUNTIME -> OneiosPlain.label(OneiosFix.DOWNLOAD_RUNTIME)
        OneiosFlow.Next.IMPORT_RUNTIME -> OneiosPlain.label(OneiosFix.IMPORT_RUNTIME)
        OneiosFlow.Next.IMPORT_IMAGE -> OneiosPlain.label(OneiosFix.IMPORT_IMAGE)
        OneiosFlow.Next.BACK_TO_ONE_UI -> OneiosPlain.label(OneiosFix.BACK_TO_ONE_UI)
        OneiosFlow.Next.REMOVE -> OneiosPlain.label(OneiosFix.REMOVE)
        OneiosFlow.Next.SESSION_LOGS -> OneiosPlain.label(OneiosFix.SESSION_LOGS)
    }

    fun run(a: AppCompatActivity, next: OneiosFlow.Next, picker: OneiosPicker) {
        if (OneiosJob.state.busy && next != OneiosFlow.Next.SESSION_LOGS) return
        when (next) {
            OneiosFlow.Next.WAIT, OneiosFlow.Next.NOT_THIS_PHONE -> Unit
            OneiosFlow.Next.CHECK_AGAIN -> OneiosJob.refresh(a)
            OneiosFlow.Next.GET_RUNTIME -> askRuntime(a, picker)
            OneiosFlow.Next.DOWNLOAD_RUNTIME -> download(a, null)
            OneiosFlow.Next.IMPORT_RUNTIME -> picker.pick(OneiosKind.RUNTIME)
            OneiosFlow.Next.IMPORT_IMAGE -> askImage(a, picker)
            OneiosFlow.Next.BACK_TO_ONE_UI -> OneiosJob.backToOneUi(a)
            OneiosFlow.Next.REMOVE -> confirmRemove(a)
            OneiosFlow.Next.SESSION_LOGS -> a.startActivity(OneiosLogsActivity.intent(a))
            OneiosFlow.Next.SWITCH -> OneiosSwitchConfirm.show(a)
        }
    }

    /** Set up iOS 27 shows a download or an import while it runs (from iOS 27's page too). */
    fun showProgress(a: AppCompatActivity) {
        if (a !is OneiosSetupActivity && OneiosJob.state.copying) a.startActivity(OneiosSetupActivity.intent(a))
    }

    fun download(a: AppCompatActivity, tag: String?) {
        OneiosJob.downloadRuntime(a, tag)
        showProgress(a)
    }

    /** One choice of a [choose] list: its name, and under it in smaller, quieter text what it does. */
    private fun choice(a: AppCompatActivity, title: Int, line: Int): CharSequence {
        val t = a.getString(title)
        val l = a.getString(line)
        return android.text.SpannableStringBuilder(t).append('\n').append(l).apply {
            val from = t.length + 1
            setSpan(android.text.style.RelativeSizeSpan(0.85f), from, length, android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
            setSpan(android.text.style.ForegroundColorSpan(a.getColor(R.color.preboot_secondary)), from, length, android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }

    /** A list of ways, the recommended one first; each item's action runs when it is tapped. */
    private fun choose(a: AppCompatActivity, title: Int, items: List<Pair<CharSequence, () -> Unit>>) {
        AlertDialog.Builder(a).setTitle(title)
            .setItems(items.map { it.first }.toTypedArray()) { _, i -> items[i].second() }
            .setNegativeButton(android.R.string.cancel, null).show()
    }

    /**
     * The runtime step: where the runtime comes from, as a list with the recommended way first (OneiOS's latest
     * release), then an older release by its tag, then a file the user has. Before 2026-11-22 this was "Do you have the
     * file? Yes / No, download it", where the usual way was the second button.
     */
    fun askRuntime(a: AppCompatActivity, picker: OneiosPicker) = choose(
        a, R.string.oneios_runtime_choose_title,
        listOf(
            choice(a, R.string.oneios_runtime_choice_download, R.string.oneios_runtime_choice_download_line) to { download(a, null) },
            choice(a, R.string.oneios_runtime_choice_tag, R.string.oneios_runtime_choice_tag_line) to { askTag(a) },
            choice(a, R.string.oneios_runtime_choice_file, R.string.oneios_runtime_choice_file_line) to { picker.pick(OneiosKind.RUNTIME) },
        ),
    )

    /** The runtime's other ways (an older release, a file), for the runtime section of iOS 27's page. */
    fun askRuntimeOther(a: AppCompatActivity, picker: OneiosPicker) = choose(
        a, R.string.oneios_runtime_choose_title,
        listOf(
            choice(a, R.string.oneios_runtime_choice_tag, R.string.oneios_runtime_choice_tag_line) to { askTag(a) },
            choice(a, R.string.oneios_runtime_choice_file, R.string.oneios_runtime_choice_file_line) to { picker.pick(OneiosKind.RUNTIME) },
        ),
    )

    /**
     * The image step (docs/oneios.md, "Make iOS image"): where the image comes from, as a list with the recommended
     * way first. Make it on this phone goes on to [makeImage], which says what it downloads from Apple, the room it
     * needs at its peak and this phone's free room. Use an image set I have is the picker. Nothing in it needs a PC.
     * OneOS never ships the image set: this phone makes it from Apple's own files, for its owner. Before 2026-11-22
     * the picker was a third button of Make iOS image's own dialog.
     */
    fun askImage(a: AppCompatActivity, picker: OneiosPicker) {
        if (OneiosToolJob.state.busy) {
            a.startActivity(OneiosToolActivity.intent(a))
            return
        }
        choose(
            a, R.string.oneios_image_choose_title,
            listOf(
                choice(a, R.string.oneios_image_choice_make, R.string.oneios_image_choice_make_line) to { makeImage(a) },
                choice(a, R.string.oneios_image_choice_file, R.string.oneios_image_choice_file_line) to { picker.pick(OneiosKind.IMAGE) },
            ),
        )
    }

    /**
     * Make iOS image ([OneiosToolJob.Flow.MAKE_IMAGE]), asked first: the iOS it makes on this phone and its download
     * ([OneiosJob.imageChoice]: iOS 27.0.1, about 11 GB from Apple, once; iOS 16.5, about 5.8 GB, on the Galaxy A56),
     * the free room it needs while it builds (the choice's room; the tool checks the exact room itself before it
     * downloads anything) and the room this phone has now. While the flow runs, its screen opens
     * instead.
     */
    fun makeImage(a: AppCompatActivity) {
        if (OneiosToolJob.state.busy) {
            a.startActivity(OneiosToolActivity.intent(a))
            return
        }
        val free = runCatching { android.os.StatFs(android.os.Environment.getDataDirectory().path).availableBytes }.getOrNull()
        val image = OneiosJob.imageChoice()
        val text = buildString {
            append(a.getString(R.string.oneios_make_image_confirm, Units.bytes(image.downloadBytes), Units.bytes(image.roomBytes), image.version))
            if (free != null) {
                append("\n\n")
                append(a.getString(if (free < image.roomBytes) R.string.oneios_make_image_free_short else R.string.oneios_make_image_free, Units.bytes(free)))
            }
        }
        val d = AlertDialog.Builder(a).setTitle(R.string.oneios_make_image).setMessage(text)
            .setPositiveButton(R.string.oneios_make_image_start) { _, _ -> OneiosToolActivity.start(a, OneiosToolJob.Flow.MAKE_IMAGE) }
            .setNegativeButton(android.R.string.cancel, null)
        d.show()
    }

    /** A release by its tag (empty: the latest). */
    fun askTag(a: AppCompatActivity) {
        if (OneiosJob.state.busy) return
        val input = EditText(a).apply {
            hint = a.getString(R.string.oneios_tag_hint)
            isSingleLine = true
        }
        val frame = FrameLayout(a).apply {
            val d = a.resources.displayMetrics.density
            setPadding((24 * d).toInt(), (8 * d).toInt(), (24 * d).toInt(), 0)
            addView(input)
        }
        AlertDialog.Builder(a).setTitle(R.string.oneios_tag_title).setView(frame)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_runtime_download) { _, _ -> download(a, input.text?.toString()) }
            .show()
    }

    fun confirmRemove(a: AppCompatActivity) {
        AlertDialog.Builder(a).setTitle(R.string.oneios_remove).setMessage(R.string.oneios_remove_confirm)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_remove_run) { _, _ -> OneiosJob.remove(a) }.show()
    }

    /** The kept kernel set becomes the image's again (root's `restore kernel`, with its own receipt). */
    fun confirmRestoreKernel(a: AppCompatActivity) {
        AlertDialog.Builder(a).setTitle(R.string.oneios_kernel_restore).setMessage(R.string.oneios_kernel_restore_line)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_kernel_restore) { _, _ -> OneiosJob.restoreKernel(a) }.show()
    }

    /** The step's name, as Set up iOS 27's checklist says it. */
    fun stepTitle(a: AppCompatActivity, step: OneiosFlow.Step): String = a.getString(
        when (step) {
            OneiosFlow.Step.PHONE -> R.string.setup_step_check_phone
            OneiosFlow.Step.RUNTIME -> R.string.oneios_step_runtime
            OneiosFlow.Step.IMAGE -> R.string.oneios_step_image
            OneiosFlow.Step.DATA -> R.string.oneios_step_data
            OneiosFlow.Step.READY -> R.string.oneios_step_ready
        },
    )

    /** What a step does, shown while it waits for the user. */
    fun stepAbout(a: AppCompatActivity, step: OneiosFlow.Step): String = a.getString(
        when (step) {
            OneiosFlow.Step.PHONE -> R.string.setup_step_check_phone_pending
            OneiosFlow.Step.RUNTIME -> R.string.oneios_step_runtime_about
            OneiosFlow.Step.IMAGE -> R.string.oneios_step_image_about
            OneiosFlow.Step.DATA -> R.string.oneios_step_data_about
            OneiosFlow.Step.READY -> R.string.oneios_step_ready_about
        },
    )

    /** The title of what runs now. */
    fun runningTitle(a: AppCompatActivity, job: OneiosFlow.Job): String = a.getString(
        when (job) {
            OneiosFlow.Job.CHECK -> R.string.oneios_running_check
            OneiosFlow.Job.DOWNLOAD_RUNTIME -> R.string.oneios_running_download
            OneiosFlow.Job.IMPORT_RUNTIME -> R.string.oneios_running_import_runtime
            OneiosFlow.Job.IMPORT_IMAGE -> R.string.oneios_running_import_image
            OneiosFlow.Job.SWITCH -> R.string.oneios_running_switch
            OneiosFlow.Job.RETURN -> R.string.oneios_running_return
            OneiosFlow.Job.REMOVE -> R.string.oneios_running_remove
            OneiosFlow.Job.STAGE_KB -> R.string.oneios_running_stage_kb
            OneiosFlow.Job.FINISH_KERNEL -> R.string.oneios_running_finish_kernel
            OneiosFlow.Job.RESTORE_KERNEL -> R.string.oneios_running_restore_kernel
        },
    )
}
