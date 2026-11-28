package com.oplus.keyguard.security;

import android.os.AsyncTask;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import com.android.internal.widget.VerifyCredentialResponse;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Authored source occurrences around the exact adopted request. */
public final class GuestPinOccurrenceFixture {
    private static final int USER = 17;
    private static final AtomicInteger originalRunnableRuns = new AtomicInteger();
    private static final AtomicInteger modeledExecutorSubmissions = new AtomicInteger();
    private static int passed;

    private interface Action {
        void run() throws Throwable;
    }

    private interface Case {
        void run(World world) throws Throwable;
    }

    private static final class User {
        final int id;

        User(int id) {
            this.id = id;
        }

        @Override public boolean equals(Object other) {
            return other instanceof User && ((User) other).id == id;
        }

        @Override public int hashCode() {
            return id;
        }
    }

    private static final class Readback implements GuestPinSourceOccurrence.Readback {
        boolean resumed = true;
        boolean bouncerShowing = true;
        boolean complete = true;
        View displayed;
        User user = new User(USER);
        Runnable duringSelectionComplete;

        Readback(View view) {
            displayed = view;
        }

        @Override public boolean isResumed() {
            return resumed;
        }

        @Override public boolean isBouncerShowing() {
            return bouncerShowing;
        }

        @Override public View displayedView() {
            return displayed;
        }

        @Override public Object selectedUser() {
            return user;
        }

        @Override public int selectedUserId(Object record) {
            return ((User) record).id;
        }

        @Override public boolean selectionComplete(Object record) {
            boolean sample = complete;
            Runnable reenter = duringSelectionComplete;
            duringSelectionComplete = null;
            if (reenter != null) reenter.run();
            return sample;
        }
    }

    private static final class Request {
        final AsyncTask<?, ?, ?> task;
        final GuestPinCheckRequest request;
        final WrappedCallback receiver = new WrappedCallback();
        final Runnable ticket = () -> {
            originalRunnableRuns.incrementAndGet();
            throw new AssertionError("Occurrence proof never executes the original ticket");
        };

        Request(AsyncTask<?, ?, ?> task, GuestPinCheckRequest request) {
            this.task = task;
            this.request = request;
        }
    }

    private static final class World implements AutoCloseable {
        final Object checker = new Object();
        final Object controller = new Object();
        final Object monitor = new Object();
        final Object higher = new Object();
        final View view = new View();
        final Handler handler = new Handler(Looper.getMainLooper());
        final Readback readback = new Readback(view);
        final GuestPinSourceOccurrence.Owner owner =
                new GuestPinSourceOccurrence.Owner(checker, controller, view, monitor, readback);
        final GuestPinCheckRequest.Slot slot = new GuestPinCheckRequest.Slot(checker);
        final Executor executor = work -> {
            modeledExecutorSubmissions.incrementAndGet();
            throw new AssertionError("No modeled executor submission in an occurrence proof");
        };
        final Object[] args = {new Object()};
        final ExecutorService worker = Executors.newSingleThreadExecutor(work -> {
            Thread thread = new Thread(work, "inert-occurrence-worker");
            thread.setDaemon(true);
            return thread;
        });

        GuestPinSourceOccurrence begin() {
            return owner.begin(readback.user, readback.user.id);
        }

        Request adopt(GuestPinSourceOccurrence occurrence) {
            AsyncTask<?, ?, ?> task = new OplusLockPatternChecker$oplusCheckCredential$task$1();
            return new Request(task, slot.adoptBeforeExecute(
                    checker, controller, view, monitor, readback.user.id, task, higher, occurrence));
        }

        Request matched(GuestPinSourceOccurrence occurrence) throws Throwable {
            Request r = adopt(occurrence);
            r.task.setStartAction((task, suppliedExecutor, suppliedArgs) -> {
                require(task == r.task && suppliedExecutor == executor && suppliedArgs == args,
                        "Preserve modeled start references");
                return task;
            });
            require(slot.executeAdopted(r.request, r.task, executor, args) == r.task, "Modeled exact task start");
            worker.submit(() -> {
                r.request.bindBeforeOriginalDispatch(r.task, higher, r.receiver, handler);
                r.request.observeOriginalTicket(r.receiver, handler, r.ticket);
                try {
                    r.request.observeOriginalFinal(r.task, new VerifyCredentialResponse(true));
                } catch (Throwable failure) {
                    throw new AssertionError(failure);
                }
            }).get(3, TimeUnit.SECONDS);
            return r;
        }

        boolean claim(Request r) {
            return r.request.claimOriginalProgressAtEntry(
                    controller, view, monitor, USER, r.task, higher, r.receiver, handler, r.ticket);
        }

        void cancel(Request r) {
            r.request.retireFromOriginalSource(r.task);
        }

        @Override public void close() throws Exception {
            worker.shutdown();
            require(worker.awaitTermination(3, TimeUnit.SECONDS), "Inert worker terminates");
        }
    }

    private static void require(boolean condition, String detail) {
        if (!condition) throw new AssertionError(detail);
    }

    private static void refuse(Action action) throws Throwable {
        try {
            action.run();
        } catch (IllegalStateException expected) {
            return;
        }
        throw new AssertionError("Expected exact local admission refusal");
    }

    private static void runCase(String name, Case test) throws Throwable {
        try (World world = new World()) {
            test.run(world);
            require(originalRunnableRuns.get() == 0 && Handler.postCalls() == 0
                    && modeledExecutorSubmissions.get() == 0, "No original delivery, post or submission");
        }
        System.out.println("PASS " + name);
        passed++;
    }

    public static void main(String[] args) throws Throwable {
        require(args.length == 0, "Inert fixture accepts no arguments");
        runCase("current_occurrence_claim_once", w -> {
            GuestPinSourceOccurrence occurrence = w.begin();
            require(occurrence.isLive() && occurrence.matchesNow(), "Actual current modeled source evidence");
            Request r = w.matched(occurrence);
            require(w.claim(r) && !w.claim(r), "One exact current claim");
        });
        runCase("same_view_reused_after_retire_refuses_old", w -> {
            GuestPinSourceOccurrence old = w.begin();
            Request r = w.matched(old);
            w.owner.retire(old);
            w.readback.resumed = false;
            w.readback.displayed = new View();
            w.readback.displayed = w.view;
            w.readback.resumed = true;
            GuestPinSourceOccurrence fresh = w.begin();
            require(w.view.isAttachedToWindow() && fresh.matchesNow() && !old.isLive(),
                    "Original view reference is displayed again under a new occurrence");
            require(!w.claim(r), "A reused exact view cannot restore the old ticket");
            require(w.claim(w.matched(fresh)), "Fresh occurrence on the same view still claims");
        });
        runCase("selected_user_aba_refuses_old", w -> {
            GuestPinSourceOccurrence old = w.begin();
            Request r = w.matched(old);
            User original = w.readback.user;
            w.readback.user = new User(USER + 1);
            GuestPinSourceOccurrence between = w.begin();
            w.readback.user = original;
            GuestPinSourceOccurrence fresh = w.begin();
            require(!between.isLive() && !old.isLive() && fresh.matchesNow(),
                    "Exact original selected record and scalar returned under a new occurrence");
            require(!w.claim(r), "Restored selected values cannot revive the old claim");
            require(w.claim(w.matched(fresh)), "New occurrence for the original user still claims");
        });
        runCase("wrong_equal_user_record_refuses", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            User original = w.readback.user;
            w.readback.user = new User(USER);
            require(w.readback.user != original && w.readback.user.equals(original), "Fixture's equal foreign record");
            require(!source.matchesNow() && !w.claim(r), "User equality does not replace original identity");
        });
        runCase("selection_incomplete_refuses", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.complete = false;
            require(!source.matchesNow() && !w.claim(r), "Current user record still needs complete selection");
        });
        runCase("bouncer_hidden_while_view_current_refuses", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.bouncerShowing = false;
            require(w.readback.resumed && w.readback.displayed == w.view && w.view.isAttachedToWindow(),
                    "Only bouncer visibility changed");
            require(!source.matchesNow() && !w.claim(r), "Hidden bouncer cannot claim during the pause gap");
        });
        runCase("attached_but_not_displayed_refuses", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.displayed = new View();
            require(w.view.isAttachedToWindow() && !source.matchesNow() && !w.claim(r),
                    "Attached former view is not the actual displayed child");
        });
        runCase("retire_during_selection_read_refuses_stale_positive", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.duringSelectionComplete = () -> {
                try {
                    w.worker.submit(() -> {
                        require(Looper.myLooper() != Looper.getMainLooper(), "Off-main modeled source transition");
                        w.owner.retire(source);
                    }).get(3, TimeUnit.SECONDS);
                } catch (Exception failure) {
                    throw new AssertionError(failure);
                }
            };
            require(!w.claim(r) && !source.isLive() && w.readback.duringSelectionComplete == null,
                    "A sampled positive cannot restore a source retired off-main during the read");
        });
        runCase("replace_during_selection_read_refuses_stale_positive", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request old = w.matched(source);
            AtomicReference<Request> replacement = new AtomicReference<>();
            w.readback.duringSelectionComplete = () -> {
                try {
                    replacement.set(w.matched(w.begin()));
                } catch (Throwable failure) {
                    throw new AssertionError(failure);
                }
            };
            require(!w.claim(old) && replacement.get() != null, "Reentry refuses the stale request evidence");
            require(w.claim(replacement.get()), "Reentry does not consume the replacement's independent ticket");
        });
        runCase("exact_cancel_during_read_refuses_claim", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.duringSelectionComplete = () -> w.cancel(r);
            require(!w.claim(r) && source.isLive() && w.readback.duringSelectionComplete == null,
                    "Live source cannot override exact request cancellation during readback");
        });
        runCase("nested_same_ticket_claim_refuses", w -> {
            Request r = w.matched(w.begin());
            w.readback.duringSelectionComplete = () -> require(!w.claim(r),
                    "A nested probe cannot claim the same in-flight ticket");
            require(w.claim(r) && !w.claim(r), "Only the outer entry owns the one-use claim");
        });
        runCase("throwing_readback_retires_exact_request", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.duringSelectionComplete = () -> {
                throw new IllegalStateException("modeled readback failure");
            };
            require(!w.claim(r) && !w.claim(r) && source.isLive(),
                    "An observation failure retires only the exact request");
            require(w.claim(w.matched(source)), "A new request can use the same live source");
        });
        runCase("late_old_cancel_during_new_read_preserves_new", w -> {
            Request old = w.matched(w.begin());
            Request current = w.matched(w.begin());
            w.readback.duringSelectionComplete = () -> {
                w.cancel(old);
                current.request.retireFromOriginalSource(old.task);
            };
            require(w.claim(current) && w.readback.duringSelectionComplete == null && !w.claim(old),
                    "Delayed exact old cancellation cannot poison new readback or claim");
        });
        runCase("stale_occurrence_cannot_adopt_or_retire_new", w -> {
            GuestPinSourceOccurrence old = w.begin();
            GuestPinSourceOccurrence fresh = w.begin();
            Request r = w.matched(fresh);
            refuse(() -> w.adopt(old));
            w.owner.retire(old);
            w.owner.retire(old);
            require(fresh.isLive() && w.claim(r), "Stale adoption/retirement preserves the current occurrence");
        });
        runCase("off_main_transition_blocks_reissue_with_old_readback", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            User originalUser = w.readback.user;
            GuestPinSourceOccurrence.Transition transition = w.worker.submit(() -> {
                require(Looper.myLooper() != Looper.getMainLooper(), "Original producer can start off-main");
                return w.owner.startTransition();
            }).get(3, TimeUnit.SECONDS);
            require(w.readback.user == originalUser && w.readback.complete && w.readback.resumed
                    && w.readback.bouncerShowing && w.readback.displayed == w.view && w.view.isAttachedToWindow(),
                    "The external readback still samples the old positive values");
            require(!source.isLive() && !source.matchesNow() && !w.claim(r),
                    "Starting the transition cuts the exact old occurrence and its claim");
            refuse(w::begin);
            boolean settledOffMain = w.worker.submit(() -> {
                try {
                    return w.owner.settleTransition(transition);
                } catch (IllegalStateException expected) {
                    return false;
                }
            }).get(3, TimeUnit.SECONDS);
            require(!settledOffMain, "The off-main producer cannot settle its transition");
            refuse(w::begin);
            require(w.owner.settleTransition(transition), "Main settles the exact transition");
            require(w.claim(w.matched(w.begin())), "Fresh source can issue only after exact settlement");
        });
        runCase("overlapping_transitions_require_each_exact_settlement", w -> {
            GuestPinSourceOccurrence.Transition previous = w.owner.startTransition();
            require(w.owner.settleTransition(previous), "Establish a previously settled transition");
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            GuestPinSourceOccurrence.Transition first = w.owner.startTransition();
            GuestPinSourceOccurrence.Transition second = w.owner.startTransition();
            GuestPinSourceOccurrence.Owner otherOwner =
                    new GuestPinSourceOccurrence.Owner(w.checker, w.controller, w.view, w.monitor, w.readback);
            GuestPinSourceOccurrence.Transition foreign = otherOwner.startTransition();
            require(!w.owner.settleTransition(previous) && !w.owner.settleTransition(foreign),
                    "Settled and foreign tokens cannot clear either pending transition");
            refuse(w::begin);
            require(w.owner.settleTransition(second), "The later transition can settle first");
            require(!w.owner.settleTransition(second), "Duplicate settlement cannot clear the earlier transition");
            refuse(w::begin);
            require(w.owner.settleTransition(first), "Only the first exact token closes the remaining transition");
            require(otherOwner.settleTransition(foreign), "Wrong owner left the foreign transition untouched");
            require(!source.isLive() && !w.claim(r) && w.claim(w.matched(w.begin())),
                    "Both settlements permit a fresh source without restoring the old claim");
        });
        runCase("false_readback_retires_only_exact_request", w -> {
            GuestPinSourceOccurrence source = w.begin();
            Request r = w.matched(source);
            w.readback.bouncerShowing = false;
            require(!w.claim(r) && source.isLive(), "A genuine false readback retires the request only");
            w.readback.bouncerShowing = true;
            require(source.matchesNow() && !w.claim(r), "Restored values cannot reclaim the refused request");
            refuse(() -> r.request.originalFinalKind(w.controller, w.view, w.monitor, USER, r.task));
            require(w.claim(w.matched(source)), "A fresh request can use the unchanged live source");
        });
        System.out.println("PASS total=" + passed + " originalRunnableRuns=" + originalRunnableRuns.get()
                + " handlerPosts=" + Handler.postCalls() + " modeledExecutorSubmissions="
                + modeledExecutorSubmissions.get());
    }
}
