package com.fahadali.oneos.guest

import android.content.Context
import android.graphics.Matrix
import android.graphics.drawable.BitmapDrawable
import android.util.AttributeSet
import androidx.appcompat.widget.AppCompatImageView
import com.fahadali.oneos.core.model.ArtworkFraming
import com.fahadali.oneos.core.model.SystemFamily

/** The original exports, with ordinary full-bleed image cropping and per-OS focus points. */
class GuestArtworkView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : AppCompatImageView(context, attrs) {
    private var artwork = 0
    private var rendered = 0
    private var family = SystemFamily.COLOROS
    internal val artworkFamily: SystemFamily get() = family
    init {
        scaleType = ScaleType.CENTER_CROP
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO
        setBackgroundResource(R.drawable.catalog_card_bg)
        foreground = androidx.appcompat.content.res.AppCompatResources.getDrawable(context, R.drawable.catalog_card_outline)
        clipToOutline = true
    }
    fun bind(image: String?) = bindArtwork(when {
        image?.contains("Pixel", true) == true -> R.drawable.os_pixel
        image?.contains("Hyper", true) == true -> R.drawable.os_hyperos
        image?.contains("Nothing", true) == true -> R.drawable.os_nothing
        image?.contains("Infinity", true) == true -> R.drawable.os_infinity
        else -> R.drawable.os_coloros
    })
    fun bindArtwork(resource: Int) {
        if (artwork == resource) return
        artwork = resource
        family = when (resource) {
            R.drawable.os_hyperos -> SystemFamily.HYPEROS
            R.drawable.os_nothing -> SystemFamily.NOTHING
            R.drawable.os_infinity -> SystemFamily.INFINITYX
            R.drawable.os_pixel -> SystemFamily.PIXEL
            else -> SystemFamily.COLOROS
        }
        frame()
    }
    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) { super.onSizeChanged(w, h, oldw, oldh); frame() }
    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        // Thin/wide qualifiers share the same resource ID. Reload its drawable
        // after a display change even if this view survives the configuration.
        rendered = 0
        frame()
    }
    private fun frame() {
        if (artwork == 0) return
        val header = tag?.toString()?.startsWith("heading") == true && height > 0 && width.toFloat() / height > .8f
        val resource = if (!header) artwork else when (family) {
            SystemFamily.HYPEROS -> R.drawable.os_hyperos_header
            SystemFamily.NOTHING -> R.drawable.os_nothing_header
            SystemFamily.INFINITYX -> R.drawable.os_infinity_header
            SystemFamily.PIXEL -> R.drawable.os_pixel_header
            else -> R.drawable.os_coloros_header
        }
        if (rendered != resource) { rendered = resource; setImageResource(resource) }
        if (!header) { scaleType = ScaleType.CENTER_CROP; return }
        val bitmap = (drawable as? BitmapDrawable)?.bitmap ?: return
        scaleType = ScaleType.MATRIX
        val bottom = if (tag == "heading_progress") minOf(112 * resources.displayMetrics.density, height * .30f) else 0f
        val crop = ArtworkFraming.transform(family, bitmap.width, bitmap.height, width, height, bottom)
        imageMatrix = Matrix().apply { setScale(crop.scale, crop.scale); postTranslate(crop.x, crop.y) }
    }
}
