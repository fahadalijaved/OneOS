package com.oneos.glyph;

import android.app.KeyguardManager;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.View;

/**
 * The Infinity-X keyguard fingerprint glyph (vdcoolok, pull request #152: Infinity-X's SystemUI builds its UDFPS
 * overlay with a null animation controller, so the lock screen shows nothing over the sensor while the sensor still
 * unlocks). A white ring in the shade window, shown while the keyguard reports locked.
 *
 * OneOS: the ring's place comes from ro.oneos.fp_glyph ("cx cy r", ten-thousandths of the view's width, height and
 * width), which guest_props.sh writes from this phone's own sensor position; his build drew it at 50 % / 78 % with a
 * 98 px radius, the Galaxy S25 Ultra's. Without the property the ring stays hidden.
 */
public class OneOSGlyphView extends View {
    public static final int ID = 0x0e05ee01;

    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float fx, fy, fr;
    private boolean placed;

    public OneOSGlyphView(Context context) {
        super(context);
        setId(ID);
        setWillNotDraw(false);
        setClickable(false);
        setFocusable(false);
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setColor(Color.argb(200, 255, 255, 255));
        try {
            String v = (String) Class.forName("android.os.SystemProperties")
                    .getMethod("get", String.class, String.class).invoke(null, "ro.oneos.fp_glyph", "");
            String[] p = v.trim().split("\\s+");
            if (p.length == 3) {
                fx = Integer.parseInt(p[0]) / 10000f;
                fy = Integer.parseInt(p[1]) / 10000f;
                fr = Integer.parseInt(p[2]) / 10000f;
                placed = fx > 0 && fx < 1 && fy > 0 && fy < 1 && fr > 0 && fr < 0.5f;
            }
        } catch (Throwable ignored) {
            placed = false;
        }
        setVisibility(INVISIBLE);
        try {
            KeyguardManager km = context.getSystemService(KeyguardManager.class);
            if (km != null && placed) {
                setVisibility(km.isKeyguardLocked() ? VISIBLE : INVISIBLE);
                km.addKeyguardLockedStateListener(context.getMainExecutor(),
                        new KeyguardManager.KeyguardLockedStateListener() {
                            @Override
                            public void onKeyguardLockedStateChanged(boolean locked) {
                                setVisibility(locked ? VISIBLE : INVISIBLE);
                            }
                        });
            }
        } catch (Throwable ignored) {
            setVisibility(INVISIBLE);
        }
        // Above the shade's own children, as his build kept it.
        getViewTreeObserver().addOnGlobalLayoutListener(new android.view.ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                bringToFront();
            }
        });
    }

    @Override
    protected void onDraw(Canvas canvas) {
        if (!placed) return;
        int w = getWidth(), h = getHeight();
        if (w <= 0 || h <= 0) return;
        float r = fr * w;
        stroke.setStrokeWidth(Math.max(4f, r * 0.12f));
        canvas.drawCircle(fx * w, fy * h, r, stroke);
    }
}
