package com.fahadali.oneos.guest

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * How's it going? (0.4.30): the user's answers while still in the guest,
 * `files/oneos_checklist.json` in this app's own data folder, like
 * [ReturnRequest]. After the return, OneOS's log collection on the host
 * copies it with the guest's other files (assets/logs/collect.list,
 * logs.guest) and Send to the OneOS team fills them in. guest_prepare.sh
 * deletes it at each switch, so a new session starts empty.
 *
 * The item ids are the ones :core:model's CheckItem and the report service
 * count by (Back to One UI is answered after the return, in One UI).
 */
object Checklist {
    const val FILE_NAME = "oneos_checklist.json"
    const val WORKS = "works"
    const val PROBLEM = "problem"
    const val NOT_TRIED = "not_tried"
    const val NOTE_MAX = 500

    /** Id and label, in the order shown. */
    val ITEMS: List<Pair<String, Int>> = listOf(
        "screen" to R.string.item_screen,
        "wifi" to R.string.item_wifi,
        "data" to R.string.item_data,
        "calls" to R.string.item_calls,
        "sms" to R.string.item_sms,
        "bluetooth" to R.string.item_bluetooth,
        "sound" to R.string.item_sound,
        "camera" to R.string.item_camera,
        "google" to R.string.item_google,
        "location" to R.string.item_location,
        "heat" to R.string.item_heat,
        "fold" to R.string.item_fold,
    )

    data class Answers(val items: Map<String, String>, val note: String)

    fun read(context: Context): Answers {
        val f = File(context.filesDir, FILE_NAME)
        val json = runCatching { JSONObject(f.readText()) }.getOrNull() ?: return Answers(emptyMap(), "")
        val items = json.optJSONObject("items")
        val map = ITEMS.mapNotNull { (id, _) -> items?.optString(id)?.takeIf { it == WORKS || it == PROBLEM }?.let { id to it } }.toMap()
        return Answers(map, json.optString("note").take(NOTE_MAX))
    }

    /** Written to a temporary name and renamed, so the collection never reads half of it. */
    @Throws(IOException::class)
    fun save(context: Context, answers: Answers) {
        val json = JSONObject()
            .put("schema", "oneos.guest-checklist/1")
            .put("updatedAt", System.currentTimeMillis() / 1000)
            .put("items", JSONObject(answers.items.filterValues { it == WORKS || it == PROBLEM }))
            .put("note", answers.note.take(NOTE_MAX))
        val dir = context.filesDir
        val tmp = File(dir, "$FILE_NAME.tmp")
        FileOutputStream(tmp).use { out ->
            out.write(json.toString(2).toByteArray())
            out.fd.sync()
        }
        if (!tmp.renameTo(File(dir, FILE_NAME))) {
            tmp.delete()
            throw IOException("could not write ${File(dir, FILE_NAME)}")
        }
    }
}
