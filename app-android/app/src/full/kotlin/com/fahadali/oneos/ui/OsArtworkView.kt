package com.fahadali.oneos.ui

import android.content.Context
import android.util.AttributeSet
import androidx.appcompat.widget.AppCompatImageView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.SystemFamily

/** Resource qualifiers select the user's exact mobile or wide card export. */
class OsArtworkView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : AppCompatImageView(context, attrs) {
    init { scaleType = ScaleType.CENTER_CROP; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    fun bind(image: ImageRef?) = bindArtwork(when (image?.family) {
        SystemFamily.PIXEL -> R.drawable.os_pixel
        SystemFamily.HYPEROS -> R.drawable.os_hyperos
        SystemFamily.NOTHING -> R.drawable.os_nothing
        SystemFamily.INFINITYX -> R.drawable.os_infinity
        else -> R.drawable.os_coloros
    })
    fun bindArtwork(resource: Int) { setImageResource(resource) }
}
