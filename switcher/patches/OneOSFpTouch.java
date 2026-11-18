package com.android.server.biometrics.sensors.fingerprint.aidl;

import android.os.SystemClock;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileReader;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * OneOS (0.5.20): a finger on a Galaxy's optical in-display sensor, for a guest whose own SystemUI never reports it.
 *
 * ColorOS draws its fingerprint icon but never calls FingerprintProvider.onPointerDown: on OPPO's phones the touch
 * panel driver tells OPPO's fingerprint HAL of a finger on the sensor, and a Galaxy's panel and HAL have no such
 * path (owner's A36, ColorOS 17: the icon showed, touching it did nothing, no pointer call in the log). This thread
 * reads the touch panel itself (the evdev node guest_prepare.sh names in /data/system/oneos_fp_touch, read beside
 * the guest's InputReader) and, while a fingerprint client (authentication or enrolment) is running, turns a finger
 * landing in the sensor circle (/data/system/oneos_udfps) into FingerprintProvider.onPointerDown and its lifting into
 * onPointerUp, the calls a stock SystemUI makes; OneOSSehTouch (guest_seh_touch.py) then lights the spot and tells
 * Samsung's HAL, as for Nothing OS.
 *
 * FingerprintProvider's constructor calls start() (patches/guest_fp_touchwatch.py). Without the two files, or on any
 * error, nothing runs and the guest behaves as before.
 */
public final class OneOSFpTouch implements Runnable {
    private static final String TAG = "OneOSFpTouch";
    private static final int EV_SYN = 0;
    private static final int EV_ABS = 3;
    private static final int ABS_MT_SLOT = 0x2f;
    private static final int ABS_MT_POSITION_X = 0x35;
    private static final int ABS_MT_POSITION_Y = 0x36;
    private static final int ABS_MT_TRACKING_ID = 0x39;
    private static final int SLOTS = 10;

    private static boolean sStarted;

    private final Object mProvider;
    private final String mDevice;
    private final float mScaleX;
    private final float mScaleY;
    private final int mCx;
    private final int mCy;
    private final int mR;

    private final int[] mX = new int[SLOTS];
    private final int[] mY = new int[SLOTS];
    private final int[] mId = new int[SLOTS];
    private int mSlot;
    private int mDownSlot;
    private int mIgnored = -1;
    private boolean mDown;

    /** The hold loop's instance (keeper): the watcher it holds the panel for. */
    private final OneOSFpTouch mOwner;
    private volatile boolean mHold;
    /** The running keeper thread, joined at the lift so it cannot light the spot again after it went off. */
    private volatile Thread mKeeper;

    private OneOSFpTouch(OneOSFpTouch owner) {
        mOwner = owner;
        mProvider = null;
        mDevice = null;
        mScaleX = 0;
        mScaleY = 0;
        mCx = 0;
        mCy = 0;
        mR = 0;
    }

    private OneOSFpTouch(Object provider, String device, float sx, float sy, int cx, int cy, int r) {
        mOwner = null;
        mProvider = provider;
        mDevice = device;
        mScaleX = sx;
        mScaleY = sy;
        mCx = cx;
        mCy = cy;
        mR = r;
        for (int i = 0; i < SLOTS; i++) mId[i] = -1;
    }

    /** /data/system/oneos_fp_touch: "<evdev node> <touch max x> <touch max y> <panel width> <panel height>". */
    public static synchronized void start(Object provider) {
        if (sStarted) return;
        try {
            String[] t = line("/data/system/oneos_fp_touch");
            String[] u = line("/data/system/oneos_udfps");
            if (t == null || u == null || t.length < 5 || u.length < 3) return;
            float sx = Float.parseFloat(t[3]) / (Integer.parseInt(t[1]) + 1);
            float sy = Float.parseFloat(t[4]) / (Integer.parseInt(t[2]) + 1);
            Thread th = new Thread(new OneOSFpTouch(provider, t[0], sx, sy,
                    Integer.parseInt(u[0]), Integer.parseInt(u[1]), Integer.parseInt(u[2])), TAG);
            th.setDaemon(true);
            th.start();
            sStarted = true;
            Log.i(TAG, "watching " + t[0] + " for the sensor at " + u[0] + "," + u[1] + " r " + u[2]);
        } catch (Throwable e) {
            Log.w(TAG, "not started", e);
        }
    }

    private static String[] line(String path) {
        File f = new File(path);
        if (!f.isFile()) return null;
        try (BufferedReader r = new BufferedReader(new FileReader(f))) {
            String s = r.readLine();
            return s == null ? null : s.trim().split("\\s+");
        } catch (Throwable e) {
            return null;
        }
    }

    @Override
    public void run() {
        if (mOwner != null) {
            mOwner.keep();
            return;
        }
        byte[] ev = new byte[24];
        while (true) {
            try (InputStream in = new FileInputStream(mDevice)) {
                while (true) {
                    int n = 0;
                    while (n < 24) {
                        int k = in.read(ev, n, 24 - n);
                        if (k < 0) throw new java.io.EOFException();
                        n += k;
                    }
                    int type = (ev[16] & 0xff) | (ev[17] & 0xff) << 8;
                    int code = (ev[18] & 0xff) | (ev[19] & 0xff) << 8;
                    int value = (ev[20] & 0xff) | (ev[21] & 0xff) << 8 | (ev[22] & 0xff) << 16 | (ev[23] & 0xff) << 24;
                    event(type, code, value);
                }
            } catch (Throwable e) {
                Log.w(TAG, mDevice + ": " + e);
                mDown = false;
                SystemClock.sleep(2000);
            }
        }
    }

    private void event(int type, int code, int value) {
        if (type == EV_ABS) {
            if (code == ABS_MT_SLOT) {
                mSlot = value >= 0 && value < SLOTS ? value : 0;
            } else if (code == ABS_MT_POSITION_X) {
                mX[mSlot] = value;
            } else if (code == ABS_MT_POSITION_Y) {
                mY[mSlot] = value;
            } else if (code == ABS_MT_TRACKING_ID) {
                mId[mSlot] = value;
            }
            return;
        }
        if (type != EV_SYN || code != 0) return;
        if (mDown) {
            // Down until that finger lifts, wherever it moves: a firm press spreads the finger and moved its centre
            // out of the circle, so the spot went off and on every half second and each capture was cut (A36).
            if (mId[mDownSlot] < 0) {
                mDown = false;
                hold(false);
                pointer(false, mCx, mCy);
            }
            return;
        }
        // A finger that landed with no scan running is not tried again on every report until it lifts.
        if (mIgnored >= 0 && mId[mIgnored] < 0) mIgnored = -1;
        long reach = (long) mR * mR * 2;
        for (int i = 0; i < SLOTS; i++) {
            if (mId[i] < 0 || i == mIgnored) continue;
            long dx = (long) (mX[i] * mScaleX) - mCx;
            long dy = (long) (mY[i] * mScaleY) - mCy;
            if (dx * dx + dy * dy <= reach) {
                // No scan running (unlocked; a swipe up from the bottom edge crosses the sensor): the spot stays
                // off. It was lit first and left lit when no scan took the touch (A36: the circle came back over
                // recents after an unlock and stayed for seconds).
                if (!scanning()) {
                    mIgnored = i;
                    return;
                }
                mDownSlot = i;
                hold(true);
                mDown = pointer(true, mX[i] * mScaleX, mY[i] * mScaleY);
                if (!mDown) {
                    hold(false);
                    off();
                    mIgnored = i;
                }
                return;
            }
        }
    }

    /** FingerprintProvider.onPointerDown/onPointerUp for the running Udfps client; false when there is none. */
    private boolean pointer(boolean down, float x, float y) {
        try {
            Field f = mProvider.getClass().getDeclaredField("mFingerprintSensors");
            f.setAccessible(true);
            Object sensors = f.get(mProvider);
            if ((Integer) sensors.getClass().getMethod("size").invoke(sensors) == 0) return false;
            int sensorId = (Integer) sensors.getClass().getMethod("keyAt", int.class).invoke(sensors, 0);
            Object sensor = sensors.getClass().getMethod("valueAt", int.class).invoke(sensors, 0);
            Object scheduler = sensor.getClass().getMethod("getScheduler").invoke(sensor);
            Object client = scheduler.getClass().getMethod("getCurrentClient").invoke(scheduler);
            if (client == null || !udfps(client.getClass())) {
                // The scan can end while the finger is still down (a match): the lift still turns the spot and the
                // spot off (it stayed lit on the home screen, A36).
                if (!down) release();
                return false;
            }
            long requestId = (Long) client.getClass().getMethod("getRequestId").invoke(client);
            Class<?> pcClass = Class.forName("android.hardware.biometrics.fingerprint.PointerContext");
            Object pc = pcClass.getConstructor().newInstance();
            pcClass.getField("pointerId").setInt(pc, 0);
            pcClass.getField("x").setFloat(pc, x);
            pcClass.getField("y").setFloat(pc, y);
            pcClass.getField("minor").setFloat(pc, mR);
            pcClass.getField("major").setFloat(pc, mR);
            pcClass.getField("time").setLong(pc, SystemClock.uptimeMillis());
            if (down) oplusTouch(true);
            Method m = mProvider.getClass().getMethod(down ? "onPointerDown" : "onPointerUp", long.class, int.class, pcClass);
            m.invoke(mProvider, requestId, sensorId, pc);
            if (!down) {
                oplusTouch(false);
                off();
            }
            Log.i(TAG, (down ? "finger down" : "finger up") + " for " + client.getClass().getSimpleName());
            return true;
        } catch (Throwable e) {
            Log.w(TAG, "pointer " + (down ? "down" : "up") + " failed", e);
            if (!down) release();
            return false;
        }
    }

    /**
     * While the finger is down the spot stays lit, set at once and again if anything turns it off, with a frame sent to
     * the panel every 16 ms so it shows at once (it came a second late on a still lock screen, after the capture, and
     * the scans were BAD_QUALITY; A36 ColorOS, 0.5.20). Only the spot: the screen keeps its brightness, as on One UI.
     */
    private void hold(boolean on) {
        if (on) {
            spot("2");
            backlight(true);
            repaint();
            mHold = true;
            Thread t = new Thread(new OneOSFpTouch(this), TAG + "Hold");
            t.setDaemon(true);
            mKeeper = t;
            t.start();
        } else {
            mHold = false;
            // The keeper may be inside a spot("2") (up to ~60 ms): let it finish before the spot goes off, or it
            // lit the spot again just after (A36: 2 lifts in 10 left the circle on after the unlock).
            Thread k = mKeeper;
            mKeeper = null;
            if (k != null && k != Thread.currentThread()) {
                try {
                    k.join(250);
                } catch (InterruptedException e) {
                    // Off below all the same.
                }
            }
        }
    }

    /** Whether a fingerprint scan (authentication or enrolment with the sensor under the screen) still runs. */
    private boolean scanning() {
        try {
            Field f = mProvider.getClass().getDeclaredField("mFingerprintSensors");
            f.setAccessible(true);
            Object sensors = f.get(mProvider);
            if ((Integer) sensors.getClass().getMethod("size").invoke(sensors) == 0) return false;
            Object sensor = sensors.getClass().getMethod("valueAt", int.class).invoke(sensors, 0);
            Object scheduler = sensor.getClass().getMethod("getScheduler").invoke(sensor);
            Object client = scheduler.getClass().getMethod("getCurrentClient").invoke(scheduler);
            return client != null && udfps(client.getClass());
        } catch (Throwable e) {
            return true;
        }
    }

    private void keep() {
        File lhbm = new File("/sys/class/lcd/panel/local_hbm");
        int n = 0;
        while (mHold) {
            try {
                // A match ends the scan while the finger is still down: the spot goes off then, as on One UI, not at
                // the lift (it stayed lit on the unlocked screen while the finger rested). Checked every ~80 ms.
                if (++n % 5 == 0 && !scanning()) {
                    mHold = false;
                    off();
                    return;
                }
                String[] v = line(lhbm.getPath());
                if (mHold && (v == null || !"2".equals(v[0]))) spot("2");
                if (mHold) backlight(true);
                repaint();
                Thread.sleep(16);
            } catch (Throwable e) {
                return;
            }
        }
    }

    /**
     * The panel's local HBM moves one step at a time, 0 (off) <-> 1 (on, source off) <-> 2 (lit), as One UI's
     * SemFpLocalHbmOpticalController.changeToNextState writes it: a write of 2 straight after 0, or of 0 after 2, is
     * ignored (A36: the spot came late or never, and stayed lit after an unlock). So every change goes through 1.
     */
    private static void spot(String v) {
        try {
            File f = new File("/sys/class/lcd/panel/local_hbm");
            String[] cur = line(f.getPath());
            if (cur != null && v.equals(cur[0])) return;
            if (!"1".equals(v) && (cur == null || !"1".equals(cur[0]))) {
                write(f, "1");
                // Into the lit state the panel needs a few frames at 1 first (it takes the change with the frames it
                // is sent): stepped straight on, the spot still came late; with ~40 ms of frames between, at once.
                if ("2".equals(v)) {
                    for (int i = 0; i < 4; i++) {
                        repaint();
                        Thread.sleep(10);
                    }
                }
            }
            write(f, v);
        } catch (Throwable e) {
            // No local HBM on this panel.
        }
    }

    /** The lift without a scan to tell: OPPO's touch-up, Samsung's finger up and the spot off. */
    private void release() {
        oplusTouch(false);
        try {
            Class.forName("com.android.server.biometrics.sensors.fingerprint.aidl.OneOSSehTouch").getMethod("up").invoke(null);
        } catch (Throwable e) {
            Log.w(TAG, "finger up failed", e);
        }
        off();
    }

    /** The spot off through 1 (OneOSSehTouch.up writes 0 straight after 2, which the panel ignores) and the backlight back. */
    private void off() {
        spot("0");
        backlight(false);
    }

    /**
     * One composition of the screen (SurfaceFlinger's repaint, transaction 1004). A Galaxy's AMOLED panel takes the
     * local HBM spot with the next frame it is sent; on a still lock screen there is none, so the spot came a second
     * late, after the capture (A36 ColorOS, 0.5.20; a stock SystemUI draws its pressed animation, which sends frames).
     * Called while the finger is down. The rest of the screen keeps its brightness, as on One UI.
     */
    private static void repaint() {
        android.os.Parcel d = android.os.Parcel.obtain();
        try {
            Object sf = Class.forName("android.os.ServiceManager").getMethod("getService", String.class)
                    .invoke(null, "SurfaceFlinger");
            if (sf == null) return;
            d.writeInterfaceToken("android.ui.ISurfaceComposer");
            ((android.os.IBinder) sf).transact(1004, d, null, 0);
        } catch (Throwable e) {
            // Nothing to do: the spot comes with the next frame anyway.
        } finally {
            d.recycle();
        }
    }

    private String mSavedBacklight;

    /**
     * The backlight raised for the touch, as One UI freezes the panel at about 500 nits while the spot is lit
     * (SemFpLocalHbmOpticalController.freezingBrightness): 60% of the panel's range, never lowered, and given back after.
     * The panel's top (its outdoor level) lit the whole screen and is not used.
     */
    private void backlight(boolean high) {
        try {
            File node = null;
            int max = 0;
            File[] all = new File("/sys/class/backlight").listFiles();
            if (all != null) {
                for (File d : all) {
                    String[] m = line(new File(d, "max_brightness").getPath());
                    int v = m == null ? 0 : Integer.parseInt(m[0]);
                    if (v > max) {
                        max = v;
                        node = new File(d, "brightness");
                    }
                }
            }
            if (node == null) return;
            String[] cur = line(node.getPath());
            int now = cur == null ? 0 : Integer.parseInt(cur[0]);
            int want = max * 6 / 10;
            if (high) {
                if (mSavedBacklight == null) mSavedBacklight = String.valueOf(now);
                if (now < want) write(node, String.valueOf(want));
            } else if (mSavedBacklight != null) {
                write(node, mSavedBacklight);
                mSavedBacklight = null;
            }
        } catch (Throwable e) {
            Log.w(TAG, "backlight " + (high ? "up" : "back") + " failed", e);
        }
    }

    private static void write(File f, String v) throws java.io.IOException {
        try (java.io.FileOutputStream o = new java.io.FileOutputStream(f)) {
            o.write(v.getBytes());
        }
    }

    /**
     * ColorOS: the touch-down/up an OPPO phone's fingerprint HAL reports (fingerprint commands 1201 and 1202, which
     * FingerprintServiceProviderExtImpl turns into dispatchTouchDown/Up). Without it OPPO's SystemUI took the finger for
     * a lock screen swipe and cancelled the authentication 3 ms after the pointer down (A36, 0.5.20). Nothing elsewhere.
     */
    private void oplusTouch(boolean down) {
        try {
            Field f = mProvider.getClass().getDeclaredField("mFingerprintProviderExt");
            f.setAccessible(true);
            Object ext = f.get(null);
            if (ext == null) return;
            Method m = ext.getClass().getMethod(down ? "dispatchTouchDown" : "dispatchTouchUp");
            m.setAccessible(true);
            m.invoke(ext);
        } catch (NoSuchFieldException | NoSuchMethodException e) {
            // Not ColorOS's framework.
        } catch (Throwable e) {
            Log.w(TAG, "OPPO touch " + (down ? "down" : "up") + " failed", e);
        }
    }

    private static boolean udfps(Class<?> c) {
        for (; c != null; c = c.getSuperclass()) {
            for (Class<?> i : c.getInterfaces()) {
                if (i.getName().endsWith(".fingerprint.Udfps")) return true;
            }
        }
        return false;
    }
}
