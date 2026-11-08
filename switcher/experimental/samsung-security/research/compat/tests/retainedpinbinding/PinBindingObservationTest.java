package model;

import android.content.pm.UserInfo;
import android.os.Looper;
import com.android.internal.os.ZygoteInit;
import com.android.server.LocalServices;
import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;

/** Only authored model objects and the retained host capture classes. */
public final class PinBindingObservationTest {
    private static final String PREFIX = "com.appleexploit.oneos.security.authority.";
    private static final String DRIFT = "physical user registry record changed";
    private static final int SERIAL = 41;

    private final Method init;
    private final Method expected;
    private final Method locks;
    private final Method makeRegistry;
    private final Method makeFamily;
    private final Method makeBinding;
    private final Method checkBinding;

    private PinBindingObservationTest(ClassLoader service, ClassLoader module) throws Exception {
        Class<?> world = Class.forName("com.android.server.PinBindingWorld", true, service);
        Class<?> registry = module.loadClass(PREFIX + "PreparedRetainedUserRegistryCapture");
        Class<?> family = module.loadClass(PREFIX + "PreparedRetainedSecurityFamilyCapture");
        Class<?> binding = module.loadClass(PREFIX + "PreparedRetainedPinBinding");
        require(world.getClassLoader() == service && registry.getClassLoader() == module
                && family.getClassLoader() == module && binding.getClassLoader() == module,
                "model loader placement changed");
        init = world.getMethod("init", int.class, int.class, int.class);
        expected = world.getMethod("expected");
        locks = world.getMethod("locks");
        makeRegistry = registry.getMethod("captureExisting");
        makeFamily = family.getMethod("captureExisting", registry);
        makeBinding = binding.getMethod("captureExisting", registry, family);
        checkBinding = binding.getMethod("checkStillBound");
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static Object call(Method method, Object receiver, Object... args) throws Throwable {
        try {
            return method.invoke(receiver, args);
        } catch (InvocationTargetException failure) {
            throw failure.getCause();
        }
    }

    private static void requireDrift(IllegalStateException failure) {
        require(DRIFT.equals(failure.getMessage()), "refused for a different reason: " + failure);
    }

    private int observe(boolean capture, int mutateAt, boolean expectRefusal) throws Throwable {
        call(init, null, 3, SERIAL, 3);
        Object registry = call(makeRegistry, null);
        Object family = call(makeFamily, null, registry);
        Object binding = capture ? null : call(makeBinding, null, registry, family);
        Object[] monitors = (Object[]) call(locks, null);
        UserInfo info = (UserInfo) ((Object[]) call(expected, null))[4];
        int[] callbacks = {0};
        int[] mutations = {0};
        int forbidden = Forbidden.calls;
        int constructed = Forbidden.constructions;

        LocalServices.modelObserver = () -> {
            require(!Thread.holdsLock(monitors[0]) && !Thread.holdsLock(monitors[1]),
                    "control lookup entered under a subject monitor");
            callbacks[0]++;
            if (callbacks[0] == mutateAt) {
                synchronized (monitors[1]) {
                    require(info.serialNumber == SERIAL, "the actual model record changed early");
                    info.serialNumber++;
                    mutations[0]++;
                }
            }
        };
        boolean refused = false;
        try {
            if (capture) binding = call(makeBinding, null, registry, family);
            else call(checkBinding, binding);
        } catch (IllegalStateException failure) {
            requireDrift(failure);
            refused = true;
        } finally {
            LocalServices.modelObserver = null;
        }

        require(refused == expectRefusal, "unexpected return/refusal at the final callback");
        require(Forbidden.calls == forbidden && Forbidden.constructions == constructed,
                "the observation invoked a forbidden model method or constructed a backend");
        require(callbacks[0] > 1, "expected multiple control lookups");
        require(mutations[0] == (mutateAt == 0 ? 0 : 1), "expected one selected mutation");
        require(((Object[]) call(expected, null))[4] == info
                && info.serialNumber == SERIAL + mutations[0], "the retained record or mutation changed");
        if (mutateAt != 0) {
            require(callbacks[0] == mutateAt, "mutation was not at the final control lookup");
            if (!refused) {
                // The baseline returned normally even though the identical record had drifted.
                require(binding != null, "accepted operation has no retained binding");
                try {
                    call(checkBinding, binding);
                    throw new AssertionError("the stale baseline binding failed to detect later readback");
                } catch (IllegalStateException failure) {
                    requireDrift(failure);
                }
            }
        }
        return callbacks[0];
    }

    public static void main(String[] args) throws Throwable {
        require(args.length == 4, "service, binding, dependencies, mode required");
        boolean successor = "successor".equals(args[3]);
        require(successor || "baseline".equals(args[3]), "unknown test mode");
        ClassLoader parent = PinBindingObservationTest.class.getClassLoader();
        URL service = new File(args[0]).toURI().toURL();
        URL binding = new File(args[1]).toURI().toURL();
        URL dependencies = new File(args[2]).toURI().toURL();
        Thread main = Thread.currentThread();
        ClassLoader previous = main.getContextClassLoader();
        try (URLClassLoader services = new URLClassLoader(new URL[]{service}, parent);
             URLClassLoader module = new URLClassLoader(new URL[]{binding, dependencies}, parent)) {
            main.setContextClassLoader(services);
            ZygoteInit.modelSet(services);
            Looper.main = new Looper(main);
            PinBindingObservationTest test = new PinBindingObservationTest(services, module);
            int capture = test.observe(true, 0, false);
            test.observe(true, capture, successor);
            int check = test.observe(false, 0, false);
            test.observe(false, check, successor);
            System.out.println(args[3] + " capture=" + capture + " check=" + check
                    + (successor ? " both=REFUSED" : " both=ACCEPTED_STALE"));
        } finally {
            main.setContextClassLoader(previous);
        }
    }
}
