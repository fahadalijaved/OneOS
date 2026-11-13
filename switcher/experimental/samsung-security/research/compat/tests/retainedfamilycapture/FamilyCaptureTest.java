package model;

import android.os.Looper;
import com.android.internal.os.ZygoteInit;
import com.android.server.LocalServices;
import java.io.File;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;

/** Executes exact authored SDK-compiled capture bytes with explicitly authored worlds. */
public final class FamilyCaptureTest {
    private static int checks, scenarios;
    private static CountingLoader services;
    private static Class<?> world, registryType, familyType;
    private static Method registryCapture, familyCapture, current;

    private interface Action { void run() throws Throwable; }
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("authored check " + checks);
    }
    private static Object call(Method method, Object receiver, Object... arguments) throws Throwable {
        try { return method.invoke(receiver, arguments); }
        catch (InvocationTargetException failure) { throw failure.getCause(); }
    }
    private static Object world(String name, Class<?>[] types, Object... arguments) throws Throwable {
        return call(world.getMethod(name, types), null, arguments);
    }
    private static Object world(String name) throws Throwable { return world(name, new Class<?>[0]); }
    private static void init() throws Throwable {
        Thread.currentThread().setContextClassLoader(services);
        ZygoteInit.modelSet(services);
        Looper.main = new Looper(Thread.currentThread());
        LocalServices.modelObserver = null;
        world("init");
        check(Forbidden.calls == 0);
    }
    private static Object registry() throws Throwable { return call(registryCapture, null); }
    private static Object capture(Object registry) throws Throwable { return call(familyCapture, null, registry); }
    private static void live(Object capture) throws Throwable { call(current, capture); }
    private static Throwable failure(Action action) {
        try { action.run(); } catch (Throwable thrown) { return thrown; }
        throw new AssertionError("refusal expected");
    }
    private static void refuse(Action action) {
        check(failure(action) instanceof IllegalStateException);
        scenarios++;
    }
    private static Object field(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }
    private static void change(String key) throws Throwable {
        world("change", new Class<?>[]{String.class}, key);
    }

    public static void main(String[] arguments) throws Throwable {
        final ClassLoader base = FamilyCaptureTest.class.getClassLoader();
        services = new CountingLoader(new File(arguments[2]).toURI().toURL(), base);
        world = Class.forName("com.android.server.FamilyWorld", true, services);
        final URLClassLoader module = new URLClassLoader(new URL[]{
                new File(arguments[0]).toURI().toURL(), new File(arguments[1]).toURI().toURL()}, base);
        registryType = Class.forName("com.appleexploit.oneos.security.authority.PreparedRetainedUserRegistryCapture", true, module);
        familyType = Class.forName("com.appleexploit.oneos.security.authority.PreparedRetainedSecurityFamilyCapture", true, module);
        registryCapture = registryType.getMethod("captureExisting");
        familyCapture = familyType.getMethod("captureExisting", registryType);
        current = familyType.getMethod("checkStillBound");

        init();
        Object anchor = registry();
        int constructions = Forbidden.constructions;
        Object first = capture(anchor);
        live(first);
        check(Forbidden.constructions == constructions && Forbidden.calls == 0);
        Object[] expected = (Object[]) world("expected");
        Object[] retained = (Object[]) field(first, "owners");
        check(retained.length == 19 && expected.length == 19);
        for (int index = 0; index < expected.length; index++) check(retained[index] == expected[index]);
        Object metadata = field(first, "metadata");
        check(field(metadata, "registry") == anchor);
        check(field(metadata, "realm") == services);
        check(field(metadata, "manager") == fieldStatic("com.android.server.World", "m"));
        Field[] fields = (Field[]) field(metadata, "fields");
        check(fields.length == 30);
        int accessible = 0;
        for (Field value : fields) if (value.isAccessible()) accessible++;
        check(accessible == 6);
        int loadCount = services.loads;
        live(first);
        check(field(first, "metadata") == metadata && field(metadata, "fields") == fields);
        check(services.loads == loadCount);
        for (Method method : familyType.getDeclaredMethods()) {
            if (Modifier.isPublic(method.getModifiers())) check(method.getName().equals("captureExisting")
                    || method.getName().equals("checkStillBound"));
        }
        for (Field value : familyType.getDeclaredFields()) check(Modifier.isPrivate(value.getModifiers())
                && Modifier.isFinal(value.getModifiers()));
        scenarios++;

        // Poisoned provider/native getters and service constructors remain untouched by checks.
        final Object lock = expected[13];
        LocalServices.modelObserver = new Runnable() {
            public void run() {
                if (Thread.holdsLock(lock)) throw new AssertionError("anchor nested in source monitor");
            }
        };
        live(first);
        check(Forbidden.constructions == constructions && Forbidden.calls == 0);
        LocalServices.modelObserver = null;
        scenarios++;

        String[] changes = {"missing-lss","missing-sms","missing-fp","missing-bio","missing-auth",
                "duplicate","null-entry","list-replaced","list-subclass","list-linked","lss-null",
                "lss-replaced","sms-null","strong","tracker","spm","store","context","spm-context",
                "store-context","strong-context","spm-store","marker-false","marker-created","marker-removed",
                "lock","storage-interface","lss-smi","smi-parent","sms-internal","fp-wrapper","fp-registry",
                "fp-parent","registry-wrapper","bio-wrapper","bio-parent","auth-wrapper","auth-parent",
                "auth-biometric","auth-null","cross-storage","phase","over-max"};
        for (String key : changes) {
            init(); final Object existing = capture(registry()); change(key);
            refuse(new Action() { public void run() throws Throwable { live(existing); } });
            check(Forbidden.calls == 0);
        }

        // Discriminating fresh-capture counterexample: same SSM/C, internally coherent A,
        // but the real registry capture retains B. A mere current-anchor check is insufficient.
        init(); final Object crossAnchor = registry(); change("cross-storage");
        refuse(new Action() { public void run() throws Throwable { capture(crossAnchor); } });

        init(); final Object listAnchor = registry(); change("list-subclass");
        refuse(new Action() { public void run() throws Throwable { capture(listAnchor); } });
        check(((Integer)world.getField("listCalls").get(null)) == 0);

        // A replaced monitor must be refused before attempting to acquire it.
        init(); final Object oldLockCapture = capture(registry()); change("lock");
        final Object foreignLock = ((Object[])world("expected"))[13];
        final java.util.concurrent.CountDownLatch held = new java.util.concurrent.CountDownLatch(1);
        final java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
        final java.util.concurrent.atomic.AtomicBoolean holderLeft = new java.util.concurrent.atomic.AtomicBoolean();
        Thread holder = new Thread(new Runnable() { public void run() {
            synchronized(foreignLock) {
                held.countDown();
                try { release.await(2,java.util.concurrent.TimeUnit.SECONDS); }
                catch(InterruptedException failure) { Thread.currentThread().interrupt(); }
                finally { holderLeft.set(true); }
            }
        }});
        holder.start();
        try {
            check(held.await(2,java.util.concurrent.TimeUnit.SECONDS));
            refuse(new Action() { public void run() throws Throwable { live(oldLockCapture); } });
            check(!holderLeft.get());
        } finally {
            release.countDown();holder.join(2000);
            check(!holder.isAlive());
        }

        init(); Object extras = capture(registry()); change("extra"); live(extras); scenarios++;
        init(); change("max"); Object maximum = capture(registry()); live(maximum); scenarios++;

        init(); final Object mainAnchor = registry(); final Object mainCapture = capture(mainAnchor);
        final Throwable[] foreign = new Throwable[2];
        Thread worker = new Thread(new Runnable() { public void run() {
            foreign[0] = failure(new Action() { public void run() throws Throwable { capture(mainAnchor); } });
            foreign[1] = failure(new Action() { public void run() throws Throwable { live(mainCapture); } });
        }});
        worker.start(); worker.join(2000);
        check(!worker.isAlive() && foreign[0] instanceof IllegalStateException
                && foreign[1] instanceof IllegalStateException); scenarios += 2;

        refuse(new Action() { public void run() throws Throwable { capture(null); } });
        init(); final Object cached = capture(registry());
        Thread.currentThread().setContextClassLoader(null);
        refuse(new Action() { public void run() throws Throwable { live(cached); } });
        init(); final Object lostLooper = capture(registry()); Looper.main = null;
        refuse(new Action() { public void run() throws Throwable { live(lostLooper); } });
        init(); final Object replacedAnchor = registry();
        Class<?> originalWorld = Class.forName("com.android.server.World", true, services);
        call(originalWorld.getMethod("install", boolean.class), null, true);
        refuse(new Action() { public void run() throws Throwable { capture(replacedAnchor); } });

        init(); final Object sourceAnchor = registry();
        final URL familyUrl = new File(arguments[0]).toURI().toURL();
        URLClassLoader foreignModule = new URLClassLoader(new URL[]{familyUrl}, module) {
            @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
                if (name.startsWith("com.appleexploit.oneos.security.authority.PreparedRetainedSecurityFamilyCapture")) {
                    Class<?> value = findLoadedClass(name);
                    if (value == null) value = findClass(name);
                    if (resolve) resolveClass(value);
                    return value;
                }
                return super.loadClass(name, resolve);
            }
        };
        final Method foreignCapture = Class.forName(familyType.getName(), true, foreignModule)
                .getMethod("captureExisting", registryType);
        refuse(new Action() { public void run() throws Throwable { call(foreignCapture, null, sourceAnchor); } });

        // Actual SDK class bytes remain the same; only authored source-world metadata varies.
        for (int index = 3; index < arguments.length; index++) {
            services = new CountingLoader(new File(arguments[index]).toURI().toURL(), base);
            world = Class.forName("com.android.server.FamilyWorld", true, services);
            init(); final Object variantAnchor = registry();
            refuse(new Action() { public void run() throws Throwable { capture(variantAnchor); } });
        }
        System.out.println("{\"pass\":true,\"checks\":" + checks + ",\"scenarios\":"
                + scenarios + ",\"modeledOnly\":true}");
    }

    private static Object fieldStatic(String name, String field) throws Exception {
        return Class.forName(name, true, services).getField(field).get(null);
    }

    private static final class CountingLoader extends URLClassLoader {
        int loads;
        CountingLoader(URL source, ClassLoader parent) {super(new URL[]{source}, parent);}
        @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            loads++;
            return super.loadClass(name, resolve);
        }
    }
}
