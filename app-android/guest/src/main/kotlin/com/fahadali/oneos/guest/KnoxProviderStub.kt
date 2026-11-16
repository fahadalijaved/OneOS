package com.fahadali.oneos.guest

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri

/**
 * A stand-in for Samsung's Knox provider (`com.sec.knox.provider2`), OxygenOS only (0.5.17). One UI's calling service
 * (com.sec.imsservice) registers a content observer on it while it starts (RcsPolicyManager.initSequentially); in
 * OxygenOS there is no such provider, the registration throws "Failed to find provider com.sec.knox.provider2" and
 * the service dies at every start (hundreds of times a session: A15, A15 5G, A16, A17), so no SMS and no VoLTE.
 * It is off in the manifest; the session (oneos_switch.sh) turns it on in an OxygenOS guest only. It holds nothing:
 * every query is an empty cursor, every write is refused.
 */
class KnoxProviderStub : ContentProvider() {
    override fun onCreate() = true
    override fun query(uri: Uri, projection: Array<out String>?, selection: String?, selectionArgs: Array<out String>?, sortOrder: String?): Cursor =
        MatrixCursor(projection ?: arrayOf("_id"))
    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?) = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?) = 0
}
