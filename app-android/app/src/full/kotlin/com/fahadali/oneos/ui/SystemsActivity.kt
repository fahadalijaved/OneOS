package com.fahadali.oneos.ui

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContract
import androidx.annotation.StringRes
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.AndroidRelease
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.ImageIdentifier
import com.fahadali.oneos.core.model.ImageIdentity
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.session.LaunchJob
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.QuickSwitch
import com.fahadali.oneos.session.Readiness
import com.fahadali.oneos.session.PrepareJob
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck
import java.util.concurrent.Executors
import dev.oneuiproject.oneui.R as OuiIcons

/** Figma's height-adaptive catalogue. File identity, setup jobs and launch gates retain their existing paths. */
open class SystemsActivity : ToolbarActivity() {
    // The bar shows the title only once the hero has scrolled away (setBarTitle).
    override val screenTitle: CharSequence get() = getString(R.string.app_name)

    override val layoutRes: Int get() = R.layout.activity_systems

    override fun createFragment(): Fragment = SystemsFragment()

    private lateinit var pick: ActivityResultLauncher<Unit>

    /** The system whose "I have the file" opened the picker (kept across recreation). */
    private var pickFor: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        pick = registerForActivityResult(SystemsNav.OpenGz()) { uri -> if (uri != null) picked(uri) }
        pickFor = savedInstanceState?.getString(KEY_PICK_FOR)
        super.onCreate(savedInstanceState)
        ArtworkTransitions.prepare(this)
        toolbarLayout.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbarLayout.setEdgeInsetHorizontal(0f)
        findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0
            fillHorizontalPadding = false
        }
        findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
    }

    override fun onActivityReenter(resultCode: Int, data: Intent?) {
        super.onActivityReenter(resultCode, data)
        postponeEnterTransition()
        val root = findViewById<View>(R.id.fragment_container)
        root.viewTreeObserver.addOnPreDrawListener(object : android.view.ViewTreeObserver.OnPreDrawListener {
            override fun onPreDraw(): Boolean {
                root.viewTreeObserver.removeOnPreDrawListener(this)
                startPostponedEnterTransition()
                return true
            }
        })
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        pickFor?.let { outState.putString(KEY_PICK_FOR, it) }
    }

    fun setBarTitle(text: CharSequence) {
        toolbarLayout.setTitle(text)
    }

    /** "I have the file" of [imageId] (null: whichever system it is). */
    fun choose(imageId: String?) {
        pickFor = imageId
        try {
            pick.launch(Unit)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    /** The same as the OS image page: a persistable read grant, the name and size, the source = this file. */
    private fun picked(uri: Uri) {
        runCatching { contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
        var name: String? = null
        var size: Long? = null
        runCatching {
            contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    name = c.getString(0)
                    size = if (c.isNull(1)) null else c.getLong(1)
                }
            }
        }
        SessionPrefs.setPicked(this, uri, name, size)
        SessionPrefs.setSource(this, SessionPrefs.Source.GZ)
        (supportFragmentManager.findFragmentById(R.id.fragment_container) as? SystemsFragment)?.afterPick(pickFor)
    }

    private companion object {
        const val KEY_PICK_FOR = "pick_for"
    }
}

/** Navigation shared by Choose a system and Setting up. */
internal object SystemsNav {
    /** Back to Home (the instance already open, else a new one), closing the screens above it. */
    fun home(a: Activity, image: ImageRef? = null) {
        a.startActivity(Intent(a, MainActivity::class.java).putExtra("system_detail", true).putExtra("system_name", image?.name).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        a.finish()
    }

    fun progress(a: Activity) {
        a.startActivity(Intent(a, SetupProgressActivity::class.java))
    }

    /** "Download": the shared link in the browser (no in-app download). */
    fun open(a: Activity, url: String) {
        try {
            a.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addCategory(Intent.CATEGORY_BROWSABLE))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(a, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(a, R.string.fix_no_app, Toast.LENGTH_LONG).show()
        }
    }

    /** ACTION_OPEN_DOCUMENT for the .img.gz (any type: providers label .gz differently), as the OS image page. */
    class OpenGz : ActivityResultContract<Unit, Uri?>() {
        override fun createIntent(context: Context, input: Unit): Intent =
            Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("*/*")
                .putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/gzip", "application/x-gzip", "application/octet-stream", "*/*"))

        override fun parseResult(resultCode: Int, intent: Intent?): Uri? = if (resultCode == Activity.RESULT_OK) intent?.data else null
    }
}

class SystemsFragment : Fragment() {
    private val io = Executors.newSingleThreadExecutor()
    private val subs = mutableListOf<() -> Unit>()
    private var profile: PhoneProfile? = null
    private var profileRead = false
    private var lastKey: List<Any?>? = null
    private var snapHelper: androidx.recyclerview.widget.PagerSnapHelper? = null
    private var revealed = false
    private var initialDraw: android.view.ViewTreeObserver.OnPreDrawListener? = null
    private var currentEntries: List<CatalogEntry> = emptyList()
    private var viewportKey: List<Int>? = null
    private var navigatingAway = false
    private var swiping = false
    private var swipeStart = androidx.recyclerview.widget.RecyclerView.NO_POSITION

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.systems_screen, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        val carousel = view.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)
        navigatingAway = false
        carousel.alpha = 0f
        carousel.translationY = dp(6).toFloat()
        carousel.itemAnimator = null
        lastKey = null
        viewportKey = null
        carousel.viewTreeObserver.addOnGlobalLayoutListener {
            // Fold/unfold can change ancestor clipping or insets without changing
            // RecyclerView's own bounds in the same frame.
            val key = listOf(carousel.width, carousel.height, visibleCardHeight(carousel),
                if (resources.getBoolean(R.bool.home_two_pane)) 1 else 0)
            if (key != viewportKey) {
                viewportKey = key
                carousel.post { resizeVisibleCards(carousel) }
            }
        }
        carousel.addOnLayoutChangeListener { _, left, top, right, bottom, oldLeft, oldTop, oldRight, oldBottom ->
            scaleCards(carousel)
            if (right - left != oldRight - oldLeft || bottom - top != oldBottom - oldTop) {
                carousel.post { resizeVisibleCards(carousel) }
            }
        }
        carousel.addOnScrollListener(object : androidx.recyclerview.widget.RecyclerView.OnScrollListener() {
            override fun onScrolled(rv: androidx.recyclerview.widget.RecyclerView, dx: Int, dy: Int) = scaleCards(rv)
            override fun onScrollStateChanged(rv: androidx.recyclerview.widget.RecyclerView, state: Int) {
                val layout = rv.layoutManager ?: return
                if (state == androidx.recyclerview.widget.RecyclerView.SCROLL_STATE_DRAGGING) {
                    swiping = true
                    swipeStart = snapHelper?.findSnapView(layout)?.let(layout::getPosition) ?: androidx.recyclerview.widget.RecyclerView.NO_POSITION
                }
                if (state == androidx.recyclerview.widget.RecyclerView.SCROLL_STATE_IDLE && swiping) rv.post {
                    if (rv.scrollState != androidx.recyclerview.widget.RecyclerView.SCROLL_STATE_IDLE || !swiping) return@post
                    val selected = snapHelper?.findSnapView(layout)?.let(layout::getPosition)
                    if (selected != null && currentEntries.isNotEmpty()) currentEntries[selected % currentEntries.size].image?.let { CarouselSelection.remember(rv.context, it) }
                    if (selected != null && selected != swipeStart) {
                        val samsungTick = if (androidx.reflect.DeviceInfo.isOneUI())
                            androidx.reflect.view.SeslHapticFeedbackConstantsReflector.semGetVibrationIndex(41) else -1
                        val accepted = if (samsungTick >= 0 && rv.performHapticFeedback(samsungTick)) true
                            else rv.performHapticFeedback(android.view.HapticFeedbackConstants.CLOCK_TICK)
                        if (com.fahadali.oneos.BuildConfig.DEBUG) android.util.Log.d("OneOSCarousel", "Settled card tick: $selected accepted=$accepted samsung=$samsungTick")
                    }
                    swiping = false
                }
            }
        })

        // This phone: from the last check when there is one, else read now (no root), as the OS image page does.
        StageCheck.state.result?.facts?.let { f -> Profiles.resolve(f).profile }?.let {
            profile = it
            profileRead = true
        }
        if (!profileRead) {
            val app = requireContext().applicationContext
            io.execute {
                val f = runCatching { FactProbe(app).collect(RootProbe(app).signals()) }.getOrNull()
                val p = f?.let { Profiles.resolve(it).profile }
                activity?.runOnUiThread {
                    profile = p
                    profileRead = true
                    redraw(force = true)
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        Readiness.onResume(requireContext())
        com.fahadali.oneos.session.AppUpdater.check(requireContext())
        if (navigatingAway) {
            // Keep the mapped source attached until the 280 ms shared return finishes.
            view?.postDelayed({
                if (isResumed) {
                    navigatingAway = false
                    view?.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)?.suppressLayout(false)
                    redraw(force = true)
                }
            }, 500)
        } else redraw(force = true)
    }

    override fun onStart() {
        super.onStart()
        // A finished check also reads the last session's logs (Readiness.tick), as Home does.
        subs += StageCheck.observe { if (!it.busy) context?.let(Readiness::tick); redraw() }
        subs += com.fahadali.oneos.session.AppUpdater.observe { updateLine() }
        subs += PrepareJob.observe { redraw() }
        subs += OldStagesJob.observe { redraw() }
        subs += com.fahadali.oneos.session.RemoveJob.observe { redraw() }
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
    }

    override fun onDestroyView() {
        view?.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)?.let { rv ->
            initialDraw?.let { rv.viewTreeObserver.removeOnPreDrawListener(it) }
            rv.animate().cancel()
        }
        initialDraw = null; revealed = false; currentEntries = emptyList()
        snapHelper?.attachToRecyclerView(null); snapHelper = null
        super.onDestroyView()
    }

    override fun onDestroy() {
        io.shutdownNow()
        super.onDestroy()
    }

    /** After the file picker: a good pick goes back to Home (nothing set up) or shows "Set up {system}" here; a bad one says why. */
    fun afterPick(cardId: String?) {
        val ctx = context ?: return
        val a = activity as? SystemsActivity ?: return
        val p = profile
        val file = SessionPrefs.picked(ctx)
        if (p == null || file == null) {
            redraw(force = true)
            return
        }
        val good = FixActions.pickedImage(ctx, p)
        if (good == null) {
            redraw(force = true)
            badPick(a, p, ImageIdentifier.identify(file.check, p), cardId)
            return
        }
        if (cardId != null && good.id != cardId) {
            Toast.makeText(ctx, getString(R.string.systems_pick_other, Images.systemName(good, p)), Toast.LENGTH_LONG).show()
        }
        // Home offers "Set up {system}" only while nothing is set up. With another system set up, the
        // file goes straight to the set-up confirmation (0.4.49, owner: "the hero card keeps saying Set up
        // over and over, like it doesn't accept the gz": the card only redrew and asked for the file again).
        val st = StageCheck.state.result?.status
        when {
            PrepareJob.state.busy -> redraw(force = true)
            st?.ours == true -> {
                redraw(force = true)
                FixActions.run(a, FixAction.SET_UP, good)
            }
            else -> SystemsNav.home(a)
        }
    }

    private fun badPick(a: SystemsActivity, p: PhoneProfile, id: ImageIdentity, cardId: String?) {
        val card = cardId?.let { cid -> p.images().firstOrNull { it.id == cid } }
        val b = AlertDialog.Builder(a)
        if (id.finding.reason == ImageIdentifier.R_SIZE_UNKNOWN) {
            // Only reading the whole file tells what it is: Check file on the file page.
            b.setTitle(R.string.systems_size_unknown_title)
                .setMessage(R.string.systems_size_unknown_line)
                .setPositiveButton(R.string.systems_open_file_page) { _, _ -> startActivity(Intent(a, ImageActivity::class.java)) }
        } else {
            val plain = Plain.of(id.finding, id.image ?: card, p)
            b.setTitle(plain.title).setMessage(plain.line)
            val label = plain.actionLabel
            if (label != null) {
                when (plain.action) {
                    FixAction.CHOOSE_FILE -> b.setPositiveButton(label) { _, _ -> a.choose(cardId) }
                    FixAction.DOWNLOAD_AGAIN -> (id.image ?: card)?.mirrorUrl?.let { url ->
                        b.setPositiveButton(label) { _, _ -> SystemsNav.open(a, url) }
                    }
                    else -> Unit
                }
            }
        }
        b.setNegativeButton(R.string.systems_close, null).show()
    }

    /**
     * The line under the title (0.4.43, UX audit: the launch screen never showed a new OneOS, only the status
     * Home did): a newer OneOS with its progress, tap to update; else the no-phone line when this phone is
     * not supported; else hidden.
     */
    private fun updateLine() {
        val root = view ?: return
        val ctx = context ?: return
        val line = root.findViewById<TextView>(R.id.systems_hero_subtitle)
        val banner = root.findViewById<View>(R.id.systems_update_banner)
        val u = com.fahadali.oneos.session.AppUpdater.state
        val next = u.update?.takeIf { it.newerThan(com.fahadali.oneos.BuildConfig.VERSION_CODE) }
        if (next != null && banner != null) {
            // 0.4.47 (owner: "the update bar is so small on the main page"): a banner with the version,
            // what it fixes or its progress, and an Update button; the whole card is the tap target.
            val system = EnvironmentNavigation.preparedImage(ctx)?.takeIf { next.changes(it.id) }
            root.findViewById<TextView>(R.id.systems_update_title).text = getString(R.string.systems_update_banner_title, next.versionName)
            root.findViewById<TextView>(R.id.systems_update_text).text = when (u.phase) {
                com.fahadali.oneos.session.AppUpdater.Phase.DOWNLOADING -> getString(R.string.home_update_downloading, u.percent)
                com.fahadali.oneos.session.AppUpdater.Phase.INSTALLING -> getString(R.string.home_app_update_installing)
                com.fahadali.oneos.session.AppUpdater.Phase.FAILED -> getString(R.string.systems_update_banner_failed)
                com.fahadali.oneos.session.AppUpdater.Phase.CONFIRM -> getString(R.string.systems_update_banner_confirm)
                else -> next.notes ?: system?.let { getString(R.string.systems_update_banner_for, it.name) }
                    ?: getString(R.string.systems_update_banner_default)
            }
            val action = root.findViewById<TextView>(R.id.systems_update_action)
            action.text = getString(
                when (u.phase) {
                    com.fahadali.oneos.session.AppUpdater.Phase.FAILED -> R.string.systems_update_action_retry
                    com.fahadali.oneos.session.AppUpdater.Phase.CONFIRM -> R.string.systems_update_action_confirm
                    else -> R.string.systems_update_action
                },
            )
            action.visibility = if (u.busy) View.GONE else View.VISIBLE
            val go = View.OnClickListener { activity?.let { if (!com.fahadali.oneos.session.AppUpdater.state.busy) FixActions.confirmAppUpdate(it) } }
            banner.setOnClickListener(go)
            action.setOnClickListener(go)
            banner.isClickable = !u.busy
            banner.contentDescription = root.findViewById<TextView>(R.id.systems_update_title).text.toString() + ". " +
                root.findViewById<TextView>(R.id.systems_update_text).text
            banner.visibility = View.VISIBLE
            line.setOnClickListener(null)
            line.visibility = View.GONE
            return
        }
        banner?.visibility = View.GONE
        line.setOnClickListener(null)
        line.isClickable = false
        if (profileRead && profile == null) {
            line.text = getString(R.string.systems_none_line)
            line.visibility = View.VISIBLE
        } else {
            line.visibility = View.GONE
        }
    }

    private fun redraw(force: Boolean = false) {
        if (navigatingAway) return
        val root = view ?: return
        val ctx = context ?: return
        val p = profile
        val check = StageCheck.state
        val prep = PrepareJob.state
        val picked = SessionPrefs.picked(ctx)
        val jobsBusy = prep.busy || LaunchJob.state.busy || LogJob.state.busy || OldStagesJob.state.busy || com.fahadali.oneos.session.RemoveJob.state.busy
        // PrepareJob reports every few MB: redraw only when something on the cards changes.
        val key = listOf(
            p?.id, profileRead, check.busy, check.result?.at, prep.phase, prep.image?.id,
            picked?.uri, picked?.sha256, jobsBusy, resources.configuration.screenWidthDp,
        )
        if (key == lastKey && root.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel).adapter != null) return
        lastKey = key

        updateLine()
        val carousel = root.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)
        val available = p?.images().orEmpty()
        val st = check.result?.status
        val rememberedImage = EnvironmentNavigation.preparedImage(ctx)
        val setUpId = st?.marker?.takeIf { st.ours && it.profileId == p?.id }?.imageId
            ?: check.result?.takeIf { it.status.partial }?.let(ImageMaintenance::identifiedImage)?.id
            ?: rememberedImage?.id?.takeIf { st?.complete != true }
        val maintenance = rememberedImage?.let { ImageMaintenance.message(ctx, it, check.result) }
        val pickedId = p?.let { FixActions.pickedImage(ctx, it)?.id }
        val settingUpId = prep.image?.id?.takeIf { prep.busy }
        fun image(family: com.fahadali.oneos.core.model.SystemFamily, fallback: ImageRef): ImageRef =
            available.firstOrNull { it.family == family && it.id == setUpId }
                ?: available.firstOrNull { it.family == family && it.id in st?.oldImages.orEmpty().values }
                ?: rememberedImage?.takeIf { it.family == family && it.id == setUpId }
                ?: available.firstOrNull { it.family == family } ?: fallback
        val color = image(com.fahadali.oneos.core.model.SystemFamily.COLOROS, Images.FIND_N6)
        val pixel = image(com.fahadali.oneos.core.model.SystemFamily.PIXEL, Images.PIXEL_YOGI)
        val infinity = image(com.fahadali.oneos.core.model.SystemFamily.INFINITYX, Images.INFINITYX)
        val hyper = image(com.fahadali.oneos.core.model.SystemFamily.HYPEROS, Images.HYPEROS_LHASA)
        val nothing = image(com.fahadali.oneos.core.model.SystemFamily.NOTHING, Images.NOTHING_METROID)
        val oxygen = image(com.fahadali.oneos.core.model.SystemFamily.OXYGENOS, Images.OXYGEN16)
        val origin = image(com.fahadali.oneos.core.model.SystemFamily.ORIGINOS, Images.ORIGINOS7)
        // OxygenOS 16 (Android 16, 0.4.67) only where the phone can take it (One UI 8), and first there.
        val entries = listOfNotNull(
            CatalogEntry(oxygen.name, oxygen, R.drawable.os_oxygenos, true).takeIf { available.any { it.id == oxygen.id } },
            // OriginOS 7 (0.4.73, experimental) only on its phones (the Snapdragon S23 to S26 series, the Exynos S24 and S24+, and Z Fold7/8).
            CatalogEntry(origin.name, origin, R.drawable.os_originos, true).takeIf { available.any { it.id == origin.id } },
            CatalogEntry(infinity.name, infinity, R.drawable.os_infinity, available.any { it.id == infinity.id }),
            CatalogEntry(hyper.name, hyper, R.drawable.os_hyperos, available.any { it.id == hyper.id }),
            CatalogEntry(color.name, color, R.drawable.os_coloros, available.any { it.id == color.id }),
            CatalogEntry(nothing.name, nothing, R.drawable.os_nothing, available.any { it.id == nothing.id }),
            CatalogEntry(pixel.name, pixel, R.drawable.os_pixel, available.any { it.id == pixel.id }),
        )


        currentEntries = entries
        val state = if (revealed) carousel.layoutManager?.onSaveInstanceState() else null
        carousel.adapter = object : androidx.recyclerview.widget.RecyclerView.Adapter<CarouselHolder>() {
            override fun getItemCount() = Int.MAX_VALUE
            override fun onCreateViewHolder(parent: ViewGroup, type: Int): CarouselHolder =
                CarouselHolder(android.widget.FrameLayout(parent.context))
            override fun onBindViewHolder(holder: CarouselHolder, position: Int) {
                val entry = entries[position % entries.size]
                val image = entry.image
                holder.box.removeAllViews()
                val (width, height) = cardSize(carousel)
                val verticalInset = ((visibleCardHeight(carousel) - height) / 2).coerceAtLeast(0)
                holder.box.layoutParams = androidx.recyclerview.widget.RecyclerView.LayoutParams(width, height).apply {
                    marginStart = cardSideMargin(); marginEnd = cardSideMargin()
                    topMargin = verticalInset; bottomMargin = verticalInset
                }
                holder.box.addView(card(holder.box, p, entry, position,
                    image?.id == setUpId && setUpId != null, image?.id == pickedId && pickedId != null, image?.id == settingUpId && settingUpId != null, prep.busy, jobsBusy, maintenance?.takeIf { image?.id == setUpId }, st?.oldImages?.entries?.firstOrNull { it.value == image?.id }?.key))
            }
        }
        if (carousel.layoutManager == null) {
            carousel.layoutManager = androidx.recyclerview.widget.LinearLayoutManager(ctx, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false)
            snapHelper = androidx.recyclerview.widget.PagerSnapHelper().also { it.attachToRecyclerView(carousel) }
        }
        if (state != null) carousel.layoutManager?.onRestoreInstanceState(state)
        if (!revealed) {
            initialDraw?.let { carousel.viewTreeObserver.removeOnPreDrawListener(it) }
            val family = CarouselSelection.family(ctx)
            val selected = entries.indexOfFirst { it.image?.family == family }.takeIf { it >= 0 } ?: 2
            val target = Int.MAX_VALUE / 2 - (Int.MAX_VALUE / 2 % entries.size) + selected
            initialDraw = object : android.view.ViewTreeObserver.OnPreDrawListener {
                override fun onPreDraw(): Boolean {
                    val manager = carousel.layoutManager as? androidx.recyclerview.widget.LinearLayoutManager ?: return true
                    if (carousel.width == 0 || carousel.height == 0) return false
                    val card = manager.findViewByPosition(target)
                    if (card == null) {
                        val (width, _) = cardSize(carousel)
                        manager.scrollToPositionWithOffset(target, (carousel.width - width - 2 * cardSideMargin()) / 2)
                        carousel.postInvalidateOnAnimation()
                        return false
                    }
                    val distance = snapHelper?.calculateDistanceToFinalSnap(manager, card)
                    if (distance != null && (distance[0] != 0 || distance[1] != 0)) {
                        carousel.scrollBy(distance[0], distance[1])
                        carousel.postInvalidateOnAnimation()
                        return false
                    }
                    carousel.viewTreeObserver.removeOnPreDrawListener(this)
                    initialDraw = null
                    revealed = true
                    scaleCards(carousel)
                    carousel.animate().alpha(1f).translationY(0f).setDuration(220)
                        .setInterpolator(android.view.animation.DecelerateInterpolator()).start()
                    return true
                }
            }.also { carousel.viewTreeObserver.addOnPreDrawListener(it) }
        }
    }

    /** Continuous, layout-independent emphasis; snapping still uses the unscaled card bounds. */
    private fun scaleCards(carousel: androidx.recyclerview.widget.RecyclerView) {
        val centre = carousel.paddingLeft + (carousel.width - carousel.paddingLeft - carousel.paddingRight) / 2f
        for (index in 0 until carousel.childCount) {
            val child = carousel.getChildAt(index)
            if (child.width == 0) continue
            val params = child.layoutParams as androidx.recyclerview.widget.RecyclerView.LayoutParams
            val step = child.width + params.leftMargin + params.rightMargin
            val distance = (kotlin.math.abs((child.left + child.right) / 2f - centre) / step).coerceIn(0f, 1f)
            val eased = distance * distance * (3f - 2f * distance)
            val scale = 1f - .08f * eased
            child.pivotX = child.width / 2f
            child.pivotY = child.height / 2f
            child.scaleX = scale
            child.scaleY = scale
        }
    }

    private data class CatalogEntry(val name: String, val image: ImageRef?, val art: Int, val supported: Boolean)

    private class CarouselHolder(val box: android.widget.FrameLayout) : androidx.recyclerview.widget.RecyclerView.ViewHolder(box)

    private fun card(
        parent: ViewGroup,
        p: PhoneProfile?,
        entry: CatalogEntry,
        index: Int,
        setUp: Boolean,
        picked: Boolean,
        settingUp: Boolean,
        prepBusy: Boolean,
        jobsBusy: Boolean,
        maintenance: com.fahadali.oneos.core.model.PlainMessage?,
        savedCopy: String?,
    ): View {
        val ctx = parent.context
        val inflater = LayoutInflater.from(ctx)
        val v = inflater.inflate(R.layout.systems_card, parent, false)
        val image = entry.image
        v.contentDescription = entry.name
        v.isScreenReaderFocusable = true
        v.findViewById<OsArtworkView>(R.id.systems_artwork).apply {
            if (entry.art != 0) bindArtwork(entry.art) else bind(image)
        }
        val badge = v.findViewById<TextView>(R.id.systems_badge)
        badge.text = getString(when {
            !entry.supported -> R.string.catalog_unsupported
            p?.choice(image?.id.orEmpty())?.tested == true -> R.string.catalog_optimised
            else -> R.string.catalog_experimental
        })
        badge.setCompoundDrawablesRelativeWithIntrinsicBounds(R.drawable.ic_catalog_device, 0, 0, 0)
        badge.compoundDrawablePadding = dp(8)
        // Not for this phone (0.4.43, UX audit): an Unsupported card used to run the whole setup flow and send
        // people to a download of several GB. Its button now says so, and nothing else on it starts setup.
        if (image == null || !entry.supported) {
            v.findViewById<Button>(R.id.systems_primary).apply {
                setText(R.string.catalog_not_available)
                setOnClickListener { showUnsupported(entry.name) }
            }
            v.setOnClickListener { showUnsupported(entry.name) }
            v.findViewById<View>(R.id.systems_more).setOnClickListener { showUnsupported(entry.name) }
            return v
        }
        val primary = v.findViewById<Button>(R.id.systems_primary)
        v.findViewById<View>(R.id.systems_more).setOnClickListener { anchor ->
            androidx.appcompat.widget.PopupMenu(ctx, anchor).apply {
                menu.add(R.string.systems_download).setOnMenuItemClickListener { activity?.let { SystemsNav.open(it, image.mirrorUrl) }; true }
                image.downloadUrl?.let { drive ->
                    menu.add(R.string.systems_download_drive).setOnMenuItemClickListener { activity?.let { SystemsNav.open(it, drive) }; true }
                }
                menu.add(R.string.systems_have_file).setOnMenuItemClickListener { (activity as? SystemsActivity)?.choose(image.id); true }
                menu.add(R.string.systems_phone_status).setOnMenuItemClickListener {
                    startActivity(Intent(ctx, MainActivity::class.java).putExtra("system_detail", true)); true
                }
                menu.add(R.string.catalog_details).setOnMenuItemClickListener {
                    AlertDialog.Builder(ctx).setTitle(image.displayName).setMessage(image.blurb + "\n\n" + image.variant.orEmpty() + "\n" + Units.bytes(image.gzBytes)).setPositiveButton(android.R.string.ok, null).show(); true
                }
            }.show()
        }
        val a = activity as? SystemsActivity
        fun makeCardClickable(description: CharSequence, enabled: Boolean, onClick: () -> Unit) {
            v.isFocusable = true
            v.isEnabled = enabled
            v.contentDescription = description
            val attributes = ctx.obtainStyledAttributes(intArrayOf(androidx.appcompat.R.attr.colorControlHighlight))
            val highlight = attributes.getColorStateList(0) ?: android.content.res.ColorStateList.valueOf(0)
            attributes.recycle()
            v.foreground = android.graphics.drawable.RippleDrawable(highlight, v.foreground,
                androidx.appcompat.content.res.AppCompatResources.getDrawable(ctx, R.drawable.catalog_card_bg))
            v.setOnClickListener { CarouselSelection.remember(ctx, image); onClick() }
        }
        fun only(text: CharSequence, enabled: Boolean, onCardClick: (() -> Unit)? = null, onClick: () -> Unit) {
            primary.visibility = View.VISIBLE
            primary.text = text
            primary.isEnabled = enabled
            primary.setOnClickListener { CarouselSelection.remember(ctx, image); onClick() }
            makeCardClickable("$text ${image.nameWithVariant}", if (onCardClick != null) true else enabled, onCardClick ?: onClick)
        }
        fun openCard(onClick: () -> Unit) {
            primary.visibility = View.GONE
            makeCardClickable(getString(R.string.catalog_open_checks, image.nameWithVariant), true, onClick)
        }
        when {
            settingUp -> only(getString(R.string.systems_show_progress), true) { a?.let { startArtwork(it, Intent(it, SetupProgressActivity::class.java), v.findViewById(R.id.systems_artwork)) } }
            setUp && maintenance != null -> only(maintenance.actionLabel ?: getString(R.string.catalog_update),
                !jobsBusy && StageCheck.state.phase == StageCheck.Phase.DONE,
                onCardClick = { a?.let { startArtwork(it, EnvironmentNavigation.intent(it, image), v.findViewById(R.id.systems_artwork)) } }) {
                a?.let {
                    if (maintenance.action == FixAction.SET_UP_AGAIN) askDownloaded(image, v.findViewById(R.id.systems_artwork))
                    else FixActions.run(it, maintenance.action, image)
                }
            }
            setUp -> openCard { a?.let { startArtwork(it, EnvironmentNavigation.intent(it, image), v.findViewById(R.id.systems_artwork)) } }
            savedCopy != null -> only(getString(R.string.catalog_switch), !jobsBusy && !StageCheck.state.busy) {
                val current = StageCheck.state.result?.status?.marker?.imageId?.let { Images.byId(it) }?.name ?: getString(R.string.home_other_current_unknown)
                AlertDialog.Builder(ctx).setTitle(getString(R.string.home_other_confirm_title, image.name))
                    .setMessage(getString(R.string.home_other_confirm_message, image.name, current))
                    .setPositiveButton(R.string.home_other_confirm_go) { _, _ ->
                        if (a != null) {
                            OldStagesJob.restore(a, com.fahadali.oneos.core.root.OldStage(savedCopy, 0, image.id, hasData = true, busy = false))
                            if (OldStagesJob.state.restoring == savedCopy && OldStagesJob.state.busy) {
                                startArtwork(a, EnvironmentNavigation.intent(a, image), v.findViewById(R.id.systems_artwork))
                            }
                        }
                    }.setNegativeButton(android.R.string.cancel, null).show()
            }
            else -> {
                // The file of this system is already picked (0.4.49): Set up starts the setup, not another pick.
                val ready = profile?.let { FixActions.pickedImage(ctx, it) }?.id == image.id
                only(getString(R.string.catalog_set_up), !jobsBusy) {
                    if (ready && a != null) FixActions.run(a, FixAction.SET_UP, image) else askDownloaded(image, v.findViewById(R.id.systems_artwork))
                }
            }
        }

        primary.contentDescription = primary.text.toString() + " " + image.nameWithVariant
        return v
    }

    /** Freeze the actual source view while Android captures and returns the shared artwork. */
    private fun startArtwork(a: Activity, intent: Intent, artwork: OsArtworkView) {
        if (navigatingAway) return
        navigatingAway = true
        view?.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)?.suppressLayout(true)
        ArtworkTransitions.start(a, intent, artwork)
    }

    private fun askDownloaded(image: ImageRef, artwork: OsArtworkView) {
        val a = activity as? SystemsActivity ?: return
        AlertDialog.Builder(a).setTitle(getString(R.string.setup_mock_title, image.name))
            .setMessage(R.string.setup_download_question)
            .setPositiveButton(R.string.setup_download_yes) { _, _ ->
                if (DebugPreview.enabled(a)) startPreview(image, artwork)
                else a.choose(image.id)
            }
            .setNegativeButton(R.string.setup_download_no) { _, _ ->
                SystemsNav.open(a, image.mirrorUrl)
            }
            .setNeutralButton(android.R.string.cancel, null).show()
    }

    private fun startPreview(image: ImageRef, artwork: OsArtworkView) {
        if (!DebugPreview.enabled(requireContext())) return
        if (PrepareJob.state.busy || LaunchJob.state.busy || StageCheck.state.busy || LogJob.state.busy || OldStagesJob.state.busy || com.fahadali.oneos.session.RemoveJob.state.busy) {
            Toast.makeText(requireContext(), R.string.setup_preview_busy, Toast.LENGTH_LONG).show()
            return
        }
        val a = activity ?: return
        startArtwork(a, Intent(a, SetupProgressActivity::class.java)
            .putExtra(SetupProgressActivity.EXTRA_PREVIEW_IMAGE, image.id), artwork)
    }

    private fun showUnsupported(name: String) {
        val dialog = AlertDialog.Builder(requireContext()).setTitle(name)
            .setMessage(getString(R.string.catalog_unsupported_message, name, profile?.label ?: getString(R.string.catalog_this_phone)))
            .setPositiveButton(android.R.string.ok, null)
        dialog.show()
    }

    /** A card with a header and an optional line (reading this phone, or no system for it). */
    private fun note(column: LinearLayout, title: String, line: String?, level: Level) {
        val card = Cards.section(column, title, null, level)
        if (line != null) {
            val t = TextView(column.context)
            t.setTextAppearance(R.style.OneOS_Text_Body)
            t.text = line
            card.addView(t, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
    }

    private fun visibleCardHeight(carousel: View): Int {
        // A shared-element return can temporarily hide the view. Its measured
        // viewport is still valid; getGlobalVisibleRect would fall back to an
        // oversized card while hidden.
        val location = IntArray(2)
        carousel.getLocationInWindow(location)
        val navigation = carousel.rootWindowInsets?.getInsets(android.view.WindowInsets.Type.navigationBars())?.bottom ?: 0
        val safeBottom = carousel.rootView.height - navigation
        val measured = carousel.height.takeIf { it > 0 } ?: carousel.measuredHeight
        var safeHeight = if (safeBottom > location[1]) minOf(measured, safeBottom - location[1]) else measured
        val visible = android.graphics.Rect()
        if (carousel.getGlobalVisibleRect(visible) && visible.height() > 0) {
            safeHeight = minOf(safeHeight, visible.height())
        }
        return (safeHeight - carousel.paddingTop - carousel.paddingBottom).coerceAtLeast(1)
    }

    private fun resizeVisibleCards(carousel: androidx.recyclerview.widget.RecyclerView) {
        if (navigatingAway || carousel.width <= 0 || carousel.height <= 0) return
        val manager = carousel.layoutManager as? androidx.recyclerview.widget.LinearLayoutManager ?: return
        val selected = snapHelper?.findSnapView(manager)?.let(manager::getPosition)
        val (width, height) = cardSize(carousel)
        val verticalInset = ((visibleCardHeight(carousel) - height) / 2).coerceAtLeast(0)
        var changed = false
        for (index in 0 until carousel.childCount) {
            val child = carousel.getChildAt(index)
            val params = child.layoutParams as androidx.recyclerview.widget.RecyclerView.LayoutParams
            val side = cardSideMargin()
            if (params.width != width || params.height != height || params.topMargin != verticalInset || params.bottomMargin != verticalInset ||
                params.marginStart != side || params.marginEnd != side) {
                child.layoutParams = params.apply {
                    this.width = width; this.height = height
                    topMargin = verticalInset; bottomMargin = verticalInset
                    marginStart = side; marginEnd = side
                }
                changed = true
            }
        }
        if (changed && selected != null && selected != androidx.recyclerview.widget.RecyclerView.NO_POSITION) {
            manager.scrollToPositionWithOffset(selected, (carousel.width - width - 2 * cardSideMargin()) / 2)
            carousel.post { scaleCards(carousel) }
        }
    }

    private fun cardSideMargin() = dp(if (resources.getBoolean(R.bool.home_two_pane)) 8 else 4)

    private fun cardSize(carousel: View): Pair<Int, Int> {
        val height = visibleCardHeight(carousel)
        val aspect = cardAspect()
        val viewport = carousel.width.takeIf { it > 0 } ?: resources.displayMetrics.widthPixels
        val widthLimit = if (resources.getBoolean(R.bool.home_two_pane)) Int.MAX_VALUE else (viewport * .78f).toInt()
        val width = minOf((height * aspect).toInt(), widthLimit).coerceAtLeast(1)
        return width to (width / aspect).toInt().coerceIn(1, height)
    }

    private fun cardAspect(): Float = if (resources.getBoolean(R.bool.home_two_pane)) 1050f / 1548f else 730f / 1464f

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private companion object {
        /** Device glyphs by the system's place in the phone's list (never by brand). */
        val GLYPHS = intArrayOf(R.drawable.ic_oneos_system_0, R.drawable.ic_oneos_system_1, R.drawable.ic_oneos_system_2)
    }
}
