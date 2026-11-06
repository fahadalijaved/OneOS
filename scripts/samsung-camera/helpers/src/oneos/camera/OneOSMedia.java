package oneos.camera;

import android.content.ContentProviderClient;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.provider.MediaStore;
import android.util.Log;
import java.util.LinkedHashSet;
import java.util.regex.Pattern;

/**
 * One UI's camera keeps its media in Samsung's own provider (content://secmedia/...), which a
 * guest does not have. Inserts came back null, and the camera crashed on the null uri after a
 * video (Pixel on the Z Fold8 Ultra, 0.4.59 test); queries came back null, so the camera found
 * "the camera bucket empty" and its thumbnail opened nothing. Without that provider, inserts go
 * to MediaStore with the standard columns, and queries on secmedia/media[/id] go to MediaStore's
 * files table, with Samsung's column names put in MediaStore's (redirect). With the provider, or
 * for any other uri, nothing changes.
 */
public final class OneOSMedia {
    private static final String[] KEEP = {
        "_display_name", "mime_type", "_data", "datetaken", "duration", "orientation", "is_pending",
        "width", "height", "date_added", "date_modified", "title", "_size", "relative_path",
        "resolution", "latitude", "longitude", "date_expires",
    };
    private static Boolean secmedia;

    private OneOSMedia() {}

    public static Uri insert(ContentResolver cr, Uri uri, ContentValues values) {
        if (!redirected(cr, uri)) return cr.insert(uri, values);
        String mime = values.getAsString("mime_type");
        Integer type = null;
        try { type = values.getAsInteger("media_type"); } catch (RuntimeException ignored) { }
        Uri target;
        if ((mime != null && mime.startsWith("video/")) || (type != null && type == 3)) {
            target = MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
        } else if ((mime != null && mime.startsWith("image/")) || (type != null && type == 1)) {
            target = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
        } else {
            target = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
        }
        ContentValues v = new ContentValues();
        if (!values.containsKey("datetaken") && values.get("datetime") instanceof Number) {
            v.put("datetaken", ((Number) values.get("datetime")).longValue());
        }
        for (String k : KEEP) {
            if (!values.containsKey(k)) continue;
            Object o = values.get(k);
            if (o == null) v.putNull(k);
            else if (o instanceof String) v.put(k, (String) o);
            else if (o instanceof Integer) v.put(k, (Integer) o);
            else if (o instanceof Long) v.put(k, (Long) o);
            else if (o instanceof Double) v.put(k, (Double) o);
            else if (o instanceof Float) v.put(k, (Float) o);
            else if (o instanceof Boolean) v.put(k, (Boolean) o);
            else v.put(k, o.toString());
        }
        try {
            Uri r = cr.insert(target, v);
            Log.i("OneOSCamera", "no secmedia provider: " + uri + " -> " + r);
            return r;
        } catch (RuntimeException e) {
            Log.w("OneOSCamera", "no secmedia provider, and MediaStore refused " + target, e);
            return null;
        }
    }

    public static Cursor query(ContentResolver cr, Uri uri, String[] projection, String selection, String[] args, String sort) {
        Uri t = filesUri(cr, uri);
        if (t == null) return cr.query(uri, projection, selection, args, sort);
        return redirect(cr, uri, t, projection, sqlBundle(selection, args, sort), null);
    }

    public static Cursor query(ContentResolver cr, Uri uri, String[] projection, String selection, String[] args, String sort,
                               CancellationSignal signal) {
        Uri t = filesUri(cr, uri);
        if (t == null) return cr.query(uri, projection, selection, args, sort, signal);
        return redirect(cr, uri, t, projection, sqlBundle(selection, args, sort), signal);
    }

    public static Cursor query(ContentResolver cr, Uri uri, String[] projection, Bundle extras, CancellationSignal signal) {
        Uri t = filesUri(cr, uri);
        if (t == null) return cr.query(uri, projection, extras, signal);
        return redirect(cr, uri, t, projection, extras, signal);
    }

    /**
     * The query on MediaStore's files table, in its own column names: datetime (Samsung's taken time,
     * ms) is datetaken or else date_modified, media_id is _id, and Samsung's own columns (is_hide,
     * burst_group_id, sef_file_type...) are NULL, in the selection and the order as in the result.
     * A query MediaStore still refuses comes back null, as before (logged with the reason).
     */
    private static Cursor redirect(ContentResolver cr, Uri uri, Uri t, String[] projection, Bundle extras, CancellationSignal signal) {
        Bundle b = extras == null ? new Bundle() : new Bundle(extras);
        for (String k : new String[] {ContentResolver.QUERY_ARG_SQL_SELECTION, ContentResolver.QUERY_ARG_SQL_SORT_ORDER}) {
            String s = b.getString(k);
            if (s != null) b.putString(k, sql(s));
        }
        String[] sortCols = b.getStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS);
        if (sortCols != null) {
            String[] m = sortCols.clone();
            for (int i = 0; i < m.length; i++) m[i] = "datetime".equals(m[i]) ? "datetaken" : "media_id".equals(m[i]) ? "_id" : m[i];
            b.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, m);
        }
        String[] real = columns(projection);
        try {
            Cursor c = cr.query(t, real, b, signal);
            return real == projection ? c : rebuild(c, projection);
        } catch (RuntimeException e) {
            Log.w("OneOSCamera", "no secmedia provider, and MediaStore refused the query " + uri + " " + b + ": " + e);
            return null;
        }
    }

    private static Bundle sqlBundle(String selection, String[] args, String sort) {
        Bundle b = new Bundle();
        if (selection != null) b.putString(ContentResolver.QUERY_ARG_SQL_SELECTION, selection);
        if (args != null) b.putStringArray(ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS, args);
        if (sort != null) b.putString(ContentResolver.QUERY_ARG_SQL_SORT_ORDER, sort);
        return b;
    }

    private static final String DATETIME = "COALESCE(datetaken, date_modified * 1000)";
    private static final Pattern DATETIME_COL = Pattern.compile("\\bdatetime\\b");
    private static final Pattern MEDIA_ID_COL = Pattern.compile("\\bmedia_id\\b");
    private static final Pattern SAMSUNG_COL = Pattern.compile(
            "\\b(is_hide|is_cloud|_data_draft|burst_group_id|group_type|sef_file_type|sef_file_sub_type|best_image|recording_mode|is_favorite|cloud_server_id|cloud_server_path)\\b");

    private static String sql(String s) {
        s = DATETIME_COL.matcher(s).replaceAll(DATETIME);
        s = MEDIA_ID_COL.matcher(s).replaceAll("_id");
        return SAMSUNG_COL.matcher(s).replaceAll("NULL");
    }

    /** The columns to ask MediaStore for; the same array when the camera asked only for its columns. */
    private static String[] columns(String[] projection) {
        if (projection == null) return null;
        boolean own = true;
        for (String p : projection) {
            if (p == null || "datetime".equals(p) || "media_id".equals(p) || SAMSUNG_COL.matcher(p).matches()) own = false;
        }
        if (own) return projection;
        LinkedHashSet<String> r = new LinkedHashSet<>();
        for (String p : projection) {
            if (p == null || SAMSUNG_COL.matcher(p).matches()) continue;
            if ("datetime".equals(p)) { r.add("datetaken"); r.add("date_modified"); }
            else if ("media_id".equals(p)) r.add("_id");
            else r.add(p);
        }
        if (r.isEmpty()) r.add("_id");
        return r.toArray(new String[0]);
    }

    /** The asked columns from MediaStore's: datetime and media_id mapped, Samsung's own null. */
    private static Cursor rebuild(Cursor c, String[] projection) {
        if (c == null) return null;
        MatrixCursor m = new MatrixCursor(projection, c.getCount());
        try {
            int taken = c.getColumnIndex("datetaken"), modified = c.getColumnIndex("date_modified");
            int[] idx = new int[projection.length];
            for (int i = 0; i < projection.length; i++) {
                String p = projection[i];
                idx[i] = p == null ? -1 : "datetime".equals(p) ? -2 : c.getColumnIndex("media_id".equals(p) ? "_id" : p);
            }
            while (c.moveToNext()) {
                Object[] row = new Object[projection.length];
                for (int i = 0; i < projection.length; i++) {
                    if (idx[i] == -2) {
                        if (taken >= 0 && !c.isNull(taken)) row[i] = c.getLong(taken);
                        else if (modified >= 0 && !c.isNull(modified)) row[i] = c.getLong(modified) * 1000;
                    } else if (idx[i] >= 0) {
                        row[i] = value(c, idx[i]);
                    }
                }
                m.addRow(row);
            }
        } finally {
            c.close();
        }
        return m;
    }

    private static Object value(Cursor c, int i) {
        switch (c.getType(i)) {
            case Cursor.FIELD_TYPE_INTEGER: return c.getLong(i);
            case Cursor.FIELD_TYPE_FLOAT: return c.getDouble(i);
            case Cursor.FIELD_TYPE_BLOB: return c.getBlob(i);
            case Cursor.FIELD_TYPE_STRING: return c.getString(i);
            default: return null;
        }
    }

    /** secmedia/media[/id] (query parameters kept) as MediaStore's files table, when there is no secmedia; else null. */
    private static Uri filesUri(ContentResolver cr, Uri uri) {
        if (!redirected(cr, uri)) return null;
        java.util.List<String> seg = uri.getPathSegments();
        if (seg.isEmpty() || !"media".equals(seg.get(0))) return null;
        Uri.Builder b = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL).buildUpon();
        for (int i = 1; i < seg.size(); i++) b.appendPath(seg.get(i));
        b.encodedQuery(uri.getEncodedQuery());
        return b.build();
    }

    private static boolean redirected(ContentResolver cr, Uri uri) {
        return uri != null && "secmedia".equals(uri.getAuthority()) && !hasSecmedia(cr);
    }

    private static boolean hasSecmedia(ContentResolver cr) {
        Boolean s = secmedia;
        if (s == null) {
            ContentProviderClient c = null;
            try { c = cr.acquireUnstableContentProviderClient("secmedia"); } catch (RuntimeException ignored) { }
            s = c != null;
            if (c != null) c.close();
            secmedia = s;
        }
        return s;
    }
}
