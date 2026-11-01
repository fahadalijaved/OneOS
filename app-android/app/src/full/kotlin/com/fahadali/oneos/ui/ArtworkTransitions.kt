package com.fahadali.oneos.ui

import android.app.Activity
import android.app.ActivityOptions
import android.app.SharedElementCallback
import android.content.Intent
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.RectF
import android.os.Handler
import android.os.Looper
import android.os.Parcelable
import android.transition.Fade
import android.view.View
import android.view.ViewGroup
import android.view.animation.PathInterpolator
import com.google.android.material.shape.ShapeAppearanceModel
import com.google.android.material.transition.platform.MaterialContainerTransform
import com.google.android.material.transition.platform.MaterialContainerTransformSharedElementCallback
import java.lang.ref.WeakReference

/** Native SESL9 Material artwork morphs; navigation and OS jobs retain their normal paths. */
internal object ArtworkTransitions {
    private const val NAME = "oneos_selected_artwork"
    private const val EXTRA = "oneos.artwork_transition"
    private const val DURATION = 420L

    private fun shape(activity: Activity) = ShapeAppearanceModel.builder()
        .setAllCornerSizes(28 * activity.resources.displayMetrics.density).build()

    fun prepare(activity: Activity) {
        fun transform(returning: Boolean) = MaterialContainerTransform().apply {
            addTarget(NAME)
            duration = if (returning) 320L else DURATION
            interpolator = PathInterpolator(.2f, 0f, 0f, 1f)
            drawingViewId = android.R.id.content
            // Keep the source opaque underneath the destination, avoiding the
            // double fade through black when the thin/wide artwork crops differ.
            fadeMode = MaterialContainerTransform.FADE_MODE_IN
            fadeProgressThresholds = MaterialContainerTransform.ProgressThresholds(.12f, .96f)
            fitMode = MaterialContainerTransform.FIT_MODE_AUTO
            scrimColor = Color.TRANSPARENT
            setAllContainerColors(activity.getColor(com.fahadali.oneos.R.color.oneos_page_background))
            startShapeAppearanceModel = shape(activity)
            endShapeAppearanceModel = shape(activity)
            isElevationShadowEnabled = false
        }
        activity.window.apply {
            sharedElementEnterTransition = transform(false)
            sharedElementReturnTransition = transform(true)
            // The destination owns the morph; do not animate a second copy in the source window.
            sharedElementExitTransition = null
            sharedElementReenterTransition = null
            enterTransition = Fade().apply { duration = 160 }
            exitTransition = Fade().apply { duration = 160 }
            allowEnterTransitionOverlap = true
            allowReturnTransitionOverlap = true
        }
        activity.setEnterSharedElementCallback(MaterialContainerTransformSharedElementCallback().apply {
            setShapeProvider { shape(activity) }
        })
        if (activity.intent.getBooleanExtra(EXTRA, false)) activity.postponeEnterTransition()
    }

    fun bindTarget(activity: Activity, artwork: OsArtworkView) {
        if (!activity.intent.getBooleanExtra(EXTRA, false)) return
        artwork.transitionName = NAME
        artwork.viewTreeObserver.addOnPreDrawListener(object : android.view.ViewTreeObserver.OnPreDrawListener {
            override fun onPreDraw(): Boolean {
                artwork.viewTreeObserver.removeOnPreDrawListener(this)
                activity.startPostponedEnterTransition()
                return true
            }
        })
    }

    fun start(activity: Activity, intent: Intent, artwork: OsArtworkView?, finishSource: Boolean = false) {
        if (artwork == null || !artwork.isLaidOut || !artwork.isShown) {
            activity.startActivity(intent)
            if (finishSource) activity.finish()
            return
        }
        artworks(activity.window.decorView).forEach { it.transitionName = null }
        artwork.transitionName = NAME
        val source = WeakReference(artwork)
        val family = artwork.artworkFamily
        val capture = MaterialContainerTransformSharedElementCallback().apply { setShapeProvider { shape(activity) } }
        activity.setExitSharedElementCallback(object : SharedElementCallback() {
            override fun onCaptureSharedElementSnapshot(view: View, matrix: Matrix, bounds: RectF): Parcelable? =
                capture.onCaptureSharedElementSnapshot(view, matrix, bounds)

            override fun onMapSharedElements(names: MutableList<String>, sharedElements: MutableMap<String, View>) {
                val current = source.get()?.takeIf { it.isAttachedToWindow && it.isShown }
                    ?: artworks(activity.window.decorView).firstOrNull { it.isShown && it.artworkFamily == family }
                if (current != null && NAME in names) {
                    current.transitionName = NAME
                    sharedElements[NAME] = current
                }
            }
        })
        val options = ActivityOptions.makeSceneTransitionAnimation(activity, artwork, NAME)
        activity.startActivity(intent.putExtra(EXTRA, true), options.toBundle())
        if (finishSource) Handler(Looper.getMainLooper()).postDelayed({
            // Let the captured shared element finish moving before discarding the completed setup page.
            if (!activity.isFinishing && !activity.isDestroyed) activity.finish()
        }, DURATION + 100)
    }

    private fun artworks(view: View): Sequence<OsArtworkView> = sequence {
        if (view is OsArtworkView) yield(view)
        if (view is ViewGroup) for (index in 0 until view.childCount) yieldAll(artworks(view.getChildAt(index)))
    }
}
