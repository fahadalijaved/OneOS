package oneos.camera;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ContentProviderClient;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;

/**
 * The camera's thumbnail opens Samsung Gallery's quick view by class name; a guest has none, so the
 * start threw ActivityNotFoundException and the camera said no gallery is installed. The start is
 * tried unchanged first (a guest with Samsung Gallery keeps it), then the same picture or video
 * opens with a plain ACTION_VIEW in the guest's own gallery. The camera names it as Samsung's
 * provider has it (content://secmedia/media/<id>, which a guest has not: the same id in MediaStore)
 * or, when it has not found its last shot, as a whole collection (then the newest DCIM/Camera
 * picture or video). When no app takes it either, the camera gets its own exception back.
 */
public final class OneOSGallery {
    private OneOSGallery() {}

    public static void startActivityForResult(Activity a, Intent i, int code, Bundle options) {
        try {
            a.startActivityForResult(i, code, options);
            return;
        } catch (ActivityNotFoundException e) {
            ContentResolver cr = a.getContentResolver();
            Uri u = null;
            try {
                u = viewUri(cr, i.getData());
            } catch (RuntimeException f) {
                Log.w("OneOSCamera", "no Samsung Gallery, and no picture for " + i.getData(), f);
            }
            if (u == null) throw e;
            String type = null;
            try { type = cr.getType(u); } catch (RuntimeException ignored) { }
            if (type == null) type = i.getType();
            Intent v = new Intent(Intent.ACTION_VIEW).setDataAndType(u, type).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            Log.i("OneOSCamera", "no Samsung Gallery: " + i.getData() + " opens with ACTION_VIEW as " + u + " (" + type + ")");
            try {
                a.startActivity(v);
            } catch (ActivityNotFoundException g) {
                throw e;
            }
        }
    }

    private static Uri viewUri(ContentResolver cr, Uri data) {
        if (data == null || "secmedia".equals(data.getAuthority()) && !hasSecmedia(cr)) {
            long id = data == null ? -1 : id(data);
            return id >= 0 ? item(cr, id) : newest(cr);
        }
        if (MediaStore.AUTHORITY.equals(data.getAuthority()) && id(data) < 0) return newest(cr);
        return data;
    }

    private static long id(Uri u) {
        String s = u.getLastPathSegment();
        if (s == null) return -1;
        try { return Long.parseLong(s); } catch (NumberFormatException e) { return -1; }
    }

    /** MediaStore's picture or video uri for a files-table id (what galleries open best). */
    private static Uri item(ContentResolver cr, long id) {
        Uri f = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id);
        try (Cursor c = cr.query(f, new String[] {MediaStore.Files.FileColumns.MEDIA_TYPE}, null, null)) {
            if (c != null && c.moveToFirst()) {
                int t = c.getInt(0);
                if (t == MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE) return ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id);
                if (t == MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO) return ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, id);
            }
        }
        return f;
    }

    /** The newest picture or video in DCIM/Camera. */
    private static Uri newest(ContentResolver cr) {
        Bundle q = new Bundle();
        q.putString(ContentResolver.QUERY_ARG_SQL_SELECTION, "media_type IN (1, 3) AND relative_path LIKE ?");
        q.putStringArray(ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS, new String[] {"DCIM/Camera/%"});
        q.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, new String[] {"date_added", "_id"});
        q.putInt(ContentResolver.QUERY_ARG_SORT_DIRECTION, ContentResolver.QUERY_SORT_DIRECTION_DESCENDING);
        q.putInt(ContentResolver.QUERY_ARG_LIMIT, 1);
        try (Cursor c = cr.query(MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL), new String[] {"_id"}, q, null)) {
            if (c != null && c.moveToFirst()) return item(cr, c.getLong(0));
        }
        return null;
    }

    private static boolean hasSecmedia(ContentResolver cr) {
        ContentProviderClient c = null;
        try { c = cr.acquireUnstableContentProviderClient("secmedia"); } catch (RuntimeException ignored) { }
        if (c == null) return false;
        c.close();
        return true;
    }
}
