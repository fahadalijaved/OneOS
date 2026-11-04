package com.fahadali.oneos.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.RectF
import android.graphics.drawable.Drawable
import com.fahadali.oneos.R

/**
 * The setup step in progress (0.4.41): the ring of ic_oneos_step_current (28dp, a 3dp track),
 * filled clockwise from the top to the step's own progress, so a long step (the downloads,
 * the image) visibly moves. [fraction] null: the step measures nothing, a quarter arc as before.
 */
class StepRingDrawable(ctx: Context, private val fraction: Float?) : Drawable() {
    private val density = ctx.resources.displayMetrics.density
    private val size = (28 * density).toInt()
    private val stroke = 3 * density
    private val track = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeWidth = stroke; color = ctx.getColor(R.color.oneos_ring_track)
    }
    private val arc = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeWidth = stroke; strokeCap = Paint.Cap.ROUND; color = ctx.getColor(R.color.oneos_primary_text)
    }
    private val oval = RectF()

    override fun getIntrinsicWidth() = size
    override fun getIntrinsicHeight() = size

    override fun draw(canvas: Canvas) {
        val b = bounds
        val inset = 2 * density
        oval.set(b.left + inset, b.top + inset, b.right - inset, b.bottom - inset)
        canvas.drawArc(oval, 0f, 360f, false, track)
        val sweep = fraction?.let { (it * 360f).coerceIn(4f, 360f) } ?: 90f
        canvas.drawArc(oval, -90f, sweep, false, arc)
    }

    override fun setAlpha(alpha: Int) { track.alpha = alpha; arc.alpha = alpha }
    override fun setColorFilter(colorFilter: ColorFilter?) { track.colorFilter = colorFilter; arc.colorFilter = colorFilter }
    @Deprecated("Deprecated in Java")
    override fun getOpacity() = PixelFormat.TRANSLUCENT
}
