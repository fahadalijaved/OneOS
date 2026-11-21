package com.fahadali.oneos.session

import android.content.Context
import androidx.annotation.StringRes
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Images

/** Feature choices belong to a guest image and are resolved again for each launch. */
object GuestFeatures {
    enum class Flag(val key: String, @StringRes val label: Int, val defaultEnabled: Boolean) {
        MEDIA_CHIP("media_chip", R.string.system_feature_dynamic_island_player, true),
    }

    data class LaunchOptions(val mediaChip: Boolean)

    fun forSystem(profileId: String?, imageId: String): List<Flag> =
        if (profileId == "f8" && imageId == Images.ID_ONEUI95) listOf(Flag.MEDIA_CHIP) else emptyList()

    fun enabled(ctx: Context, imageId: String, flag: Flag): Boolean =
        SessionPrefs.p(ctx).getBoolean(prefKey(imageId, flag), flag.defaultEnabled)

    fun setEnabled(ctx: Context, imageId: String, flag: Flag, enabled: Boolean) {
        SessionPrefs.p(ctx).edit().putBoolean(prefKey(imageId, flag), enabled).apply()
    }

    fun optionsForLaunch(ctx: Context, profileId: String, imageId: String): LaunchOptions {
        val mediaChip = Flag.MEDIA_CHIP
        return LaunchOptions(
            mediaChip = mediaChip !in forSystem(profileId, imageId) || enabled(ctx, imageId, mediaChip),
        )
    }

    private fun prefKey(imageId: String, flag: Flag) = "guest_feature|$imageId|${flag.key}"
}
