package com.oplus.gesture.server;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.hardware.TriggerEvent;
import android.hardware.TriggerEventListener;
import android.util.Log;
import java.lang.reflect.Constructor;
import java.util.Locale;

/**
 * ColorOS's raise to wake on a Galaxy (patches/coloros_lift_wake.py, in OplusGestureUI.apk).
 *
 * ScreenOffGestureService listens to the tilt detector while the screen is off and wakes the screen for an event
 * whose value is 0, what OPPO's motion sensor sends for a lift (1 is "put down"). A Galaxy's Tilt Detector sends
 * 1.0 for every tilt, so every lift read as a put down and the screen never woke (S24 FE, ColorOS X9U IN, report
 * 44afc238: four tilt events, each "handle put down").
 * <ul>
 * <li>{@link #register}: on a phone whose tilt detector is not OPPO's and that has Android's pick-up gesture
 * sensor (Samsung's "Pick Up Gesture", one-shot), that sensor is armed instead of the tilt detector, and each
 * pick-up reaches the service's listener as OPPO's lift (value 0). No tilt is listened to then, so no "put down"
 * either. Otherwise the tilt detector as ColorOS registers it.</li>
 * <li>{@link #value}: the listener's value as OPPO's sensor would send it: a tilt from another maker's tilt
 * detector is a lift (as the AOD lift patch takes it, scripts/patch-coloros-aod-tilt-wake.py).</li>
 * </ul>
 * Never throws.
 */
public final class OneOSLift extends TriggerEventListener {
    private static final String TAG = "OneOSLift";
    private static final int TYPE_TILT_DETECTOR = 22;
    private static final int TYPE_PICK_UP_GESTURE = 25;

    private static OneOSLift sArmed;

    private final SensorManager mManager;
    private final SensorEventListener mTarget;
    private final Sensor mPickUp;

    private OneOSLift(SensorManager manager, SensorEventListener target, Sensor pickUp) {
        mManager = manager;
        mTarget = target;
        mPickUp = pickUp;
    }

    /** In place of {@code manager.registerListener(listener, tilt, rate)}. */
    public static boolean register(SensorManager manager, SensorEventListener listener, Sensor tilt, int rate) {
        try {
            if (manager != null && listener != null && tilt != null && !isOplus(tilt) && event(0f, 0L, tilt) != null) {
                Sensor pickUp = manager.getDefaultSensor(TYPE_PICK_UP_GESTURE, true);
                if (pickUp == null) {
                    pickUp = manager.getDefaultSensor(TYPE_PICK_UP_GESTURE);
                }
                if (pickUp != null && pickUp.getReportingMode() == Sensor.REPORTING_MODE_ONE_SHOT) {
                    disarm();
                    OneOSLift lift = new OneOSLift(manager, listener, pickUp);
                    if (manager.requestTriggerSensor(lift, pickUp)) {
                        sArmed = lift;
                        Log.d(TAG, "raise to wake: " + pickUp.getName() + " in place of " + tilt.getName());
                        return true;
                    }
                }
            }
        } catch (Throwable e) {
            Log.w(TAG, "raise to wake: pick-up sensor not armed: " + e);
        }
        return manager.registerListener(listener, tilt, rate);
    }

    /** In place of {@code manager.unregisterListener(listener)}. */
    public static void unregister(SensorManager manager, SensorEventListener listener) {
        try {
            OneOSLift lift = sArmed;
            if (lift != null && lift.mTarget == listener) {
                disarm();
            }
        } catch (Throwable e) {
            // The tilt listener below goes either way.
        }
        manager.unregisterListener(listener);
    }

    /** The value the service compares with OPPO's lift (0): 0 for another maker's tilt event. */
    public static float value(SensorEvent event) {
        float v = event.values[0];
        try {
            Sensor s = event.sensor;
            if (v == 1f && s != null && s.getType() == TYPE_TILT_DETECTOR && !isOplus(s)) {
                return 0f;
            }
        } catch (Throwable e) {
            // OPPO's own value.
        }
        return v;
    }

    @Override
    public void onTrigger(TriggerEvent trigger) {
        try {
            if (sArmed != this) {
                return;
            }
            SensorEvent lift = event(0f, trigger == null ? 0L : trigger.timestamp, mPickUp);
            if (lift != null) {
                Log.d(TAG, "raise to wake: picked up");
                mTarget.onSensorChanged(lift);
            }
            // One-shot: armed again for the next lift while the screen stays off.
            if (sArmed == this && !mManager.requestTriggerSensor(this, mPickUp)) {
                sArmed = null;
            }
        } catch (Throwable e) {
            Log.w(TAG, "raise to wake: " + e);
        }
    }

    private static void disarm() {
        OneOSLift lift = sArmed;
        sArmed = null;
        if (lift != null) {
            try {
                lift.mManager.cancelTriggerSensor(lift, lift.mPickUp);
            } catch (Throwable e) {
                // Already gone.
            }
        }
    }

    /** A sensor event with one value, or null where the framework does not let this app make one. */
    private static SensorEvent event(float value, long timestamp, Sensor sensor) {
        try {
            Constructor<SensorEvent> c = SensorEvent.class.getDeclaredConstructor(int.class);
            c.setAccessible(true);
            SensorEvent e = c.newInstance(1);
            e.values[0] = value;
            e.timestamp = timestamp;
            e.sensor = sensor;
            e.accuracy = SensorManager.SENSOR_STATUS_ACCURACY_HIGH;
            return e;
        } catch (Throwable e) {
            return null;
        }
    }

    private static boolean isOplus(Sensor s) {
        String v = s.getVendor();
        if (v == null) {
            return false;
        }
        String l = v.toLowerCase(Locale.ROOT);
        return l.contains("oplus") || l.contains("oppo") || l.contains("oneplus");
    }
}
