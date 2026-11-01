package com.fahadali.oneos.guest

import android.content.Context
import android.util.AttributeSet
import androidx.appcompat.widget.AppCompatImageView

/** Resource qualifiers select the user's exact mobile or wide card export. */
class GuestArtworkView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : AppCompatImageView(context, attrs) {
    init { scaleType = ScaleType.CENTER_CROP; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    fun bind(image: String?) = bindArtwork(when {
        image?.contains("Pixel", true) == true -> R.drawable.os_pixel
        image?.contains("Hyper", true) == true -> R.drawable.os_hyperos
        image?.contains("Nothing", true) == true -> R.drawable.os_nothing
        image?.contains("Infinity", true) == true -> R.drawable.os_infinity
        else -> R.drawable.os_coloros
    })
    fun bindArtwork(resource: Int) { setImageResource(resource) }
}
