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
        if (args.length != 2 || Process.myUid() != 0) throw new IllegalArgumentException("root and a status directory required");
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
        long deadline = android.os.SystemClock.elapsedRealtime() + 600_000;
        try {
            while (generation.equals(read(dir, "generation", "")) && !new File(dir, "stop").exists() && android.os.SystemClock.elapsedRealtime() < deadline) {
                int[] current = dimensions();
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
                    if (verbose) {
                        paint.setTypeface(Typeface.create("sec", Typeface.NORMAL));
                        paint.setTextSize(24 * unit);
                        String status = read(dir, "status", "Waiting for boot events");
                        if (status.length() > 120) status = status.substring(0, 117) + "…";
                        fit(paint, status, size[0] - 40*unit);
                        canvas.drawText(status, size[0]/2f, top + 320*unit, paint);
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
            Class<?> sc = Class.forName("android.view.SurfaceControl");
            long[] ids = (long[])sc.getMethod("getPhysicalDisplayIds").invoke(null);
            Object info = sc.getMethod("getDynamicDisplayInfo", long.class).invoke(null, ids[0]);
            int active = info.getClass().getField("activeDisplayModeId").getInt(info);
            Object[] modes = (Object[])info.getClass().getField("supportedDisplayModes").get(info);
            for (Object mode : modes) if (mode.getClass().getField("id").getInt(mode) == active)
                return new int[]{mode.getClass().getField("width").getInt(mode), mode.getClass().getField("height").getInt(mode)};
            throw unavailable;
        }
    }
}
