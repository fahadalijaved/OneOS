package com.fahadali.oneos.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.SetupPreviewTimeline
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck

/** The Figma setup screen, driven by the original PrepareJob or an isolated debug timeline. */

/** Steps that report their own bytes (PrepareJob.State.stepFraction): the hash, the downloads, the image, the files. */
private val MEASURED_STEPS = setOf(PrepareJob.Step.HASH, PrepareJob.Step.DOWNLOAD, PrepareJob.Step.IMAGE, PrepareJob.Step.FILES)

class SetupProgressActivity : EdgeToEdgeActivity() {
    var previewImage: ImageRef? = null
        private set
    companion object {
        const val EXTRA_PREVIEW_IMAGE = "oneos.debug.preview_image"
        const val EXTRA_UPDATE = "oneos.setup.update"
        const val EXTRA_REUSE_IMAGE = "oneos.setup.reuse_image"
        const val EXTRA_IMAGE = "oneos.setup.image"
        const val EXTRA_RETURN_TO_CHECKS = "oneos.setup.return_to_checks"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        previewImage = if (DebugPreview.enabled(this)) intent.getStringExtra(EXTRA_PREVIEW_IMAGE)?.let(Images::byId) else null
        super.onCreate(savedInstanceState)
        ArtworkTransitions.prepare(this)
        setContentView(R.layout.activity_setup_progress)
        // The setup notification (PrepareService, 0.4.41) needs this on Android 13+; asked once
        // here, where setup starts. Setup runs either way, without the notification if refused.
        if (savedInstanceState == null && android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 41)
        }
        findViewById<View>(R.id.setup_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.setup_toolbar).apply {
            setNavigationIcon(dev.oneuiproject.oneui.R.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }
        }
        if (savedInstanceState == null) supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, SetupProgressFragment()).commit()
    }

    private var unsubscribe: (() -> Unit)? = null

    fun setBarTitle(text: CharSequence) {
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.setup_toolbar).title = text
    }

    fun setExpandedSubtitle(text: CharSequence) {
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.setup_toolbar).subtitle = text
    }

    override fun onStart() {
        super.onStart()
        if (previewImage != null) return
        unsubscribe = PrepareJob.observe { s ->
            if (s.busy) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }
}

class SetupProgressFragment : Fragment() {
    private val previewImage: ImageRef? get() = (activity as? SetupProgressActivity)?.previewImage
    private val previewTimeline = SetupPreviewTimeline(PrepareJob.Step.entries.size, stepDurationMs = 3000)
    private val previewHandler = android.os.Handler(android.os.Looper.getMainLooper())
    private var previewElapsedMs = 0L
    private var previewResumedAt = 0L
    private var previewCancelledAt: Long? = null
    private fun elapsedPreview(): Long = previewElapsedMs + if (previewResumedAt == 0L) 0 else android.os.SystemClock.uptimeMillis() - previewResumedAt
    private fun displayedState(): PrepareJob.State {
        val image = previewImage ?: return PrepareJob.state
        val snap = previewTimeline.at(elapsedPreview(), previewCancelledAt)
        return PrepareJob.State(
            phase = when (snap.phase) {
                SetupPreviewTimeline.Phase.RUNNING -> PrepareJob.Phase.RUNNING
                SetupPreviewTimeline.Phase.DONE -> PrepareJob.Phase.DONE
                SetupPreviewTimeline.Phase.CANCELLED -> PrepareJob.Phase.STOPPED
            },
            step = snap.currentStep?.let { PrepareJob.Step.entries[it] },
            done = PrepareJob.Step.entries.take(snap.completedSteps).toSet(),
            image = image, bytesDone = snap.percent.toLong(), bytesTotal = 100,
            detail = getString(R.string.setup_preview_simulated),
            etaSeconds = ((previewTimeline.durationMs - elapsedPreview()).coerceAtLeast(0) / 1000).toInt(),
        )
    }
    private val previewTick = object : Runnable {
        override fun run() {
            if (!isAdded || view == null || previewImage == null) return
            val state = displayedState()
            bind(state)
            if (state.busy) previewHandler.postDelayed(this, 160)
        }
    }


    private var unsubscribe: (() -> Unit)? = null
    private var stopping = false
    private var routed = false
    private var lastChecklistState: Any? = null
    private var stepRows: List<dev.oneuiproject.oneui.widget.CardItemView> = emptyList()
    /** The set-aside copy the old copies were listed for (once per screen). */
    private var listedFor: String? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.setup_progress_screen, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        previewElapsedMs = savedInstanceState?.getLong("preview_elapsed") ?: 0L
        previewCancelledAt = savedInstanceState?.getLong("preview_cancelled", -1)?.takeIf { it >= 0 }
        view.findViewById<androidx.core.widget.NestedScrollView>(R.id.setup_scroll).apply {
            isNestedScrollingEnabled = false
            clipToPadding = false
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(requireContext().getColor(R.color.oneos_page_background))
            seslSetFadingEdgeWindowBottomAlignment(false)
            seslSetAllowTopFadingEdgeWithoutEdgeToEdge(true)
        }
        ArtworkTransitions.bindTarget(requireActivity(), view.findViewById(R.id.setup_artwork))
        lastChecklistState = null
        val steps = view.findViewById<LinearLayout>(R.id.setup_steps)
        Cards.round(steps)
        stepRows = checklist.map { (title, _) ->
            (Cards.row(steps, R.drawable.ic_oneos_step_pending, title) as dev.oneuiproject.oneui.widget.CardItemView).apply {
                isClickable = false
                isFocusable = false
            }
        }
        if (!resources.getBoolean(R.bool.home_two_pane)) {
            view.findViewById<View>(R.id.setup_title).visibility = View.GONE
            view.post {
                val hero = view.findViewById<View>(R.id.setup_hero)
                val viewport = view.height
                hero.layoutParams = hero.layoutParams.apply {
                    val image = previewImage ?: PrepareJob.state.image
                    val family = image?.family ?: com.fahadali.oneos.core.model.SystemFamily.COLOROS
                    val heading = com.fahadali.oneos.core.model.ArtworkFraming.heading(family, true)
                    val headingHeight = (heading.bottom - heading.top) * 1548 * hero.width / 1050f
                    val readable = headingHeight + 144 * resources.displayMetrics.density
                    height = maxOf(minOf((hero.width * 356f / 392f).toInt(), (viewport * .55f).toInt()), readable.toInt())
                        .coerceAtLeast((180 * resources.displayMetrics.density).toInt())
                }
            }
        }
        if (previewImage != null) (activity as? SetupProgressActivity)?.setExpandedSubtitle(getString(R.string.setup_preview_badge))
    }

    override fun onStart() {
        super.onStart()
        if (previewImage != null) {
            previewResumedAt = android.os.SystemClock.uptimeMillis()
            previewHandler.post(previewTick)
            return
        }
        val prepare = PrepareJob.observe { bind(it) }
        // Delete the old copy (0.4.11) runs in OldStagesJob.
        val old = OldStagesJob.observe { bind(displayedState()) }
        unsubscribe = { prepare(); old() }
    }

    override fun onStop() {
        if (previewImage != null) {
            previewElapsedMs = elapsedPreview(); previewResumedAt = 0L
            previewHandler.removeCallbacks(previewTick)
        }
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (previewImage != null) {
            outState.putLong("preview_elapsed", elapsedPreview())
            outState.putLong("preview_cancelled", previewCancelledAt ?: -1)
        }
    }

    private fun bind(s: PrepareJob.State) {
        val root = view ?: return
        val ctx = root.context
        val phase = s.phase
        if (phase == PrepareJob.Phase.DONE && !routed && s.image != null) {
            routed = true
            val a = activity ?: return
            val simulated = previewImage != null
            EnvironmentNavigation.remember(a, s.image, simulated)
            if (!simulated && a.intent.getBooleanExtra(SetupProgressActivity.EXTRA_RETURN_TO_CHECKS, false)) {
                // Return through the same shared element to the checks page underneath.
                // Its normal observers refresh the gates; no duplicate checks page is pushed.
                a.finishAfterTransition()
                return
            }
            ArtworkTransitions.start(a, EnvironmentNavigation.intent(a, s.image, simulated),
                root.findViewById(R.id.setup_artwork), finishSource = true)
            return
        }
        if (phase != PrepareJob.Phase.RUNNING) stopping = false

        // The system: the job's, else (its first seconds) the picked download's.
        val profile = StageCheck.state.result?.facts?.let { Profiles.resolve(it).profile }
        val image = s.image ?: activity?.intent?.getStringExtra(SetupProgressActivity.EXTRA_IMAGE)?.let(Images::byId)
            ?: FixActions.pickedImage(ctx, profile)
        val updating = activity?.intent?.getBooleanExtra(SetupProgressActivity.EXTRA_UPDATE, false) == true ||
            s.plan?.kind in setOf(com.fahadali.oneos.core.root.SetupPlan.Kind.UPDATE, com.fahadali.oneos.core.root.SetupPlan.Kind.REPAIR)
        val reuseImage = if (s.source != null) s.source == SessionPrefs.Source.ON_PHONE else
            activity?.intent?.getBooleanExtra(SetupProgressActivity.EXTRA_REUSE_IMAGE, false) == true
        val system = image?.let { Images.systemName(it, profile) }

        root.findViewById<OsArtworkView>(R.id.setup_artwork).bind(image)
        // Step by step (0.4.41, owner: "it's not step wise"): each row of the checklist an equal
        // part of the bar, the current one filled to its own progress.
        root.findViewById<androidx.appcompat.widget.SeslProgressBar>(R.id.setup_linear_progress).apply {
            isIndeterminate = false
            progress = if (phase == PrepareJob.Phase.DONE) 100 else stepWisePercent(s, reuseImageFor(s))
        }
        // The title and its line (the result's plain message once it stops).
        val title: String
        val subtitle: String
        when (phase) {
            PrepareJob.Phase.IDLE -> {
                title = getString(R.string.setup_idle_title)
                subtitle = getString(R.string.setup_idle_subtitle)
            }
            PrepareJob.Phase.RUNNING -> {
                title = system?.let { getString(if (updating) R.string.setup_update_title else R.string.setup_mock_title, it) } ?: getString(R.string.setup_label)
                subtitle = ""
            }
            PrepareJob.Phase.DONE -> {
                title = system?.let { getString(R.string.setup_done_title, it) } ?: getString(R.string.setup_ring_done)
                subtitle = getString(R.string.setup_done_subtitle)
            }
            PrepareJob.Phase.STOPPED, PrepareJob.Phase.FAILED -> {
                title = s.plain?.title ?: getString(R.string.setup_failed_title)
                subtitle = s.plain?.line.orEmpty()
            }
        }
        val titleView = root.findViewById<TextView>(R.id.setup_title)
        // Set only on a change: it is a polite live region.
        if (titleView.text.toString() != title) titleView.text = title
        if (!resources.getBoolean(R.bool.home_two_pane)) (activity as? SetupProgressActivity)?.setBarTitle(title)
        val subtitleView = root.findViewById<TextView>(R.id.setup_subtitle)
        subtitleView.text = subtitle
        subtitleView.visibility = if (subtitle.isEmpty()) View.GONE else View.VISIBLE

        root.findViewById<TextView>(R.id.setup_artwork_state).text = when (phase) {
            // "Installing · 42% · About 8 min left" (0.4.43, UX audit: the ETA was computed but never shown).
            PrepareJob.Phase.RUNNING -> listOf(
                getString(if (updating) R.string.setup_updating else R.string.setup_installing),
                getString(R.string.setup_percent, stepWisePercent(s, reuseImageFor(s))),
                s.etaSeconds?.let { if (it < 60) getString(R.string.setup_eta_soon) else getString(R.string.setup_eta_minutes, (it + 59) / 60) }
                    ?: getString(R.string.setup_eta_estimating),
            ).joinToString(" · ")
            PrepareJob.Phase.DONE -> getString(R.string.setup_ring_done)
            PrepareJob.Phase.STOPPED -> getString(R.string.setup_ring_stopped)
            PrepareJob.Phase.FAILED -> getString(R.string.setup_ring_failed)
            PrepareJob.Phase.IDLE -> ""
        }
        val measured = s.step in MEASURED_STEPS
        val checklistState = listOf(updating, reuseImage, s.phase, s.step, s.done, if (measured) s.detail else null,
            if (measured) s.stepFraction?.let { (it * 100).toInt() } else null, s.plain?.line, s.message)
        if (checklistState != lastChecklistState) {
            lastChecklistState = checklistState
            stepRows.zip(checklist).forEach { (row, item) ->
                val (defaultLabel, stages) = item
                val label = when {
                    reuseImage && PrepareJob.Step.IMAGE in stages -> getString(R.string.setup_verify_existing_image)
                    updating && PrepareJob.Step.CHECK in stages -> getString(R.string.setup_check_update)
                    else -> defaultLabel
                }
                // No downloaded-file hash is performed when reusing the installed image.
                // BEGIN completes the grouped local-files row when HASH was already cached.
                val completed = rowCompleted(s, stages, reuseImage)
                val current = s.step in stages
                val failed = current && phase in setOf(PrepareJob.Phase.FAILED, PrepareJob.Phase.STOPPED)
                row.title = label
                row.summary = when {
                    current && s.busy && measured && previewImage == null -> s.detail
                    failed -> s.plain?.line ?: s.message
                    else -> null
                }
                val drawable = when {
                    completed -> R.drawable.ic_setup_complete
                    failed -> R.drawable.oneos_badge_warn
                    current && s.busy -> R.drawable.ic_oneos_step_current
                    else -> R.drawable.ic_oneos_step_pending
                }
                row.icon = if (current && s.busy && !completed && !failed) StepRingDrawable(ctx, if (measured) s.stepFraction else null)
                    else androidx.appcompat.content.res.AppCompatResources.getDrawable(ctx, drawable)
                row.contentDescription = "$label, " + getString(when {
                    completed -> R.string.setup_state_done
                    failed -> R.string.setup_state_failed
                    current && s.busy -> R.string.setup_state_current
                    else -> R.string.setup_state_pending
                }) + row.summary?.let { ", $it" }.orEmpty()
            }
        }
        // Failure diagnostics stay available without duplicating every step in a second card.
        val slot = root.findViewById<LinearLayout>(R.id.setup_details_slot)
        slot.removeAllViews()
        slot.visibility = if (phase == PrepareJob.Phase.FAILED) View.VISIBLE else View.GONE
        if (phase == PrepareJob.Phase.FAILED) {
            val card = Cards.section(slot, null, rows = true)
            s.finding?.let { CardRows.finding(card, it) }
            s.message?.let { Cards.row(card, 0, getString(R.string.setup_details_result), it) }
        }
        bindFooter(s)
        if (previewImage != null) {
            subtitleView.visibility = View.GONE
            (activity as? SetupProgressActivity)?.setExpandedSubtitle(getString(when (phase) {
                PrepareJob.Phase.RUNNING -> R.string.setup_preview_badge
                PrepareJob.Phase.STOPPED -> R.string.setup_preview_cancelled
                else -> R.string.setup_preview_finished
            }))
            if (phase == PrepareJob.Phase.STOPPED) titleView.setText(R.string.setup_preview_cancelled_title)
        }
    }

    /** Whether a checklist row is done: its steps are, or they were skipped and a later step runs. */
    private fun rowCompleted(s: PrepareJob.State, stages: Set<PrepareJob.Step>, reuseImage: Boolean): Boolean {
        if (s.phase == PrepareJob.Phase.DONE) return true
        val now = s.step?.ordinal ?: -1
        return stages.all {
            it in s.done || when (it) {
                // No hash when the image on the phone is reused; skipped, done once a later step runs.
                PrepareJob.Step.HASH -> reuseImage || now > PrepareJob.Step.HASH.ordinal
                PrepareJob.Step.DOWNLOAD -> now > PrepareJob.Step.DOWNLOAD.ordinal
                else -> false
            }
        }
    }

    private fun reuseImageFor(s: PrepareJob.State): Boolean =
        if (s.source != null) s.source == SessionPrefs.Source.ON_PHONE
        else activity?.intent?.getBooleanExtra(SetupProgressActivity.EXTRA_REUSE_IMAGE, false) == true

    /** The bar: every row an equal share, the current one filled to its step's own progress. */
    private fun stepWisePercent(s: PrepareJob.State, reuseImage: Boolean): Int {
        val rows = checklist
        if (rows.isEmpty()) return 0
        var done = 0f
        for ((_, stages) in rows) {
            done += when {
                rowCompleted(s, stages, reuseImage) -> 1f
                s.step in stages && s.step in MEASURED_STEPS -> s.stepFraction ?: 0f
                else -> 0f
            }
        }
        return (done * 100 / rows.size).toInt().coerceIn(0, 100)
    }

    /** Group backend stages into the rows shown in the design (0.4.41: nine, with the download); no job semantics change. */
    private val checklist: List<Pair<String, Set<PrepareJob.Step>>> get() = listOf(
        getString(R.string.setup_check_phone) to setOf(PrepareJob.Step.CHECK),
        getString(R.string.setup_check_files) to setOf(PrepareJob.Step.HASH),
        getString(R.string.setup_download_files) to setOf(PrepareJob.Step.DOWNLOAD),
        // The stage folder (BEGIN) comes after the downloads (0.4.41): with the image, not the local files.
        getString(R.string.setup_image) to setOf(PrepareJob.Step.BEGIN, PrepareJob.Step.IMAGE),
        getString(R.string.setup_files_patches) to setOf(PrepareJob.Step.FILES),
        getString(R.string.setup_table) to setOf(PrepareJob.Step.TABLE),
        getString(R.string.setup_session) to setOf(PrepareJob.Step.ENV),
        getString(R.string.setup_cleanup) to setOf(PrepareJob.Step.FINISH),
        getString(R.string.setup_step_finish) to setOf(PrepareJob.Step.VERIFY),
    )

    /** Stop while it runs; then Done, or the plain message's fix and Close. */
    private fun bindFooter(s: PrepareJob.State) {
        if (previewImage != null) { bindPreviewFooter(s); return }

        val a = activity as? SetupProgressActivity ?: return
        val primary = a.findViewById<Button>(R.id.setup_primary) ?: return
        val secondary = a.findViewById<Button>(R.id.setup_secondary) ?: return

        fun show(b: Button, text: CharSequence?, enabled: Boolean = true, onClick: () -> Unit = {}) {
            if (text == null) {
                b.visibility = View.GONE
                b.setOnClickListener(null)
                return
            }
            b.visibility = View.VISIBLE
            b.text = text
            b.isEnabled = enabled
            b.setOnClickListener { onClick() }
        }

        when (s.phase) {
            PrepareJob.Phase.RUNNING -> {
                show(primary, null)
                show(secondary, getString(if (stopping) R.string.setup_stopping else R.string.setup_stop_setup), enabled = !stopping) {
                    // Asked first (0.4.43, UX audit): one tap ended a 15-minute setup. Nothing is lost either way.
                    val name = s.image?.name ?: getString(R.string.setup_label)
                    androidx.appcompat.app.AlertDialog.Builder(a)
                        .setTitle(getString(R.string.setup_stop_title, name))
                        .setMessage(R.string.prepare_stop_summary)
                        .setPositiveButton(R.string.setup_stop) { _, _ ->
                            stopping = true
                            PrepareJob.cancel()
                            bind(displayedState())
                        }
                        .setNegativeButton(R.string.setup_keep_going, null)
                        .show()
                }
            }
            PrepareJob.Phase.DONE -> {
                show(primary, getString(R.string.setup_done_button)) { SystemsNav.home(a) }
                // 0.4.11: a fresh setup kept the system before as an old copy; delete it from here.
                val aside = asideCopy(s)
                val old = OldStagesJob.state
                // Its size for the question: list the old copies once (read only).
                if (aside != null && listedFor != aside && !old.busy && old.stages?.none { it.name == aside } != false) {
                    listedFor = aside
                    OldStagesJob.refresh(a)
                }
                when {
                    aside == null -> show(secondary, null)
                    old.deletedNames?.contains(aside) == true ->
                        show(secondary, getString(R.string.setup_old_deleted, Units.bytes((old.freedKib ?: 0) * 1024)), enabled = false)
                    old.phase == OldStagesJob.Phase.DELETING -> show(secondary, getString(R.string.setup_old_deleting), enabled = false)
                    old.deletedNames != null && old.deleteFailed -> show(secondary, getString(R.string.setup_old_not_deleted), enabled = false)
                    else -> show(secondary, getString(R.string.setup_delete_old), enabled = !old.busy) { confirmDeleteOld(aside) }
                }
            }
            PrepareJob.Phase.STOPPED, PrepareJob.Phase.FAILED -> {
                val fix = s.plain?.takeIf { it.action != FixAction.NONE && it.action != FixAction.ACKNOWLEDGE && it.actionLabel != null }
                // A session that ended with a force restart blocks every update until One UI's
                // settings are restored: "Restore now", never "Retry update", which only met
                // the same block again (owner's F8U and user reports, 11-08).
                if (s.plan?.keepsData == true && fix?.action != FixAction.RESTORE) {
                    show(primary, getString(R.string.retry_update)) { FixActions.run(a, FixAction.UPDATE, s.image) }
                } else show(primary, fix?.actionLabel) { if (fix != null) FixActions.run(a, fix.action, s.image) }
                show(secondary, getString(R.string.setup_close)) { SystemsNav.home(a) }
            }
            PrepareJob.Phase.IDLE -> {
                show(primary, null)
                show(secondary, getString(R.string.setup_close)) { SystemsNav.home(a) }
            }
        }
        val lp = secondary.layoutParams as? ViewGroup.MarginLayoutParams ?: return
        val top = if (primary.visibility == View.VISIBLE) (8 * resources.displayMetrics.density).toInt() else 0
        if (lp.topMargin != top) {
            lp.topMargin = top
            secondary.layoutParams = lp
        }
    }

    /** Deliberately independent of PrepareJob.cancel/start, LaunchJob and old-stage operations. */
    private fun bindPreviewFooter(state: PrepareJob.State) {
        val a = activity as? SetupProgressActivity ?: return
        val primary = a.findViewById<Button>(R.id.setup_primary)
        val secondary = a.findViewById<Button>(R.id.setup_secondary)
        primary.visibility = if (state.phase == PrepareJob.Phase.DONE) View.VISIBLE else View.GONE
        primary.setText(R.string.setup_preview_boot)
        primary.setOnClickListener {
            AlertDialog.Builder(a).setTitle(getString(R.string.setup_preview_boot_title, state.image?.name.orEmpty()))
                .setMessage(R.string.setup_preview_boot_message)
                .setPositiveButton(R.string.setup_preview_finish) { _, _ ->
                    startActivity(android.content.Intent(a, GapSplashActivity::class.java)
                        .putExtra(SetupProgressActivity.EXTRA_PREVIEW_IMAGE, state.image?.id))
                }.setNegativeButton(android.R.string.cancel, null).show()
        }
        secondary.visibility = View.VISIBLE
        secondary.isEnabled = true
        secondary.setText(if (state.busy) android.R.string.cancel else R.string.setup_close)
        secondary.setOnClickListener {
            if (state.busy) {
                previewCancelledAt = elapsedPreview()
                previewHandler.removeCallbacks(previewTick)
                bind(displayedState())
            } else a.finish()
        }
    }

    /** The copy this setup set aside (root's "aside <path>" result), as Free up space names it. */
    private fun asideCopy(s: PrepareJob.State): String? =
        s.infos.lastOrNull { it.startsWith("aside ") }?.substringAfter("aside ")?.trim()?.substringAfterLast('/')
            ?.takeIf { it.startsWith("oneos.old-") }

    private fun confirmDeleteOld(name: String) {
        val ctx = requireContext()
        // The size, when Free up space has listed it.
        val size = OldStagesJob.state.stages?.firstOrNull { it.name == name }?.let { Units.bytes(it.kib * 1024) }
            ?: getString(R.string.setup_old_size_unknown)
        AlertDialog.Builder(ctx)
            .setTitle(R.string.setup_delete_old_title)
            .setMessage(getString(R.string.setup_delete_old_message, size))
            .setPositiveButton(R.string.space_delete_run) { _, _ -> OldStagesJob.deleteAll(ctx, setOf(name)) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

}
