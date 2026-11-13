package android.view;

import android.content.Context;

/** JVM fixture for the Activity's observable view state and listener. */
public class View {
    public static final int VISIBLE = 0;
    public static final int GONE = 8;
    public static final int ACCESSIBILITY_LIVE_REGION_POLITE = 1;

    private boolean enabled = true;
    private int visibility = VISIBLE;
    private OnClickListener clickListener;

    public View(Context context) {}

    public interface OnClickListener {
        void onClick(View view);
    }

    public interface OnApplyWindowInsetsListener {
        WindowInsets onApplyWindowInsets(View view, WindowInsets insets);
    }

    public void setOnClickListener(OnClickListener listener) {
        clickListener = listener;
    }

    public boolean performClick() {
        if (clickListener == null) return false;
        clickListener.onClick(this);
        return true;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setVisibility(int visibility) {
        this.visibility = visibility;
    }

    public int getVisibility() {
        return visibility;
    }

    // Layout and accessibility rendering are outside the fixture.
    public void setPadding(int left, int top, int right, int bottom) {}
    public void setOnApplyWindowInsetsListener(OnApplyWindowInsetsListener listener) {}
    public void setAccessibilityHeading(boolean heading) {}
    public void setAccessibilityLiveRegion(int mode) {}
}
