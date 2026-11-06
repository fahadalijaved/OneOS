package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

class DeviceListTest {
    /** docs/devices.json is generated; on a change, the new text is written next to the build. */
    @Test
    fun checkedInListMatchesThePhoneList() {
        val doc = File("../../../docs/devices.json")
        val now = DeviceList.json()
        if (!doc.isFile || doc.readText() != now) {
            File("build/devices.json").apply { parentFile.mkdirs() }.writeText(now)
        }
        assertEquals("docs/devices.json is out of date: copy core/model/build/devices.json over it", now, doc.takeIf { it.isFile }?.readText())
    }
}
