package com.fahadali.oneos.viewprep.filetree;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.TextView;
import com.fahadali.oneos.core.root.RetainedRootHostServiceV2;
import com.fahadali.oneos.core.root.RetainedViewAppProtocol;
import java.lang.reflect.Field;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/** Executes the complete SDK-compiled Activity against authored JVM boundaries. */
public final class ActivityLifecycleFixture {
    private static final String PARTIAL = "Partial filesystem view observed.";
    private static final String LOCAL_TERMINAL = "Local terminal observed. Cleanup still pending.";
    private static final String CLEANUP = "Local cleanup observed.";
    private static final String PREPARE_DIALOG = "Prepare a private view?", STOP_DIALOG = "Stop preparation?";
    private static final App APP = new App();

    private static final class App extends Context {
        int binds, unbinds;
        ServiceConnection connection;

        @Override public boolean bindService(Intent intent, ServiceConnection actual, int flags) {
            check(flags == BIND_AUTO_CREATE && intent.getComponent() != null && connection == null,
                    "expected one explicit modeled service binding");
            binds++;
            connection = actual;
            actual.onServiceConnected(intent.getComponent(), RetainedRootHostServiceV2.BROKER);
            return true;
        }

        @Override public void unbindService(ServiceConnection actual) {
            check(connection != null && actual == connection, "only exact registration is releasable");
            unbinds++;
            connection = null;
        }
    }

    private static void check(boolean condition, String description) {
        if (!condition) throw new AssertionError(description);
    }

    private static TextView widget(PrepareActivity activity, String name) {
        try {
            Field field = PrepareActivity.class.getDeclaredField(name);
            field.setAccessible(true);
            return (TextView) field.get(activity);
        } catch (ReflectiveOperationException failure) {
            throw new AssertionError("missing actual Activity widget " + name, failure);
        }
    }

    private static String text(PrepareActivity activity) { return widget(activity, "status").getText().toString(); }

    private static void tap(PrepareActivity activity, String name) {
        View button = widget(activity, name);
        check(button.getVisibility() == View.VISIBLE && button.isEnabled() && button.performClick(),
                "expected enabled visible " + name + " button");
    }

    private static AlertDialog show(PrepareActivity activity, String name, String title) {
        AlertDialog before = AlertDialog.lastShownForTest();
        tap(activity, name);
        AlertDialog actual = AlertDialog.lastShownForTest();
        check(actual != null && actual != before && title.contentEquals(actual.getTitleForTest()),
                "expected fresh " + name + " confirmation");
        return actual;
    }

    private static void await(BooleanSupplier condition, String description) throws InterruptedException {
        long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        do {
            Handler.runReadyForTest();
            if (condition.getAsBoolean()) return;
            Thread.sleep(1);
        } while (System.nanoTime() < until);
        throw new AssertionError(description);
    }

    private static PrepareActivity start() {
        PrepareActivity activity = new PrepareActivity();
        activity.createForTest();
        activity.startForTest();
        return activity;
    }

    private static void oneAttempt(int stops) {
        check(APP.binds == 1 && RetainedRootHostServiceV2.claims == 1
                && RetainedRootHostServiceV2.prepares == 1 && RetainedRootHostServiceV2.stops == stops,
                "one binding, broker claim and Prepare with expected Stop count");
    }

    private static PrepareActivity prepared() throws InterruptedException {
        PrepareActivity activity = start();
        show(activity, "prepare", PREPARE_DIALOG).clickForTest(DialogInterface.BUTTON_POSITIVE);
        await(() -> text(activity).startsWith(PARTIAL), "Prepare never reached a partial observation");
        oneAttempt(0);
        return activity;
    }

    private static void overlap() throws InterruptedException {
        PrepareActivity first = prepared(), second = start();
        check(text(first).equals(text(second)), "both started screens initially display the same operation");
        second.stopForTest();
        AlertDialog before = AlertDialog.lastShownForTest();
        tap(first, "stop");
        AlertDialog actual = AlertDialog.lastShownForTest();
        check(actual != before && actual != null && STOP_DIALOG.contentEquals(actual.getTitleForTest()),
                "OVERLAP_A_LOST");
        actual.clickForTest(DialogInterface.BUTTON_POSITIVE);
        await(() -> text(first).contains("Stop request acknowledged."), "first screen did not receive Stop ack");
        oneAttempt(1);
        check(!text(second).contains("Stop request acknowledged."), "stopped screen did not render new status");

        RetainedRootHostServiceV2.sample = RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL;
        await(() -> widget(first, "refresh").isEnabled(), "Stop refresh never returned");
        tap(first, "refresh");
        await(() -> text(first).startsWith(LOCAL_TERMINAL), "first screen could not Refresh after other screen stopped");
        check(APP.unbinds == 0, "status 6 keeps registration");
        RetainedRootHostServiceV2.sample = RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
        tap(first, "refresh");
        await(() -> text(first).startsWith(CLEANUP), "first screen did not render cleanup");
        check(APP.unbinds == 1, "cleanup released registration once");
        oneAttempt(1);
        first.stopForTest();
    }

    private static void renderBoth() throws InterruptedException {
        PrepareActivity first = prepared(), second = start();
        RetainedRootHostServiceV2.sample = RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL;
        tap(second, "refresh");
        await(() -> text(second).startsWith(LOCAL_TERMINAL), "second screen did not render refresh");
        check(text(first).equals(text(second)), "OVERLAP_RENDER_STALE");
        check(APP.unbinds == 0, "shared partial operation stays retained");
        oneAttempt(0);
        second.stopForTest();
        first.stopForTest();
    }

    private static void dialogReentry(boolean stop) throws InterruptedException {
        PrepareActivity screen = stop ? prepared() : start();
        String button = stop ? "stop" : "prepare", title = stop ? STOP_DIALOG : PREPARE_DIALOG;
        AlertDialog.setShowHookForTest(dialog -> {
            screen.stopForTest();
            screen.startForTest();
        });
        AlertDialog stale = show(screen, button, title);
        boolean retiredBeforeCallback = !stale.isShowing();
        stale.clickForTest(DialogInterface.BUTTON_POSITIVE);
        check(retiredBeforeCallback && APP.binds == (stop ? 1 : 0) && RetainedRootHostServiceV2.stops == 0,
                "DIALOG_LIFECYCLE_STALE");

        AlertDialog fresh = show(screen, button, title);
        stale.clickForTest(DialogInterface.BUTTON_POSITIVE);
        Handler.runReadyForTest(); // Delivers the old dismissal after the replacement was adopted.
        check(fresh.isShowing(), "old click cannot dismiss newer confirmation");
        fresh.clickForTest(DialogInterface.BUTTON_POSITIVE);
        await(() -> stop ? text(screen).contains("Stop request acknowledged.") : text(screen).startsWith(PARTIAL),
                "fresh visible confirmation did not dispatch");
        oneAttempt(stop ? 1 : 0);
        screen.stopForTest();
    }

    private static void dialogCreateReentry() throws InterruptedException {
        PrepareActivity screen = start();
        AlertDialog[] stale = new AlertDialog[1];
        AlertDialog before = AlertDialog.lastShownForTest();
        AlertDialog.setCreateHookForTest(dialog -> {
            stale[0] = dialog;
            screen.stopForTest();
            screen.startForTest();
        });
        tap(screen, "prepare");
        check(stale[0] != null && !stale[0].isShowing() && AlertDialog.lastShownForTest() == before,
                "DIALOG_CREATE_OWNER_LOST");
        stale[0].clickForTest(DialogInterface.BUTTON_POSITIVE);
        check(APP.binds == 0, "never-shown old dialog cannot bind");
        show(screen, "prepare", PREPARE_DIALOG).clickForTest(DialogInterface.BUTTON_POSITIVE);
        await(() -> text(screen).startsWith(PARTIAL), "fresh confirmation did not dispatch after stale create");
        oneAttempt(0);
        screen.stopForTest();
    }

    private static void recreate() throws InterruptedException {
        PrepareActivity first = prepared();
        String last = text(first);
        int reads = RetainedRootHostServiceV2.statusReads;
        first.stopForTest();
        PrepareActivity replacement = start();
        check(text(replacement).equals(last) && RetainedRootHostServiceV2.statusReads == reads,
                "replacement redraws retained operation without new host work");
        oneAttempt(0);
        AlertDialog before = AlertDialog.lastShownForTest();
        widget(first, "stop").performClick();
        check(AlertDialog.lastShownForTest() == before, "stopped instance cannot open a stale confirmation");
        RetainedRootHostServiceV2.sample = RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL;
        tap(replacement, "refresh");
        await(() -> text(replacement).startsWith(LOCAL_TERMINAL), "replacement can Refresh the existing operation");
        oneAttempt(0);
        replacement.stopForTest();
    }

    public static void main(String[] args) {
        try {
            check(args.length == 1, "one scenario required");
            check(Looper.myLooper() == Looper.getMainLooper(), "fixture main Looper required");
            Context.setApplicationForTest(APP);
            switch (args[0]) {
                case "overlap": overlap(); break;
                case "render-both": renderBoth(); break;
                case "dialog-prepare": dialogReentry(false); break;
                case "dialog-stop": dialogReentry(true); break;
                case "dialog-create": dialogCreateReentry(); break;
                case "recreate": recreate(); break;
                default: throw new AssertionError("unexpected scenario");
            }
            System.out.println("FILE_STAGE_ACTIVITY_LIFECYCLE " + args[0] + " PASS");
            System.exit(0);
        } catch (Throwable failure) {
            failure.printStackTrace();
            System.exit(1);
        }
    }
}
