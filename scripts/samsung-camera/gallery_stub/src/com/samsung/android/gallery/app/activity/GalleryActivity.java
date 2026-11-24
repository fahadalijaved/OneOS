package com.samsung.android.gallery.app.activity;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;

import java.util.List;
import java.util.Set;

/**
 * Forwards Samsung Camera's gallery / quick-view launches to the guest's gallery
 * (ColorOS Gallery first, then any non-self gallery handler), including when no
 * photos exist yet in DCIM/Camera.
 */
public final class GalleryActivity extends Activity {
    private static final String TAG = "OneOSGalleryStub";
    private static final String[] GALLERY_PACKAGES = {
        "com.coloros.gallery3d",
        "com.oneplus.gallery",
        "com.oplus.gallery",
        "com.google.android.apps.photos",
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            Intent src = getIntent();
            Uri data = extractUri(src);
            String mime = src != null ? src.getType() : null;
            Log.i(TAG, "incoming action=" + (src != null ? src.getAction() : null)
                    + " component=" + (src != null ? src.getComponent() : null)
                    + " data=" + data + " type=" + mime + " extras=" + extraKeys(src));
            Uri targetUri = resolveViewUri(data, mime);
            if (targetUri != null && launchView(targetUri, mime)) {
                return;
            }
            if (launchGalleryApp()) {
                return;
            }
            Log.w(TAG, "no guest gallery app available for " + data);
        } catch (Throwable t) {
            Log.w(TAG, "gallery forward failed", t);
        } finally {
            finish();
            overridePendingTransition(0, 0);
        }
    }

    @SuppressWarnings("deprecation")
    private static Uri extractUri(Intent src) {
        if (src == null) {
            return null;
        }
        Uri data = src.getData();
        if (data != null) {
            return data;
        }
        try {
            Bundle extras = src.getExtras();
            if (extras != null) {
                Object stream = extras.get(Intent.EXTRA_STREAM);
                if (stream instanceof Uri) {
                    return (Uri) stream;
                }
                if (stream instanceof String && !((String) stream).isEmpty()) {
                    return Uri.parse((String) stream);
                }
                String strUri = extras.getString("uri");
                if (strUri != null && !strUri.isEmpty()) {
                    return Uri.parse(strUri);
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "failed reading incoming extras", e);
        }
        return null;
    }

    private static String extraKeys(Intent src) {
        if (src == null) {
            return "none";
        }
        try {
            Bundle b = src.getExtras();
            if (b == null || b.isEmpty()) {
                return "none";
            }
            Set<String> keys = b.keySet();
            return keys != null ? keys.toString() : "none";
        } catch (RuntimeException e) {
            return "<unreadable>";
        }
    }

    private Uri resolveViewUri(Uri data, String mime) {
        ContentResolver cr = getContentResolver();
        if (data == null) {
            return newestInCamera(cr);
        }
        String auth = data.getAuthority();
        long id = parseTrailingId(data);
        if ("secmedia".equals(auth)) {
            return id >= 0 ? mediaStoreUri(cr, id, mime) : newestInCamera(cr);
        }
        if (MediaStore.AUTHORITY.equals(auth) && id < 0) {
            return newestInCamera(cr);
        }
        return data;
    }

    private boolean launchView(Uri uri, String fallbackMime) {
        ContentResolver cr = getContentResolver();
        String type = null;
        try {
            type = cr.getType(uri);
        } catch (RuntimeException ignored) {
        }
        if (type == null || type.isEmpty()) {
            type = fallbackMime;
        }
        if (type == null || type.isEmpty() || !type.contains("/") || "*/*".equals(type)
                || (!type.startsWith("image/") && !type.startsWith("video/"))) {
            type = uri.toString().contains("/video/") ? "video/*" : "image/*";
        }
        ClipData clip = null;
        try {
            clip = ClipData.newUri(cr, "media", uri);
        } catch (RuntimeException ignored) {
        }
        boolean forward = getCallingActivity() != null;
        for (String pkg : GALLERY_PACKAGES) {
            Intent inTask = new Intent(Intent.ACTION_VIEW)
                    .setDataAndType(uri, type)
                    .setPackage(pkg)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if (clip != null) {
                inTask.setClipData(clip);
            }
            if (forward) {
                inTask.addFlags(Intent.FLAG_ACTIVITY_FORWARD_RESULT);
            }
            if (tryStart(inTask)) {
                return true;
            }
            Intent newTask = new Intent(Intent.ACTION_VIEW)
                    .setDataAndType(uri, type)
                    .setPackage(pkg)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            if (clip != null) {
                newTask.setClipData(clip);
            }
            if (tryStart(newTask)) {
                return true;
            }
        }
        Intent generic = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, type)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (clip != null) {
            generic.setClipData(clip);
        }
        if (tryStartExcludingSelf(generic)) {
            return true;
        }
        return tryStartExcludingSelf(new Intent(generic).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    private boolean launchGalleryApp() {
        PackageManager pm = getPackageManager();
        for (String pkg : GALLERY_PACKAGES) {
            Intent launch = pm.getLaunchIntentForPackage(pkg);
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
                if (tryStart(launch)) {
                    return true;
                }
            }
        }
        Intent colorOsMain = new Intent(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_LAUNCHER)
                .setClassName("com.coloros.gallery3d", "com.coloros.gallery3d.app.MainActivity")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
        if (tryStart(colorOsMain)) {
            return true;
        }
        Intent cat = Intent.makeMainSelectorActivity(Intent.ACTION_MAIN, Intent.CATEGORY_APP_GALLERY)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        if (tryStartExcludingSelf(cat)) {
            return true;
        }
        Intent collection = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, "vnd.android.cursor.dir/image")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return tryStartExcludingSelf(collection);
    }

    private boolean tryStartExcludingSelf(Intent intent) {
        PackageManager pm = getPackageManager();
        List<ResolveInfo> resolved = pm.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY);
        String self = getPackageName();
        for (ResolveInfo ri : resolved) {
            if (ri.activityInfo == null || self.equals(ri.activityInfo.packageName)) {
                continue;
            }
            Intent explicit = new Intent(intent).setClassName(ri.activityInfo.packageName, ri.activityInfo.name);
            if (tryStart(explicit)) {
                return true;
            }
        }
        return false;
    }

    private boolean tryStart(Intent intent) {
        try {
            startActivity(intent);
            return true;
        } catch (ActivityNotFoundException | SecurityException e) {
            Log.d(TAG, "tryStart failed for " + intent + ": " + e.getMessage());
            return false;
        }
    }

    private static long parseTrailingId(Uri u) {
        String s = u.getLastPathSegment();
        if (s == null) {
            return -1;
        }
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    private static Uri mediaStoreUri(ContentResolver cr, long id, String mime) {
        Uri f = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id);
        try (Cursor c = cr.query(f, new String[] { MediaStore.Files.FileColumns.MEDIA_TYPE }, null, null)) {
            if (c != null && c.moveToFirst()) {
                int t = c.getInt(0);
                if (t == MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE) {
                    return ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id);
                }
                if (t == MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO) {
                    return ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, id);
                }
            }
        } catch (RuntimeException ignored) {
        }
        if (mime != null && mime.startsWith("video/")) {
            return ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, id);
        }
        return ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id);
    }

    private static Uri newestInCamera(ContentResolver cr) {
        Bundle q = new Bundle();
        q.putString(ContentResolver.QUERY_ARG_SQL_SELECTION, "media_type IN (1, 3) AND relative_path LIKE ?");
        q.putStringArray(ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS, new String[] { "DCIM/Camera/%" });
        q.putStringArray(ContentResolver.QUERY_ARG_SORT_COLUMNS, new String[] { "date_added", "_id" });
        q.putInt(ContentResolver.QUERY_ARG_SORT_DIRECTION, ContentResolver.QUERY_SORT_DIRECTION_DESCENDING);
        q.putInt(ContentResolver.QUERY_ARG_LIMIT, 1);
        try (Cursor c = cr.query(MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL), new String[] { "_id" }, q, null)) {
            if (c != null && c.moveToFirst()) {
                return mediaStoreUri(cr, c.getLong(0), null);
            }
        } catch (RuntimeException ignored) {
        }
        return null;
    }
}
