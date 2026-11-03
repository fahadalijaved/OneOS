package com.fahadali.oneos.ui

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.content.Context
import android.content.res.Configuration
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import kotlin.math.abs
import android.graphics.Paint
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.util.AttributeSet
import android.view.View
import android.view.ViewGroup
import android.view.animation.LinearInterpolator
import android.view.animation.PathInterpolator
import android.widget.FrameLayout
import android.provider.Settings

class AnimatedTitleView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : FrameLayout(context, attrs, defStyleAttr) {
    private val fadeInterpolator = PathInterpolator(0.333f, 0f, 0.667f, 1f)
    private val movementInterpolator = PathInterpolator(0.22f, 0.25f, 0f, 1f)
    private val titlePaint = TextPaint(Paint.ANTI_ALIAS_FLAG or Paint.SUBPIXEL_TEXT_FLAG).apply {
        typeface = dev.oneuiproject.oneui.utils.getBoldFont()
    }
    @get:androidx.annotation.ChecksSdkIntAtLeast(api = Build.VERSION_CODES.S)
    private val usesHardwareBlur = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
    private val lettersLayer = TitleLayer(context, titlePaint)
    private val hardwareGlyphLayers = mutableListOf<HardwareGlyphLayer>()
    private var elapsedMs = Float.MAX_VALUE
    var onAnimationFinished: (() -> Unit)? = null

    private var title = ""
    private var geometry = TitleGeometry.EMPTY
    private var letterAnimator: ValueAnimator? = null
    private var cancelHaptic: (() -> Unit)? = null
    private var playbackGeneration = 0

    init {
        clipChildren = false
        clipToPadding = false
        val styled = context.obtainStyledAttributes(
            attrs,
            com.fahadali.oneos.R.styleable.AnimatedTitleView,
        )
        title = styled.getText(com.fahadali.oneos.R.styleable.AnimatedTitleView_android_text)?.toString().orEmpty()
        titlePaint.textSize = styled.getDimension(com.fahadali.oneos.R.styleable.AnimatedTitleView_android_textSize, sp(32f))
        titlePaint.color = if (isDarkMode()) Color.WHITE else styled.getColor(com.fahadali.oneos.R.styleable.AnimatedTitleView_android_textColor, titlePaint.color)
        styled.recycle()
        lettersLayer.updatePaint(titlePaint)
        if (!usesHardwareBlur) addView(lettersLayer, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setTitle(title)
    }

    fun setTitle(value: CharSequence) {
        title = value.toString()
        contentDescription = value
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES
        requestLayout()
    }

    fun prepare() {
        cancel()
        elapsedMs = -LETTER_STAGGER_MS
        updateAnimationFrame()
    }

    fun play() {
        cancel()
        if (geometry.glyphs.isEmpty()) {
            val generation = playbackGeneration
            if (title.isNotBlank()) post {
                if (generation == playbackGeneration && isShown) play()
            }
            return
        }
        elapsedMs = 0f
        val finalStart = (geometry.glyphs.last().sequence * LETTER_STAGGER_MS).toLong()
        val duration = finalStart + MOVEMENT_DURATION_MS
        letterAnimator = ValueAnimator.ofFloat(0f, 1f).apply {
            var cancelled = false
            this.duration = duration
            interpolator = LinearInterpolator()
            addUpdateListener { animator ->
                elapsedMs = animator.currentPlayTime.toFloat()
                updateAnimationFrame()
            }
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationCancel(animation: Animator) {
                    cancelled = true
                }

                override fun onAnimationEnd(animation: Animator) {
                    cancelHaptic?.invoke()
                    cancelHaptic = null
                    if (cancelled) return
                    elapsedMs = duration.toFloat()
                    updateAnimationFrame()
                    onAnimationFinished?.invoke()
                }
            })
            start()
        }
    }

    fun cancel() {
        playbackGeneration++
        letterAnimator?.cancel()
        letterAnimator = null
        cancelHaptic?.invoke()
        cancelHaptic = null
    }

    fun finish() {
        cancel()
        elapsedMs = Float.MAX_VALUE
        updateAnimationFrame()
    }

    override fun onDetachedFromWindow() {
        cancel()
        super.onDetachedFromWindow()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val availableWidth = MeasureSpec.getSize(widthMeasureSpec).coerceAtLeast(1)
        rebuildGeometry(availableWidth)
        val desiredHeight = geometry.height.coerceAtLeast(1)
        val measuredWidth = resolveSize(availableWidth, widthMeasureSpec)
        val measuredHeight = resolveSize(desiredHeight, heightMeasureSpec)
        setMeasuredDimension(measuredWidth, measuredHeight)
        val childWidthSpec = MeasureSpec.makeMeasureSpec(measuredWidth, MeasureSpec.EXACTLY)
        // Blur needs drawing room, but must not add space before the next view.
        val layerHeight = measuredHeight + dp(TITLE_BLUR_BOTTOM_INSET_DP).toInt()
        val childHeightSpec = MeasureSpec.makeMeasureSpec(layerHeight, MeasureSpec.EXACTLY)
        for (index in 0 until childCount) getChildAt(index).measure(childWidthSpec, childHeightSpec)
    }

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        for (index in 0 until childCount) getChildAt(index).layout(0, 0, width, height + dp(TITLE_BLUR_BOTTOM_INSET_DP).toInt())
        updateAnimationFrame()
    }

    private fun rebuildGeometry(width: Int) {
        if (title.isBlank()) {
            setGeometry(TitleGeometry.EMPTY)
            return
        }
        val layout = StaticLayout.Builder.obtain(title, 0, title.length, titlePaint, width)
            .setAlignment(Layout.Alignment.ALIGN_CENTER)
            .setIncludePad(false)
            .setLineSpacing(0f, 1f)
            .build()
        var sequence = 0
        val glyphs = buildList {
            var offset = 0
            while (offset < title.length) {
                val next = offset + Character.charCount(title.codePointAt(offset))
                if (!title.substring(offset, next).all(Char::isWhitespace)) {
                    val line = layout.getLineForOffset(offset)
                    add(
                        Glyph(
                            start = offset,
                            end = next,
                            x = layout.getPrimaryHorizontal(offset),
                            baseline = layout.getLineBaseline(line).toFloat(),
                            sequence = sequence++,
                        ),
                    )
                }
                offset = next
            }
        }
        setGeometry(
            TitleGeometry(
                title,
                glyphs,
                layout.height,
            ),
        )
    }

    private fun setGeometry(value: TitleGeometry) {
        if (geometry == value) return
        geometry = value
        if (usesHardwareBlur) {
            rebuildHardwareGlyphLayers()
        } else {
            lettersLayer.geometry = geometry
        }
        updateAnimationFrame()
    }

    @androidx.annotation.RequiresApi(Build.VERSION_CODES.S)
    private fun rebuildHardwareGlyphLayers() {
        removeAllViews()
        hardwareGlyphLayers.clear()
        geometry.glyphs.forEach { glyph ->
            HardwareGlyphLayer(context, titlePaint, glyph).also { layer ->
                layer.setLayerType(LAYER_TYPE_HARDWARE, null)
                hardwareGlyphLayers += layer
                addView(
                    layer,
                    LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
                )
            }
        }
    }

    private fun updateAnimationFrame() {
        if (usesHardwareBlur) {
            val distance = (width * 0.16f).coerceAtMost(dp(80f))
            hardwareGlyphLayers.forEach { layer ->
                layer.updateAnimation(elapsedMs, distance)
            }
        } else {
            lettersLayer.elapsedMs = elapsedMs
            lettersLayer.invalidate()
        }
    }

    private fun dp(value: Float): Float = value * resources.displayMetrics.density

    private fun sp(value: Float): Float = value * resources.displayMetrics.scaledDensity

    private fun isDarkMode(): Boolean =
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES

    private data class Glyph(
        val start: Int,
        val end: Int,
        val x: Float,
        val baseline: Float,
        val sequence: Int,
    )

    private data class TitleGeometry(
        val text: String,
        val glyphs: List<Glyph>,
        val height: Int,
    ) {
        companion object {
            val EMPTY = TitleGeometry("", emptyList(), 0)
        }
    }

    @androidx.annotation.RequiresApi(Build.VERSION_CODES.S)
    private inner class HardwareGlyphLayer(
        context: Context,
        paintSource: TextPaint,
        private val glyph: Glyph,
    ) : View(context) {
        private val paint = TextPaint(paintSource)
        private var lastBlurRadius = Float.NaN

        fun updateAnimation(globalTime: Float, horizontalDistance: Float) {
            val localTime = globalTime - glyph.sequence * LETTER_STAGGER_MS
            if (localTime < 0f) {
                alpha = 0f
                translationX = horizontalDistance
                updateBlur(GLYPH_BLUR_RADIUS_PX)
                return
            }
            val fade = fadeInterpolator.getInterpolation(
                (localTime / FADE_DURATION_MS).coerceIn(0f, 1f),
            )
            val movement = movementInterpolator.getInterpolation(
                (localTime / MOVEMENT_DURATION_MS).coerceIn(0f, 1f),
            )
            alpha = fade
            translationX = horizontalDistance * (1f - movement)
            updateBlur(GLYPH_BLUR_RADIUS_PX * (1f - movement))
        }

        private fun updateBlur(radius: Float) {
            val normalizedRadius = if (radius > 0.5f) radius else 0f
            if (normalizedRadius == lastBlurRadius ||
                normalizedRadius > 0f && abs(normalizedRadius - lastBlurRadius) < BLUR_UPDATE_THRESHOLD_PX) return
            lastBlurRadius = normalizedRadius
            setRenderEffect(
                if (normalizedRadius > 0.5f) {
                    RenderEffect.createBlurEffect(
                        normalizedRadius,
                        normalizedRadius,
                        Shader.TileMode.DECAL,
                    )
                } else {
                    null
                },
            )
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawText(title, glyph.start, glyph.end, glyph.x, glyph.baseline, paint)
        }
    }

    private inner class TitleLayer(
        context: Context,
        paintSource: TextPaint,
    ) : View(context) {
        private val paint = TextPaint(paintSource)
        var geometry: TitleGeometry = TitleGeometry.EMPTY
            set(value) {
                field = value
                invalidate()
            }
        var elapsedMs = Float.MAX_VALUE

        fun updatePaint(source: TextPaint) {
            paint.set(source)
            invalidate()
        }

        init { setLayerType(LAYER_TYPE_SOFTWARE, null) }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            if (geometry.glyphs.isEmpty()) return
            val horizontalDistance = (width * 0.16f).coerceAtMost(dp(80f))
            geometry.glyphs.forEach { glyph ->
                val localTime = elapsedMs - glyph.sequence * LETTER_STAGGER_MS
                if (localTime < 0f) return@forEach
                val alpha = fadeInterpolator.getInterpolation(
                    (localTime / FADE_DURATION_MS).coerceIn(0f, 1f),
                )
                val movement = movementInterpolator.getInterpolation(
                    (localTime / MOVEMENT_DURATION_MS).coerceIn(0f, 1f),
                )
                paint.alpha = (alpha * 255).toInt()
                val blurRadius = (GLYPH_BLUR_RADIUS_PX * (1f - movement)).coerceAtLeast(0f)
                paint.maskFilter = if (blurRadius > 0.5f) {
                    BlurMaskFilter(blurRadius, BlurMaskFilter.Blur.NORMAL)
                } else {
                    null
                }
                canvas.drawText(
                    geometry.text,
                    glyph.start,
                    glyph.end,
                    glyph.x + horizontalDistance * (1f - movement),
                    glyph.baseline,
                    paint,
                )
            }
            paint.maskFilter = null
        }

        private fun dp(value: Float): Float = value * resources.displayMetrics.density
    }

    private companion object {
        const val HAPTIC_END_LEAD_MS = 100L
        const val FRAMES_PER_SECOND = 60f
        const val FRAMES_PER_LETTER = 7f
        const val LETTER_STAGGER_MS = FRAMES_PER_LETTER / FRAMES_PER_SECOND * 1_000f
        const val FADE_DURATION_MS = 500f
        const val MOVEMENT_DURATION_MS = 1_000L
        const val GLYPH_BLUR_RADIUS_PX = 100f
        const val BLUR_UPDATE_THRESHOLD_PX = 1f
        const val TITLE_BLUR_BOTTOM_INSET_DP = 24f
    }
}
