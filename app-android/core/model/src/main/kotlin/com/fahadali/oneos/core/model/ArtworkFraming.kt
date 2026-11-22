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
        // 0.5.06: LineageOS 24's default wallpaper with Lineage's logo (its boot animation) and LineageOS in Google Sans Flex (from the image).
        SystemFamily.LINEAGE -> if (wide) Heading(.153f, .371f, .846f, .629f) else Heading(.153f, .406f, .845f, .594f)
        // 0.5.22: One UI 9.5's own arches (the Software update app's artwork) with "One UI" / "9.5" in One UI Sans, bottom left.
        // 0.5.23: the card's heading drawn higher (it sat behind the Set up button).
        SystemFamily.ONEUI -> if (wide) Heading(.067f, .663f, .521f, .907f) else Heading(.071f, .600f, .553f, .791f)
        // 0.5.35: Google's Pixel "Iris" wallpaper (PixelWallpapers2025 premium_iris_dark, in the PixelOS image) with "PixelOS / 17" in Google Sans Flex (from the
        // image), in the top 40% so the Set up card never covers it.
        SystemFamily.PIXELOS -> if (wide) Heading(.07f, .108f, .751f, .488f) else Heading(.067f, .099f, .751f, .379f)
        else -> Heading(.1f, .2f, .9f, .6f)
    }
    /**
     * 0.5.27: HyperOS 4 Global's own card (os_hyperos_global), apart from the Xiaomi 18 Fold build's: the image's lock
     * wallpaper with "HyperOS / 4 / Global" in MiSans, in the top third so the Set up card never covers it.
     */
    fun hyperOsGlobalHeading(wide: Boolean): Heading =
        if (wide) Heading(.07f, .114f, .895f, .528f) else Heading(.069f, .104f, .894f, .41f)
    fun transform(
        family: SystemFamily, sourceWidth: Int, sourceHeight: Int, width: Int, height: Int, reservedBottom: Float = 0f,
        hyperOsGlobal: Boolean = false,
    ): Transform {
        require(sourceWidth > 0 && sourceHeight > 0 && width > 0 && height > 0)
        val wide = sourceWidth.toFloat() / sourceHeight > .6f
        val heading = if (hyperOsGlobal) hyperOsGlobalHeading(wide) else heading(family, wide)
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
