package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.session.StageCheck

/** Navigation hints only. A remembered image never authorizes a setup or boot. */
internal object EnvironmentNavigation {
    private fun prefs(ctx: Context) = ctx.getSharedPreferences("oneos_navigation", Context.MODE_PRIVATE)
    fun remember(ctx: Context, image: ImageRef, preview: Boolean) {
        CarouselSelection.remember(ctx, image)
        prefs(ctx).edit().putString(if (preview) "preview_image" else "prepared_image", image.id).apply()
    }
    fun image(ctx: Context): ImageRef? {
        if (DebugPreview.enabled(ctx)) prefs(ctx).getString("preview_image", null)?.let(Images::byId)?.let { return it }
        return preparedImage(ctx)
    }
    /** Cached real-stage identity is a navigation hint while fresh checks run. */
    fun preparedImage(ctx: Context): ImageRef? {
        val status = StageCheck.state.result?.status
        if (status?.complete == true) {
            val image = StageCheck.state.result?.let(ImageMaintenance::identifiedImage)
            prefs(ctx).edit().putString("prepared_image", image?.id).apply()
            return image
        }
        return prefs(ctx).getString("prepared_image", null)?.let(Images::byId)
            ?: com.fahadali.oneos.session.SessionPrefs.homeSnapshot(ctx)?.takeIf {
                it.kind in setOf(com.fahadali.oneos.core.root.HomeState.Kind.READY,
                    com.fahadali.oneos.core.root.HomeState.Kind.WELCOME_BACK,
                    com.fahadali.oneos.core.root.HomeState.Kind.UPDATE) || it.primary == com.fahadali.oneos.core.model.FixAction.SWITCH
            }?.image
    }
    fun intent(ctx: Context, image: ImageRef, preview: Boolean = false) = Intent(ctx, EnvironmentActivity::class.java)
        .putExtra("image", image.id).putExtra("preview", preview)
}
