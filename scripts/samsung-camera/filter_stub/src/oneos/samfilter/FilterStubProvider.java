package oneos.samfilter;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;

/** An empty Filter Provider: no filters, every change ignored. */
public final class FilterStubProvider extends ContentProvider {
    /** The columns the camera reads (com.sec.android.app.camera.filter.b, g). */
    private static final String[] COLUMNS = {
        "_id", "name", "filename", "version", "filter_type", "vendor", "package_name",
        "preload_filter", "title_id", "category", "filter_thumbnail", "filter_order",
        "param_intensity", "param_filter_temperature", "param_filter_contrast",
        "param_filter_saturation", "param_grain_power",
    };

    @Override public boolean onCreate() { return true; }

    @Override public Cursor query(Uri uri, String[] projection, String selection,
            String[] selectionArgs, String sortOrder) {
        return new MatrixCursor(projection != null && projection.length > 0 ? projection : COLUMNS);
    }

    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { return 0; }
    @Override public Bundle call(String method, String arg, Bundle extras) { return null; }
}
