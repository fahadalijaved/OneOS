package com.fahadali.oneos.guest

import android.content.Context
import java.io.File
import java.io.FileOutputStream

/**
 * Persistent speaker & equalizer settings read by OneOSSoundFx (OneOSEdmStub.dex) in the guest.
 *
 * Stored in `files/oneos_sound.conf` inside this app's own data directory, written atomically via
 * `.tmp` + `fsync` + `renameTo` so root `OneOSSoundFx` never observes a partial write and no extra
 * SELinux rules or permissions are needed.
 */
object SoundEffectsConfig {
    const val FILE_NAME = "oneos_sound.conf"
    const val STATE_PATH = "/data/oneos_bootui/sound_state"
    const val BAND_COUNT = 9
    const val BAND_MIN_DB = -12
    const val BAND_MAX_DB = 12

    const val PROFILE_AUTO = 0
    const val PROFILE_MOVIE = 1
    const val PROFILE_MUSIC = 2
    const val PROFILE_VOICE = 3

    const val PRESET_BALANCED = "balanced"
    const val PRESET_CUSTOM = "custom"

    val BAND_FREQ_LABELS = arrayOf(
        "63 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz"
    )

    data class Preset(
        val id: String,
        val labelRes: Int,
        val bands: IntArray
    )

    val PRESETS: List<Preset> = listOf(
        Preset(PRESET_BALANCED, R.string.sound_eq_preset_balanced, intArrayOf(0, 0, 0, 0, 0, 0, 0, 0, 0)),
        Preset("pop", R.string.sound_eq_preset_pop, intArrayOf(-1, 1, 3, 4, 2, 0, -1, 1, 2)),
        Preset("classic", R.string.sound_eq_preset_classic, intArrayOf(3, 2, 1, 0, -1, 0, 2, 3, 3)),
        Preset("jazz", R.string.sound_eq_preset_jazz, intArrayOf(2, 2, 1, 2, -1, -1, 0, 1, 2)),
        Preset("rock", R.string.sound_eq_preset_rock, intArrayOf(4, 3, 1, -1, -1, 0, 2, 3, 4)),
        Preset("bass", R.string.sound_eq_preset_bass, intArrayOf(6, 5, 3, 1, 0, 0, 0, 0, 0)),
        Preset("treble", R.string.sound_eq_preset_treble, intArrayOf(0, 0, 0, 0, 0, 1, 3, 5, 6)),
        Preset("clear", R.string.sound_eq_preset_clear, intArrayOf(0, 0, 1, 2, 3, 3, 2, 1, 0))
    )

    data class Config(
        val dolbyEnable: Boolean = true,
        val dolbyProfile: Int = PROFILE_AUTO,
        val soundBoosterEnable: Boolean = true,
        val eqPreset: String = PRESET_BALANCED,
        val eqBands: IntArray = IntArray(BAND_COUNT)
    )

    data class LiveState(
        val dolbyActive: Boolean,
        val soundAliveActive: Boolean,
        val soundBoosterActive: Boolean
    )

    fun read(context: Context): Config {
        var enable = true
        var profile = PROFILE_AUTO
        var soundBooster = true
        var preset = PRESET_BALANCED
        val bands = IntArray(BAND_COUNT)

        val file = File(context.filesDir, FILE_NAME)
        if (file.isFile) {
            runCatching {
                file.forEachLine { raw ->
                    val line = raw.trim()
                    if (line.isEmpty() || line.startsWith("#")) return@forEachLine
                    val eq = line.indexOf('=')
                    if (eq <= 0) return@forEachLine
                    val k = line.substring(0, eq).trim()
                    val v = line.substring(eq + 1).trim()
                    when (k) {
                        "enable" -> enable = v != "0" && !v.equals("false", ignoreCase = true)
                        "profile" -> {
                            val p = v.toIntOrNull()
                            if (p != null && p in PROFILE_AUTO..PROFILE_VOICE) profile = p
                        }
                        "soundbooster" -> soundBooster = v != "0" && !v.equals("false", ignoreCase = true)
                        "eq_preset" -> preset = v
                        "eq_bands" -> {
                            val parts = v.split(',')
                            for (i in 0 until minOf(BAND_COUNT, parts.size)) {
                                parts[i].trim().toIntOrNull()?.let {
                                    bands[i] = it.coerceIn(BAND_MIN_DB, BAND_MAX_DB)
                                }
                            }
                        }
                    }
                }
            }
        }
        val matched = matchingPresetId(bands)
        val resolvedPreset = matched ?: if (preset == PRESET_BALANCED && bands.all { it == 0 }) PRESET_BALANCED else PRESET_CUSTOM
        return Config(
            dolbyEnable = enable,
            dolbyProfile = profile,
            soundBoosterEnable = soundBooster,
            eqPreset = resolvedPreset,
            eqBands = bands
        )
    }

    fun write(context: Context, cfg: Config) {
        val clamped = IntArray(BAND_COUNT) { idx ->
            cfg.eqBands.getOrElse(idx) { 0 }.coerceIn(BAND_MIN_DB, BAND_MAX_DB)
        }
        val profile = cfg.dolbyProfile.coerceIn(PROFILE_AUTO, PROFILE_VOICE)
        val preset = matchingPresetId(clamped) ?: cfg.eqPreset
        val body = buildString {
            append("enable=").append(if (cfg.dolbyEnable) 1 else 0).append('\n')
            append("profile=").append(profile).append('\n')
            append("soundbooster=").append(if (cfg.soundBoosterEnable) 1 else 0).append('\n')
            append("eq_preset=").append(preset).append('\n')
            append("eq_bands=").append(clamped.joinToString(",")).append('\n')
        }
        val dir = context.filesDir
        val tmp = File(dir, "$FILE_NAME.tmp")
        FileOutputStream(tmp).use { out ->
            out.write(body.toByteArray(Charsets.US_ASCII))
            out.fd.sync()
        }
        val dst = File(dir, FILE_NAME)
        if (!tmp.renameTo(dst)) {
            tmp.delete()
            FileOutputStream(dst).use { out ->
                out.write(body.toByteArray(Charsets.US_ASCII))
                out.fd.sync()
            }
        }
    }

    fun matchingPresetId(bands: IntArray): String? {
        if (bands.size < BAND_COUNT) return null
        return PRESETS.firstOrNull { preset ->
            (0 until BAND_COUNT).all { i -> bands[i] == preset.bands[i] }
        }?.id
    }

    fun presetLabelRes(presetId: String): Int =
        PRESETS.firstOrNull { it.id == presetId }?.labelRes ?: R.string.sound_eq_preset_custom

    fun dolbyProfileLabelRes(profile: Int): Int = when (profile) {
        PROFILE_MOVIE -> R.string.sound_dolby_mode_movie
        PROFILE_MUSIC -> R.string.sound_dolby_mode_music
        PROFILE_VOICE -> R.string.sound_dolby_mode_voice
        else -> R.string.sound_dolby_mode_auto
    }

    fun readLiveState(): LiveState? {
        val f = File(STATE_PATH)
        if (!f.isFile || f.length() !in 1..256) return null
        return runCatching {
            var dolby = false
            var sa = false
            var sb = false
            f.forEachLine { raw ->
                val line = raw.trim()
                val eq = line.indexOf('=')
                if (eq <= 0) return@forEachLine
                val k = line.substring(0, eq).trim()
                val v = line.substring(eq + 1).trim() == "1"
                when (k) {
                    "dolby" -> dolby = v
                    "soundalive" -> sa = v
                    "soundbooster" -> sb = v
                }
            }
            LiveState(dolbyActive = dolby, soundAliveActive = sa, soundBoosterActive = sb)
        }.getOrNull()
    }
}
