import android.os.IBinder;
import android.os.Parcel;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.lang.reflect.Method;

/**
 * OneOS (0.5.17): Nothing OS's colour mode and warm/cool slider on a Galaxy (owner, A36: "colours in NothingOS doesnt do
 * anything ... cool/warm also didnt do shit"). Nothing writes them as settings (system display_color_mode: 0 natural,
 * 260 vivid; global current_screen_color_temperature in kelvin) for its own display hardware, which Samsung's ignores.
 * This applies them through SurfaceFlinger, as Android's own colour features do: the saturation (transaction 1022) for
 * the mode, and a colour matrix (1015) for the temperature, both tested on the A36. While Night Light, colour inversion
 * or colour correction is on, the matrix is theirs and is left alone. The mode and temperature are read every
 * 0.5 s (2 s felt slow on the slider), the other three every 5 s; it writes only on a change.
 *
 * Run in the guest's mount namespace: app_process ... OneOSNtColor <guest system_server pid>. Ends with that process.
 */
public final class OneOSNtColor {
    private static final String TOKEN = "android.ui.ISurfaceComposer";
    /** D65, the slider's middle (it runs 4000-8000 K on the A36): no tint there; lower warmer, higher cooler. */
    private static final double NEUTRAL_K = 6500;
    /** Alive (260); Standard (0) stays 1. 1.25 looked too close to Standard on the A36. */
    private static final float VIVID = 1.35f;

    private static IBinder sf;

    public static void main(String[] args) throws Exception {
        int guest = Integer.parseInt(args[0]);
        Method get = Class.forName("android.os.ServiceManager").getMethod("getService", String.class);
        for (int i = 0; sf == null && i < 60 && alive(guest); i++) {
            sf = (IBinder) get.invoke(null, "SurfaceFlinger");
            if (sf == null) Thread.sleep(2000);
        }
        if (sf == null) { log("no SurfaceFlinger; exiting"); return; }
        log("watching Nothing's colour mode and temperature (SurfaceFlinger saturation and matrix), guest " + guest);
        String last = "";
        int changes = 0, round = 0;
        boolean others = false;
        while (alive(guest)) {
            String mode = setting("system", "display_color_mode");
            String kelvin = setting("global", "current_screen_color_temperature");
            if (round++ % 10 == 0) {
                others = "1".equals(setting("secure", "night_display_activated"))
                        || "1".equals(setting("secure", "accessibility_display_inversion_enabled"))
                        || "1".equals(setting("secure", "accessibility_display_daltonizer_enabled"));
            }
            String now = mode + "|" + kelvin + "|" + others;
            if (!now.equals(last)) {
                float sat = "260".equals(mode) ? VIVID : 1f;
                saturation(sat);
                float[] g = others ? null : gains(kelvin);
                if (!others) matrix(g);
                if (changes++ < 30) {
                    log("mode " + mode + " -> saturation " + sat + "; " + (others
                            ? "matrix left to Night Light / inversion / correction"
                            : (g == null ? "temperature " + kelvin + ": no tint" : String.format("temperature %s K: r %.3f g %.3f b %.3f", kelvin, g[0], g[1], g[2]))));
                }
                last = now;
            }
            Thread.sleep(500);
        }
        saturation(1f);
        matrix(null);
        log("guest system_server " + guest + " gone; colour back to plain");
    }

    /** Red, green and blue gains for a white point of [kelvinText] relative to NEUTRAL_K, or null for none. */
    static float[] gains(String kelvinText) {
        double k;
        try { k = Double.parseDouble(kelvinText); } catch (Exception e) { return null; }
        if (k < 1500 || k > 20000) return null;
        double[] a = rgb(k), n = rgb(NEUTRAL_K);
        double r = a[0] / n[0], g = a[1] / n[1], b = a[2] / n[2];
        double m = Math.max(r, Math.max(g, b));
        r /= m; g /= m; b /= m;
        if (Math.abs(1 - r) < 0.01 && Math.abs(1 - g) < 0.01 && Math.abs(1 - b) < 0.01) return null;
        return new float[] {(float) r, (float) g, (float) b};
    }

    /** Black-body colour (Tanner Helland's fit), 0..255 per channel. */
    static double[] rgb(double kelvin) {
        double t = kelvin / 100, r, g, b;
        if (t <= 66) { r = 255; g = 99.4708025861 * Math.log(t) - 161.1195681661; }
        else { r = 329.698727446 * Math.pow(t - 60, -0.1332047592); g = 288.1221695283 * Math.pow(t - 60, -0.0755148492); }
        if (t >= 66) b = 255;
        else if (t <= 19) b = 0;
        else b = 138.5177312231 * Math.log(t - 10) - 305.0447927307;
        return new double[] {clamp(r), clamp(g), clamp(b)};
    }

    static double clamp(double v) { return Math.max(1, Math.min(255, v)); }

    static void saturation(float s) {
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try { d.writeInterfaceToken(TOKEN); d.writeFloat(s); sf.transact(1022, d, r, 0); }
        catch (Throwable t) { log("saturation failed: " + t); }
        finally { d.recycle(); r.recycle(); }
    }

    /** A diagonal colour matrix for gains [g], or the matrix off for null. */
    static void matrix(float[] g) {
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try {
            d.writeInterfaceToken(TOKEN);
            if (g == null) d.writeInt(0);
            else {
                d.writeInt(1);
                float[] m = {g[0], 0, 0, 0, 0, g[1], 0, 0, 0, 0, g[2], 0, 0, 0, 0, 1};
                for (float v : m) d.writeFloat(v);
            }
            sf.transact(1015, d, r, 0);
        } catch (Throwable t) { log("matrix failed: " + t); }
        finally { d.recycle(); r.recycle(); }
    }

    static String setting(String ns, String key) {
        try {
            Process p = Runtime.getRuntime().exec(new String[] {"/system/bin/settings", "get", ns, key});
            String s = new BufferedReader(new InputStreamReader(p.getInputStream())).readLine();
            p.waitFor();
            return s == null ? "" : s.trim();
        } catch (Throwable t) {
            return "";
        }
    }

    private static boolean alive(int pid) { return new File("/proc/" + pid).exists(); }

    private static void log(String s) { System.out.println(s); }
}
