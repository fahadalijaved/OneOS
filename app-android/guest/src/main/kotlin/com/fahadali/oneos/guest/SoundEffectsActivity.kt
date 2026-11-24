package com.fahadali.oneos.guest

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.LinearLayout
import android.widget.RadioGroup
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.AppCompatRadioButton
import androidx.appcompat.widget.AppCompatSeekBar
import androidx.appcompat.widget.AppCompatTextView
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.shared.NativeCards
import dev.oneuiproject.oneui.layout.ToolbarLayout
import dev.oneuiproject.oneui.utils.applyEdgeToEdge
import dev.oneuiproject.oneui.widget.CardItemView
import dev.oneuiproject.oneui.widget.SwitchItemView

/**
 * Samsung Dolby Atmos, SoundBoosterPlus speaker calibration & 9-band SoundAlive Equalizer panel.
 * Handles `android.media.action.DISPLAY_AUDIO_EFFECT_CONTROL_PANEL` (e.g., YouTube Music Equalizer)
 * and persists live settings read by OneOSSoundFx inside the guest.
 */
class SoundEffectsActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())
    private var cfg = SoundEffectsConfig.Config()
    private var suppressUi = false

    private lateinit var statusRow: CardItemView
    private lateinit var dolbySwitch: SwitchItemView
    private lateinit var dolbyModes: RadioGroup
    private val modeButtons = linkedMapOf<Int, AppCompatRadioButton>()
    private lateinit var boosterSwitch: SwitchItemView
    private lateinit var presetRow: CardItemView
    private val bandSeekBars = arrayOfNulls<AppCompatSeekBar>(SoundEffectsConfig.BAND_COUNT)
    private val bandValueViews = arrayOfNulls<AppCompatTextView>(SoundEffectsConfig.BAND_COUNT)

    private val refreshStatusRunnable = Runnable {
        if (!isDestroyed) updateStatusBanner()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
        setContentView(R.layout.activity_sound_effects)
        setResult(RESULT_OK)

        val toolbar = findViewById<ToolbarLayout>(R.id.sound_toolbar)
        toolbar.setTitle(getString(R.string.sound_title))
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO)
        toolbar.setEdgeInsetHorizontal(0f)

        val scroll = findViewById<NestedScrollView>(R.id.sound_scroll)
        toolbar.setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(bars.left, bars.top, bars.right, 0)
            scroll.setPadding(0, 0, 0, bars.bottom + dp(24))
            insets
        }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply {
            roundedCorners = 0
            fillHorizontalPadding = false
        }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility = View.GONE
        if (GuestName.read()?.contains("Infinity", ignoreCase = true) != true) {
            scroll.seslSetFadingEdgeEnabled(true)
            scroll.seslSetFadingEdgeColor(getColor(R.color.preboot_page))
        }

        cfg = SoundEffectsConfig.read(this)
        buildUi()
        applyConfigToUi()
        updateStatusBanner()
    }

    override fun onResume() {
        super.onResume()
        updateStatusBanner()
    }

    override fun onDestroy() {
        handler.removeCallbacks(refreshStatusRunnable)
        super.onDestroy()
    }

    private fun buildUi() {
        val list = findViewById<LinearLayout>(R.id.sound_list)
        val cardColor = getColor(R.color.preboot_card)

        // Status banner card
        val statusCard = NativeCards.section(list, null, cardColor)
        statusRow = NativeCards.row(statusCard, getString(R.string.sound_engine_title), getString(R.string.sound_engine_standby))

        // Dolby Atmos card
        val dolbyCard = NativeCards.section(list, getString(R.string.sound_dolby_section), cardColor)
        dolbySwitch = createSwitchRow(
            title = getString(R.string.sound_dolby_title),
            summaryOn = getString(R.string.sound_dolby_on),
            summaryOff = getString(R.string.sound_dolby_off)
        ) { checked ->
            if (!suppressUi) {
                cfg = cfg.copy(dolbyEnable = checked)
                updateDolbyModeAvailability()
                saveConfig()
            }
        }
        dolbyCard.addView(dolbySwitch, LinearLayout.LayoutParams(-1, -2))

        dolbyModes = RadioGroup(this).apply {
            orientation = RadioGroup.VERTICAL
            setPadding(dp(20), dp(4), dp(20), dp(12))
        }
        val modes = listOf(
            SoundEffectsConfig.PROFILE_AUTO to R.string.sound_dolby_mode_auto,
            SoundEffectsConfig.PROFILE_MOVIE to R.string.sound_dolby_mode_movie,
            SoundEffectsConfig.PROFILE_MUSIC to R.string.sound_dolby_mode_music,
            SoundEffectsConfig.PROFILE_VOICE to R.string.sound_dolby_mode_voice
        )
        for ((id, labelRes) in modes) {
            val rb = AppCompatRadioButton(this).apply {
                this.id = View.generateViewId()
                text = getString(labelRes)
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
                setPadding(dp(8), dp(8), dp(8), dp(8))
                tag = id
            }
            modeButtons[id] = rb
            dolbyModes.addView(rb, LinearLayout.LayoutParams(-1, -2))
        }
        dolbyModes.setOnCheckedChangeListener { group, checkedId ->
            if (suppressUi) return@setOnCheckedChangeListener
            val profile = group.findViewById<View>(checkedId)?.tag as? Int ?: return@setOnCheckedChangeListener
            cfg = cfg.copy(dolbyProfile = profile)
            saveConfig()
        }
        dolbyCard.addView(dolbyModes, LinearLayout.LayoutParams(-1, -2))

        // Speaker calibration (SoundBoosterPlus) card
        val boosterCard = NativeCards.section(list, getString(R.string.sound_booster_section), cardColor)
        boosterSwitch = createSwitchRow(
            title = getString(R.string.sound_booster_title),
            summaryOn = getString(R.string.sound_booster_on),
            summaryOff = getString(R.string.sound_booster_off)
        ) { checked ->
            if (!suppressUi) {
                cfg = cfg.copy(soundBoosterEnable = checked)
                saveConfig()
            }
        }
        boosterCard.addView(boosterSwitch, LinearLayout.LayoutParams(-1, -2))

        // SoundAlive 9-band Equalizer card
        val eqCard = NativeCards.section(list, getString(R.string.sound_eq_section), cardColor)
        presetRow = NativeCards.row(
            eqCard,
            getString(R.string.sound_eq_preset_title),
            getString(SoundEffectsConfig.presetLabelRes(cfg.eqPreset))
        ) {
            showPresetDialog()
        }
        presetRow.showTopDivider = false

        val slidersBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(12))
        }
        for (i in 0 until SoundEffectsConfig.BAND_COUNT) {
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(0, dp(6), 0, dp(6))
            }
            val freqLabel = SoundEffectsConfig.BAND_FREQ_LABELS[i]
            val freqView = AppCompatTextView(this).apply {
                text = freqLabel
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
                setSecondaryColor(this)
            }
            row.addView(freqView, LinearLayout.LayoutParams(dp(56), -2))

            val seek = AppCompatSeekBar(this).apply {
                max = SoundEffectsConfig.BAND_MAX_DB - SoundEffectsConfig.BAND_MIN_DB
                contentDescription = freqLabel
                setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                    override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                        if (!fromUser || suppressUi) return
                        val db = (progress + SoundEffectsConfig.BAND_MIN_DB)
                            .coerceIn(SoundEffectsConfig.BAND_MIN_DB, SoundEffectsConfig.BAND_MAX_DB)
                        bandValueViews[i]?.text = formatDb(db)
                        updateBandDbColor(bandValueViews[i], db)
                        if (cfg.eqBands[i] != db) {
                            val updated = cfg.eqBands.copyOf()
                            updated[i] = db
                            val preset = SoundEffectsConfig.matchingPresetId(updated) ?: SoundEffectsConfig.PRESET_CUSTOM
                            cfg = cfg.copy(eqPreset = preset, eqBands = updated)
                            presetRow.summary = getString(SoundEffectsConfig.presetLabelRes(preset))
                            saveConfig(scheduleStatusRefresh = false)
                        }
                    }

                    override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit

                    override fun onStopTrackingTouch(seekBar: SeekBar?) {
                        if (!suppressUi) saveConfig()
                    }
                })
            }
            bandSeekBars[i] = seek
            row.addView(seek, LinearLayout.LayoutParams(0, -2, 1f).apply {
                marginStart = dp(4)
                marginEnd = dp(4)
            })

            val valView = AppCompatTextView(this).apply {
                gravity = Gravity.END or Gravity.CENTER_VERTICAL
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
            }
            bandValueViews[i] = valView
            row.addView(valView, LinearLayout.LayoutParams(dp(54), -2))

            slidersBox.addView(row, LinearLayout.LayoutParams(-1, -2))
        }
        eqCard.addView(slidersBox, LinearLayout.LayoutParams(-1, -2))

        NativeCards.row(eqCard, getString(R.string.sound_eq_reset), null) {
            applyPreset(SoundEffectsConfig.PRESETS.first())
        }.showTopDivider = true
    }

    @android.annotation.SuppressLint("RestrictedApi")
    private fun createSwitchRow(
        title: String,
        summaryOn: String,
        summaryOff: String,
        onToggle: (Boolean) -> Unit
    ): SwitchItemView = SwitchItemView(this).apply {
        this.title = title
        this.summaryOn = summaryOn
        this.summaryOff = summaryOff
        showTopDivider = false
        showBottomDivider = false
        separateSwitch = false
        findViewById<TextView>(dev.oneuiproject.oneui.design.R.id.switch_card_summary)?.apply {
            maxLines = Int.MAX_VALUE
            ellipsize = null
            setLineSpacing(dp(2).toFloat(), 1f)
        }
        onCheckedChangedListener = { _, value -> onToggle(value) }
    }

    private fun applyConfigToUi() {
        suppressUi = true
        try {
            dolbySwitch.isChecked = cfg.dolbyEnable
            modeButtons[cfg.dolbyProfile]?.isChecked = true
            updateDolbyModeAvailability()
            boosterSwitch.isChecked = cfg.soundBoosterEnable
            presetRow.summary = getString(SoundEffectsConfig.presetLabelRes(cfg.eqPreset))
            for (i in 0 until SoundEffectsConfig.BAND_COUNT) {
                val db = cfg.eqBands[i].coerceIn(SoundEffectsConfig.BAND_MIN_DB, SoundEffectsConfig.BAND_MAX_DB)
                bandSeekBars[i]?.progress = db - SoundEffectsConfig.BAND_MIN_DB
                bandValueViews[i]?.text = formatDb(db)
                updateBandDbColor(bandValueViews[i], db)
            }
        } finally {
            suppressUi = false
        }
    }

    private fun updateDolbyModeAvailability() {
        val enabled = cfg.dolbyEnable
        dolbyModes.alpha = if (enabled) 1f else 0.45f
        for (rb in modeButtons.values) {
            rb.isEnabled = enabled
        }
    }

    private fun showPresetDialog() {
        val presets = SoundEffectsConfig.PRESETS
        val labels = presets.map { getString(it.labelRes) }.toTypedArray()
        val selected = presets.indexOfFirst { it.id == cfg.eqPreset }
        AlertDialog.Builder(this)
            .setTitle(R.string.sound_eq_preset_title)
            .setSingleChoiceItems(labels, selected) { dialog, which ->
                presets.getOrNull(which)?.let { applyPreset(it) }
                dialog.dismiss()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun applyPreset(preset: SoundEffectsConfig.Preset) {
        cfg = cfg.copy(eqPreset = preset.id, eqBands = preset.bands.copyOf())
        applyConfigToUi()
        saveConfig()
    }

    private fun saveConfig(scheduleStatusRefresh: Boolean = true) {
        runCatching {
            SoundEffectsConfig.write(this, cfg)
            setResult(RESULT_OK)
        }.onFailure { e ->
            Toast.makeText(
                this,
                getString(R.string.sound_save_failed, e.message ?: e.javaClass.simpleName),
                Toast.LENGTH_LONG
            ).show()
        }
        if (scheduleStatusRefresh) {
            handler.removeCallbacks(refreshStatusRunnable)
            handler.postDelayed(refreshStatusRunnable, 650L)
        }
    }

    private fun updateStatusBanner() {
        val live = SoundEffectsConfig.readLiveState()
        if (live == null) {
            statusRow.summary = getString(R.string.sound_engine_standby)
            return
        }
        val active = buildList {
            if (live.dolbyActive) add(getString(R.string.sound_engine_dolby))
            if (live.soundAliveActive) add(getString(R.string.sound_engine_soundalive))
            if (live.soundBoosterActive) add(getString(R.string.sound_engine_soundbooster))
        }
        statusRow.summary = if (active.isEmpty()) {
            getString(R.string.sound_engine_inactive)
        } else {
            active.joinToString(" · ")
        }
    }

    private fun formatDb(db: Int): String = when {
        db > 0 -> getString(R.string.sound_db_pos, db)
        db < 0 -> getString(R.string.sound_db_neg, -db)
        else -> getString(R.string.sound_db_zero)
    }

    private fun updateBandDbColor(view: AppCompatTextView?, db: Int) {
        view ?: return
        if (db != 0) {
            view.setTextColor(getColor(R.color.preboot_primary))
        } else {
            setSecondaryColor(view)
        }
    }

    private fun setSecondaryColor(view: TextView) {
        val attrs = obtainStyledAttributes(intArrayOf(android.R.attr.textColorSecondary))
        view.setTextColor(attrs.getColorStateList(0))
        attrs.recycle()
    }

    private fun dp(n: Int): Int = (n * resources.displayMetrics.density + 0.5f).toInt()
}
