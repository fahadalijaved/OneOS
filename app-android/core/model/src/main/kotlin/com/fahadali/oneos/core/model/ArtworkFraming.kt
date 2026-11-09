package com.fahadali.oneos.core.model

/** The complete embedded brand heading in each supplied export, in normalized coordinates. */
object ArtworkFraming {
    data class Heading(val left: Float, val top: Float, val right: Float, val bottom: Float)
    data class Transform(val scale: Float, val x: Float, val y: Float)
    fun heading(family: SystemFamily, wide: Boolean = false): Heading = when (family) {
        SystemFamily.COLOROS -> Heading(.12f, .16f, .88f, .54f)
        SystemFamily.HYPEROS -> Heading(.16f, .24f, .84f, .715f)
        SystemFamily.INFINITYX -> Heading(.025f, .41f, .975f, .59f)
        SystemFamily.NOTHING -> if (wide) Heading(.14f, .127f, .86f, .18f) else Heading(.085f, .135f, .915f, .19f)
        SystemFamily.PIXEL -> if (wide) Heading(.32f, .378f, .68f, .46f) else Heading(.24f, .345f, .76f, .435f)
        // 0.4.67: OxygenOS 16's "16" and wordmark (the owner's key visual, extended to the card and header sizes).
        SystemFamily.OXYGENOS -> if (wide) Heading(.32f, .28f, .68f, .53f) else Heading(.32f, .27f, .68f, .46f)
        // 0.4.73: OriginOS 7's default wallpaper (VivoThemeRes wallpaper_02) with vivo's "originOS 7" wordmark from
        // Settings' About phone banner (about_phone_origin_os_img), keyed out and placed on it (the owner's choice).
        SystemFamily.ORIGINOS -> if (wide) Heading(.21f, .26f, .79f, .34f) else Heading(.19f, .24f, .81f, .30f)
        else -> Heading(.1f, .2f, .9f, .6f)
    }
    fun transform(family: SystemFamily, sourceWidth: Int, sourceHeight: Int, width: Int, height: Int, reservedBottom: Float = 0f): Transform {
        require(sourceWidth > 0 && sourceHeight > 0 && width > 0 && height > 0)
        val heading = heading(family, sourceWidth.toFloat() / sourceHeight > .6f)
        val areaHeight = (height - reservedBottom.coerceIn(0f, height * .4f)).coerceAtLeast(1f)
        val cover = maxOf(width.toFloat() / sourceWidth, height.toFloat() / sourceHeight)
        // Keep the real bitmap covering the view: no edge stretching or side bands.
        val x = (width / 2f - (heading.left + heading.right) / 2f * sourceWidth * cover)
            .coerceIn(minOf(width - sourceWidth * cover, 0f), 0f)
        val y = (areaHeight / 2f - (heading.top + heading.bottom) / 2f * sourceHeight * cover)
            .coerceIn(minOf(height - sourceHeight * cover, 0f), 0f)
        return Transform(cover, x, y)
    }
}
