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
import com.fahadali.oneos.core.model.OneiosReleases
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

    private val launcher: ActivityResultLauncher<Array<String>> =
        a.registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            if (uri != null) {
                OneiosJob.importFile(a, kind, uri)
                OneiosActions.showProgress(a)
            }
        }

    fun save(out: Bundle) = out.putString(KEY_KIND, kind.word)

    fun pick(what: OneiosKind) {
        if (OneiosJob.state.busy) return
        kind = what
        try {
            launcher.launch(arrayOf("application/zstd", "application/octet-stream", "*/*"))
        } catch (_: android.content.ActivityNotFoundException) {
            Toast.makeText(a, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    private companion object {
        const val KEY_KIND = "oneios_pick_kind"
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

    /** "Do you have the file?", as the Android systems' Set up asks: yes, the picker; no, OneiOS's latest release. */
    fun askRuntime(a: AppCompatActivity, picker: OneiosPicker) {
        AlertDialog.Builder(a).setTitle(R.string.oneios_step_runtime)
            .setMessage(R.string.oneios_runtime_question)
            .setPositiveButton(R.string.setup_download_yes) { _, _ -> picker.pick(OneiosKind.RUNTIME) }
            .setNegativeButton(R.string.oneios_runtime_download_it) { _, _ -> download(a, null) }
            .setNeutralButton(android.R.string.cancel, null).show()
    }

    /**
     * "Have you built the image set?": I have the file (the picker); Make iOS image (oneios-tool makes it on this
     * phone from Apple's server, [OneiosToolJob.Flow.MAKE_IMAGE]); how to build it on a PC or a Mac. OneOS never
     * downloads the image set itself: it is made from Apple's own files, for this phone's owner.
     */
    fun askImage(a: AppCompatActivity, picker: OneiosPicker) {
        val items = arrayOf(a.getString(R.string.oneios_image_choose), a.getString(R.string.oneios_make_image), a.getString(R.string.oneios_image_how))
        AlertDialog.Builder(a).setTitle(R.string.oneios_image_question)
            .setItems(items) { _, which ->
                when (which) {
                    0 -> picker.pick(OneiosKind.IMAGE)
                    1 -> OneiosToolActivity.start(a, OneiosToolJob.Flow.MAKE_IMAGE)
                    else -> SystemsNav.open(a, "https://github.com/${OneiosReleases.REPO}#readme")
                }
            }
            .setNegativeButton(android.R.string.cancel, null).show()
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
        },
    )
}
