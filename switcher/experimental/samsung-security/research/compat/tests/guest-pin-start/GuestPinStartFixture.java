package com.oplus.keyguard.security;

import android.os.AsyncTask;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import com.android.internal.widget.VerifyCredentialResponse;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Inert model for the exact adopted start and its local retirement boundary. */
public final class GuestPinStartFixture {
    private static final int USER = 17;
    private static final AtomicInteger originalRunnableRuns = new AtomicInteger();
    private static final AtomicInteger modeledQueueRuns = new AtomicInteger();
    private static int passed;

    private interface Action {
        void run() throws Throwable;
    }

    private interface Case {
        void run(World world) throws Throwable;
    }

    private static final class RecordingExecutor implements Executor {
        Runnable queued;
        int submissions;

        @Override public void execute(Runnable work) {
            require(work != null && submissions == 0, "Expected a single modeled enqueue");
            queued = work;
            submissions++;
        }
    }

    private static final class Request {
        final AsyncTask<?, ?, ?> task;
        final GuestPinCheckRequest owner;
        final WrappedCallback receiver = new WrappedCallback();
        final Runnable originalTicket = () -> {
            originalRunnableRuns.incrementAndGet();
            throw new AssertionError("No original progress delivery in this fixture");
        };

        Request(AsyncTask<?, ?, ?> task, GuestPinCheckRequest owner) {
            this.task = task;
            this.owner = owner;
        }
    }

    private static final class World implements AutoCloseable {
        final Object checker = new Object();
        final Object controller = new Object();
        final Object monitor = new Object();
        final Object higher = new Object();
        final View view = new View();
        final Handler handler = new Handler(Looper.getMainLooper());
        final GuestPinCheckRequest.Slot slot = new GuestPinCheckRequest.Slot(checker);
        final RecordingExecutor submission = new RecordingExecutor();
        final Object argument = new Object();
        final Object[] arguments = {argument, null};
        final Runnable queuedWork = () -> {
            modeledQueueRuns.incrementAndGet();
            throw new AssertionError("The fixture retains the queued work without running it");
        };
        final ExecutorService worker = Executors.newSingleThreadExecutor(work -> {
            Thread thread = new Thread(work, "inert-start-worker");
            thread.setDaemon(true);
            return thread;
        });

        Request adopt() {
            AsyncTask<?, ?, ?> task = new OplusLockPatternChecker$oplusCheckCredential$task$1();
            return new Request(task, slot.adoptBeforeExecute(checker, controller, view, monitor, USER, task, higher));
        }

        AsyncTask<?, ?, ?> start(Request request) throws Throwable {
            return slot.executeAdopted(request.owner, request.task, submission, arguments);
        }

        <T> T onWorker(Callable<T> action) throws Exception {
            return worker.submit(action).get(3, TimeUnit.SECONDS);
        }

        void bind(Request request) {
            request.owner.bindBeforeOriginalDispatch(request.task, higher, request.receiver, handler);
        }

        void complete(Request request) throws Exception {
            onWorker(() -> {
                bind(request);
                progress(request);
                try {
                    request.owner.observeOriginalFinal(request.task, new VerifyCredentialResponse(true));
                } catch (Throwable failure) {
                    throw new AssertionError(failure);
                }
                return null;
            });
        }

        void progress(Request request) {
            request.owner.observeOriginalTicket(request.receiver, handler, request.originalTicket);
        }

        boolean claim(Request request) {
            return request.owner.claimOriginalProgressAtEntry(controller, view, monitor, USER, request.task, higher,
                    request.receiver, handler, request.originalTicket);
        }

        void originalArguments(Request request, AsyncTask<?, ?, ?> task, Executor executor, Object[] args) {
            require(Looper.myLooper() == Looper.getMainLooper(), "Modeled original start runs on the source main");
            require(task == request.task && executor == submission && args == arguments,
                    "Original start receives exact task, executor and array references");
            require(args.length == 2 && args[0] == argument && args[1] == null, "Original arguments remain intact");
        }

        void simpleStart(Request request) throws Throwable {
            request.task.setStartAction((task, executor, args) -> {
                originalArguments(request, task, executor, args);
                return task;
            });
            require(start(request) == request.task, "Original start result identity");
        }

        @Override public void close() throws Exception {
            worker.shutdown();
            require(worker.awaitTermination(3, TimeUnit.SECONDS), "Inert worker terminates");
        }
    }

    private static void require(boolean condition, String detail) {
        if (!condition) throw new AssertionError(detail);
    }

    private static Throwable thrown(Action action) {
        try {
            action.run();
        } catch (Throwable failure) {
            return failure;
        }
        throw new AssertionError("Expected a refusal or the original start failure");
    }

    private static void refused(Action action) {
        require(thrown(action) instanceof IllegalStateException, "Unadmitted start or adoption must refuse locally");
    }

    private static void runCase(String name, Case test) throws Throwable {
        try (World world = new World()) {
            test.run(world);
            require(originalRunnableRuns.get() == 0 && modeledQueueRuns.get() == 0 && Handler.postCalls() == 0,
                    "No progress delivery, Handler post or modeled queued work execution");
        }
        System.out.println("PASS " + name);
        passed++;
    }

    public static void main(String[] args) throws Throwable {
        require(args.length == 0, "Inert fixture accepts no arguments");
        runCase("normal_exact_identity_return_and_one_use", w -> {
            Request r = w.adopt();
            AsyncTask<?, ?, ?> returned = new OplusLockPatternChecker$oplusCheckCredential$task$1();
            AtomicInteger calls = new AtomicInteger();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                calls.incrementAndGet();
                return returned;
            });
            require(w.start(r) == returned, "Preserve even a distinct exact modeled return");
            refused(() -> w.start(r));
            require(calls.get() == 1 && w.submission.submissions == 0, "Exactly one original start, no wrapper submit");
            w.simpleStart(w.adopt());
        });
        runCase("wrong_task_foreign_request_and_wrong_thread_preserve_current", w -> {
            Request r = w.adopt();
            Object otherChecker = new Object();
            GuestPinCheckRequest.Slot otherSlot = new GuestPinCheckRequest.Slot(otherChecker);
            GuestPinCheckRequest other = otherSlot.adoptBeforeExecute(
                    otherChecker, w.controller, w.view, w.monitor, USER, r.task, w.higher);
            AsyncTask<?, ?, ?> wrong = new OplusLockPatternChecker$oplusCheckCredential$task$1();
            wrong.setStartAction((task, executor, original) -> {
                throw new AssertionError("Wrong task reached modeled original execute");
            });
            AtomicInteger calls = new AtomicInteger();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                calls.incrementAndGet();
                return task;
            });
            refused(() -> w.slot.executeAdopted(r.owner, wrong, w.submission, w.arguments));
            refused(() -> w.slot.executeAdopted(other, r.task, w.submission, w.arguments));
            Throwable offMain = w.onWorker(() -> thrown(() -> w.start(r)));
            require(offMain instanceof IllegalStateException && calls.get() == 0,
                    "Exact tuple off the source main does not execute");
            require(w.start(r) == r.task && calls.get() == 1, "Refusals leave the exact current admission intact");
        });
        runCase("retired_and_replaced_requests_cannot_execute", w -> {
            Request retired = w.adopt();
            retired.owner.retireFromOriginalSource(retired.task);
            retired.task.setStartAction((task, executor, original) -> {
                throw new AssertionError("Retired request executed");
            });
            refused(() -> w.start(retired));
            Request replaced = w.adopt();
            Request current = w.adopt();
            replaced.task.setStartAction((task, executor, original) -> {
                throw new AssertionError("Replaced request executed");
            });
            refused(() -> w.start(replaced));
            w.simpleStart(current);
        });
        runCase("reentrant_start_and_adoption_refused", w -> {
            Request r = w.adopt();
            AtomicInteger calls = new AtomicInteger();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                require(calls.incrementAndGet() == 1, "Reentry reached original start again");
                refused(() -> w.start(r));
                refused(w::adopt);
                return task;
            });
            require(w.start(r) == r.task && calls.get() == 1, "Outer original start completes once");
            w.simpleStart(w.adopt());
        });
        runCase("worker_progress_before_original_returns", w -> {
            Request r = w.adopt();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                executor.execute(w.queuedWork);
                w.complete(r);
                return task;
            });
            require(w.start(r) == r.task && w.submission.queued == w.queuedWork && w.submission.submissions == 1,
                    "Exact modeled enqueue and worker completion before return");
            require(w.claim(r) && !w.claim(r), "Started request retains one exact progress claim");
        });
        runCase("throw_before_submit_cuts_slot_and_preserves_throwable", w -> {
            Request r = w.adopt();
            Exception exact = new Exception("authored original pre-submit failure");
            AtomicInteger calls = new AtomicInteger();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                calls.incrementAndGet();
                throw exact;
            });
            require(thrown(() -> w.start(r)) == exact, "Original checked Throwable survives exactly");
            refused(() -> w.start(r));
            refused(w::adopt);
            try {
                w.onWorker(() -> {
                    w.bind(r);
                    return null;
                });
                throw new AssertionError("Throwing request still admitted a late worker");
            } catch (ExecutionException expected) {
                require(expected.getCause() instanceof IllegalStateException, "Existing bind refuses exact retirement");
            }
            require(calls.get() == 1 && w.submission.submissions == 0 && !w.claim(r),
                    "No retry or progress after pre-submit throw");
        });
        runCase("throw_after_submit_retires_ticket_but_retains_queue_evidence", w -> {
            Request r = w.adopt();
            Error exact = new AssertionError("authored original post-submit failure");
            AtomicInteger calls = new AtomicInteger();
            r.task.setStartAction((task, executor, original) -> {
                w.originalArguments(r, task, executor, original);
                calls.incrementAndGet();
                executor.execute(w.queuedWork);
                w.complete(r);
                require(r.owner.originalFinalKind(w.controller, w.view, w.monitor, USER, r.task)
                        == PinCheckCompletion.FinalKind.ORIGINAL_MATCH, "Matched final happened before modeled throw");
                throw exact;
            });
            require(thrown(() -> w.start(r)) == exact, "Original post-submit Error survives exactly");
            require(w.submission.submissions == 1 && w.submission.queued == w.queuedWork,
                    "The model retains the actual queued identity after throw");
            w.progress(r);
            require(!w.claim(r), "Original throw invalidates already matched progress");
            r.owner.retireFromOriginalSource(r.task);
            refused(w::adopt);
            refused(() -> w.start(r));
            require(calls.get() == 1 && w.submission.submissions == 1, "No retry after possibly submitted original work");
        });
        runCase("late_cancel_is_exact_after_replacement", w -> {
            Request old = w.adopt();
            w.simpleStart(old);
            w.complete(old);
            Request next = w.adopt();
            w.simpleStart(next);
            w.complete(next);
            old.owner.retireFromOriginalSource(old.task);
            next.owner.retireFromOriginalSource(old.task);
            w.progress(old);
            require(!w.claim(old) && w.claim(next), "Delayed old cancellation leaves the replacement claim intact");
        });
        runCase("exact_delayed_cancel_before_entry", w -> {
            Request r = w.adopt();
            w.simpleStart(r);
            w.complete(r);
            r.owner.retireFromOriginalSource(r.task);
            r.owner.retireFromOriginalSource(r.task);
            require(!w.claim(r), "Exact delayed cancellation cuts the already matched ticket");
        });
        System.out.println("PASS total=" + passed + " originalRunnableRuns=" + originalRunnableRuns.get()
                + " handlerPosts=" + Handler.postCalls() + " modeledQueueRuns=" + modeledQueueRuns.get());
    }
}
