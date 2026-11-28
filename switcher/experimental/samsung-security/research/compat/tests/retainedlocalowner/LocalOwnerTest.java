package model;

import android.os.Looper;
import android.util.ArrayMap;
import com.android.internal.os.ZygoteInit;
import com.android.server.LocalServices;
import java.io.File;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Exact SDK classes with authored Java metadata models; no Android/OEM/native runtime. */
public final class LocalOwnerTest {
    private static int checks, scenarios;
    private static Class<?> world, registryType, familyType, ownerType;
    private static URLClassLoader services, module;
    private static Method registryCapture, familyCapture, ownerCapture, current;

    private interface Action { void run() throws Throwable; }
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("authored local-owner check " + checks);
    }
    private static Object call(Method method, Object receiver, Object... args) throws Throwable {
        try { return method.invoke(receiver, args); }
        catch (InvocationTargetException failure) { throw failure.getCause(); }
    }
    private static Object world(String name, Class<?>[] types, Object... args) throws Throwable {
        return call(world.getMethod(name, types), null, args);
    }
    private static Object world(String name) throws Throwable { return world(name, new Class<?>[0]); }
    private static Object field(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }
    private static Object registry() throws Throwable { return call(registryCapture, null); }
    private static Object family(Object registry) throws Throwable { return call(familyCapture, null, registry); }
    private static Object capture(Object registry, Object family) throws Throwable {
        return call(ownerCapture, null, registry, family);
    }
    private static void live(Object owner) throws Throwable { call(current, owner); }
    private static Throwable failure(Action action) {
        try { action.run(); } catch (Throwable value) { return value; }
        throw new AssertionError("refusal expected");
    }
    private static void refuse(Action action) {
        check(failure(action) instanceof IllegalStateException); scenarios++;
    }
    private static void change(String kind) throws Throwable {
        world("change", new Class<?>[]{String.class}, kind);
    }
    private static void init() throws Throwable {
        Thread.currentThread().setContextClassLoader(services);
        ZygoteInit.modelSet(services);
        Looper.main = new Looper(Thread.currentThread());
        LocalServices.modelObserver = null;
        world("init");
        check(Forbidden.calls == 0);
    }
    private static Object[] sample() throws Throwable { return (Object[])world("expected"); }

    public static void main(String[] args) throws Throwable {
        check(args.length == 3);
        ClassLoader base = LocalOwnerTest.class.getClassLoader();
        services = new URLClassLoader(new URL[]{new File(args[2]).toURI().toURL()}, base);
        world = Class.forName("com.android.server.LocalOwnerWorld", true, services);
        module = new URLClassLoader(new URL[]{new File(args[0]).toURI().toURL(),
                new File(args[1]).toURI().toURL()}, base);
        registryType = Class.forName("com.appleexploit.oneos.security.authority.PreparedRetainedUserRegistryCapture", true, module);
        familyType = Class.forName("com.appleexploit.oneos.security.authority.PreparedRetainedSecurityFamilyCapture", true, module);
        ownerType = Class.forName("com.appleexploit.oneos.security.authority.PreparedRetainedLockSettingsLocalOwner", true, module);
        registryCapture = registryType.getMethod("captureExisting");
        familyCapture = familyType.getMethod("captureExisting", registryType);
        ownerCapture = ownerType.getMethod("captureExisting", registryType, familyType);
        current = ownerType.getMethod("checkStillBound");

        init();
        Object anchor = registry(), family = family(anchor);
        int constructions = Forbidden.constructions;
        Object owner = capture(anchor, family);
        live(owner);
        Object[] expected = sample(), retained = (Object[])field(owner, "owners");
        check(retained.length == 3);
        for (int index=0; index<3; index++) check(retained[index] == expected[index]);
        Object metadata = field(owner, "metadata");
        check(field(metadata, "registry") == anchor && field(metadata, "family") == family);
        check(field(metadata, "realm") == services);
        check(field(metadata, "map") == expected[0]);
        check(((Field)field(metadata, "mapField")).isAccessible());
        check(!((Field)field(metadata, "parentField")).isAccessible());
        Field parent = (Field)field(metadata, "parentField");
        check(parent.getModifiers() == 0x1001 && parent.isSynthetic());
        live(owner);
        check(field(owner, "metadata") == metadata);
        check(Forbidden.constructions == constructions && Forbidden.calls == 0);
        for (Method method : ownerType.getDeclaredMethods()) if (Modifier.isPublic(method.getModifiers()))
            check(method.getName().equals("captureExisting") || method.getName().equals("checkStillBound"));
        for (Field value : ownerType.getDeclaredFields())
            check(Modifier.isPrivate(value.getModifiers()) && Modifier.isFinal(value.getModifiers()));
        scenarios++;

        // Registry and Family controls must run outside the retained map monitor.
        final Object actualMap = expected[0];
        final int[] outside = new int[1];
        LocalServices.modelObserver = new Runnable() { public void run() {
            if (Thread.holdsLock(actualMap)) throw new AssertionError("external anchor under local map");
            outside[0]++;
        }};
        live(owner);
        check(outside[0] > 0 && Forbidden.calls == 0);
        LocalServices.modelObserver = null; scenarios++;

        for (String kind : new String[]{"missing","wrong-key","wrong-class","null-parent","other-parent"}) {
            init(); final Object r = registry(), f = family(r); change(kind);
            refuse(new Action() { public void run() throws Throwable { capture(r,f); }});
        }
        for (String kind : new String[]{"missing","wrong-key","wrong-class","null-parent","other-parent","same-parent-new-local"}) {
            init(); Object r = registry(); final Object o = capture(r,family(r)); change(kind);
            refuse(new Action() { public void run() throws Throwable { live(o); }});
        }

        // A foreign realm's same-named Class is not the actual key.
        init(); final Object namesR = registry(), namesF = family(namesR);
        try (URLClassLoader namesake = new URLClassLoader(new URL[]{new File(args[2]).toURI().toURL()},base)) {
            Class<?> foreignKey = Class.forName("com.android.server.locksettings.LockSettingsInternal",false,namesake);
            Class<?> genuineKey = (Class<?>)field(field(capture(namesR,namesF),"metadata"),"key");
            check(foreignKey != genuineKey && foreignKey.getName().equals(genuineKey.getName()));
            synchronized(LocalServices.modelMap()) {
                Object value=LocalServices.entries.remove(genuineKey);LocalServices.entries.put(foreignKey,value);
            }
            refuse(new Action() { public void run() throws Throwable { capture(namesR,namesF); }});
        }

        init(); final Object registryA=registry(), registryB=registry(), familyA=family(registryA);
        check(registryA != registryB);
        refuse(new Action() { public void run() throws Throwable { capture(registryB,familyA); }});

        // Strictly model-only Unsafe swap of the authored static-final field.
        // The replacement is held by another thread. It must not be locked by check.
        init(); Object r=registry(); final Object old=capture(r,family(r));
        final ArrayMap<Class<?>,Object> before=LocalServices.modelMap();
        final ArrayMap<Class<?>,Object> replacement=new ArrayMap<Class<?>,Object>();replacement.putAll(before);
        final CountDownLatch held=new CountDownLatch(1), release=new CountDownLatch(1);
        final AtomicBoolean holderLeft=new AtomicBoolean();
        Thread holder=new Thread(new Runnable() { public void run() {
            synchronized(replacement) {
                held.countDown();
                try { if(!release.await(3,TimeUnit.SECONDS)) throw new AssertionError("fixture holder timeout"); }
                catch(InterruptedException failure) {throw new AssertionError(failure);}
                finally {holderLeft.set(true);}
            }
        }},"authored-replacement-map-holder");
        holder.start();
        try {
            check(held.await(2,TimeUnit.SECONDS));
            FixtureMapAccess.replace(before,replacement);
            refuse(new Action() { public void run() throws Throwable { live(old); }});
            check(!holderLeft.get());
        } finally {
            try {
                if(LocalServices.modelMap()==replacement) FixtureMapAccess.replace(replacement,before);
                else if(LocalServices.modelMap()!=before) throw new AssertionError("unexpected authored map owner");
            } finally {
                release.countDown();holder.join(2000);check(!holder.isAlive());
            }
        }
        check(FixtureMapAccess.swaps == 2); live(old);

        // Force the last outside anchor to BLOCK on the actual modeled user lock.
        // Mutate only the modeled map while it is blocked, then release the owner.
        // No production callback/field or alternate owner implementation is inserted.
        blockedDrift(false);
        blockedDrift(true);

        init(); Object errorR=registry(); final Object errorOwner=capture(errorR,family(errorR));
        final RuntimeException runtime=new RuntimeException("authored map failure");
        LocalServices.modelLocalFault=runtime;
        check(failure(new Action(){public void run()throws Throwable{live(errorOwner);}})==runtime);scenarios++;
        final Error error=new AssertionError("authored map error");LocalServices.modelLocalFault=error;
        check(failure(new Action(){public void run()throws Throwable{live(errorOwner);}})==error);scenarios++;

        init(); final Object threadR=registry(), threadF=family(threadR), threadO=capture(threadR,threadF);
        final Throwable[] wrong=new Throwable[2];
        Thread worker=new Thread(new Runnable(){public void run(){
            wrong[0]=failure(new Action(){public void run()throws Throwable{capture(threadR,threadF);}});
            wrong[1]=failure(new Action(){public void run()throws Throwable{live(threadO);}});
        }},"authored-wrong-control-thread");
        worker.start();worker.join(2000);
        check(!worker.isAlive() && wrong[0] instanceof IllegalStateException && wrong[1] instanceof IllegalStateException);scenarios+=2;
        init(); final Object loaderR=registry(),loaderF=family(loaderR);
        try(URLClassLoader foreignModule=new URLClassLoader(new URL[]{new File(args[0]).toURI().toURL()},module){
            @Override protected Class<?> loadClass(String name,boolean resolve)throws ClassNotFoundException{
                if(name.startsWith("com.appleexploit.oneos.security.authority.PreparedRetainedLockSettingsLocalOwner")){
                    Class<?> value=findLoadedClass(name);if(value==null)value=findClass(name);
                    if(resolve)resolveClass(value);return value;
                }
                return super.loadClass(name,resolve);
            }
        }){
            final Method foreignCapture=Class.forName(ownerType.getName(),true,foreignModule)
                    .getMethod("captureExisting",registryType,familyType);
            refuse(new Action(){public void run()throws Throwable{call(foreignCapture,null,loaderR,loaderF);}});
        }
        init(); final Object ctxR=registry(),ctxO=capture(ctxR,family(ctxR));Thread.currentThread().setContextClassLoader(null);
        refuse(new Action(){public void run()throws Throwable{live(ctxO);}});
        init(); final Object loopR=registry(),loopO=capture(loopR,family(loopR));Looper.main=null;
        refuse(new Action(){public void run()throws Throwable{live(loopO);}});
        refuse(new Action(){public void run()throws Throwable{capture(null,null);}});
        check(Forbidden.calls==0);
        module.close();services.close();
        System.out.println("{\"pass\":true,\"checks\":"+checks+",\"scenarios\":"+scenarios
                +",\"modeledOnly\":true,\"fixtureStaticFinalMapSwaps\":"+FixtureMapAccess.swaps+"}");
    }

    private static void blockedDrift(final boolean parent) throws Throwable {
        init(); Object r=registry();final Object o=capture(r,family(r));
        final Object lock=world("userLock"), map=LocalServices.modelMap();
        final Thread main=Thread.currentThread();
        final CountDownLatch held=new CountDownLatch(1), start=new CountDownLatch(1);
        final AtomicBoolean blocked=new AtomicBoolean(), left=new AtomicBoolean(), installed=new AtomicBoolean();
        final Throwable[] foreign=new Throwable[1];
        LocalServices.modelLocalLookups=0;
        final Thread holder=new Thread(new Runnable(){public void run(){
            try {
                if(!start.await(2,TimeUnit.SECONDS))throw new AssertionError("fixture schedule not reached");
                synchronized(lock){
                    held.countDown();
                    long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(2);
                    while(System.nanoTime()<end){
                        ThreadInfo info=ManagementFactory.getThreadMXBean().getThreadInfo(main.getId());
                        if(info!=null && info.getThreadState()==Thread.State.BLOCKED && info.getLockInfo()!=null
                                && info.getLockInfo().getIdentityHashCode()==System.identityHashCode(lock)){
                            blocked.set(true);break;
                        }
                        Thread.yield();
                    }
                    if(!blocked.get())throw new AssertionError("real modeled user-lock block not observed");
                    world(parent?"replaceParent":"replaceLocal");
                }
            }catch(Throwable failure){foreign[0]=failure;}finally{left.set(true);}
        }},"authored-late-anchor-drift");
        LocalServices.modelObserver=new Runnable(){public void run(){
            if(Thread.holdsLock(map))throw new AssertionError("outside anchor under map");
            // Four stable local samples precede the public check's last anchor.
            if(LocalServices.modelLocalLookups>=4 && installed.compareAndSet(false,true)){
                start.countDown();
                try{if(!held.await(2,TimeUnit.SECONDS))throw new AssertionError("fixture holder not entered");}
                catch(InterruptedException failure){throw new AssertionError(failure);}
            }
        }};
        holder.start();
        try { refuse(new Action(){public void run()throws Throwable{live(o);}}); }
        finally {start.countDown();holder.join(2500);LocalServices.modelObserver=null;}
        check(!holder.isAlive() && left.get() && blocked.get() && installed.get());
        if(foreign[0]!=null)throw foreign[0];
        check(LocalServices.modelLocalLookups==5);
    }
}
