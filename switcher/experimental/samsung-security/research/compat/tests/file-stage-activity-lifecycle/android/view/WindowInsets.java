package android.view;

import android.graphics.Insets;

/** A zero-inset fixture. It does not model window layout. */
public final class WindowInsets {
    public Insets getInsets(int typeMask) {
        return Insets.NONE;
    }

    public static final class Type {
        private Type() {}

        public static int systemBars() { return 1 | 2 | 4 | 256; }
        public static int displayCutout() { return 128; }
    }
}
