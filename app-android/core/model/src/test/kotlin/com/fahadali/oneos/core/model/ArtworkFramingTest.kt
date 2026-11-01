package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test

class ArtworkFramingTest {
    private val families = listOf(SystemFamily.COLOROS, SystemFamily.HYPEROS, SystemFamily.INFINITYX, SystemFamily.NOTHING, SystemFamily.PIXEL)
    @Test fun shortHeaderCropsKeepCompleteHeadingsAndNeverExposeSideBands() {
        for (family in families) for ((w, h) in listOf(388 to 356, 320 to 300, 600 to 500)) {
            val a = ArtworkFraming.heading(family, true)
            val m = ArtworkFraming.transform(family, 1050, 1548, w, h)
            assertTrue(m.x <= .01f && m.y <= .01f)
            assertTrue(1050 * m.scale + m.x >= w - .01f)
            assertTrue(1548 * m.scale + m.y >= h - .01f)
            assertTrue("$family version visible", a.top * 1548 * m.scale + m.y >= -.01f)
            assertTrue("$family name visible", a.bottom * 1548 * m.scale + m.y <= h + .01f)
        }
    }
    @Test fun colourHeaderLeavesRoomForProgressWithoutScalingDownTheBitmap() {
        val a = ArtworkFraming.heading(SystemFamily.COLOROS, true)
        val m = ArtworkFraming.transform(SystemFamily.COLOROS, 1050, 1548, 388, 356, 89f)
        assertEquals(388f / 1050, m.scale, .001f)
        assertTrue(a.top * 1548 * m.scale + m.y >= 0)
        assertTrue(a.bottom * 1548 * m.scale + m.y <= 267)
    }
}
