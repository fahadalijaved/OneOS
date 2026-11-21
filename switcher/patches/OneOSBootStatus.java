import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.os.Process;
import android.view.Surface;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;

/** Root-only, framework-independent handoff layer. No ActivityManager or app permissions. */
public final class OneOSBootStatus {
    private static Object call(Object o, String name, Class<?>[] types, Object... args) throws Exception {
        return o.getClass().getMethod(name, types).invoke(o, args);
    }
    private static String read(File dir, String name, String fallback) {
        try { return new String(Files.readAllBytes(new File(dir, name).toPath()), "UTF-8").trim(); }
        catch (Exception e) { return fallback; }
    }
    public static void main(String[] args) {
        try { run(args); } catch (Throwable failure) { failure.printStackTrace(System.err); }
    }
    private static void run(String[] args) throws Exception {
        if (args.length < 2 || args.length > 3 || Process.myUid() != 0) throw new IllegalArgumentException("root and a status directory required");
        long started = android.os.SystemClock.elapsedRealtime();
        boolean published = false;
        File dir = new File(args[0]);
        String generation = args[1];
        if (!generation.equals(read(dir, "generation", ""))) { System.err.println("Retired handoff generation " + generation); return; }
        System.err.println("Starting OneOS handoff " + generation + " in " + dir);
        Class<?> sc = Class.forName("android.view.SurfaceControl");
        Object builder = Class.forName("android.view.SurfaceControl$Builder").getConstructor().newInstance();
        call(builder, "setName", new Class<?>[]{String.class}, "OneOS handoff status");
        call(builder, "setBLASTLayer", new Class<?>[]{});
        Object layer = call(builder, "build", new Class<?>[]{});
        System.err.println("Handoff layer created");
        Object transaction = Class.forName("android.view.SurfaceControl$Transaction").getConstructor().newInstance();
        call(transaction, "setLayer", new Class<?>[]{sc, int.class}, layer, 2_000_000_000);
        call(transaction, "setLayerStack", new Class<?>[]{sc, int.class}, layer, 0);
        call(transaction, "show", new Class<?>[]{sc}, layer);
        call(transaction, "apply", new Class<?>[]{});
        System.err.println("Handoff transaction applied");
        int[] size = dimensions();
        System.err.println("Handoff size " + size[0] + "x" + size[1]);
        Class<?> blast = Class.forName("android.graphics.BLASTBufferQueue");
        Object queue;
        try {
            queue = blast.getConstructor(String.class, sc, int.class, int.class, int.class)
                .newInstance("OneOS handoff buffers", layer, size[0], size[1], 1);
        } catch (NoSuchMethodException changed) {
            queue = blast.getConstructor(String.class, boolean.class).newInstance("OneOS handoff buffers", false);
            call(queue, "update", new Class<?>[]{sc, int.class, int.class, int.class}, layer, size[0], size[1], 1);
        }
        System.err.println("Handoff queue created");
        Surface surface = (Surface) call(queue, "createSurface", new Class<?>[]{});
        Bitmap icon = BitmapFactory.decodeFile(new File(dir, "icon.png").getPath());
        if (icon == null) throw new IllegalStateException("OneOS icon missing");
        Typeface.class.getMethod("loadPreinstalledSystemFontMap").invoke(null);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        // The third argument (iOS 27, boot_status.sh "ios"): this layer's upper bound in seconds.
        long bound = 600;
        if (args.length == 3) try { bound = Math.max(10, Math.min(7200, Long.parseLong(args[2]))); } catch (NumberFormatException plain) { }
        long deadline = android.os.SystemClock.elapsedRealtime() + bound * 1000;
        try {
            while (generation.equals(read(dir, "generation", "")) && !new File(dir, "stop").exists() && android.os.SystemClock.elapsedRealtime() < deadline) {
                // iOS 27: OneiOS's display helper sets the display's projection to the panel's active mode when it
                // connects (the switch then leaves a "native" file here). The layer space is that mode's pixels
                // from then on, not the logical size One UI's display manager last gave.
                int[] current = null;
                if (new File(dir, "native").exists()) try { current = mode(); } catch (Exception unreadable) { }
                if (current == null) current = dimensions();
                if (current[0] != size[0] || current[1] != size[1]) {
                    size = current;
                    call(queue, "update", new Class<?>[]{sc, int.class, int.class, int.class}, layer, size[0], size[1], 1);
                }
                Canvas canvas = surface.lockCanvas(null);
                try {
                    canvas.drawColor(Color.rgb(1, 1, 2));
                    boolean wide = size[0] > size[1];
                    float unit = Math.min(size[0] / (wide ? 1230f : 412f), size[1] / 928f);
                    boolean verbose = read(dir, "verbose", "0").equals("1");
                    float group = (verbose ? 327 : 274) * unit;
                    float top = (size[1] - group) / 2f;
                    float edge = 180 * unit;
                    canvas.drawBitmap(icon, null, new RectF((size[0]-edge)/2, top, (size[0]+edge)/2, top+edge), paint);
                    paint.setColor(Color.WHITE);
                    paint.setTextAlign(Paint.Align.CENTER);
                    paint.setTypeface(Typeface.create("sec", Typeface.BOLD));
                    paint.setTextSize(36 * unit);
                    String title = read(dir, "title", "Returning to One UI");
                    fit(paint, title, size[0] - 40 * unit);
                    canvas.drawText(title, size[0]/2f, top + 267*unit, paint);
                    // A hint (iOS 27: the way back to One UI) is drawn near the bottom edge, and the
                    // status above it may then be a sentence: both wrap instead of shrinking.
                    String hint = read(dir, "hint", "");
                    if (verbose) {
                        paint.setTypeface(Typeface.create("sec", Typeface.NORMAL));
                        paint.setTextSize(24 * unit);
                        String status = read(dir, "status", "Waiting for boot events");
                        if (hint.isEmpty()) {
                            if (status.length() > 120) status = status.substring(0, 117) + "…";
                            fit(paint, status, size[0] - 40*unit);
                            canvas.drawText(status, size[0]/2f, top + 320*unit, paint);
                        } else {
                            if (status.length() > 240) status = status.substring(0, 237) + "…";
                            paint.setTextSize(22 * unit);
                            float y = top + 320*unit;
                            for (String line : wrap(paint, status, size[0] - 48*unit, 4)) { line(canvas, paint, line, size[0], y, unit); y += 30*unit; }
                        }
                    }
                    if (!hint.isEmpty()) {
                        if (hint.length() > 160) hint = hint.substring(0, 157) + "…";
                        paint.setTypeface(Typeface.create("sec", Typeface.NORMAL));
                        paint.setTextSize(18 * unit);
                        paint.setColor(Color.rgb(170, 170, 178));
                        java.util.List<String> lines = wrap(paint, hint, size[0] - 48*unit, 3);
                        float y = size[1] - 56*unit - (lines.size() - 1) * 26*unit;
                        for (String line : lines) { line(canvas, paint, line, size[0], y, unit); y += 26*unit; }
                    }
                } finally { surface.unlockCanvasAndPost(canvas); }
                // Readiness is published only after posting a real frame.
                if (!generation.equals(read(dir, "generation", ""))) break;
                File ready = new File(dir, "ready." + Process.myPid());
                try (FileWriter out = new FileWriter(ready)) { out.write(Process.myPid() + " " + generation + "\n"); }
                if (!ready.renameTo(new File(dir, "ready"))) throw new IllegalStateException("Cannot publish live frame readiness");
                if (!published) {
                    System.err.println("First frame posted after " + (android.os.SystemClock.elapsedRealtime() - started) + " ms; pid " + Process.myPid());
                    published = true;
                }
                Thread.sleep(150);
            }
        } finally {
            try { call(transaction, "remove", new Class<?>[]{sc}, layer); call(transaction, "apply", new Class<?>[]{}); } catch (Exception ignored) { }
            surface.release();
            try { call(queue, "destroy", new Class<?>[]{}); } catch (Exception ignored) { }
            if (read(dir, "ready", "").equals(Process.myPid() + " " + generation)) new File(dir, "ready").delete();
        }
    }
    /** One centred line; a single word wider than the screen is shrunk for this line only. */
    private static void line(Canvas canvas, Paint p, String s, int width, float y, float unit) {
        float size = p.getTextSize();
        fit(p, s, width - 40*unit);
        canvas.drawText(s, width/2f, y, p);
        p.setTextSize(size);
    }
    /** Whole words to lines of at most width; what does not fit in max lines ends in an ellipsis. */
    private static java.util.List<String> wrap(Paint p, String s, float width, int max) {
        java.util.ArrayList<String> out = new java.util.ArrayList<>();
        String line = "";
        for (String word : s.split(" ")) {
            if (word.isEmpty()) continue;
            String next = line.isEmpty() ? word : line + " " + word;
            if (!line.isEmpty() && p.measureText(next) > width) { out.add(line); line = word; }
            else line = next;
        }
        if (!line.isEmpty()) out.add(line);
        if (out.size() > max) {
            String last = out.get(max - 1) + "…";
            while (out.size() >= max) out.remove(out.size() - 1);
            out.add(last);
        }
        return out;
    }
    private static void fit(Paint p, String s, float width) {
        float measured = p.measureText(s);
        if (measured > width) p.setTextSize(p.getTextSize() * width / measured);
    }
    private static int[] dimensions() throws Exception {
        try {
            Class<?> dm = Class.forName("android.hardware.display.DisplayManagerGlobal");
            Object instance = dm.getMethod("getInstance").invoke(null);
            Object info = dm.getMethod("getDisplayInfo", int.class).invoke(instance, 0);
            return new int[]{info.getClass().getField("logicalWidth").getInt(info), info.getClass().getField("logicalHeight").getInt(info)};
        } catch (Exception unavailable) {
            int[] mode = mode();
            if (mode == null) throw unavailable;
            return mode;
        }
    }
    /** The first physical display's active mode, or null when it names none. */
    private static int[] mode() throws Exception {
        Class<?> sc = Class.forName("android.view.SurfaceControl");
        long[] ids = (long[])sc.getMethod("getPhysicalDisplayIds").invoke(null);
        Object info = sc.getMethod("getDynamicDisplayInfo", long.class).invoke(null, ids[0]);
        int active = info.getClass().getField("activeDisplayModeId").getInt(info);
        Object[] modes = (Object[])info.getClass().getField("supportedDisplayModes").get(info);
        for (Object mode : modes) if (mode.getClass().getField("id").getInt(mode) == active)
            return new int[]{mode.getClass().getField("width").getInt(mode), mode.getClass().getField("height").getInt(mode)};
        return null;
    }
}
