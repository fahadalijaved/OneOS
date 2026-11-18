package android.app;

import android.content.Context;
import android.content.DialogInterface;
import android.os.Handler;
import android.os.Looper;
import java.util.function.Consumer;

/** Models a reentrant show and lets the fixture deliver an already captured listener. */
public final class AlertDialog implements DialogInterface {
    private static AlertDialog lastShown;
    private static Consumer<AlertDialog> createHook;
    private static Consumer<AlertDialog> showHook;

    private final CharSequence title;
    private final CharSequence message;
    private final CharSequence positiveLabel;
    private final CharSequence negativeLabel;
    private final OnClickListener positive;
    private final OnClickListener negative;
    private OnDismissListener dismissListener;
    private boolean showing;

    private AlertDialog(Builder builder) {
        title = builder.title;
        message = builder.message;
        positiveLabel = builder.positiveLabel;
        negativeLabel = builder.negativeLabel;
        positive = builder.positive;
        negative = builder.negative;
    }

    public static void setCreateHookForTest(Consumer<AlertDialog> hook) { createHook = hook; }
    public static void setShowHookForTest(Consumer<AlertDialog> hook) { showHook = hook; }
    public static AlertDialog lastShownForTest() { return lastShown; }
    public CharSequence getTitleForTest() { return title; }
    public CharSequence getMessageForTest() { return message; }
    public CharSequence getPositiveLabelForTest() { return positiveLabel; }
    public CharSequence getNegativeLabelForTest() { return negativeLabel; }

    public void show() {
        showing = true;
        lastShown = this;
        Consumer<AlertDialog> hook = showHook;
        showHook = null;
        if (hook != null) hook.accept(this);
    }

    public boolean isShowing() { return showing; }
    public void setOnDismissListener(OnDismissListener listener) { dismissListener = listener; }

    @Override public void dismiss() {
        if (!showing) return;
        showing = false;
        OnDismissListener listener = dismissListener;
        if (listener != null) {
            new Handler(Looper.getMainLooper()).post(() -> listener.onDismiss(this));
        }
    }

    /** Dispatches the listener even after dismissal to model a previously queued click. */
    public void clickForTest(int which) {
        OnClickListener listener;
        if (which == BUTTON_POSITIVE) listener = positive;
        else if (which == BUTTON_NEGATIVE) listener = negative;
        else throw new IllegalArgumentException("Unexpected dialog button");
        try {
            if (listener != null) listener.onClick(this, which);
        } finally {
            dismiss();
        }
    }

    public static final class Builder {
        private CharSequence title;
        private CharSequence message;
        private CharSequence positiveLabel;
        private CharSequence negativeLabel;
        private OnClickListener positive;
        private OnClickListener negative;

        public Builder(Context context) {}
        public Builder setTitle(CharSequence value) { title = value; return this; }
        public Builder setMessage(CharSequence value) { message = value; return this; }
        public Builder setPositiveButton(CharSequence label, OnClickListener listener) {
            positiveLabel = label;
            positive = listener;
            return this;
        }
        public Builder setNegativeButton(CharSequence label, OnClickListener listener) {
            negativeLabel = label;
            negative = listener;
            return this;
        }

        public AlertDialog create() {
            AlertDialog dialog = new AlertDialog(this);
            Consumer<AlertDialog> hook = createHook;
            createHook = null;
            if (hook != null) hook.accept(dialog);
            return dialog;
        }
        public AlertDialog show() {
            AlertDialog dialog = create();
            dialog.show();
            return dialog;
        }
    }
}
