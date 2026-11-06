package oneos.launcher;

import android.app.BroadcastOptions;
import android.content.Intent;
import android.os.SystemClock;
import android.util.Log;
import android.view.View;
import android.view.ViewConfiguration;

/**
 * Double tap to sleep on the home screen, as One UI has it (owner, 0.4.59). Pixel Launcher's
 * WorkspaceTouchListener sends the wallpaper its "android.wallpaper.tap" for a tap on an empty
 * spot (icons, folders and widgets take their own taps); two of them within 400 ms, close
 * together, ask SystemUI to sleep (oneos.sysui.OneOSDt2s, which takes it from this launcher only:
 * the broadcast shares its sender's identity).
 */
public final class OneOSDt2s {
    private static final String ACTION = "oneos.intent.action.DOUBLE_TAP_SLEEP";
    private static long last;
    private static int lastX, lastY;

    private OneOSDt2s() {}

    /** After WorkspaceTouchListener's sendWallpaperCommand: cmd, the tap's screen x and y, the workspace. */
    public static void wallpaperTap(String cmd, int x, int y, View workspace) {
        try {
            if (!"android.wallpaper.tap".equals(cmd)) return;
            long now = SystemClock.uptimeMillis();
            int near = ViewConfiguration.get(workspace.getContext()).getScaledTouchSlop() * 6;
            if (last != 0 && now - last < 400 && Math.abs(x - lastX) < near && Math.abs(y - lastY) < near) {
                last = 0;
                BroadcastOptions o = BroadcastOptions.makeBasic();
                o.setShareIdentityEnabled(true);
                workspace.getContext().sendBroadcast(new Intent(ACTION).setPackage("com.android.systemui"), null, o.toBundle());
                Log.i("OneOSDt2s", "double tap on the home screen: sleep asked");
                return;
            }
            last = now;
            lastX = x;
            lastY = y;
        } catch (RuntimeException e) {
            Log.w("OneOSDt2s", "home screen double tap", e);
        }
    }
}
