package oneos.sysui;

import android.app.KeyguardManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Rect;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;

/**
 * Double tap to sleep, as One UI has it (owner, 0.4.59): a double tap on an empty spot of the lock
 * screen (NotificationShadeWindowView.dispatchTouchEvent, no clickable view under the finger, so a
 * notification's "tap again to open" stays), and on an empty spot of the home screen: Pixel
 * Launcher (oneos.launcher.OneOSDt2s) asks for it with a broadcast this checks by the sender's
 * identity, which the system gives (only that launcher). SystemUI holds DEVICE_POWER.
 */
public final class OneOSDt2s {
    public static final String ACTION = "oneos.intent.action.DOUBLE_TAP_SLEEP";
    private static final String LAUNCHER = "com.google.android.apps.nexuslauncher";
    private static final String TAG = "OneOSDt2s";
    private static boolean registered;
    private static long downTime, lastUpTime;
    private static float downX, downY, lastUpX, lastUpY;
    private static boolean moved, lastTapOk, onEmpty, dozing;
    private static String blocker;

    private OneOSDt2s() {}

    /** NotificationShadeWindowView.onAttachedToWindow: the launcher's requests from now on. */
    public static void register(View v) {
        if (registered) return;
        final Context c = v.getContext().getApplicationContext();
        try {
            c.registerReceiver(new BroadcastReceiver() {
                @Override
                public void onReceive(Context ctx, Intent intent) {
                    String from = getSentFromPackage();
                    if (!LAUNCHER.equals(from)) {
                        Log.w(TAG, "double tap to sleep asked by " + from + ": ignored");
                        return;
                    }
                    sleep(c, "home screen");
                }
            }, new IntentFilter(ACTION), Context.RECEIVER_EXPORTED);
            registered = true;
        } catch (RuntimeException e) {
            Log.w(TAG, "no receiver for the home screen's double tap", e);
        }
    }

    /** NotificationShadeWindowView.dispatchTouchEvent: the lock screen. */
    public static void shadeTouch(View root, MotionEvent e) {
        try {
            KeyguardManager km = root.getContext().getSystemService(KeyguardManager.class);
            if (km == null || !km.isKeyguardLocked()) {
                if (e.getActionMasked() == MotionEvent.ACTION_UP && lastTapOk && e.getEventTime() - lastUpTime < 400) {
                    Log.d(TAG, "lock screen double tap: keyguard not locked, ignored");
                }
                lastTapOk = false;
                return;
            }
            int slop = ViewConfiguration.get(root.getContext()).getScaledTouchSlop();
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downTime = e.getEventTime();
                    downX = e.getRawX();
                    downY = e.getRawY();
                    moved = false;
                    blocker = null;
                    // AOD (test build 9): the guest is asleep and the touches still reach the
                    // shade; a double tap there wakes it, as on a Pixel, whatever is drawn.
                    PowerManager pm = root.getContext().getSystemService(PowerManager.class);
                    dozing = pm != null && !pm.isInteractive();
                    onEmpty = dozing || !clickableAt(root, (int) downX, (int) downY, (long) root.getWidth() * root.getHeight() / 2);
                    break;
                case MotionEvent.ACTION_MOVE:
                    if (Math.abs(e.getRawX() - downX) > slop || Math.abs(e.getRawY() - downY) > slop) moved = true;
                    break;
                case MotionEvent.ACTION_POINTER_DOWN:
                case MotionEvent.ACTION_CANCEL:
                    moved = true;
                    lastTapOk = false;
                    break;
                case MotionEvent.ACTION_UP:
                    long now = e.getEventTime();
                    boolean tap = !moved && onEmpty && now - downTime < 250;
                    if (tap && lastTapOk && downTime - lastUpTime < 400
                            && Math.abs(downX - lastUpX) < slop * 6 && Math.abs(downY - lastUpY) < slop * 6) {
                        lastTapOk = false;
                        if (dozing) {
                            wake(root.getContext(), "always-on display");
                        } else {
                            sleep(root.getContext(), "lock screen");
                        }
                        return;
                    }
                    if (!onEmpty && downTime - lastUpTime < 400) {
                        Log.d(TAG, "lock screen double tap on " + blocker + ": ignored (a control is there)");
                    }
                    lastTapOk = tap;
                    lastUpTime = now;
                    lastUpX = e.getRawX();
                    lastUpY = e.getRawY();
                    break;
                default:
                    break;
            }
        } catch (RuntimeException ex) {
            Log.w(TAG, "lock screen double tap", ex);
        }
    }

    /**
     * A clickable view under the point smaller than half the window (a notification, a shortcut, a
     * button), the root left out. Long-press-only views and the full-screen containers (the lock
     * screen's own view is clickable and long-clickable for its editor; test build 8: no lock screen
     * double tap at all) do not count.
     */
    private static boolean clickableAt(View v, int x, int y, long half) {
        if (!(v instanceof ViewGroup)) return false;
        ViewGroup g = (ViewGroup) v;
        Rect r = new Rect();
        for (int i = g.getChildCount() - 1; i >= 0; i--) {
            View c = g.getChildAt(i);
            if (c.getVisibility() != View.VISIBLE || c.getAlpha() == 0f) continue;
            if (!c.getGlobalVisibleRect(r) || !r.contains(x, y)) continue;
            if (c.isClickable() && (long) r.width() * r.height() < half) {
                blocker = c.getClass().getSimpleName();
                return true;
            }
            if (clickableAt(c, x, y, half)) return true;
        }
        return false;
    }

    /** PowerManager.wakeUp(time, WAKE_REASON_TAP, details), hidden, by reflection (SystemUI may). */
    static void wake(Context c, String where) {
        try {
            PowerManager pm = c.getSystemService(PowerManager.class);
            int reason = 4; // WAKE_REASON_GESTURE where WAKE_REASON_TAP is missing
            try {
                reason = PowerManager.class.getField("WAKE_REASON_TAP").getInt(null);
            } catch (ReflectiveOperationException ignored) {
            }
            PowerManager.class.getMethod("wakeUp", long.class, int.class, String.class)
                    .invoke(pm, SystemClock.uptimeMillis(), reason, "oneos:double-tap");
            Log.i(TAG, "double tap on the " + where + ": wake");
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "double tap on the " + where + ": wakeUp failed", e);
        }
    }

    static void sleep(Context c, String where) {
        try {
            PowerManager pm = c.getSystemService(PowerManager.class);
            PowerManager.class.getMethod("goToSleep", long.class).invoke(pm, SystemClock.uptimeMillis());
            Log.i(TAG, "double tap on the " + where + ": sleep");
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "double tap on the " + where + ": goToSleep failed", e);
        }
    }
}
