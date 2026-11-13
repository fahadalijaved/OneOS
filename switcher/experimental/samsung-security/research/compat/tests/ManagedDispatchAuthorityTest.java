package com.appleexploit.oneos.security.transport;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Authored synchronous transport fixtures only; no security service or credential. */
public final class ManagedDispatchAuthorityTest {
    private static int checks;

    private interface Action {
        void run() throws Throwable;
    }

    private static void require(boolean value, String description) {
        checks++;
        if (!value) {
            throw new AssertionError(description);
        }
    }

    private static Throwable expect(Class<? extends Throwable> type, Action action)
            throws Throwable {
        try {
            action.run();
        } catch (Throwable failure) {
            require(failure.getClass() == type, "exact failure type");
            return failure;
        }
        throw new AssertionError("Expected " + type.getName());
    }

    private static Object field(Object value, String name) throws Exception {
        Field field = value.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(value);
    }

    private static int active(Object owner) throws Exception {
        return (Integer) field(owner, "activeCalls");
    }

    private static int opening(Object owner) throws Exception {
        return (Integer) field(owner, "openingCalls");
    }

    private static void await(CountDownLatch latch) throws InterruptedException {
        if (!latch.await(5, TimeUnit.SECONDS)) {
            throw new AssertionError("Fixture barrier timed out");
        }
    }

    private static Thread worker(Action action, AtomicReference<Throwable> failure) {
        Thread thread = new Thread(() -> {
            try {
                action.run();
            } catch (Throwable problem) {
                failure.set(problem);
            }
        });
        thread.start();
        return thread;
    }

    private static void join(Thread worker, AtomicReference<Throwable> failure)
            throws Throwable {
        worker.join(6000);
        require(!worker.isAlive(), "fixture thread completed");
        if (failure.get() != null) {
            throw failure.get();
        }
    }

    private static final class Anchor implements AutoCloseable {
        int closes;

        @Override
        public void close() {
            closes++;
        }
    }

    private static final class Prepared implements PreparedDispatch<Object>, AutoCloseable {
        int invokes;
        int closes;

        @Override
        public boolean invoke(int code, Object data, Object reply, int flags) {
            invokes++;
            return false;
        }

        @Override
        public void close() {
            closes++;
        }
    }

    private static ManagedDispatchAuthority.TrustedAdmission fixtureAdmission() {
        // Synthetic fixture policy, deliberately supplied at every construction.
        return (guest, source, uid, pid, flags) -> {
            if (guest != 11 || source != 21 || uid != 1001 || pid != 2002 || flags != 3) {
                throw new SecurityException("Fixture caller or route denied");
            }
        };
    }

    private static DispatchCall<Object> open(ManagedDispatchAuthority<Object> owner)
            throws Throwable {
        return owner.open(11, 21, 1001, 2002, 3);
    }

    private static void basicLifetime() throws Throwable {
        Anchor anchor = new Anchor();
        Prepared prepared = new Prepared();
        AtomicInteger admissions = new AtomicInteger();
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                prepared, anchor, (g, s, u, p, f) -> {
                    fixtureAdmission().validate(g, s, u, p, f);
                    admissions.incrementAndGet();
                });
        expect(NullPointerException.class,
                () -> new ManagedDispatchAuthority<Object>(null, anchor, fixtureAdmission()));
        expect(NullPointerException.class,
                () -> new ManagedDispatchAuthority<Object>(prepared, null, fixtureAdmission()));
        expect(NullPointerException.class,
                () -> new ManagedDispatchAuthority<Object>(prepared, anchor, null));
        expect(SecurityException.class, () -> owner.open(11, 21, 1002, 2002, 3));
        require(active(owner) == 0 && opening(owner) == 0, "denied open has no lease");
        DispatchCall<Object> call = open(owner);
        require(active(owner) == 1 && opening(owner) == 0, "published exact lease");
        call.checkLive();
        require(!call.invoke(21, new Object(), new Object(), 3), "real false result preserved");
        call.checkLive();
        require(admissions.get() == 4 && prepared.invokes == 1, "fresh admission at each boundary");
        expect(IllegalStateException.class, () -> call.invoke(21, null, null, 3));
        call.close();
        call.close();
        require(active(owner) == 0, "idempotent close decrements once");
        expect(IllegalStateException.class, call::checkLive);
        expect(IllegalStateException.class, () -> call.invoke(21, null, null, 3));
        owner.retire();
        owner.retire();
        expect(IllegalStateException.class, () -> open(owner));
        require(field(owner, "anchor") == anchor && field(owner, "prepared") == prepared,
                "borrowed owners strongly retained after zero and retirement");
        require(anchor.closes == 0 && prepared.closes == 0, "no borrowed owner disposal");
    }

    private static void boundArgumentsAndThread() throws Throwable {
        Object data = new Object();
        Object reply = new Object();
        Thread creator = Thread.currentThread();
        AtomicInteger invokes = new AtomicInteger();
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                (code, d, r, flags) -> {
                    require(code == 21 && flags == 3 && d == data && r == reply,
                            "exact original arguments");
                    require(Thread.currentThread() == creator, "synchronous creating thread");
                    invokes.incrementAndGet();
                    return true;
                }, new Object(), fixtureAdmission());
        DispatchCall<Object> wrongCode = open(owner);
        expect(IllegalArgumentException.class, () -> wrongCode.invoke(22, data, reply, 3));
        expect(IllegalStateException.class, () -> wrongCode.invoke(21, data, reply, 3));
        wrongCode.close();
        DispatchCall<Object> wrongFlags = open(owner);
        expect(IllegalArgumentException.class, () -> wrongFlags.invoke(21, data, reply, 4));
        wrongFlags.close();
        DispatchCall<Object> call = open(owner);
        AtomicReference<Throwable> failed = new AtomicReference<Throwable>();
        Thread other = worker(() -> {
            expect(IllegalStateException.class, call::checkLive);
            expect(IllegalStateException.class, () -> call.invoke(21, data, reply, 3));
            expect(IllegalStateException.class, call::close);
        }, failed);
        join(other, failed);
        require(active(owner) == 1, "foreign thread cannot release lease");
        require(call.invoke(21, data, reply, 3), "owner-thread real true result");
        call.close();
        require(invokes.get() == 1 && active(owner) == 0, "only exact attempt reached dispatcher");
        ManagedDispatchAuthority<Object> another = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> true, new Object(), fixtureAdmission());
        DispatchCall<Object> anotherCall = open(another);
        require(field(call, "owner") == owner && field(anotherCall, "owner") == another,
                "each opaque call binds its own owner");
        require(field(call, "generation") != field(anotherCall, "generation"),
                "owners have distinct generation identity");
        anotherCall.close();
    }

    private static void exceptionsAndReentry() throws Throwable {
        Error primary = new AssertionError("Synthetic dispatch failure");
        AtomicReference<DispatchCall<Object>> current = new AtomicReference<DispatchCall<Object>>();
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> {
                    expect(IllegalStateException.class, current.get()::close);
                    expect(IllegalStateException.class, current.get()::checkLive);
                    expect(IllegalStateException.class, () -> current.get().invoke(c, d, r, f));
                    throw primary;
                }, new Object(), fixtureAdmission());
        current.set(open(owner));
        require(expect(AssertionError.class, () -> current.get().invoke(21, null, null, 3))
                == primary, "original dispatch Throwable identity survives cleanup");
        require(primary.getSuppressed().length == 0 && active(owner) == 1,
                "no replacement failure or premature release");
        current.get().close();
        require(active(owner) == 0, "unwound failed original call can close");

        AtomicInteger admissions = new AtomicInteger();
        Error denied = new AssertionError("Synthetic admission failure");
        ManagedDispatchAuthority<Object> deniedOwner = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> { throw new AssertionError("Unexpected dispatcher"); },
                new Object(), (g, s, u, p, f) -> {
                    if (admissions.incrementAndGet() > 1) {
                        throw denied;
                    }
                });
        DispatchCall<Object> deniedCall = open(deniedOwner);
        require(expect(AssertionError.class, () -> deniedCall.invoke(21, null, null, 3))
                == denied, "admission failure identity preserved");
        expect(IllegalStateException.class, () -> deniedCall.invoke(21, null, null, 3));
        deniedCall.close();
        require(active(deniedOwner) == 0, "failed admission does not pin busy stack");

        AtomicReference<ManagedDispatchAuthority<Object>> ref =
                new AtomicReference<ManagedDispatchAuthority<Object>>();
        ManagedDispatchAuthority<Object> retiredDuringOpen = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> true, new Object(), (g, s, u, p, f) -> ref.get().retire());
        ref.set(retiredDuringOpen);
        expect(IllegalStateException.class, () -> open(retiredDuringOpen));
        require(active(retiredDuringOpen) == 0 && opening(retiredDuringOpen) == 0,
                "reentrant retirement prevents publication");

        AtomicInteger entered = new AtomicInteger();
        AtomicReference<DispatchCall<Object>> checking = new AtomicReference<DispatchCall<Object>>();
        ManagedDispatchAuthority<Object> reentry = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> true, new Object(), (g, s, u, p, f) -> {
                    if (entered.incrementAndGet() > 1) {
                        expect(IllegalStateException.class, checking.get()::close);
                        expect(IllegalStateException.class, checking.get()::checkLive);
                    }
                });
        checking.set(open(reentry));
        checking.get().checkLive();
        require(active(reentry) == 1, "admission reentry cannot end current lease");
        checking.get().close();
    }

    private static void retireDuringAdmission(int stage) throws Throwable {
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        AtomicInteger admissions = new AtomicInteger();
        AtomicInteger invokes = new AtomicInteger();
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> { invokes.incrementAndGet(); return true; }, new Object(),
                (g, s, u, p, f) -> {
                    int at = admissions.incrementAndGet();
                    if ((stage == 0 && at == 1) || (stage != 0 && at == 2)) {
                        entered.countDown();
                        await(release);
                    }
                });
        AtomicReference<Throwable> failed = new AtomicReference<Throwable>();
        Thread thread = worker(() -> {
            DispatchCall<Object> call = null;
            try {
                if (stage == 0) {
                    expect(IllegalStateException.class, () -> open(owner));
                } else {
                    call = open(owner);
                    final DispatchCall<Object> held = call;
                    if (stage == 1) {
                        expect(IllegalStateException.class, held::checkLive);
                    } else {
                        expect(IllegalStateException.class, () -> held.invoke(21, null, null, 3));
                    }
                }
            } finally {
                if (call != null) {
                    call.close();
                }
            }
        }, failed);
        try {
            await(entered);
            owner.retire();
        } finally {
            release.countDown();
            join(thread, failed);
        }
        require(invokes.get() == 0 && opening(owner) == 0 && active(owner) == 0,
                "retirement after external admission stops new dispatch/publication");
    }

    private static void concurrentOriginalWork() throws Throwable {
        CountDownLatch entered = new CountDownLatch(2);
        CountDownLatch release = new CountDownLatch(1);
        AtomicInteger completed = new AtomicInteger();
        AtomicInteger postChecks = new AtomicInteger();
        Anchor anchor = new Anchor();
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> {
                    entered.countDown();
                    await(release);
                    completed.incrementAndGet();
                    return true;
                }, anchor, fixtureAdmission());
        AtomicReference<Throwable> firstFailure = new AtomicReference<Throwable>();
        AtomicReference<Throwable> secondFailure = new AtomicReference<Throwable>();
        Action action = () -> {
            DispatchCall<Object> call = open(owner);
            try {
                if (!call.invoke(21, new Object(), new Object(), 3)) {
                    throw new AssertionError("Original result lost");
                }
                try {
                    call.checkLive();
                    throw new AssertionError("Retired post-check succeeded");
                } catch (IllegalStateException expected) {
                    postChecks.incrementAndGet();
                }
            } finally {
                call.close();
            }
        };
        Thread first = worker(action, firstFailure);
        Thread second = worker(action, secondFailure);
        try {
            await(entered);
            require(active(owner) == 2, "independent original calls run concurrently");
            owner.retire();
            require(active(owner) == 2 && field(owner, "anchor") == anchor,
                    "retirement retains in-flight owners");
        } finally {
            release.countDown();
            join(first, firstFailure);
            join(second, secondFailure);
        }
        require(completed.get() == 2 && postChecks.get() == 2, "existing original work unwinds");
        require(active(owner) == 0 && anchor.closes == 0 && field(owner, "anchor") == anchor,
                "zero calls neither disposes anchor nor acknowledges backend drain");
    }

    private static void statelessPacketShape() throws Throwable {
        ManagedDispatchAuthority<Object> owner = new ManagedDispatchAuthority<Object>(
                (c, d, r, f) -> true, new Object(), fixtureAdmission());
        DispatchCall<Object> call = open(owner);
        for (Field field : call.getClass().getDeclaredFields()) {
            Class<?> type = field.getType();
            require(type == ManagedDispatchAuthority.class || type == Thread.class
                    || type == Object.class || type == int.class || type == boolean.class,
                    "call holds only lifetime metadata");
            require(!field.getName().equals("data") && !field.getName().equals("reply"),
                    "no packet field");
        }
        require(Modifier.isFinal(ManagedDispatchAuthority.class.getModifiers()), "final owner");
        call.close();
    }

    public static void main(String[] args) throws Throwable {
        basicLifetime();
        boundArgumentsAndThread();
        exceptionsAndReentry();
        retireDuringAdmission(0);
        retireDuringAdmission(1);
        retireDuringAdmission(2);
        concurrentOriginalWork();
        statelessPacketShape();
        System.out.println("{\"pass\":true,\"checks\":" + checks
                + ",\"androidExecuted\":false,\"oemExecuted\":false}");
    }
}
