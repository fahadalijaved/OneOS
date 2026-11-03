package com.fahadali.oneos.ui

import android.content.Context
import android.graphics.drawable.AnimatedVectorDrawable
import android.util.AttributeSet
import androidx.appcompat.widget.SeslProgressBar

/** SESL's spinner, with its loop callback removed before stopping a hidden view. */
class LoadingSpinner @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : SeslProgressBar(context, attrs) {
    override fun onVisibilityAggregated(isVisible: Boolean) {
        if (!isVisible) clearLoopCallback()
        super.onVisibilityAggregated(isVisible)
    }

    override fun onDetachedFromWindow() {
        clearLoopCallback()
        super.onDetachedFromWindow()
    }

    private fun clearLoopCallback() {
        // SESL stops the AVD before unregistering its callback. Stopping invokes
        // onAnimationEnd, which can otherwise post a restart while hidden.
        // SESL registers its callback again when the view becomes visible.
        (indeterminateDrawable as? AnimatedVectorDrawable)?.clearAnimationCallbacks()
    }
}
