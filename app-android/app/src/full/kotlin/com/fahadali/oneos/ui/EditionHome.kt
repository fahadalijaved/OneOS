package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.os.Bundle
import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.widget.SeslProgressBar
import androidx.fragment.app.Fragment
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.AndroidRelease
import com.fahadali.oneos.core.model.DeviceFacts
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.PlainMessage
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.RootKind
import com.fahadali.oneos.core.model.ScreenLockRule
import com.fahadali.oneos.core.model.Sentence
import com.fahadali.oneos.core.model.SpaceRule
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.HomeCheck
import com.fahadali.oneos.core.root.HomeInput
import com.fahadali.oneos.core.root.HomeJob
import com.fahadali.oneos.core.root.HomeState
import com.fahadali.oneos.core.root.LastSession
import com.fahadali.oneos.core.root.OldStage
import com.fahadali.oneos.core.root.OutcomeKind
import com.fahadali.oneos.session.LaunchJob
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.QuickSwitch
import com.fahadali.oneos.session.Readiness
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.layout.ToolbarLayout
import java.util.Date
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * The full edition's Home (the redesign, docs/app/redesign-2.md; the spec is
 * Main.dc.html and HomeInner.dc.html): where you are and the one thing to do
 * next, as One UI cards. The state is decided by [HomeState] from the
 * automatic check ([Readiness]), the running job and the last session; the
 * one button runs [FixActions]. About and How OneOS works are in the menu.
 * The probe edition has its own object with the old rows.
 */
internal object EditionHome {
    val layoutRes: Int get() = R.layout.activity_home

    fun createFragment(): Fragment = StatusHomeFragment()

    /** On the cover the hero under the bar says "OneOS", so the bar has no title; the inner screen's bar has it. */
    fun created(a: MainActivity) {
        if (!a.resources.getBoolean(R.bool.home_two_pane)) a.findViewById<ToolbarLayout>(R.id.toolbar_layout)?.setTitle("")
    }

    fun createMenu(a: MainActivity, menu: Menu): Boolean {
        a.menuInflater.inflate(R.menu.home, menu)
        return true
    }

    fun menuItem(a: MainActivity, item: MenuItem): Boolean = when (item.itemId) {
        R.id.menu_how -> {
            a.startActivity(Intent(a, BeforeYouStartActivity::class.java))
            true
        }
        R.id.menu_about -> {
            a.startActivity(Intent(a, AboutActivity::class.java))
            true
        }
        else -> false
    }

    /** The shared HomeFragment is OneOS Probe's only. */
    fun bind(f: PreferenceFragmentCompat) = Unit

    fun resume(f: PreferenceFragmentCompat) = Unit
}

/**
 * Home's screen: the hero (the picture, the system or the state, one line),
 * the cards (the check tiles, the setup progress or Welcome back's session,
 * and the rows) and the one main button with the line under it. On the
 * cover it is one scrolling column with the button pinned in the footer
 * (activity_home); on the inner screen two panes, the button in the hero
 * card (layout-w600dp-h480dp). Every [HomeState.Kind] maps to the same
 * pieces, each text said once: the problem's title is the hero's line (or
 * its headline when no system is set up), its line is under the button, and
 * the technical finding is behind Details.
 */
class StatusHomeFragment : Fragment(R.layout.home_content) {
    private val subs = mutableListOf<() -> Unit>()

    /** The launch refusal last shown as a dialog (shown once). */
    private var shownRefusal: LaunchJob.State? = null

    /** A good "Welcome back" shown now: once Home is left it becomes the "Last time" row (a bad one stays until Done). */
    private var welcomeShownFor: String? = null

    // The cards, made once (onViewCreated), shown and filled by redraw.
    private var checksCard: LinearLayout? = null
    private var checksGrid: LinearLayout? = null
    private var checksLoader: View? = null
    private var progressCard: LinearLayout? = null
    private var welcomeCard: LinearLayout? = null
    private var timeTile: View? = null
    private var howTile: View? = null
    private var rowsCard: LinearLayout? = null

    private val twoPane: Boolean get() = resources.getBoolean(R.bool.home_two_pane)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        val cards = view.findViewById<LinearLayout>(R.id.home_cards)
        val inflater = LayoutInflater.from(view.context)

        // "Your phone is ready … 4 of 4 checks": root, space, battery, screen lock.
        val checks = Cards.section(cards, null, gapAbove = true)
        checksGrid = Cards.tileGrid(checks, emptyList())
        val header = checks.findViewById<LinearLayout>(R.id.oneos_section_header)
        checksLoader = inflater.inflate(R.layout.home_header_loader, header, false).also { header.addView(it, 1) }
        checksCard = checks

        // Setting up: the bar, the time left.
        val progress = Cards.section(cards, null, gapAbove = true)
        progress.addView(inflater.inflate(R.layout.home_progress, progress, false))
        progressCard = progress

        // Welcome back: "Your time in …", two tiles, the logs line.
        val welcome = Cards.section(cards, null, gapAbove = true)
        val stats = LinearLayout(welcome.context).apply { orientation = LinearLayout.HORIZONTAL }
        welcome.addView(stats, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        timeTile = inflater.inflate(R.layout.home_stat_tile, stats, false).also {
            stats.addView(it, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f))
        }
        howTile = inflater.inflate(R.layout.home_stat_tile, stats, false).also {
            stats.addView(
                it,
                LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f).apply {
                    marginStart = resources.getDimension(R.dimen.oneos_tile_gap).toInt()
                },
            )
        }
        welcome.addView(inflater.inflate(R.layout.home_welcome_logs, welcome, false))
        welcomeCard = welcome

        // Last time, Systems, Advanced (or Welcome back's Session details).
        rowsCard = Cards.section(cards, null, rows = true, gapAbove = true)
    }

    override fun onDestroyView() {
        checksCard = null
        checksGrid = null
        checksLoader = null
        progressCard = null
        welcomeCard = null
        timeTile = null
        howTile = null
        rowsCard = null
        super.onDestroyView()
    }

    override fun onStart() {
        super.onStart()
        val onChange: (Any) -> Unit = {
            if (isAdded) {
                redraw()
                Readiness.tick(requireContext())
            }
        }
        subs += StageCheck.observe(onChange)
        subs += PrepareJob.observe(onChange)
        subs += LaunchJob.observe(onChange)
        subs += LogJob.observe(onChange)
        subs += OldStagesJob.observe(onChange)
    }

    override fun onResume() {
        super.onResume()
        // Back from Settings (screen lock removed?), from the root app, or a new open: read again.
        Readiness.onResume(requireContext())
        redraw()
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        welcomeShownFor?.let { SessionPrefs.setWelcomeSeen(requireContext(), it) }
        welcomeShownFor = null
        super.onStop()
    }

    private fun lastSession(ctx: Context): LastSession? {
        val l = SessionPrefs.lastLaunch(ctx) ?: return null
        return LastSession(
            sessionId = l.sessionId,
            imageId = l.imageId,
            dryRun = l.dryRun,
            wallMs = l.wallMs,
            over = l.rebootedSince(),
            outcome = l.outcome?.let { o -> OutcomeKind.entries.firstOrNull { it.name == o } },
            afterSeconds = l.afterSeconds,
            seen = SessionPrefs.welcomeSeenFor(ctx, l.sessionId),
        )
    }

    /** What Home shows now, and the check it was decided from (null: none yet, or the kept Home). */
    private class Now(val state: HomeState, val report: GateReport?, val facts: DeviceFacts?)

    /** What Home shows now, from the jobs' states (no root call here). */
    private fun decide(ctx: Context): Now {
        val check = StageCheck.state
        val r = check.result?.takeIf { it.installd != null }
        val facts = r?.let { FactProbe(ctx).refresh(it.facts) }
        val report = if (r != null && facts != null) StageCheck.gates(ctx, r, GatePhase.SWITCH, screenLock = facts.screenLockSet, facts = facts) else null
        val prep = PrepareJob.state
        val launch = LaunchJob.state
        val logs = LogJob.state
        val job = when {
            prep.busy -> HomeJob(HomeJob.Kind.SETUP, prep.image, prep.percent)
            launch.busy || launch.phase == LaunchJob.Phase.LAUNCHED -> HomeJob(HomeJob.Kind.SWITCH, launch.image ?: report?.image)
            logs.busy && logs.recovering -> HomeJob(HomeJob.Kind.RESTORE)
            else -> null
        }
        val state = HomeState.decide(
            HomeInput(
                report = report,
                status = check.result?.status,
                checking = check.busy || (logs.busy && !logs.recovering) || OldStagesJob.state.busy,
                checkFailure = if (r == null && !check.busy) check.failure else null,
                job = job,
                last = lastSession(ctx),
                facts = facts,
                appVersionCode = BuildConfig.VERSION_CODE,
                picked = FixActions.pickedImage(ctx, report?.profile),
                // A cold start: the last known Home, read-only, until this start's first check ends.
                cached = Readiness.coldStartHome(ctx),
            ),
        )
        return Now(state, report, facts)
    }

    private fun redraw() {
        val root = view ?: return
        if (!isAdded) return
        val ctx = requireContext()
        val activity = activity as? MainActivity ?: return
        val now = decide(ctx)
        val s = now.state
        welcomeShownFor = s.last?.takeIf { s.kind == HomeState.Kind.WELCOME_BACK && it.outcome?.good == true }?.sessionId

        val tiles = tiles(ctx, now)
        // A Home decided from a finished check is kept for the next cold start (HomeState says which).
        if (tiles != null) s.snapshot(tiles.map { it.check }, System.currentTimeMillis())?.let { Readiness.keepHome(ctx, it) }
        val showChecks = tiles != null && s.kind in SHOWS_CHECKS

        hero(root, s, showChecks)
        checks(activity, s, tiles?.takeIf { showChecks })
        progress(s)
        welcome(s)
        rows(activity, s)
        footer(activity, s)
        spaceCards(root)
        refusalDialog(activity)
        quickSwitch(activity, s)
    }

    // Hero ===================================================================

    private fun hero(root: View, s: HomeState, showChecks: Boolean) {
        val outcome = s.last?.outcome?.takeIf { s.kind == HomeState.Kind.WELCOME_BACK }
        root.findViewById<ImageView>(R.id.home_hero_art).visibility = if (outcome == null) View.VISIBLE else View.GONE
        root.findViewById<ImageView>(R.id.home_hero_badge).apply {
            visibility = if (outcome != null) View.VISIBLE else View.GONE
            if (outcome != null) setImageResource(if (outcome.good) R.drawable.home_welcome_ok else R.drawable.home_welcome_warn)
        }
        val (title, line) = heroText(s)
        root.findViewById<TextView>(R.id.home_hero_title).text = title
        root.findViewById<TextView>(R.id.home_hero_line).apply {
            text = line
            visibility = if (line.isNullOrEmpty()) View.GONE else View.VISIBLE
        }
        // Working, or checking with no tiles to show it on.
        val checking = s.checking || s.cached != null
        val busy = s.kind in WORKING || (checking && !showChecks && s.kind != HomeState.Kind.WELCOME_BACK)
        root.findViewById<View>(R.id.home_hero_loader).visibility = if (busy && !line.isNullOrEmpty()) View.VISIBLE else View.GONE
        root.findViewById<TextView>(R.id.home_hero_extra).apply {
            val extra = if (twoPane && s.kind == HomeState.Kind.READY) getString(R.string.home_line_kept) else null
            text = extra
            visibility = if (extra != null) View.VISIBLE else View.GONE
        }
    }

    /** The headline and the line under it: the system and its state, or the problem when no system is in play. */
    private fun heroText(s: HomeState): Pair<String, String?> {
        val system = Sentence.start(Images.systemName(s.image))
        val p = s.problem
        return when (s.kind) {
            HomeState.Kind.CHECKING -> (if (s.image != null) system else getString(R.string.home_subtitle)) to getString(R.string.home_checking)
            HomeState.Kind.RESTORING -> getString(R.string.home_restoring) to getString(R.string.home_line_moment)
            HomeState.Kind.SETTING_UP ->
                system to (s.percent?.let { getString(R.string.home_line_setting_up, it) } ?: getString(R.string.home_line_setting_up_start))
            HomeState.Kind.SWITCHING ->
                system to getString(if (LaunchJob.state.phase == LaunchJob.Phase.LAUNCHED) R.string.home_closing else R.string.home_line_switching)
            HomeState.Kind.NOTHING_SET_UP ->
                if (s.primary == FixAction.SET_UP && s.image != null) {
                    system to getString(R.string.home_line_picked)
                } else {
                    getString(R.string.home_subtitle) to getString(R.string.home_line_setup_time)
                }
            HomeState.Kind.FIX -> system to p?.title
            HomeState.Kind.WELCOME_BACK -> getString(R.string.home_welcome) to welcomeLine(s.last)
            HomeState.Kind.READY -> system to s.image?.let { getString(R.string.home_line_ready, AndroidRelease.name(it.sdk)) }
            // Restore, root, a check that failed, an unsupported phone, the old switcher, a restart, an update.
            else -> (p?.title ?: system) to p?.line
        }
    }

    private fun welcomeLine(last: LastSession?): String? {
        if (last == null) return null
        val outcome = last.outcome ?: return null
        return if (outcome.good && outcome != OutcomeKind.DRY_RUN && !last.dryRun) {
            getString(R.string.home_welcome_good)
        } else {
            sentence(outcome.title(Images.systemName(last.image)))
        }
    }

    // Check tiles ============================================================

    /** One check tile: what Home keeps ([HomeCheck]) and, from a fresh check, what a tap opens. */
    private class Tile(val check: HomeCheck, val finding: Finding?, val plain: PlainMessage?)

    /** The four tiles from the check, or as kept; null when there is neither. */
    private fun tiles(ctx: Context, now: Now): List<Tile>? {
        val s = now.state
        s.cached?.let { c -> return c.checks.filter { it.id in TILE_GATES }.takeIf { it.isNotEmpty() }?.map { Tile(it, null, null) } }
        val r = now.report ?: return null
        // Before a setup, the space the chosen system needs (a hint only: Prepare's own check decides).
        val setupNeed = s.image?.takeIf { s.kind == HomeState.Kind.NOTHING_SET_UP && s.primary == FixAction.SET_UP }?.let { image ->
            SpaceRule.toStage(image, r.profile?.choice(image.id)?.packageSetId?.let { PackageSets.byId(it) })
        }
        return TILE_GATES.map { id -> tile(ctx, id, r, now.facts, setupNeed) }
    }

    private fun tile(ctx: Context, id: String, r: GateReport, facts: DeviceFacts?, setupNeed: Long?): Tile {
        val f = r.find(id)?.finding
        var level = f?.level ?: Level.INFO
        val unknown = ctx.getString(R.string.home_value_unknown)
        val value = when (id) {
            SwitchGates.ID_ROOT -> when {
                f == null -> unknown
                f.level == Level.OK ->
                    facts?.rootKind?.takeIf { it != RootKind.NONE && it != RootKind.OTHER }?.let { ctx.getString(R.string.home_value_root_app, it.label) }
                        ?: ctx.getString(R.string.home_value_root_ok)
                f.reason == SwitchGates.R_ROOT_NO_SU && (facts == null || facts.rootKind == RootKind.NONE) -> ctx.getString(R.string.home_value_root_missing)
                else -> ctx.getString(R.string.home_value_root_denied)
            }
            SwitchGates.ID_SPACE -> {
                val free = facts?.storage?.freeBytes
                when {
                    f == null || free == null || f.reason == SwitchGates.R_SPACE_UNKNOWN -> unknown
                    f.level == Level.BLOCK -> ctx.getString(R.string.home_value_space_short, Units.bytes((SpaceRule.LAUNCH_BYTES - free).coerceAtLeast(0)))
                    setupNeed != null && free < setupNeed -> {
                        if (level == Level.OK) level = Level.WARN
                        ctx.getString(R.string.home_value_space_setup, Units.bytes(free), Units.bytes(setupNeed))
                    }
                    // 0.4.11: the old copies setup kept, which the tile then opens (Free up space).
                    oldCopies() > 0 -> ctx.getString(
                        R.string.home_value_space_old, Units.bytes(free),
                        ctx.resources.getQuantityString(R.plurals.home_space_old_copies, oldCopies(), oldCopies()),
                    )
                    else -> ctx.getString(R.string.home_value_space_free, Units.bytes(free))
                }
            }
            SwitchGates.ID_BATTERY -> facts?.battery?.let { b ->
                b.temperatureC?.let { t -> ctx.getString(R.string.home_value_battery, b.levelPercent, t.toInt()) }
                    ?: ctx.getString(R.string.home_value_battery_no_temp, b.levelPercent)
            } ?: unknown
            else -> when {
                f == null || f.reason == ScreenLockRule.R_UNKNOWN -> unknown
                f.level == Level.OK -> ctx.getString(R.string.home_value_lock_off)
                else -> ctx.getString(R.string.home_value_lock_on)
            }
        }
        val plain = f?.takeIf { it.level == Level.BLOCK || it.level == Level.WARN }?.let { Plain.of(it, r, facts) }
        return Tile(HomeCheck(id, level, value), f, plain)
    }

    private fun checks(activity: MainActivity, s: HomeState, tiles: List<Tile>?) {
        val card = checksCard ?: return
        val grid = checksGrid ?: return
        if (tiles == null) {
            card.visibility = View.GONE
            return
        }
        card.visibility = View.VISIBLE
        val levels = tiles.map { it.check.level }
        val allOk = levels.none { it == Level.WARN || it == Level.BLOCK }
        // While a check runs (or the kept Home is shown): "Checking…" with the One UI loader, not the count.
        val checking = s.checking || s.cached != null
        Cards.bindSection(
            card,
            getString(if (allOk) R.string.home_checks_ready else R.string.home_checks_fix),
            if (checking) getString(R.string.home_checks_checking) else getString(R.string.home_checks_count, levels.count { it == Level.OK }, tiles.size),
            if (checking) Level.INFO else Cards.worst(levels),
        )
        checksLoader?.visibility = if (checking) View.VISIBLE else View.GONE
        card.findViewById<TextView>(R.id.oneos_section_trailing)?.let { t ->
            (t.layoutParams as? ViewGroup.MarginLayoutParams)?.let { lp ->
                lp.marginStart = ((if (checking) 6 else 12) * resources.displayMetrics.density).toInt()
                t.layoutParams = lp
            }
        }
        Cards.setTiles(
            grid,
            tiles.map { t ->
                val c = t.check
                Cards.Tile(TILE_ICONS.getValue(c.id), getString(TILE_TITLES.getValue(c.id)), c.value, c.level)
            },
        )
        // A tile from the check opens its fix, else what was checked; the kept ones are only shown.
        val views = (0 until grid.childCount).flatMap { i ->
            val line = grid.getChildAt(i) as ViewGroup
            (0 until line.childCount).map { line.getChildAt(it) }
        }
        for ((t, v) in tiles.zip(views)) {
            val action = t.plain?.action?.takeIf { it != FixAction.NONE && it != FixAction.ACKNOWLEDGE }
                ?: FixAction.FREE_UP_SPACE.takeIf { t.check.id == SwitchGates.ID_SPACE && oldCopies() > 0 }
            val finding = t.finding
            if (s.cached != null || (action == null && finding == null)) continue
            v.foreground = selectableBackground(v.context)
            v.clipToOutline = true
            v.setOnClickListener {
                if (action != null) FixActions.run(activity, action, s.image) else if (finding != null) details(finding)
            }
        }
    }

    /** Old copies the stage check saw (stage.old: kept copies and unfinished deletes). */
    private fun oldCopies(): Int = StageCheck.state.result?.status?.oldStages?.size ?: 0

    // The whole tile when pressed (SESL's selectableItemBackground is a small centred circle).
    private fun selectableBackground(ctx: Context) = ctx.getDrawable(R.drawable.oneos_tile_ripple)

    // Setting up, Welcome back =================================================

    private fun progress(s: HomeState) {
        val card = progressCard ?: return
        if (s.kind != HomeState.Kind.SETTING_UP) {
            card.visibility = View.GONE
            return
        }
        card.visibility = View.VISIBLE
        card.findViewById<SeslProgressBar>(R.id.home_progress_bar).apply {
            setMax(100)
            setProgress(s.percent ?: 0)
            setProgressTintList(ColorStateList.valueOf(card.context.getColor(R.color.oneos_primary_text)))
        }
        card.findViewById<TextView>(R.id.home_progress_eta).text =
            PrepareJob.state.etaSeconds?.let { getString(R.string.home_eta, (it + 59) / 60) } ?: getString(R.string.home_eta_wait)
    }

    private fun welcome(s: HomeState) {
        val card = welcomeCard ?: return
        val last = s.last?.takeIf { s.kind == HomeState.Kind.WELCOME_BACK }
        val outcome = last?.outcome
        if (last == null || outcome == null) {
            card.visibility = View.GONE
            return
        }
        card.visibility = View.VISIBLE
        val system = Images.systemName(last.image)
        val test = last.dryRun || outcome == OutcomeKind.DRY_RUN
        Cards.bindSection(card, if (test) getString(R.string.home_welcome_card_test) else getString(R.string.home_welcome_card, system), null)
        val minutes = last.afterSeconds?.takeIf { it > 0 && !test }?.let { (it + 59) / 60 }
        timeTile?.let { t ->
            t.visibility = if (minutes != null) View.VISIBLE else View.GONE
            if (minutes != null) stat(t, getString(R.string.home_minutes, minutes), getString(R.string.home_welcome_in, system))
        }
        howTile?.let { t ->
            t.visibility = if (test) View.GONE else View.VISIBLE
            (t.layoutParams as? ViewGroup.MarginLayoutParams)?.let { lp ->
                lp.marginStart = if (minutes != null) resources.getDimension(R.dimen.oneos_tile_gap).toInt() else 0
                t.layoutParams = lp
            }
            stat(t, getString(howCameBack(outcome)), getString(R.string.home_welcome_how))
        }
    }

    private fun stat(tile: View, value: String, label: String) {
        tile.findViewById<TextView>(R.id.home_stat_value).text = value
        tile.findViewById<TextView>(R.id.home_stat_label).text = label
    }

    private fun howCameBack(o: OutcomeKind): Int = when (o) {
        OutcomeKind.USER_RETURN -> R.string.home_how_keys
        OutcomeKind.APP_RETURN -> R.string.home_how_app
        OutcomeKind.GUEST_REBOOT, OutcomeKind.GUEST_DEAD, OutcomeKind.BLACK_SCREEN, OutcomeKind.SESSION_LIMIT, OutcomeKind.BOOT_TIMEOUT ->
            R.string.home_how_auto
        OutcomeKind.HARD_RESET -> R.string.home_how_restart
        OutcomeKind.GUEST_SHUTDOWN -> R.string.home_how_off
        OutcomeKind.PREPARE_FAILED, OutcomeKind.REFUSED -> R.string.home_how_none
        OutcomeKind.DRY_RUN -> R.string.home_how_test
        OutcomeKind.UNKNOWN -> R.string.home_how_other
    }

    // Rows ===================================================================

    private fun rows(activity: MainActivity, s: HomeState) {
        val card = rowsCard ?: return
        // Child 0 is the card's (hidden) header; the rows follow it.
        while (card.childCount > 1) card.removeViewAt(card.childCount - 1)
        val ctx = card.context
        if (s.kind == HomeState.Kind.WELCOME_BACK) {
            // After a session that went wrong, the report first (personal info removed).
            if (s.last?.outcome?.good == false) {
                Cards.row(card, OuiIcons.drawable.ic_oui_share, getString(R.string.home_send_report), getString(R.string.home_send_report_summary)) {
                    val zip = LogJob.latestZip(ctx)
                    if (zip != null) {
                        startActivity(Intent(ctx, FindingsActivity::class.java).putExtra(FindingsActivity.EXTRA_ZIP, zip.path))
                    } else {
                        startActivity(Intent(ctx, LastSessionActivity::class.java))
                    }
                }
            }
            Cards.row(card, R.drawable.ic_home_row_session, getString(R.string.home_row_session), getString(R.string.home_row_session_summary)) {
                startActivity(Intent(ctx, LastSessionActivity::class.java))
            }
            return
        }
        // Setup that did not finish (it stopped, or a check refused it): its plain message.
        val prep = PrepareJob.state
        if (!prep.busy && (prep.phase == PrepareJob.Phase.FAILED || prep.phase == PrepareJob.Phase.STOPPED)) {
            prep.plain?.let { p ->
                val row = Cards.row(card, R.drawable.ic_oneos_row_systems, p.title, p.line) { startActivity(Intent(ctx, SetupProgressActivity::class.java)) }
                Cards.setRowEnd(row, Cards.badge(p.level))
            }
        }
        lastRow(card, s)
        otherSystems(activity, card, s)
        // Another system or a downloaded file; not while checking or working, nor when the main button does the same.
        val choosing = s.kind == HomeState.Kind.NOTHING_SET_UP && s.primary == FixAction.CHOOSE_SYSTEM
        if (s.kind != HomeState.Kind.CHECKING && s.kind !in BUSY && !choosing) {
            Cards.row(card, R.drawable.ic_oneos_row_systems, getString(R.string.home_row_systems), getString(R.string.home_row_systems_summary)) {
                FixActions.run(activity, FixAction.CHOOSE_SYSTEM, s.image)
            }
        }
        Cards.row(card, R.drawable.ic_oneos_row_advanced, getString(R.string.home_advanced), getString(R.string.home_row_advanced_summary)) {
            startActivity(Intent(ctx, AdvancedActivity::class.java))
        }
    }

    // Quick switch (0.4.30) =====================================================

    /**
     * One row per other system set up earlier on this phone: each copy OneOS
     * moved aside that holds a system this phone takes (the stage check reads
     * which, stage.old_images), newest first. A tap offers Switch to it
     * ([QuickSwitch]) or Delete it; the copy being put back shows as working.
     */
    private fun otherSystems(activity: MainActivity, card: LinearLayout, s: HomeState) {
        val ctx = card.context
        val r = StageCheck.state.result ?: return
        val status = r.status
        val profile = Profiles.resolve(r.facts).profile ?: return
        val pending = QuickSwitch.pending
        val copies = status.oldStages.map { it.substringAfterLast('/') }.distinct().mapNotNull { name ->
            status.oldImages[name]?.let { Images.byId(it) }?.takeIf { profile.choice(it.id) != null }?.let { name to it }
        }.sortedByDescending { setAside(it.first) ?: 0 }
        val working = s.kind == HomeState.Kind.CHECKING || s.kind in BUSY || OldStagesJob.state.busy || pending != null
        for ((name, image) in copies) {
            val since = setAside(name)?.let { getString(R.string.home_other_since, DateFormat.getMediumDateFormat(ctx).format(Date(it * 1000))) }
            if (pending?.copy == name) {
                CardRows.tint(
                    Cards.row(card, R.drawable.ic_oneos_row_systems, getString(R.string.home_other_getting_ready, image.name), getString(R.string.home_other_getting_ready_line)),
                    Level.INFO,
                )
                continue
            }
            CardRows.row(
                card, R.drawable.ic_oneos_row_systems, getString(R.string.home_other_switch, image.name),
                listOfNotNull(since, getString(R.string.home_other_kept)).joinToString(" · "),
                enabled = !working,
            ) { chooseOther(activity, name, image, since) }
        }
    }

    /** When the copy was set aside: the seconds in its name (oneos.old-<time>[-<pid>]). */
    private fun setAside(name: String): Long? = name.removePrefix("oneos.old-").substringBefore('-').toLongOrNull()

    private fun chooseOther(activity: MainActivity, name: String, image: ImageRef, since: String?) {
        val items = arrayOf(getString(R.string.home_other_switch, image.name), getString(R.string.space_choose_delete))
        AlertDialog.Builder(activity)
            .setTitle(listOfNotNull(image.name, since).joinToString(", "))
            .setItems(items) { _, i -> if (i == 0) confirmQuickSwitch(activity, name, image) else confirmDeleteOther(activity, name, image, since) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmQuickSwitch(activity: MainActivity, name: String, image: ImageRef) {
        val now = StageCheck.state.result?.status?.marker?.imageId?.let { Images.byId(it) }?.name ?: getString(R.string.home_other_current_unknown)
        AlertDialog.Builder(activity)
            .setTitle(getString(R.string.home_other_confirm_title, image.name))
            .setMessage(getString(R.string.home_other_confirm_message, image.name, now))
            .setPositiveButton(R.string.home_other_confirm_go) { _, _ ->
                QuickSwitch.start(activity, name, image.id)
                redraw()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmDeleteOther(activity: MainActivity, name: String, image: ImageRef, since: String?) {
        AlertDialog.Builder(activity)
            .setTitle(R.string.space_delete_title)
            .setMessage(getString(R.string.space_delete_message, getString(R.string.space_delete_what_of, image.name), since ?: name))
            .setPositiveButton(R.string.space_delete_run) { _, _ -> OldStagesJob.delete(activity, OldStage(name, 0, image.id, hasData = true, busy = false)) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /**
     * Quick switch's next step, from Home's redraw: once root has put the copy
     * back and a stage check that ended after it read that system, Update when
     * Home asks for it (once), else the Switch confirm; anything else (a check
     * to fix first) ends it, and Home shows the problem as usual.
     */
    private fun quickSwitch(activity: MainActivity, s: HomeState) {
        val p = QuickSwitch.pending ?: return
        val old = OldStagesJob.state
        if (old.phase == OldStagesJob.Phase.RESTORING) return
        if (old.restoreFailed) {
            QuickSwitch.cancel()
            AlertDialog.Builder(activity)
                .setTitle(R.string.home_other_failed)
                .setMessage(old.message ?: getString(R.string.space_not_restored_line))
                .setPositiveButton(android.R.string.ok, null)
                .show()
            return
        }
        if (!old.restored) return
        val check = StageCheck.state
        // Only a stage check that ended after the copy came back; one that failed, or read
        // another system, ends it (Home shows what it found).
        if (check.busy || PrepareJob.state.busy || check.endedAt <= old.restoredAt) return
        if (check.phase == StageCheck.Phase.FAILED || check.result?.status?.marker?.imageId != p.imageId) {
            QuickSwitch.cancel()
            return
        }
        when (s.primary) {
            FixAction.UPDATE -> if (!p.updateStarted) {
                p.updateStarted = true
                FixActions.run(activity, FixAction.UPDATE, s.image)
            } else {
                QuickSwitch.cancel()
            }
            FixAction.SWITCH -> {
                QuickSwitch.cancel()
                FixActions.run(activity, FixAction.SWITCH, s.image)
            }
            else -> QuickSwitch.cancel()
        }
    }

    /** "Last time": how long and how the last session ended (read by itself after a return), or that it is being read. */
    private fun lastRow(card: LinearLayout, s: HomeState) {
        val ctx = card.context
        val last = s.last ?: return
        val system = Images.systemName(last.image)
        val logs = LogJob.state
        val outcome = last.outcome
        val summary = when {
            logs.busy && !logs.recovering -> getString(R.string.home_row_last_reading)
            outcome != null -> listOfNotNull(
                last.afterSeconds?.takeIf { it > 0 && !last.dryRun }?.let {
                    getString(R.string.home_row_last_time, getString(R.string.home_minutes, (it + 59) / 60), system)
                },
                sentence(outcome.title(system)).trimEnd('.'),
            ).joinToString(" · ")
            last.over -> getString(R.string.home_row_last_unread, DateFormat.getMediumDateFormat(ctx).format(Date(last.wallMs)))
            else -> null
        } ?: return
        Cards.row(card, R.drawable.ic_oneos_row_last_time, getString(R.string.home_row_last), summary) {
            startActivity(Intent(ctx, LastSessionActivity::class.java))
        }
    }

    /** The cards stand 12dp apart; on the inner screen the first one is level with the hero card. */
    private fun spaceCards(root: View) {
        val cards = root.findViewById<LinearLayout>(R.id.home_cards) ?: return
        val gap = resources.getDimension(R.dimen.oneos_card_gap).toInt()
        var first = true
        for (i in 0 until cards.childCount) {
            val c = cards.getChildAt(i)
            if (c.visibility != View.VISIBLE) continue
            val lp = c.layoutParams as? ViewGroup.MarginLayoutParams ?: continue
            val top = if (first && twoPane) 0 else gap
            if (lp.topMargin != top) {
                lp.topMargin = top
                c.layoutParams = lp
            }
            first = false
        }
    }

    // The main button ==========================================================

    private fun <T : View> find(id: Int): T? = view?.findViewById<T>(id) ?: activity?.findViewById<T>(id)

    private fun footer(activity: MainActivity, s: HomeState) {
        val primary = find<Button>(R.id.home_primary) ?: return
        val action = s.primary
        if (action == null) {
            primary.visibility = View.GONE
        } else {
            primary.visibility = View.VISIBLE
            val again = s.kind == HomeState.Kind.WELCOME_BACK && s.last?.dryRun == false
            primary.text = if (again) getString(R.string.home_switch_again) else s.primaryLabel ?: Plain.defaultLabel(action)
            // Off while a check or a job runs, and always on the kept Home (HomeState).
            primary.isEnabled = s.primaryEnabled
            primary.setOnClickListener { FixActions.run(activity, action, s.image) }
        }
        find<TextView>(R.id.home_caption)?.let { c ->
            val text = when (s.kind) {
                HomeState.Kind.READY -> getString(R.string.home_caption_switch)
                HomeState.Kind.FIX -> s.problem?.line
                HomeState.Kind.NOTHING_SET_UP -> if (s.primary == FixAction.SET_UP) getString(R.string.home_caption_setup) else null
                else -> null
            }
            c.text = text
            c.visibility = if (text.isNullOrEmpty()) View.GONE else View.VISIBLE
        }
        val secondary = find<Button>(R.id.home_secondary) ?: return
        val last = s.last
        val finding = s.finding?.takeIf { s.problem != null }
        when {
            s.kind == HomeState.Kind.WELCOME_BACK && last != null -> {
                secondary.visibility = View.VISIBLE
                secondary.setText(R.string.home_done)
                secondary.setOnClickListener {
                    SessionPrefs.setWelcomeSeen(activity, last.sessionId)
                    redraw()
                }
            }
            finding != null -> {
                secondary.visibility = View.VISIBLE
                secondary.setText(R.string.home_details)
                secondary.setOnClickListener { details(finding) }
            }
            else -> {
                secondary.visibility = View.GONE
                secondary.setOnClickListener(null)
            }
        }
    }

    /** Root (or a gate) refused the switch: once, as a dialog with the fix (the redesign, section 2.5). */
    private fun refusalDialog(activity: MainActivity) {
        val st = LaunchJob.state
        if (st.phase != LaunchJob.Phase.FAILED || st === shownRefusal) return
        shownRefusal = st
        val plain = st.plain ?: PlainMessage(getString(R.string.switch_not_started), st.message.orEmpty().take(PlainMessage.MAX_LINE), FixAction.NONE, null)
        val b = AlertDialog.Builder(activity)
            .setTitle(plain.title)
            .setMessage(plain.line + "\n\n" + getString(R.string.confirm_refused_tail))
            .setOnDismissListener { LaunchJob.clear() }
        val label = plain.actionLabel
        if (label != null && plain.action != FixAction.NONE && plain.action != FixAction.ACKNOWLEDGE) {
            b.setPositiveButton(label) { _, _ -> FixActions.run(activity, plain.action, st.image) }
            b.setNegativeButton(android.R.string.cancel, null)
        } else {
            b.setPositiveButton(android.R.string.ok, null)
        }
        st.finding?.let { f -> b.setNeutralButton(R.string.home_details) { _, _ -> details(f) } }
        b.show()
    }

    /** Details: the technical finding, and All checks (All checks and Test run, SwitchActivity). */
    private fun details(f: Finding) {
        val ctx = requireContext()
        AlertDialog.Builder(ctx)
            .setTitle(f.title)
            .setMessage(f.detail.ifEmpty { f.title })
            .setPositiveButton(android.R.string.ok, null)
            .setNeutralButton(R.string.home_details_all) { _, _ -> startActivity(Intent(ctx, SwitchActivity::class.java)) }
            .show()
    }

    private fun sentence(t: String): String = if (t.endsWith('.')) t else "$t."

    private companion object {
        val BUSY = setOf(HomeState.Kind.SETTING_UP, HomeState.Kind.SWITCHING, HomeState.Kind.RESTORING)

        /** The hero's line has the loader. */
        val WORKING = setOf(HomeState.Kind.CHECKING, HomeState.Kind.SWITCHING, HomeState.Kind.RESTORING)

        /** The states with the check tiles (owner, 2026-10-24: before a setup too, so a problem shows before the 15 minutes). */
        val SHOWS_CHECKS = setOf(HomeState.Kind.READY, HomeState.Kind.FIX, HomeState.Kind.UPDATE, HomeState.Kind.NOTHING_SET_UP)

        /** Root, space, battery, screen lock: the tiles, in the mockup's order. */
        val TILE_GATES = listOf(SwitchGates.ID_ROOT, SwitchGates.ID_SPACE, SwitchGates.ID_BATTERY, SwitchGates.ID_SCREEN_LOCK)

        val TILE_ICONS = mapOf(
            SwitchGates.ID_ROOT to R.drawable.ic_oneos_check_root,
            SwitchGates.ID_SPACE to R.drawable.ic_oneos_check_space,
            SwitchGates.ID_BATTERY to R.drawable.ic_oneos_check_battery,
            SwitchGates.ID_SCREEN_LOCK to R.drawable.ic_oneos_check_lock,
        )

        val TILE_TITLES = mapOf(
            SwitchGates.ID_ROOT to R.string.home_tile_root,
            SwitchGates.ID_SPACE to R.string.home_tile_space,
            SwitchGates.ID_BATTERY to R.string.home_tile_battery,
            SwitchGates.ID_SCREEN_LOCK to R.string.home_tile_lock,
        )
    }
}
