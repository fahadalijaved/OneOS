package com.fahadali.oneos.viewprep;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Insets;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import com.fahadali.oneos.core.root.RetainedRootHostServiceV2;
import com.fahadali.oneos.core.root.RetainedRootHostServiceV2.ViewAttempt;
import com.fahadali.oneos.core.root.RetainedViewAppProtocol;
import java.lang.ref.WeakReference;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/** Single-process preparation view over the existing private broker. */
public final class PrepareActivity extends Activity
        implements View.OnClickListener, DialogInterface.OnClickListener {
    private static Operation current;
    private static WeakReference<PrepareActivity> visible = new WeakReference<>(null);

    private TextView status;
    private Button prepare, stop, refresh;
    private AlertDialog confirmation;
    private boolean confirmingPrepare;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        final int margin = Math.round(20 * getResources().getDisplayMetrics().density);
        content.setPadding(margin, margin, margin, margin);
        content.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override public WindowInsets onApplyWindowInsets(View view, WindowInsets insets) {
                Insets edges = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                view.setPadding(margin + edges.left, margin + edges.top, margin + edges.right, margin + edges.bottom);
                return insets;
            }
        });
        TextView title = new TextView(this);
        title.setText("OneOS View Prep");
        title.setTextSize(24);
        title.setAccessibilityHeading(true);
        content.addView(title);
        status = new TextView(this);
        status.setTextSize(16);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        content.addView(status);
        prepare = button(content, "Prepare");
        stop = button(content, "Stop");
        refresh = button(content, "Refresh status");
        scroll.addView(content);
        setContentView(scroll);
    }

    private Button button(LinearLayout parent, String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(this);
        parent.addView(button);
        return button;
    }

    @Override protected void onStart() {
        super.onStart();
        visible = new WeakReference<>(this);
        render();
    }

    @Override protected void onStop() {
        if (visible.get() == this) visible.clear();
        if (confirmation != null) {
            confirmation.dismiss();
            confirmation = null;
        }
        super.onStop();
    }

    @Override public void onClick(View view) {
        if (visible.get() != this) return;
        if (view == refresh) {
            if (current != null) current.refresh();
            return;
        }
        boolean start = view == prepare && current == null;
        boolean end = view == stop && current != null && current.canStop();
        if ((!start && !end) || (confirmation != null && confirmation.isShowing())) return;
        confirmingPrepare = start;
        confirmation = new AlertDialog.Builder(this)
                .setTitle(start ? "Prepare a private view?" : "Stop preparation?")
                .setMessage(start ? "Ask the host to prepare the separate tester stage. This action prepares a view only."
                        : "Request that the host close this preparation. You can check cleanup status here.")
                .setPositiveButton(start ? "Prepare" : "Stop", this)
                .setNegativeButton(start ? "Cancel" : "Keep going", null)
                .show();
    }

    @Override public void onClick(DialogInterface dialog, int which) {
        if (dialog != confirmation || which != DialogInterface.BUTTON_POSITIVE || visible.get() != this) return;
        confirmation = null;
        if (confirmingPrepare && current == null) {
            current = new Operation(getApplicationContext());
            current.bind();
        } else if (!confirmingPrepare && current != null) {
            current.stop();
        }
        render();
    }

    private void render() {
        Operation operation = current;
        prepare.setVisibility(operation == null ? View.VISIBLE : View.GONE);
        stop.setVisibility(operation == null ? View.GONE : View.VISIBLE);
        refresh.setVisibility(operation == null ? View.GONE : View.VISIBLE);
        stop.setEnabled(operation != null && operation.canStop());
        refresh.setEnabled(operation != null && operation.canRefresh());
        status.setText(operation == null ? "Prepare a private view of the tester stage." : operation.message());
    }

    private static void changed() {
        PrepareActivity screen = visible.get();
        if (screen != null) screen.render();
    }

    /** Main owns registration and display. A serial worker owns the one claimed attempt. */
    private static final class Operation implements ServiceConnection {
        private static final int OPEN = 0, COMMITTED = 1, CANCELLED = 2;
        private static final long BIND_WAIT_MILLIS = 10_000;

        private final Context app;
        private final ComponentName component;
        private final Handler main = new Handler(Looper.getMainLooper());
        private final Executor worker = Executors.newSingleThreadExecutor();
        private final AtomicInteger dispatch = new AtomicInteger(OPEN);
        private final Runnable bindTimeout = new Runnable() {
            @Override public void run() { if (!brokerDispatched) finishBeforeDispatch(); }
        };

        private IBinder pendingBroker;
        private boolean bindInFlight, bindAccepted, releaseWanted, unbindAttempted;
        private boolean brokerDispatched, finishedBeforeDispatch, connectionLost, unbindUnconfirmed;
        private boolean prepareReturned, stopRequested, refreshing, unavailableSample;
        private Integer prepareReply, stopReply;
        private int observed = RetainedViewAppProtocol.STATUS_PENDING;
        private int preparationResult = RetainedViewAppProtocol.STATUS_PENDING;
        private ViewAttempt attempt; // Serial worker only.

        Operation(Context app) {
            this.app = app;
            component = new ComponentName(app, RetainedRootHostServiceV2.class);
        }

        void bind() {
            bindInFlight = true;
            try {
                bindAccepted = app.bindService(new Intent().setComponent(component), this, Context.BIND_AUTO_CREATE);
            } catch (RuntimeException refused) {
                // The exact registration still gets its one release attempt below.
            } finally {
                bindInFlight = false;
            }
            if (releaseWanted) releaseBinding();
            else if (!bindAccepted) finishBeforeDispatch();
            else {
                dispatchBroker();
                if (!brokerDispatched && !releaseWanted) main.postDelayed(bindTimeout, BIND_WAIT_MILLIS);
            }
        }

        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            if (!component.equals(name) || binder == null || releaseWanted || brokerDispatched || pendingBroker != null) return;
            pendingBroker = binder;
            dispatchBroker();
        }

        @Override public void onServiceDisconnected(ComponentName name) { connectionLost(name); }
        @Override public void onBindingDied(ComponentName name) { connectionLost(name); }
        @Override public void onNullBinding(ComponentName name) { connectionLost(name); }

        private void connectionLost(ComponentName name) {
            if (!component.equals(name) || releaseWanted) return;
            connectionLost = true;
            dispatch.compareAndSet(OPEN, CANCELLED);
            if (!brokerDispatched) finishBeforeDispatch();
            else changed();
        }

        private void dispatchBroker() {
            final IBinder binder = pendingBroker;
            if (binder == null || bindInFlight || !bindAccepted || releaseWanted) return;
            pendingBroker = null;
            brokerDispatched = true;
            main.removeCallbacks(bindTimeout);
            try {
                worker.execute(new Runnable() {
                    @Override public void run() { prepareOnWorker(binder); }
                });
            } catch (RuntimeException refused) {
                if (dispatch.compareAndSet(OPEN, CANCELLED)) finishBeforeDispatch();
            }
        }

        private void prepareOnWorker(IBinder binder) {
            if (dispatch.get() == OPEN) {
                try { attempt = RetainedRootHostServiceV2.claimView(binder); }
                catch (RuntimeException refused) { attempt = null; }
            }
            if (attempt == null || !dispatch.compareAndSet(OPEN, COMMITTED)) {
                main.post(new Runnable() {
                    @Override public void run() { finishBeforeDispatch(); }
                });
                return;
            }
            final int reply = mutation(attempt, false);
            main.post(new Runnable() {
                @Override public void run() {
                    prepareReply = reply;
                    prepareReturned = true;
                    if (!stopRequested) refresh();
                    changed();
                }
            });
        }

        boolean canStop() {
            return !terminal() && !stopRequested && (observed == RetainedViewAppProtocol.STATUS_PENDING
                    || observed == RetainedViewAppProtocol.STATUS_PARTIAL);
        }

        void stop() {
            if (!canStop()) return;
            stopRequested = true;
            dispatch.compareAndSet(OPEN, CANCELLED);
            if (!brokerDispatched) finishBeforeDispatch();
            else if (dispatch.get() == COMMITTED) {
                try {
                    worker.execute(new Runnable() {
                        @Override public void run() {
                            final int reply = mutation(attempt, true);
                            main.post(new Runnable() {
                                @Override public void run() { stopReply = reply; refresh(); changed(); }
                            });
                        }
                    });
                } catch (RuntimeException refused) {
                    stopReply = RetainedViewAppProtocol.UNCERTAIN;
                }
            }
            changed();
        }

        boolean canRefresh() { return prepareReturned && !terminal() && !refreshing; }

        void refresh() {
            if (!canRefresh()) return;
            refreshing = true;
            try {
                worker.execute(new Runnable() {
                    @Override public void run() {
                        final int sample = readStatus(attempt);
                        main.post(new Runnable() {
                            @Override public void run() { refreshing = false; observe(sample); }
                        });
                    }
                });
            } catch (RuntimeException refused) {
                refreshing = false;
                observe(RetainedViewAppProtocol.STATUS_UNAVAILABLE);
            }
            changed();
        }

        private static int mutation(ViewAttempt actual, boolean stop) {
            try {
                int value = stop ? actual.stop() : actual.prepare();
                if (RetainedViewAppProtocol.isMutationReply(value)) return value;
            } catch (RuntimeException uncertain) { }
            return RetainedViewAppProtocol.UNCERTAIN;
        }

        private static int readStatus(ViewAttempt actual) {
            try {
                int value = actual.status();
                if (RetainedViewAppProtocol.isStatus(value)) return value;
            } catch (RuntimeException unavailable) { }
            return RetainedViewAppProtocol.STATUS_UNAVAILABLE;
        }

        private void observe(int sample) {
            if (terminal()) return;
            unavailableSample = sample == RetainedViewAppProtocol.STATUS_UNAVAILABLE;
            if (!unavailableSample && sample != RetainedViewAppProtocol.STATUS_PENDING) {
                if (sample <= RetainedViewAppProtocol.STATUS_REFUSED) preparationResult = sample;
                if (observed < RetainedViewAppProtocol.STATUS_CLOSING
                        || sample >= RetainedViewAppProtocol.STATUS_CLOSING) observed = sample;
            }
            if (terminal()) releaseBinding();
            changed();
        }

        private boolean terminal() {
            return finishedBeforeDispatch || observed == RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED
                    || observed == RetainedViewAppProtocol.STATUS_STOPPED_BEFORE_DISPATCH;
        }

        private void finishBeforeDispatch() {
            if (terminal() || (!dispatch.compareAndSet(OPEN, CANCELLED) && dispatch.get() == COMMITTED)) return;
            finishedBeforeDispatch = true;
            releaseBinding();
            changed();
        }

        private void releaseBinding() {
            releaseWanted = true;
            pendingBroker = null;
            main.removeCallbacks(bindTimeout);
            if (bindInFlight || unbindAttempted) return;
            unbindAttempted = true;
            try { app.unbindService(this); }
            catch (RuntimeException uncertain) { unbindUnconfirmed = true; }
        }

        String message() {
            if (finishedBeforeDispatch) {
                String result = stopRequested ? "Stopped before dispatch." : "Preparation unavailable before dispatch.";
                return unbindUnconfirmed ? result + "\nService registration cleanup is unconfirmed." : result;
            }
            StringBuilder text = new StringBuilder(label(observed));
            if (preparationResult != RetainedViewAppProtocol.STATUS_PENDING && preparationResult != observed) {
                text.append('\n').append(label(preparationResult));
            }
            if (prepareReply != null) text.append('\n').append(replyText(prepareReply, false));
            if (stopReply != null) text.append('\n').append(replyText(stopReply, true));
            else if (stopRequested) text.append("\nStop requested. Waiting for the same attempt.");
            if (unavailableSample) text.append("\nLatest status sample unavailable.");
            if (connectionLost) text.append("\nService connection lost.");
            if (unbindUnconfirmed) text.append("\nService registration cleanup is unconfirmed.");
            return text.toString();
        }

        private static String replyText(int value, boolean stop) {
            String action = stop ? "Stop" : "Prepare";
            if (value == RetainedViewAppProtocol.QUEUED) return action + " request acknowledged.";
            if (value == RetainedViewAppProtocol.UNAVAILABLE) return action + " request unavailable.";
            return action + " acknowledgment unconfirmed.";
        }

        private static String label(int value) {
            switch (value) {
                case RetainedViewAppProtocol.STATUS_PARTIAL: return "Partial filesystem view observed.";
                case RetainedViewAppProtocol.STATUS_NEED_STAGE: return "Tester stage preparation is required.";
                case RetainedViewAppProtocol.STATUS_REFUSED: return "Preparation refused.";
                case RetainedViewAppProtocol.STATUS_CLOSING: return "Cleanup in progress.";
                case RetainedViewAppProtocol.STATUS_CLEANUP_UNCONFIRMED: return "Cleanup unconfirmed.";
                case RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL: return "Local terminal observed. Cleanup still pending.";
                case RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED: return "Local cleanup observed.";
                case RetainedViewAppProtocol.STATUS_STOPPED_BEFORE_DISPATCH: return "Stopped before dispatch.";
                default: return "Waiting for preparation status.";
            }
        }
    }
}
