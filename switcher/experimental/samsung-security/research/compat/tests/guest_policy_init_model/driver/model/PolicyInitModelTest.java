package model;

import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** JDK-only authored fixture driver. No Android/OEM implementation is executed. */
public final class PolicyInitModelTest {
    private static final String PREFIX="com.appleexploit.oneos.security.authority.";
    private static int checks;
    private static void yes(boolean value,String detail){checks++;if(!value)throw new AssertionError(detail);}
    private static Object call(Object receiver,String name,Object...args)throws Throwable{
        Class<?> type=receiver instanceof Class?(Class<?>)receiver:receiver.getClass();
        Method selected=null;
        for(Method method:type.getMethods())if(method.getName().equals(name)&&method.getParameterCount()==args.length){
            if(selected!=null)throw new AssertionError("ambiguous public fixture API: "+name);selected=method;
        }
        if(selected==null)throw new AssertionError("missing public API: "+name);
        try{return selected.invoke(receiver instanceof Class?null:receiver,args);}
        catch(InvocationTargetException failure){throw failure.getCause();}
    }
    private static void refused(Object receiver,String name,Object...args)throws Throwable{
        try{call(receiver,name,args);}catch(IllegalStateException expected){yes(true,"public refusal");return;}
        throw new AssertionError("expected public refusal: "+name);
    }
    private static URL url(String value)throws Exception{return new File(value).toURI().toURL();}
    private static Throwable cleanup(Throwable primary,AutoCloseable value){
        if(value==null)return primary;
        try{value.close();}catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}
        return primary;
    }
    private static final class World implements AutoCloseable {
        final ClassLoader prior=Thread.currentThread().getContextClassLoader();
        URLClassLoader framework,core,vendor;
        Class<?> helper,graph,control,frameworkControl;
        Object fixture,owner;
        final java.util.ArrayList<Worker> workers=new java.util.ArrayList<Worker>();
        World(String[] paths)throws Throwable{
            try{
                framework=new URLClassLoader(new URL[]{url(paths[1])},ClassLoader.getPlatformClassLoader());
                core=new URLClassLoader(new URL[]{url(paths[0]),url(paths[2])},framework);
                vendor=new URLClassLoader(new URL[]{url(paths[3])},core);
                frameworkControl=Class.forName("fixture.FrameworkControl",true,framework);
                call(frameworkControl,"initialize",core,Thread.currentThread());
                Thread.currentThread().setContextClassLoader(core);
                helper=Class.forName(PREFIX+"PreparedGuestPolicyInitCompletion",true,core);
                graph=Class.forName(PREFIX+"PreparedGuestKeyguardGraphCapture",false,core);
                control=Class.forName("fixture.PolicyControl",true,core);
                yes(helper.getClassLoader()==core&&graph.getClassLoader()==core,"fresh helper and Graph SAME C");
                yes(Class.forName("com.android.server.policy.WindowManagerPolicy",false,core).getClassLoader()==core,"typed policy C");
                yes(Class.forName("android.view.WindowManagerPolicyConstants",false,core).getClassLoader()==framework,"policy parent interface F");
            }catch(Throwable failure){
                try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable error){if(error!=failure)failure.addSuppressed(error);}
                failure=cleanup(failure,vendor);failure=cleanup(failure,core);failure=cleanup(failure,framework);throw failure;
            }
        }
        void prepare()throws Throwable{owner=call(helper,"prepareExisting");}
        void world()throws Throwable{
            fixture=Class.forName("fixture.PolicyWorld",true,vendor).getConstructor().newInstance();
            yes(fixture.getClass().getClassLoader()==vendor&&vendor!=core,"distinct modeled vendor loader");
        }
        Object[] args()throws Throwable{return(Object[])call(fixture,"arguments");}
        Object capture()throws Throwable{return call(graph,"captureExisting");}
        void mode(String value)throws Exception{control.getField("mode").set(null,value);}
        int calls()throws Exception{return control.getField("calls").getInt(null);}
        void sentinel(Throwable value)throws Exception{control.getField("sentinel").set(null,value);}
        CountDownLatch latch(String name)throws Exception{return(CountDownLatch)control.getField(name).get(null);}
        Worker start(boolean controlCheck)throws Throwable{
            Worker worker=new Worker(this,controlCheck);workers.add(worker);worker.thread.start();return worker;
        }
        Worker invoke()throws Throwable{Worker worker=start(false);worker.finish();return worker;}
        void normal()throws Throwable{Worker result=invoke();yes(result.failure==null,"normal original return");}
        void bind(Object value)throws Throwable{call(owner,"bindGraph",value);}
        void current()throws Throwable{call(owner,"checkStillBound");}
        @Override public void close()throws Exception{
            Throwable failure=null;
            try{latch("release").countDown();}catch(Throwable error){failure=error;}
            for(Worker worker:workers){try{worker.thread.join(1500);if(worker.thread.isAlive())throw new AssertionError("model worker did not stop");}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}}
            if(owner!=null){try{call(owner,"close");}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}}
            try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}
            failure=cleanup(failure,vendor);failure=cleanup(failure,core);failure=cleanup(failure,framework);
            if(failure instanceof Error)throw(Error)failure;if(failure instanceof Exception)throw(Exception)failure;if(failure!=null)throw new AssertionError(failure);
        }
    }
    private static final class Worker implements Runnable {
        final World world;final boolean controlCheck;final Thread thread;
        volatile Throwable failure;
        Worker(World world,boolean controlCheck){this.world=world;this.controlCheck=controlCheck;thread=new Thread(this,"authored-policy-ui");thread.setDaemon(true);}
        @Override public void run(){ClassLoader prior=Thread.currentThread().getContextClassLoader();try{
            Thread.currentThread().setContextClassLoader(world.core);
            call(Class.forName("android.os.Looper",false,world.framework),"attachCurrentThread");
            if(controlCheck)call(world.owner,"checkStillBound");else call(world.helper,"invokeOriginal",world.args());
        }catch(Throwable error){failure=error;}finally{try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}}}
        void finish()throws InterruptedException{thread.join(1500);yes(!thread.isAlive(),"bounded authored worker finish");}
    }
    private static final class ReleaseGuard implements Runnable {
        final CountDownLatch closed=new CountDownLatch(1),release;
        volatile boolean timedOut;
        ReleaseGuard(CountDownLatch release){this.release=release;}
        @Override public void run(){try{if(!closed.await(750,TimeUnit.MILLISECONDS)){timedOut=true;release.countDown();}}catch(InterruptedException error){Thread.currentThread().interrupt();timedOut=true;release.countDown();}}
    }
    private static final class GraphReentry implements Runnable {
        final World world;boolean fired;
        GraphReentry(World world){this.world=world;}
        @Override public void run(){fired=true;try{Worker second=world.invoke();if(second.failure!=null)throw new AssertionError(second.failure);}catch(Throwable error){throw new AssertionError(error);}}
    }
    private static void one(int id,String[] paths)throws Throwable{
        try(World w=new World(paths)){
            switch(id){
            case 0: // Metadata-only prepare succeeds before live WMS/Graph publication.
                w.prepare();yes(w.calls()==0,"prepare invokes no policy");w.world();w.normal();w.bind(w.capture());w.current();yes(w.calls()==1,"normal once");break;
            case 1: // A coherent graph is NOT a normal-return occurrence.
                w.prepare();w.world();call(w.fixture,"fixtureLinkWithoutInvocation");Object noEvent=w.capture();refused(w.owner,"bindGraph",noEvent);yes(w.calls()==0,"snapshot did not invoke init");break;
            case 2: // ABSENT still forwards and remembers first source entry.
                w.world();w.normal();yes(w.calls()==1,"absent original once");refused(w.helper,"prepareExisting");refused(w.helper,"prepareExisting");break;
            case 3:
            case 4:
            case 5: { // Exact RuntimeException, Error, and checked Throwable identity.
                w.prepare();w.world();Throwable original=id==3?new IllegalArgumentException("authored-runtime"):id==4?new AssertionError("authored-error"):new Exception("authored-checked");
                w.sentinel(original);w.mode(id==4?"THROW_BEFORE":"THROW_AFTER");Worker thrown=w.invoke();yes(thrown.failure==original,"exact original Throwable identity");yes(w.calls()==1,"throw original once");
                if(id==4)call(w.fixture,"fixtureLinkWithoutInvocation");refused(w.owner,"bindGraph",w.capture());break;
            }
            case 6: // Nested actual model originals both run; observer cannot issue.
                w.prepare();w.world();w.mode("REENTER_ONCE");w.normal();yes(w.calls()==2,"nested once per entry");refused(w.owner,"bindGraph",w.capture());break;
            case 7: { // close is logical-only and no owned lock spans the original.
                w.prepare();w.world();w.mode("BLOCK_FIRST");Worker first=w.start(false);yes(w.latch("entered").await(1,TimeUnit.SECONDS),"original entered");
                ReleaseGuard guard=new ReleaseGuard(w.latch("release"));Thread timer=new Thread(guard,"authored-close-bound");timer.setDaemon(true);timer.start();
                try{call(w.owner,"close");}finally{guard.closed.countDown();timer.join(1200);}
                yes(!timer.isAlive()&&!guard.timedOut,"close returned without original drain");yes(first.thread.isAlive(),"original remains active after logical close");
                Worker second=w.start(false);second.finish();yes(second.failure==null,"competing original forwards while first active");
                w.latch("release").countDown();first.finish();yes(first.failure==null&&w.calls()==2,"both originals once");refused(w.owner,"bindGraph",w.capture());break;
            }
            case 8:
                w.prepare();w.world();call(w.owner,"close");call(w.owner,"close");w.normal();yes(w.calls()==1,"closed still forwards");refused(w.owner,"bindGraph",w.capture());refused(w.helper,"prepareExisting");break;
            case 9: // Preserve Graph refs while injecting a duplicate actual call.
                w.prepare();w.world();w.normal();Object graph=w.capture();w.bind(graph);w.current();w.mode("KEEP_LINKS");w.normal();call(graph,"checkStillBound");refused(w.owner,"checkStillBound");yes(w.calls()==2,"duplicate original forwards");break;
            case 10:
                w.prepare();w.world();w.mode("DRIFT_AFTER");w.normal();call(w.fixture,"restorePolicy");refused(w.owner,"bindGraph",w.capture());yes(w.calls()==1,"post-normal source tuple drift sticky");break;
            case 11: { // Authored external dependency reentry, NOT Android Looper behavior.
                w.prepare();w.world();w.normal();Object reentryGraph=w.capture();w.mode("KEEP_LINKS");GraphReentry hook=new GraphReentry(w);call(w.frameworkControl,"armGraphHook",hook);
                refused(w.owner,"bindGraph",reentryGraph);yes(hook.fired&&w.calls()==2,"external Graph reentry reached original");call(reentryGraph,"checkStillBound");break;
            }
            case 12:
                w.prepare();w.world();w.normal();w.bind(w.capture());Worker wrong=w.start(true);wrong.finish();yes(wrong.failure instanceof IllegalStateException,"wrong control thread refused");w.current();yes(w.calls()==1,"wrong thread invokes no policy");break;
            case 13: {
                w.prepare();w.world();Worker actual=w.invoke();yes(actual.failure==null,"original normal");Object[] args=w.args();Object[] observed=(Object[])w.control.getField("lastArgs").get(null);
                yes(observed[0]==args[0]&&observed[1]==args[1]&&observed[2]==args[2],"exact original three arguments");yes(w.control.getField("lastThread").get(null)==actual.thread,"original stays on invocation thread");
                w.bind(w.capture());w.current();call(w.owner,"close");refused(w.owner,"checkStillBound");yes(w.calls()==1,"close does not reinvoke");break;
            }
            default:throw new AssertionError("unknown authored case");
            }
        }
    }
    public static void main(String[] paths)throws Throwable{
        if(paths.length!=4)throw new AssertionError("program5 framework core vendor paths required");
        for(int id=0;id<14;id++)one(id,paths);
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":14,\"checks\":"+checks+",\"sameCoreLoader\":true,\"distinctVendorLoader\":true}");
    }
}
