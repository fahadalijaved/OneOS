package com.fahadali.oneos.core.root;

import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.Looper;
import android.os.Parcel;
import com.fahadali.oneos.BuildConfig;
import com.fahadali.oneos.core.root.RetainedRootHostServiceV2.ViewAttempt;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Locale;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static com.fahadali.oneos.core.root.RetainedViewAppProtocol.*;

/** Drives the actual service through BEGIN, its callback, and the public ViewAttempt. */
public final class LateStopAckFixture {
    private static final long TEST_WAIT_MS = 8_000;

    private enum Reply {
        QUEUED, REFUSED, MALFORMED, RETIRED
    }

    private static final class Peer extends Binder {
        final Reply mode;
        final CountDownLatch offer = new CountDownLatch(1);
        final CountDownLatch firstStatusEntered = new CountDownLatch(1);
        final CountDownLatch releaseFirstStatus = new CountDownLatch(1);
        final CountDownLatch stopEntered = new CountDownLatch(1);
        final CountDownLatch releaseStop = new CountDownLatch(1);
        final AtomicInteger prepares = new AtomicInteger();
        final AtomicInteger stops = new AtomicInteger();
        final AtomicInteger stopReplies = new AtomicInteger();
        final AtomicInteger statuses = new AtomicInteger();
        volatile Thread relay;
        volatile int status = STATUS_PARTIAL;

        Peer(Reply mode) { this.mode = mode; }

        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) {
            check(flags == 0, "Expected synchronous callback");
            data.enforceInterface(RetainedHostControlProtocol.CALLBACK);
            check(data.readInt() == RetainedHostControlProtocol.VERSION, "Callback version");
            if (code == RetainedHostControlProtocol.OFFER) {
                check(data.readInt() == RetainedRootOfferLaunch.NATIVE_PID, "Modeled offer PID");
                check(RetainedRootOfferLaunch.ADDRESS.equals(data.readString()), "Modeled offer address");
                data.enforceNoDataAvail();
                writeResult(reply, RetainedHostControlProtocol.QUEUED);
                offer.countDown();
                return true;
            }
            data.enforceNoDataAvail();
            switch (code) {
                case APP_VIEW_PREPARE:
                    check(prepares.incrementAndGet() == 1, "Duplicate Prepare");
                    relay = Thread.currentThread();
                    writeResult(reply, QUEUED);
                    return true;
                case APP_VIEW_STATUS:
                    check(Thread.currentThread() == relay, "STATUS used another relay");
                    if (statuses.incrementAndGet() == 1) {
                        firstStatusEntered.countDown();
                        await(releaseFirstStatus, "first STATUS release");
                    }
                    writeResult(reply, status);
                    return true;
                case APP_VIEW_STOP:
                    check(Thread.currentThread() == relay, "STOP used another relay");
                    check(stops.incrementAndGet() == 1, "Duplicate STOP");
                    stopEntered.countDown();
                    await(releaseStop, "STOP reply release");
                    writeResult(reply, mode == Reply.REFUSED ? UNAVAILABLE : QUEUED);
                    if (mode == Reply.MALFORMED) reply.writeInt(17);
                    stopReplies.incrementAndGet();
                    return true;
                default:
                    throw new AssertionError("Unexpected callback code " + code);
            }
        }

        private static void writeResult(Parcel reply, int result) {
            reply.writeNoException();
            reply.writeInt(result);
        }
    }

    public static void main(String[] args) throws Exception {
        check(args.length == 2 && (args[0].equals("baseline") || args[0].equals("successor")),
                "Usage: LateStopAckFixture baseline|successor queued|refused|malformed|retired");
        boolean successor = args[0].equals("successor");
        Reply mode = Reply.valueOf(args[1].toUpperCase(Locale.ROOT));
        check(Looper.myLooper() == Looper.getMainLooper(), "Fixture must initialize the main looper");
        Method acknowledgment = acknowledgmentMethod(successor);
        Peer peer = new Peer(mode);
        RetainedRootHostServiceV2 service = new RetainedRootHostServiceV2();
        ExecutorService callers = Executors.newFixedThreadPool(2, task -> {
            Thread thread = new Thread(task, "late-stop-ack-observer");
            thread.setDaemon(true);
            return thread;
        });
        boolean destroyed = false;
        long stopWaitMs;
        try {
            IBinder broker = service.onBind(new Intent());
            begin(broker, peer);
            await(peer.offer, "OFFER callback");
            ViewAttempt attempt = claim(broker);
            check(RetainedRootHostServiceV2.claimView(broker) == null, "Attempt issued twice");
            check(offMain(callers, attempt::prepare) == QUEUED, "Prepare was not queued");
            check(peer.prepares.get() == 1, "Prepare did not reach the callback");
            check(!offMain(callers, () -> acknowledged(acknowledgment, attempt)), "ACK before STOP");

            Future<Integer> firstStatus = callers.submit(attempt::status);
            await(peer.firstStatusEntered, "first STATUS entry");
            long start = System.nanoTime();
            check(offMain(callers, attempt::stop) == UNCERTAIN, "STOP observer did not time out");
            stopWaitMs = elapsedMs(start);
            check(stopWaitMs >= 1_900, "STOP did not wait for its real two-second budget");
            check(firstStatus.get(TEST_WAIT_MS, TimeUnit.MILLISECONDS) == STATUS_UNAVAILABLE,
                    "First STATUS returned despite its held callback");
            check(peer.stops.get() == 0, "STOP overtook held STATUS");
            check(!offMain(callers, () -> acknowledged(acknowledgment, attempt)), "ACK on timeout");

            peer.releaseFirstStatus.countDown();
            await(peer.stopEntered, "the retained STOP reaching the callback");
            check(!offMain(callers, () -> acknowledged(acknowledgment, attempt)), "ACK before reply");
            if (mode == Reply.RETIRED) {
                service.onDestroy();
                destroyed = true;
            }
            peer.releaseStop.countDown();
            if (mode == Reply.RETIRED) {
                join(peer.relay);
                check(offMain(callers, attempt::status) == STATUS_UNAVAILABLE, "Retired STATUS accepted");
                check(peer.statuses.get() == 1, "Retired STATUS reached callback");
            } else {
                peer.status = STATUS_LOCAL_TERMINAL;
                observe(callers, attempt, STATUS_LOCAL_TERMINAL);
                // An accepted STATUS cannot pass the STOP slot until its reply has settled.
                check(offMain(callers, () -> acknowledged(acknowledgment, attempt))
                        == (successor && mode == Reply.QUEUED), "Wrong acknowledgment after reply");
                peer.status = STATUS_LOCAL_CLEANUP_OBSERVED;
                observe(callers, attempt, STATUS_LOCAL_CLEANUP_OBSERVED);
            }
            check(offMain(callers, () -> acknowledged(acknowledgment, attempt))
                    == (successor && mode == Reply.QUEUED), "Status or retirement changed ACK meaning");
            check(offMain(callers, attempt::stop) == UNAVAILABLE, "Duplicate STOP was allowed");
            check(peer.stops.get() == 1 && peer.stopReplies.get() == 1,
                    "Expected exactly one STOP callback and reply");
            check(peer.statuses.get() == (mode == Reply.RETIRED ? 1 : 3),
                    "Acknowledgment read or retry reached the callback");
            if (successor && mode == Reply.QUEUED) {
                service.onDestroy();
                destroyed = true;
                join(peer.relay);
                check(offMain(callers, () -> acknowledged(acknowledgment, attempt)),
                        "Retirement erased a previously verified receipt");
            }
        } finally {
            if (!destroyed) service.onDestroy();
            peer.releaseFirstStatus.countDown();
            peer.releaseStop.countDown();
            callers.shutdownNow();
            if (peer.relay != null) join(peer.relay);
        }
        System.out.println("PASS " + args[0] + " " + args[1] + " stopWaitMs=" + stopWaitMs
                + " prepares=" + peer.prepares.get() + " stops=" + peer.stops.get()
                + " statuses=" + peer.statuses.get());
    }

    private static Method acknowledgmentMethod(boolean successor) throws Exception {
        try {
            Method method = ViewAttempt.class.getMethod("stopAcknowledged");
            check(successor && method.getReturnType() == boolean.class
                    && !Modifier.isStatic(method.getModifiers()), "Unexpected acknowledgment API");
            return method;
        } catch (NoSuchMethodException missing) {
            check(!successor, "Successor is missing the acknowledgment API");
            return null;
        }
    }

    private static boolean acknowledged(Method method, ViewAttempt attempt) throws Exception {
        return method != null && (Boolean) method.invoke(attempt);
    }

    private static void begin(IBinder broker, Peer peer) throws Exception {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(RetainedHostControlProtocol.BROKER);
            data.writeInt(RetainedHostControlProtocol.VERSION);
            data.writeStrongBinder(peer);
            data.writeString(BuildConfig.RETAINED_VIEW_CONTROLLER_SHA256);
            data.writeLong(BuildConfig.RETAINED_VIEW_CONTROLLER_BYTES);
            check(broker.transact(RetainedHostControlProtocol.BEGIN, data, reply, 0), "Unhandled BEGIN");
            reply.readException();
            check(reply.readInt() == RetainedHostControlProtocol.QUEUED, "BEGIN not queued");
            reply.enforceNoDataAvail();
        } finally {
            reply.recycle();
            data.recycle();
        }
    }

    private static ViewAttempt claim(IBinder broker) throws Exception {
        long start = System.nanoTime();
        do {
            ViewAttempt attempt = RetainedRootHostServiceV2.claimView(broker);
            if (attempt != null) return attempt;
            Thread.sleep(5);
        } while (elapsedMs(start) < TEST_WAIT_MS);
        throw new AssertionError("Unable to claim the acknowledged attempt");
    }

    private static void observe(ExecutorService callers, ViewAttempt attempt, int expected)
            throws Exception {
        long start = System.nanoTime();
        do {
            int actual = offMain(callers, attempt::status);
            if (actual == expected) return;
            check(actual == STATUS_UNAVAILABLE, "Unexpected status " + actual);
            Thread.sleep(5);
        } while (elapsedMs(start) < TEST_WAIT_MS);
        throw new AssertionError("Unable to observe status " + expected);
    }

    private static <T> T offMain(ExecutorService callers, Callable<T> call) throws Exception {
        return callers.submit(call).get(TEST_WAIT_MS, TimeUnit.MILLISECONDS);
    }

    private static long elapsedMs(long start) {
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
    }

    private static void await(CountDownLatch latch, String action) {
        try {
            check(latch.await(TEST_WAIT_MS, TimeUnit.MILLISECONDS), "Timed out waiting for " + action);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new AssertionError("Interrupted waiting for " + action, interrupted);
        }
    }

    private static void join(Thread thread) throws InterruptedException {
        check(thread != null, "Missing actual relay thread");
        thread.join(TEST_WAIT_MS);
        check(!thread.isAlive(), "Actual relay did not finish");
    }

    private static void check(boolean condition, String problem) {
        if (!condition) throw new AssertionError(problem);
    }
}
