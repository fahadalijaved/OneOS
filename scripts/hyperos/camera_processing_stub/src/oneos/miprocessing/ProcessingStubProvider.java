package oneos.miprocessing;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;

/** No photo is ever processing: every query is an empty table, every change ignored. */
public final class ProcessingStubProvider extends ContentProvider {
    /** The columns the Gallery's processing loader names (media_store_id, media_path, date_taken). */
    private static final String[] COLUMNS = {"_id", "media_store_id", "media_path", "date_taken"};

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
