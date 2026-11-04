package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

class ImageGuideTest {
    /** docs/download-images.md is the generated guide; on a change, the new text is written next to the build. */
    @Test
    fun checkedInGuideMatchesThePhoneList() {
        val doc = File("../../../docs/download-images.md")
        val now = ImageGuide.markdown()
        if (!doc.isFile || doc.readText() != now) {
            File("build/download-images.md").apply { parentFile.mkdirs() }.writeText(now)
        }
        assertEquals("docs/download-images.md is out of date: copy core/model/build/download-images.md over it", now, doc.takeIf { it.isFile }?.readText())
    }
}
