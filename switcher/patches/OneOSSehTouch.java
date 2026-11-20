package com.android.server.biometrics.sensors.fingerprint.aidl;

import android.os.IBinder;
import android.os.Parcel;
import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;

/**
 * OneOS (0.5.18): a Galaxy's optical in-display fingerprint sensor for the guest, as One UI drives it.
 *
 * The guest's SystemUI sends the phone's fingerprint HAL the standard onPointerDown/onPointerUp, and the HAL captured
 * on them, but every image failed ("CAPTURE_FAILED", secure app error 39; owner's A36, Nothing OS): One UI's
 * fingerprint service (SemFpLocalHbmOpticalController.handleTouchEventInLhbm, in-house local HBM) first lights the
 * panel's local HBM spot (/sys/class/lcd/panel/local_hbm 2) and tells the HAL through Samsung's extension
 * (ISehFingerprint.sehRequest(sensor, 43, brightness frozen 1, {2 down | 1 up})). With both the A36 matched One UI's
 * enrolment ("IDENTIFY_SUCCESS"); without them never. One UI also holds the panel at a high brightness while the
 * spot is on (setFreezeBrightnessMode, 500 nits): at the owner's usual brightness every capture was BAD_QUALITY,
 * with the slider at its top every one matched. So the display is set to full brightness for the touch, the way
 * the brightness slider sets it while dragged (DisplayManager.setTemporaryBrightness), and given back after.
 * FingerprintProvider.onPointerDown and onPointerUp call down() and up() first (patches/guest_seh_touch.py).
 *
 * Only on a phone where guest_prepare.sh wrote /data/system/oneos_fp_lhbm (an optical sensor with local HBM, from
 * One UI's floating features); everywhere else both return at once. Any failure is logged and the touch goes on as
 * before.
 */
public final class OneOSSehTouch {
    private static final String TAG = "OneOSSehTouch";
    private static final String HAL = "android.hardware.biometrics.fingerprint.IFingerprint/default";
    private static final String DESC = "vendor.samsung.hardware.biometrics.fingerprint.ISehFingerprint";
    private static final String LHBM = "/sys/class/lcd/panel/local_hbm";
    private static final int REQUEST_FINGER_DOWN_UP = 43;

    private static int sOn = -1;
    private static IBinder sExt;

    private OneOSSehTouch() {}

    public static void down() {
        if (!on()) return;
        brightness(1f);
        write(LHBM, "2");
        try {
            Thread.sleep(40);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        seh(2);
    }

    public static void up() {
        if (!on()) return;
        seh(1);
        write(LHBM, "0");
        brightness(Float.NaN);
    }

    /** The default display at [value] (0..1), or back to its own brightness for NaN. */
    private static void brightness(float value) {
        try {
            Object thread = Class.forName("android.app.ActivityThread").getMethod("currentActivityThread").invoke(null);
            Object ctx = thread.getClass().getMethod("getSystemContext").invoke(thread);
            Object dm = ctx.getClass().getMethod("getSystemService", String.class).invoke(ctx, "display");
            dm.getClass().getMethod("setTemporaryBrightness", int.class, float.class).invoke(dm, 0, value);
        } catch (Throwable t) {
            Log.w(TAG, "temporary brightness " + value + " failed", t);
        }
    }

    private static synchronized boolean on() {
        if (sOn < 0) sOn = new File("/data/system/oneos_fp_lhbm").exists() ? 1 : 0;
        return sOn == 1;
    }

    private static synchronized void seh(int state) {
        Parcel d = Parcel.obtain();
        Parcel r = Parcel.obtain();
        try {
            if (sExt == null || !sExt.isBinderAlive()) {
                Method get = Class.forName("android.os.ServiceManager").getMethod("getService", String.class);
                IBinder hal = (IBinder) get.invoke(null, HAL);
                sExt = hal == null ? null : (IBinder) IBinder.class.getMethod("getExtension").invoke(hal);
            }
            if (sExt == null) {
                Log.w(TAG, "no Samsung fingerprint extension");
                return;
            }
            d.writeInterfaceToken(DESC);
            d.writeInt(0);
            d.writeInt(REQUEST_FINGER_DOWN_UP);
            d.writeInt(1);
            d.writeByteArray(new byte[] {(byte) state});
            sExt.transact(1, d, r, 0);
            r.readException();
        } catch (Throwable t) {
            sExt = null;
            Log.w(TAG, "finger " + (state == 2 ? "down" : "up") + " request failed", t);
        } finally {
            d.recycle();
            r.recycle();
        }
    }

    private static void write(String path, String value) {
        try (FileOutputStream o = new FileOutputStream(path)) {
            o.write(value.getBytes());
        } catch (Throwable t) {
            Log.w(TAG, path + ": " + t);
        }
    }
}
