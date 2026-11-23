package oneos.samgallery;

import android.content.ContentProvider;
import android.content.ContentProviderOperation;
import android.content.ContentProviderResult;
import android.content.ContentValues;
import android.content.OperationApplicationException;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;

import java.util.ArrayList;

/**
 * Stand-in for Samsung Gallery's {@code com.sec.android.gallery3d.provider2}.
 * Samsung Camera's PostSavingModuleNotifyingComplete calls this authority after
 * writing a post-processed photo; without it, post-saving fails into DRAFT->RECOVERY.
 */
public final class GalleryStubProvider extends ContentProvider {
    private static final String[] DEFAULT_COLUMNS = { "_id" };

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection,
            String[] selectionArgs, String sortOrder) {
        String[] cols = (projection != null && projection.length > 0) ? projection : DEFAULT_COLUMNS;
        return new MatrixCursor(cols);
    }

    @Override
    public String getType(Uri uri) {
        return null;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return uri;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 1;
    }

    @Override
    public Bundle call(String method, String arg, Bundle extras) {
        return new Bundle();
    }

    @Override
    public ContentProviderResult[] applyBatch(String authority,
            ArrayList<ContentProviderOperation> operations) throws OperationApplicationException {
        return super.applyBatch(authority, operations);
    }
}
