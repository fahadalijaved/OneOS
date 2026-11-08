package com.android.server.am;

import android.os.IProgressListener;
import com.android.server.utils.TimingsTraceAndSlog;

/** Records a refusal for the pinned system-user-zero profile before entering the stock writer. */
final class RetainedPinForegroundStartHook {
    private static volatile boolean incompatibleStartObserved;

    private RetainedPinForegroundStartHook() {}

    static boolean invoke(UserController controller, int userId, int displayId, int startMode,
            int autoStopUserInSecs, IProgressListener listener, TimingsTraceAndSlog timing) {
        if (startMode == 1 && userId != 0) {
            incompatibleStartObserved = true;
        }
        return controller.startUserInternal(userId, displayId, startMode, autoStopUserInSecs,
                listener, timing);
    }

    // A normal return only means this hook has not recorded a conflicting attempt.
    static void refuseObservedIncompatibleForegroundStart() {
        if (incompatibleStartObserved) {
            throw new IllegalStateException("Incompatible foreground user start observed");
        }
    }
}
