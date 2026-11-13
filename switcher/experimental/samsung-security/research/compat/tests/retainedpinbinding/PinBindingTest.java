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

/** Runs unchanged authored SDK classes against own synthetic F/C object worlds. */
public final class PinBindingTest {
    private static int checks, scenarios;
    private static URLClassLoader services;
    private static Class<?> world, registryType, familyType, bindingType;
    private static Method makeRegistry, makeFamily, makeBinding, checkBinding;
    private interface Work {void run() throws Throwable;}
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("synthetic check " + checks);
    }
    private static Object call(Method method, Object target, Object... args) throws Throwable {
        try {return method.invoke(target, args);}
        catch (InvocationTargetException failure) {throw failure.getCause();}
    }
    private static Object field(Object owner, String name) throws Exception {
        Field field = owner.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(owner);
    }
    private static Object world(String name, Class<?>[] signature, Object... args) throws Throwable {
        return call(world.getMethod(name, signature), null, args);
    }
    private static void init(int id, int serial, int state) throws Throwable {
        Thread.currentThread().setContextClassLoader(services);
        ZygoteInit.modelSet(services);
        Looper.main = new Looper(Thread.currentThread());
        LocalServices.modelObserver = null;
        world("init", new Class<?>[]{int.class, int.class, int.class}, id, serial, state);
    }
    private static void change(String key) throws Throwable {
        world("change", new Class<?>[]{String.class}, key);
    }
    private static Object[] captures() throws Throwable {
        Object registry = call(makeRegistry, null);
        return new Object[]{registry, call(makeFamily, null, registry)};
    }
    private static Object binding(Object[] pair) throws Throwable {return call(makeBinding, null, pair);}
    private static void live(Object binding) throws Throwable {call(checkBinding, binding);}
    private static void refused(Work work) throws Throwable {
        Throwable thrown = null;
        try {work.run();} catch (Throwable failure) {thrown = failure;}
        check(thrown instanceof IllegalStateException);
        check(Forbidden.calls == 0);
        check(world.getField("traps").getInt(null) == 0);
        scenarios++;
    }

    public static void main(String[] args) throws Throwable {
        ClassLoader framework = PinBindingTest.class.getClassLoader();
        services = new URLClassLoader(new URL[]{new File(args[3]).toURI().toURL()}, framework);
        world = Class.forName("com.android.server.PinBindingWorld", true, services);
        URLClassLoader module = new URLClassLoader(new URL[]{new File(args[0]).toURI().toURL(),
                new File(args[1]).toURI().toURL(), new File(args[2]).toURI().toURL()}, framework);
        String prefix = "com.appleexploit.oneos.security.authority.";
        registryType = Class.forName(prefix + "PreparedRetainedUserRegistryCapture", true, module);
        familyType = Class.forName(prefix + "PreparedRetainedSecurityFamilyCapture", true, module);
        bindingType = Class.forName(prefix + "PreparedRetainedPinBinding", true, module);
        makeRegistry = registryType.getMethod("captureExisting");
        makeFamily = familyType.getMethod("captureExisting", registryType);
        makeBinding = bindingType.getMethod("captureExisting", registryType, familyType);
        checkBinding = bindingType.getMethod("checkStillBound");

        for (int id : new int[]{0, 3, 7}) for (int state : new int[]{1, 3}) {
            init(id, 41 + id, state);
            Object[] pair = captures();
            int constructed = Forbidden.constructions;
            Object selected = binding(pair);
            live(selected);
            Object metadata = field(selected, "metadata");
            Object[] expected = (Object[]) world("expected", new Class<?>[0]);
            check(field(metadata, "registry") == pair[0] && field(metadata, "family") == pair[1]);
            check(field(metadata, "endpoint") == expected[0]);
            check(field(metadata, "ums") == expected[1] && field(metadata, "controller") == expected[2]);
            Object current = field(selected, "current"), subject = field(selected, "subject");
            check(field(subject, "data") == expected[3] && field(subject, "info") == expected[4]);
            check(field(current, "userState") == expected[5] && field(current, "handle") == expected[6]);
            check(((Integer) field(current, "id")) == id && ((Integer) field(subject, "serial")) == 41 + id);
            check(((Integer) field(current, "state")) == state);
            check(Forbidden.constructions == constructed && Forbidden.calls == 0);
            Field[] originals = (Field[]) field(metadata, "fields");
            int accessed = 0;
            for (Field original : originals) if (original.isAccessible()) accessed++;
            check(originals.length == 24 && accessed == 4);
            for (String name : new String[]{"familyOwnersField", "familyMetadataField", "pairedRegistryField", "registryOwnersField"})
                check(((Field) field(metadata, name)).isAccessible());
            scenarios++;
        }
        for (Method method : bindingType.getDeclaredMethods()) if (Modifier.isPublic(method.getModifiers()))
            check(method.getName().equals("captureExisting") || method.getName().equals("checkStillBound"));
        for (Field member : bindingType.getDeclaredFields())
            check(Modifier.isPrivate(member.getModifiers()) && Modifier.isFinal(member.getModifiers()));

        String[] changes = {"target", "current", "logout", "pending", "switching", "state:0", "state:2", "state:4", "state:5", "state:99",
                "state-record", "handle", "missing-state", "missing-user", "data-record", "info-record", "info-id", "serial", "negative-serial",
                "non-full", "profile", "disabled", "partial", "pre-created", "removing", "attributes", "group", "type", "null-type",
                "user-manager", "different-ums", "proxy-ums", "controller-lock", "users-lock", "started-container", "users-container",
                "removing-container", "queue-container", "trap-started", "trap-users", "trap-removing", "trap-queue"};
        for (String mutation : changes) {
            init(3, 41, 3);
            final Object selected = binding(captures());
            change(mutation);
            refused(new Work(){public void run() throws Throwable {live(selected);}});
        }
        // A late guard after monitor acquisition would wait for the helper's
        // timeout here. The selected contract refuses before entering old locks.
        for (int which = 0; which < 2; which++) {
            init(3, 41, 3);
            final Object selected = binding(captures());
            final Object retained = ((Object[]) world("locks", new Class<?>[0]))[which];
            change(which == 0 ? "controller-lock" : "users-lock");
            final java.util.concurrent.CountDownLatch held = new java.util.concurrent.CountDownLatch(1);
            final java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
            final java.util.concurrent.atomic.AtomicBoolean expired = new java.util.concurrent.atomic.AtomicBoolean();
            Thread holder = new Thread(new Runnable(){public void run(){
                synchronized(retained) {
                    held.countDown();
                    try {if (!release.await(3, java.util.concurrent.TimeUnit.SECONDS)) expired.set(true);}
                    catch (InterruptedException failure) {expired.set(true);Thread.currentThread().interrupt();}
                }
            }});
            holder.start();
            try {
                check(held.await(3, java.util.concurrent.TimeUnit.SECONDS));
                refused(new Work(){public void run() throws Throwable {live(selected);}});
                check(!expired.get());
            } finally {
                release.countDown(); holder.join(3000); check(!holder.isAlive());
            }
        }
        String[] initial = {"target", "logout", "pending", "switching", "state:0", "state:2", "state:4", "state:5", "state:99",
                "handle", "missing-state", "missing-user", "info-id", "negative-serial", "non-full", "profile", "disabled", "partial",
                "pre-created", "removing", "null-type", "different-ums", "proxy-ums", "trap-started", "trap-users", "trap-removing", "trap-queue"};
        for (String mutation : initial) {
            init(3, 41, 1);
            final Object[] pair = captures();
            change(mutation);
            refused(new Work(){public void run() throws Throwable {binding(pair);}});
        }

        init(3, 41, 3);
        final Object firstRegistry = call(makeRegistry, null), secondRegistry = call(makeRegistry, null);
        final Object secondFamily = call(makeFamily, null, secondRegistry);
        refused(new Work(){public void run() throws Throwable {call(makeBinding, null, firstRegistry, secondFamily);}});

        init(3, 41, 3);
        final Object selected = binding(captures());
        final Throwable[] result = new Throwable[1];
        Thread foreign = new Thread(new Runnable(){public void run(){try {live(selected);} catch(Throwable failure){result[0]=failure;}}});
        foreign.start(); foreign.join(3000);
        check(!foreign.isAlive() && result[0] instanceof IllegalStateException); scenarios++;

        init(3, 41, 3);
        final Object checked = binding(captures());
        final Object[] locks = (Object[]) world("locks", new Class<?>[0]);
        LocalServices.modelObserver = new Runnable(){public void run(){
            if (Thread.holdsLock(locks[0]) || Thread.holdsLock(locks[1])) throw new AssertionError("control nested in subject monitor");
        }};
        live(checked); LocalServices.modelObserver = null; scenarios++;

        init(3, 41, 3);
        final Object drift = binding(captures());
        LocalServices.modelObserver = new Runnable(){public void run(){LocalServices.modelObserver=null;
            try {change("serial");} catch(Throwable failure){throw new AssertionError(failure);}}};
        refused(new Work(){public void run() throws Throwable {live(drift);}});
        LocalServices.modelObserver = null;

        init(3, 41, 3);
        final Object[] coherent = captures();
        final URL ownUrl = new File(args[0]).toURI().toURL();
        URLClassLoader foreignModule = new URLClassLoader(new URL[]{ownUrl}, module){
            @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
                if (name.startsWith("com.appleexploit.oneos.security.authority.PreparedRetainedPinBinding")) {
                    Class<?> value=findLoadedClass(name);if(value==null)value=findClass(name);if(resolve)resolveClass(value);return value;
                }return super.loadClass(name,resolve);
            }};
        try {
            final Method foreignFactory=Class.forName(bindingType.getName(),true,foreignModule).getMethod("captureExisting",registryType,familyType);
            refused(new Work(){public void run() throws Throwable {call(foreignFactory,null,coherent);}});
        } finally {foreignModule.close();}
        check(Forbidden.calls == 0);
        System.out.println("{\"pass\":true,\"checks\":"+checks+",\"scenarios\":"+scenarios+",\"modeledOnly\":true}");
    }
}
