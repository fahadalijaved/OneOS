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
        toolbarLayout.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbarLayout.setEdgeInsetHorizontal(0f)
        findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0
            fillHorizontalPadding = false
        }
        findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
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

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.systems_screen, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
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
        redraw(force = true)
    }

    override fun onStart() {
        super.onStart()
        lastKey = null
        subs += StageCheck.observe { redraw() }
        subs += PrepareJob.observe { redraw() }
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
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
        // Home offers "Set up {system}" only while nothing is set up; else that button is on this card.
        val st = StageCheck.state.result?.status
        if (st?.ours == true || PrepareJob.state.busy) redraw(force = true) else SystemsNav.home(a)
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
                    FixAction.DOWNLOAD_AGAIN -> (id.image ?: card)?.downloadUrl?.let { url ->
                        b.setPositiveButton(label) { _, _ -> SystemsNav.open(a, url) }
                    }
                    else -> Unit
                }
            }
        }
        b.setNegativeButton(R.string.systems_close, null).show()
    }

    private fun redraw(force: Boolean = false) {
        val root = view ?: return
        val ctx = context ?: return
        val p = profile
        val check = StageCheck.state
        val prep = PrepareJob.state
        val picked = SessionPrefs.picked(ctx)
        val jobsBusy = prep.busy || check.busy || LaunchJob.state.busy || LogJob.state.busy
        // PrepareJob reports every few MB: redraw only when something on the cards changes.
        val key = listOf(
            p?.id, profileRead, check.busy, check.result?.at, prep.phase, prep.image?.id,
            picked?.uri, picked?.sha256, jobsBusy, resources.configuration.screenWidthDp,
        )
        if (!force && key == lastKey) return
        lastKey = key

        root.findViewById<TextView>(R.id.systems_hero_subtitle).apply {
            text = if (p != null) getString(R.string.systems_subtitle, p.label) else getString(R.string.systems_none_line)
            visibility = View.GONE
        }
        val carousel = root.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.systems_carousel)
        val available = p?.images().orEmpty()
        val st = check.result?.status
        val setUpId = st?.marker?.takeIf { st.ours && it.profileId == p?.id }?.imageId
        val pickedId = p?.let { FixActions.pickedImage(ctx, it)?.id }
        val settingUpId = prep.image?.id?.takeIf { prep.busy }
        fun image(family: com.fahadali.oneos.core.model.SystemFamily, fallback: ImageRef): ImageRef =
            available.firstOrNull { it.family == family && it.id == setUpId }
                ?: available.firstOrNull { it.family == family && it.id in st?.oldImages.orEmpty().values }
                ?: available.firstOrNull { it.family == family } ?: fallback
        val color = image(com.fahadali.oneos.core.model.SystemFamily.COLOROS, Images.FIND_N6)
        val pixel = image(com.fahadali.oneos.core.model.SystemFamily.PIXEL, Images.PIXEL_YOGI)
        val infinity = image(com.fahadali.oneos.core.model.SystemFamily.INFINITYX, Images.INFINITYX)
        val hyper = image(com.fahadali.oneos.core.model.SystemFamily.HYPEROS, Images.HYPEROS_LHASA)
        val nothing = image(com.fahadali.oneos.core.model.SystemFamily.NOTHING, Images.NOTHING_METROID)
        val entries = listOf(
            CatalogEntry(infinity.name, infinity, R.drawable.os_infinity, available.any { it.id == infinity.id }),
            CatalogEntry(hyper.name, hyper, R.drawable.os_hyperos, available.any { it.id == hyper.id }),
            CatalogEntry(color.name, color, R.drawable.os_coloros, available.any { it.id == color.id }),
            CatalogEntry(nothing.name, nothing, R.drawable.os_nothing, available.any { it.id == nothing.id }),
            CatalogEntry(pixel.name, pixel, R.drawable.os_pixel, available.any { it.id == pixel.id }),
        )


        val state = carousel.layoutManager?.onSaveInstanceState()
        carousel.adapter = object : androidx.recyclerview.widget.RecyclerView.Adapter<CarouselHolder>() {
            override fun getItemCount() = Int.MAX_VALUE
            override fun onCreateViewHolder(parent: ViewGroup, type: Int): CarouselHolder =
                CarouselHolder(android.widget.FrameLayout(parent.context))
            override fun onBindViewHolder(holder: CarouselHolder, position: Int) {
                val entry = entries[position % entries.size]
                val image = entry.image
                holder.box.removeAllViews()
                val height = visibleCardHeight(carousel)
                val width = (height / resources.displayMetrics.density * cardAspect()).toInt().coerceAtLeast(180)
                holder.box.layoutParams = androidx.recyclerview.widget.RecyclerView.LayoutParams(dp(width), height).apply {
                    marginStart = 0; marginEnd = dp(16)
                }
                holder.box.addView(card(holder.box, p, entry, position,
                    image?.id == setUpId && setUpId != null, image?.id == pickedId && pickedId != null, image?.id == settingUpId && settingUpId != null, prep.busy, jobsBusy, st?.oldImages?.entries?.firstOrNull { it.value == image?.id }?.key))
            }
        }
        if (carousel.layoutManager == null) {
            carousel.layoutManager = androidx.recyclerview.widget.LinearLayoutManager(ctx, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false)
            androidx.recyclerview.widget.PagerSnapHelper().attachToRecyclerView(carousel)
        }
        if (state != null) carousel.layoutManager?.onRestoreInstanceState(state)
        carousel.post {
            carousel.adapter?.notifyDataSetChanged()
            if (state == null) {
                val h = visibleCardHeight(carousel)
                val w = (h / resources.displayMetrics.density * cardAspect()).toInt().coerceAtLeast(180)
                (carousel.layoutManager as? androidx.recyclerview.widget.LinearLayoutManager)?.scrollToPositionWithOffset(Int.MAX_VALUE / 2 - (Int.MAX_VALUE / 2 % entries.size) + 2, (carousel.width - dp(w)) / 2)
            }
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
        if (image == null) {
            v.findViewById<Button>(R.id.systems_primary).apply {
                setText(R.string.catalog_set_up)
                setOnClickListener { showUnsupported(entry.name) }
            }
            v.findViewById<View>(R.id.systems_more).setOnClickListener { showUnsupported(entry.name) }
            return v
        }
        val primary = v.findViewById<Button>(R.id.systems_primary)
        v.findViewById<View>(R.id.systems_more).setOnClickListener { anchor ->
            androidx.appcompat.widget.PopupMenu(ctx, anchor).apply {
                menu.add(R.string.systems_download).setOnMenuItemClickListener { image.downloadUrl?.let { url -> activity?.let { SystemsNav.open(it, url) } }; true }
                menu.add(R.string.systems_have_file).setOnMenuItemClickListener { (activity as? SystemsActivity)?.choose(image.id); true }
                menu.add(R.string.home_details_all).setOnMenuItemClickListener {
                    startActivity(Intent(ctx, MainActivity::class.java).putExtra("system_detail", true)); true
                }
                menu.add(R.string.catalog_details).setOnMenuItemClickListener {
                    AlertDialog.Builder(ctx).setTitle(image.displayName).setMessage(image.blurb + "\n\n" + image.variant.orEmpty() + "\n" + Units.bytes(image.gzBytes)).setPositiveButton(android.R.string.ok, null).show(); true
                }
            }.show()
        }
        val a = activity as? SystemsActivity
        fun only(text: CharSequence, enabled: Boolean, onClick: () -> Unit) {
            primary.visibility = View.VISIBLE
            primary.text = text
            primary.isEnabled = enabled
            primary.setOnClickListener { onClick() }
        }
        when {
            settingUp -> only(getString(R.string.systems_show_progress), true) { a?.let { SystemsNav.progress(it) } }
            setUp -> only(getString(R.string.catalog_boot), !jobsBusy) { a?.let { SystemsNav.home(it, image) } }
            savedCopy != null -> only(getString(R.string.catalog_boot), !jobsBusy) {
                val current = StageCheck.state.result?.status?.marker?.imageId?.let { Images.byId(it) }?.name ?: getString(R.string.home_other_current_unknown)
                AlertDialog.Builder(ctx).setTitle(getString(R.string.home_other_confirm_title, image.name))
                    .setMessage(getString(R.string.home_other_confirm_message, image.name, current))
                    .setPositiveButton(R.string.home_other_confirm_go) { _, _ ->
                        if (a != null) { QuickSwitch.start(a, savedCopy, image.id); SystemsNav.home(a, image) }
                    }.setNegativeButton(android.R.string.cancel, null).show()
            }
            picked -> only(getString(R.string.catalog_set_up), !jobsBusy) { a?.let { FixActions.run(it, FixAction.SET_UP, image) } }
            else -> only(getString(R.string.catalog_set_up), !jobsBusy) {
                if (!entry.supported) { showUnsupported(entry.name); return@only }
                AlertDialog.Builder(ctx).setTitle(image.displayName)
                    .setItems(arrayOf(getString(R.string.systems_download), getString(R.string.systems_have_file))) { _, which ->
                        if (which == 0) image.downloadUrl?.let { url -> a?.let { SystemsNav.open(it, url) } } else a?.choose(image.id)
                    }.show()
            }
        }
        primary.contentDescription = primary.text.toString() + " " + image.nameWithVariant
        return v
    }

    private fun showUnsupported(name: String) {
        AlertDialog.Builder(requireContext()).setTitle(name)
            .setMessage(R.string.catalog_unsupported_message)
            .setPositiveButton(android.R.string.ok, null).show()
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
        val visible = android.graphics.Rect()
        if (!carousel.getGlobalVisibleRect(visible) || visible.height() <= 0) return dp(500)
        val navigation = carousel.rootWindowInsets?.getInsets(android.view.WindowInsets.Type.navigationBars())?.bottom ?: 0
        val safeBottom = carousel.rootView.height - navigation
        return (minOf(visible.bottom, safeBottom) - visible.top - carousel.paddingTop - carousel.paddingBottom).coerceAtLeast(dp(180))
    }

    private fun cardAspect(): Float = if (resources.getBoolean(R.bool.home_two_pane)) 1050f / 1548f else 730f / 1464f

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private companion object {
        /** Device glyphs by the system's place in the phone's list (never by brand). */
        val GLYPHS = intArrayOf(R.drawable.ic_oneos_system_0, R.drawable.ic_oneos_system_1, R.drawable.ic_oneos_system_2)
    }
}
