package com.fahadali.oneos.ui

import android.content.Context
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.SystemFamily

internal object CarouselSelection {
    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences("oneos_navigation", Context.MODE_PRIVATE)
    fun family(ctx: Context): SystemFamily = runCatching {
        SystemFamily.valueOf(prefs(ctx).getString("last_card_family", null).orEmpty())
    }.getOrDefault(SystemFamily.COLOROS)
    fun remember(ctx: Context, image: ImageRef) { prefs(ctx).edit().putString("last_card_family", image.family.name).apply() }
}
