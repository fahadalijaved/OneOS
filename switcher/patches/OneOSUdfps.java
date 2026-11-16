package com.android.server.biometrics.sensors.fingerprint.aidl;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;

/**
 * OneOS (0.5.18): the in-display fingerprint sensor's place for a guest on a Galaxy. Samsung's fingerprint HAL gives the
 * guest no sensor location (One UI places it its own way), so Nothing OS's SystemUI had the sensor at 0,0 with no size,
 * never drew it and never told the HAL a finger was down: touches were acquired and none matched (owner's A36).
 * guest_prepare.sh writes /data/system/oneos_udfps ("x y radius", pixels of the natural display) from the phone's
 * /sys/class/fingerprint/fingerprint/position; FingerprintProvider.getWorkaroundSensorProps asks here first
 * (patches/guest_udfps_location.py). No file, or anything unexpected in it: null, and the image's own answer stands.
 * Reflection: SensorLocationInternal is not in the public SDK this compiles against.
 */
public final class OneOSUdfps {
    private OneOSUdfps() {}

    public static List<Object> props() {
        try {
            File f = new File("/data/system/oneos_udfps");
            if (!f.isFile() || f.length() > 64) return null;
            String line;
            try (BufferedReader r = new BufferedReader(new FileReader(f))) { line = r.readLine(); }
            if (line == null) return null;
            String[] p = line.trim().split(" +");
            if (p.length != 3) return null;
            int x = Integer.parseInt(p[0]), y = Integer.parseInt(p[1]), radius = Integer.parseInt(p[2]);
            if (x <= 0 || y <= 0 || radius <= 0 || x > 10000 || y > 10000 || radius > 1000) return null;
            Object loc = Class.forName("android.hardware.biometrics.SensorLocationInternal")
                    .getConstructor(String.class, int.class, int.class, int.class).newInstance("", x, y, radius);
            List<Object> l = new ArrayList<>();
            l.add(loc);
            return l;
        } catch (Throwable t) {
            return null;
        }
    }
}
