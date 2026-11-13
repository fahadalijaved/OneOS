package model;

import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Public production API + authored model controls only. No private helper reflection. */
public final class RetainedPinCheckTest {
    private static final String A="com.appleexploit.oneos.security.authority.";
    private static final String T="com.appleexploit.oneos.security.transport.";
    private static String[] paths;
    private static int checks, scenarios;
    private interface Action { Object run() throws Throwable; }
    private static synchronized void check(boolean value) { checks++;if(!value)throw new AssertionError("endpoint model check "+checks); }
    private static Object call(Method m,Object receiver,Object...args)throws Throwable {
        try{return m.invoke(receiver,args);}catch(InvocationTargetException e){throw e.getCause();}
    }
    private static Throwable failure(Action action)throws Throwable {
        try{action.run();}catch(Throwable t){return t;}throw new AssertionError("expected authored refusal");
    }
    private static Throwable preserve(Throwable primary,Throwable next) {
        if(primary==null)return next;if(primary!=next)try{primary.addSuppressed(next);}catch(Throwable ignored){}return primary;
    }
    @SuppressWarnings("unchecked") private static <E extends Throwable> void raise(Throwable t)throws E{throw(E)t;}
    private static final class Job {
        final AtomicReference<Object> result=new AtomicReference<Object>();
        final AtomicReference<Throwable> error=new AtomicReference<Throwable>();
        final Thread thread;
        Job(final Action action){thread=new Thread(new Runnable(){public void run(){try{result.set(action.run());}catch(Throwable t){error.set(t);}}},"authored-endpoint-worker");thread.setDaemon(true);}
        void join()throws InterruptedException{thread.join(4000);check(!thread.isAlive());}
    }
    private static final class World implements AutoCloseable {
        final ClassLoader previous=Thread.currentThread().getContextClassLoader();
        final List<Job> jobs=new ArrayList<Job>();
        final List<CountDownLatch> releases=new ArrayList<CountDownLatch>();
        URLClassLoader f,c,m;
        Class<?> graph,probe,checkProbe,ownerType,checkType,endpointType,clientType,pinType,responseType,control,binderType,interfaceType;
        Object owner,checkOwner,endpoint,client,guestPin,callback,bindingObject;
        World()throws Throwable {this(true);}
        World(boolean configured)throws Throwable {
            try{
                ClassLoader platform=RetainedPinCheckTest.class.getClassLoader().getParent();
                f=new URLClassLoader(new URL[]{new File(paths[2]).toURI().toURL()},platform);
                c=new URLClassLoader(new URL[]{new File(paths[3]).toURI().toURL()},f);
                m=new URLClassLoader(new URL[]{new File(paths[0]).toURI().toURL(),new File(paths[1]).toURI().toURL(),new File(paths[4]).toURI().toURL()},f);
                Thread.currentThread().setContextClassLoader(c);
                Class<?> z=Class.forName("com.android.internal.os.ZygoteInit",true,f);
                call(z.getMethod("modelSet",ClassLoader.class),null,c);
                Class<?> looper=Class.forName("android.os.Looper",true,f);
                looper.getField("main").set(null,looper.getConstructor(Thread.class).newInstance(Thread.currentThread()));
                graph=Class.forName("com.android.server.HostPinOperationWorld",true,c);
                graph("init",new Class<?>[]{int.class,int.class,int.class},0,41,1);
                Class<?> r=Class.forName(A+"PreparedRetainedUserRegistryCapture",true,m);
                Class<?> family=Class.forName(A+"PreparedRetainedSecurityFamilyCapture",true,m);
                Class<?> binding=Class.forName(A+"PreparedRetainedPinBinding",true,m);
                Object registry=call(r.getMethod("captureExisting"),null);
                Object actualFamily=call(family.getMethod("captureExisting",r),null,registry);
                Object actualBinding=call(binding.getMethod("captureExisting",r,family),null,registry,actualFamily);bindingObject=actualBinding;
                ownerType=Class.forName(A+"PreparedRetainedPinOperationOwner",true,m);
                owner=call(ownerType.getMethod("prepare",binding),null,actualBinding);
                checkType=Class.forName(A+"PreparedRetainedPinCheckOwner",true,m);
                checkOwner=call(checkType.getMethod("prepare",ownerType),null,owner);
                endpointType=Class.forName(A+"PreparedRetainedPinEndpoint",true,m);
                endpoint=configured?call(endpointType.getMethod("prepareWithCheck",ownerType,checkType),null,owner,checkOwner):call(endpointType.getMethod("prepare",ownerType),null,owner);
                clientType=Class.forName(T+"PreparedRetainedPinEndpointClient",true,m);
                client=call(clientType.getMethod("prepareForCheck",Class.forName("android.os.IBinder",false,f)),null,endpoint);
                pinType=Class.forName("com.android.internal.widget.LockscreenCredential",true,f);
                responseType=Class.forName("com.android.internal.widget.VerifyCredentialResponse",true,f);
                probe=Class.forName("model.EndpointProbe",true,f);
                binderType=Class.forName("android.os.Binder",true,f);
                control=Class.forName(A+"CheckFixtureControl",true,m);
                interfaceType=Class.forName("android.os.IInterface",false,f);
                checkProbe=Class.forName("model.CheckProbe",true,f);
                callback=call(checkProbe.getMethod("newCallback",boolean.class),null,false);
                guestPin=pin(true);
            }catch(Throwable t){throw cleanup(t);}
        }
        Object graph(String name,Class<?>[] types,Object...args)throws Throwable{return call(graph.getMethod(name,types),null,args);}
        Object graph(String name)throws Throwable{return graph(name,new Class<?>[0]);}
        Object pin(boolean value)throws Throwable{return call(pinType.getMethod("modelCreate",boolean.class,boolean.class),null,value,false);}
        void openOwner()throws Throwable{call(control.getMethod("openBase",ownerType),null,owner);}
        void openEndpoint()throws Throwable{call(control.getMethod("openEndpoint",endpointType),null,endpoint);}
        void openCheck()throws Throwable{call(control.getMethod("openCheck",checkType),null,checkOwner);}
        void open()throws Throwable{openOwner();openCheck();openEndpoint();}
        void closeEndpoint()throws Throwable{call(endpointType.getMethod("closeIngress"),endpoint);}
        boolean idle()throws Throwable{return(Boolean)call(endpointType.getMethod("localRpcStacksIdle"),endpoint);}
        boolean ownerIdle()throws Throwable{return(Boolean)call(ownerType.getMethod("adapterCallsIdle"),owner);}
        boolean checkIdle()throws Throwable{return(Boolean)call(checkType.getMethod("adapterCallsIdle"),checkOwner);}
        Object rpc(Object pin)throws Throwable{return call(clientType.getMethod("checkPin",pinType,interfaceType),client,pin,callback);}
        Object verify()throws Throwable{return call(clientType.getMethod("verifyPin",pinType),client,guestPin);}
        int events()throws Throwable{return((java.util.concurrent.atomic.AtomicInteger)checkProbe.getField("callbacks").get(null)).get();}
        int checkCalls()throws Throwable{return((java.util.concurrent.atomic.AtomicInteger)checkProbe.getField("checkCalls").get(null)).get();}
        Object field(String name)throws Throwable{return checkProbe.getField(name).get(null);}
        void checkSet(String name,Object value)throws Throwable{checkProbe.getField(name).set(null,value);}
        Object rpc()throws Throwable{return rpc(guestPin);}
        void response()throws Throwable{
            Object value=call(responseType.getMethod("modelCreate",int.class),null,907);
            graph("response",new Class<?>[]{responseType},value);
        }
        void fault(String stage,Throwable value)throws Throwable{call(probe.getMethod("fault",String.class,Throwable.class),null,stage,value);}
        void hook(String stage,Runnable value)throws Throwable{call(probe.getMethod("hook",String.class,Runnable.class),null,stage,value);}
        void set(String name,Object value)throws Throwable{probe.getField(name).set(null,value);}
        long[] counters()throws Throwable{return(long[])call(probe.getMethod("counters"),null);}
        long[] observations()throws Throwable{return(long[])graph("observations");}
        void clean()throws Throwable{
            long[] v=counters();check(v[0]==v[2]&&v[1]==v[3]&&v[4]==0&&v[7]==0);
            check(idle()&&ownerIdle()&&checkIdle());
            check(!(Boolean)call(pinType.getMethod("modelClosed"),guestPin));
            check(!(Boolean)call(pinType.getMethod("modelZeroized"),guestPin));
        }
        Job start(Action a){Job j=new Job(a);jobs.add(j);j.thread.start();return j;}
        Object worker(final Action a)throws Throwable{Job j=start(a);j.join();if(j.error.get()!=null)throw j.error.get();return j.result.get();}
        Object worker()throws Throwable{return worker(new Action(){public Object run()throws Throwable{return rpc();}});}
        CountDownLatch release(){CountDownLatch l=new CountDownLatch(1);releases.add(l);return l;}
        Throwable cleanup(Throwable primary){
            for(CountDownLatch l:releases)l.countDown();
            boolean live=false;
            for(Job j:jobs)try{j.thread.join(4000);if(j.thread.isAlive()){live=true;primary=preserve(primary,new AssertionError("authored worker still live"));}}catch(Throwable t){live=true;primary=preserve(primary,t);}
            try{Thread.currentThread().setContextClassLoader(previous);}catch(Throwable t){primary=preserve(primary,t);}
            if(!live){
                if(client!=null)try{call(clientType.getMethod("close"),client);}catch(Throwable t){primary=preserve(primary,t);}
                if(endpoint!=null)try{closeEndpoint();}catch(Throwable t){primary=preserve(primary,t);}
                if(checkOwner!=null)try{call(checkType.getMethod("closeAdapterIngress"),checkOwner);}catch(Throwable t){primary=preserve(primary,t);}
                if(owner!=null)try{call(ownerType.getMethod("closeAdapterIngress"),owner);}catch(Throwable t){primary=preserve(primary,t);}
                for(URLClassLoader l:new URLClassLoader[]{m,c,f})if(l!=null)try{l.close();}catch(Throwable t){primary=preserve(primary,t);}
            }
            return primary;
        }
        public void close()throws Exception{Throwable t=cleanup(null);if(t!=null)RetainedPinCheckTest.<Exception>raise(t);}
    }
    private static Runnable unchecked(final Action action){return new Runnable(){public void run(){try{action.run();}catch(Throwable t){RetainedPinCheckTest.<RuntimeException>raise(t);}}};}
    private static void await(CountDownLatch latch)throws InterruptedException{check(latch.await(3,TimeUnit.SECONDS));}

    public static void main(String[] args)throws Throwable {
        if(args.length!=5)throw new AssertionError("program, empty deps, F, C, lifecycle control");paths=args;
        // A legacy endpoint remains verify-only; no code2 decode or accidental route.
        scenarios++;try(final World w=new World(false)) {
            w.open();w.response();check(failure(new Action(){public Object run()throws Throwable{return w.worker();}}) instanceof IllegalStateException);
            check(w.checkCalls()==0 && w.counters()[5]==0);
            check(w.worker(new Action(){public Object run()throws Throwable{return w.verify();}})!=null);
            check(w.checkCalls()==0 && w.observations()[0]==1 && w.counters()[12]==1);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.openOwner();w.openEndpoint();
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}}) instanceof IllegalStateException);
            check(w.checkCalls()==0 && w.counters()[5]==1 && w.counters()[6]==1);w.clean();
        }
        // Canonical local callback object and Binder identity survive unchanged.
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.checkSet("callbackAction",unchecked(new Action(){public Object run()throws Throwable {
                check(!(Boolean)w.field("finalReached") && !w.idle() && !w.checkIdle());return null;}}));
            Object result=w.worker();check(w.responseType.getField("modelMarker").getInt(result)==907);
            check(w.checkCalls()==1 && w.events()==1 && w.observations()[0]==1 && w.counters()[12]==2);
            check(w.field("lastOriginalCallback")==w.callback);
            check(w.field("checkThread")==w.field("callbackThread") && w.field("checkThread")!=Thread.currentThread());
            check(((Long)w.field("entryIdentity")).longValue()==0x123456789abL && ((Long)w.field("callbackIdentity")).longValue()==0);
            check(((Integer)w.field("lastUser")).intValue()==0 && w.observations()[5]==1 && w.observations()[6]==1);
            Object decoded=w.field("lastOriginalPin");check(decoded!=w.guestPin && (Boolean)call(w.pinType.getMethod("modelClosed"),decoded));
            check((Boolean)call(w.pinType.getMethod("modelZeroized"),decoded));w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.callback=null;check(w.worker()!=null);
            check(w.checkCalls()==1 && w.events()==0 && w.field("lastOriginalCallback")==null);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();Object value=call(w.responseType.getMethod("modelCreate",int.class),null,-1);
            w.graph("response",new Class<?>[]{w.responseType},value);Object result=w.worker();
            check(w.responseType.getField("modelMarker").getInt(result)==-1 && w.events()==1 && w.checkCalls()==1);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();check(w.worker()==null && w.events()==1 && w.checkCalls()==1 && (Boolean)w.field("finalReached"));w.clean();
        }
        // Forced proxy uses the exact one-way no-payload AIDL envelope, not a reply.
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.callback=call(w.checkProbe.getMethod("newCallback",boolean.class),null,true);
            check(w.worker()!=null && w.events()==1 && w.checkCalls()==1);
            Object original=w.field("lastOriginalCallback");
            Object expected=call(w.checkProbe.getMethod("binderOf",w.interfaceType),null,w.callback);
            check(original!=w.callback && call(w.checkProbe.getMethod("binderOf",w.interfaceType),null,original)==expected);
            check(((Integer)w.field("callbackCode")).intValue()==1 && ((Integer)w.field("callbackFlags")).intValue()==1);
            check(((java.util.concurrent.atomic.AtomicInteger)w.field("callbackTransacts")).get()==1);
            check(call(w.checkProbe.getMethod("canonicalFromBinder",Class.forName("android.os.IBinder",false,w.f)),null,new Object[]{null})==null);w.clean();
        }
        for(final boolean checked:new boolean[]{false,true}) {scenarios++;try(final World w=new World()) {
            w.open();final Throwable exact=checked?new Exception("modeled original checked failure"):new RuntimeException("modeled original failure");
            w.graph("fail",new Class<?>[]{Throwable.class},exact);
            Throwable actual=failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(checked?actual.getClass().getName().equals("android.os.RemoteException") && actual.getCause()==exact:actual==exact);
            check(w.events()==1 && w.checkCalls()==1 && (Boolean)w.field("finalReached"));w.clean();
        }}
        scenarios++;try(final World w=new World()) {
            w.open();final RuntimeException factory=new RuntimeException("modeled callback factory");w.checkSet("factoryFailure",factory);
            w.callback=call(w.checkProbe.getMethod("factoryFailureCallback"),null);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==factory);
            check(w.checkCalls()==0 && w.events()==0 && w.counters()[5]==1 && w.counters()[6]==1);
            w.callback=call(w.checkProbe.getMethod("newCallback",boolean.class),null,false);
            final RuntimeException exact=new RuntimeException("modeled callback failure");w.checkSet("callbackFailure",exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact);
            check(w.checkCalls()==1 && w.events()==1 && !(Boolean)w.field("finalReached"));w.clean();
        }
        // Public arguments are validated before owned Parcel acquisition.
        scenarios++;try(final World w=new World()) {
            w.open();
            for(final String method:new String[]{"wrongCallback","nullBinderCallback"}) {
                w.callback=call(w.checkProbe.getMethod(method),null);
                check(failure(new Action(){public Object run()throws Throwable{return w.worker();}}) instanceof IllegalArgumentException);
            }
            final RuntimeException exact=new RuntimeException("modeled asBinder failure");w.checkSet("asBinderFailure",exact);
            w.callback=call(w.checkProbe.getMethod("throwingBinderCallback"),null);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact);
            w.callback=null;
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return w.rpc(null);}});}}) instanceof IllegalArgumentException);
            final Object nonPin=w.pin(false);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return w.rpc(nonPin);}});}}) instanceof IllegalArgumentException);
            check(w.counters()[0]==0 && w.checkCalls()==0);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();Object refused=w.worker(new Action(){public Object run()throws Throwable {
                call(w.binderType.getMethod("modelCaller",int.class),null,2000);
                return failure(new Action(){public Object run()throws Throwable{return w.rpc();}});}});
            check(refused instanceof SecurityException && w.counters()[0]==0 && w.checkCalls()==0);w.clean();
        }
        for(final String variant:new String[]{"uid","version","flags","wire-user"}) {scenarios++;try(final World w=new World()) {
            w.open();
            if(variant.equals("uid"))w.set("serverUid",Integer.valueOf(2000));
            if(variant.equals("version"))w.set("versionOverride",Integer.valueOf(2));
            if(variant.equals("flags"))w.set("flagsOverride",Integer.valueOf(0));
            if(variant.equals("wire-user"))w.set("trailingRequest",Boolean.TRUE);
            failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(w.checkCalls()==0 && w.events()==0);
            check(w.counters()[6]==(variant.equals("wire-user")?1:0));w.clean();
        }}
        for(final String stage:new String[]{"request.obtain","reply.obtain","pin.decode","host.reply.typed.write","response.read"}) {scenarios++;try(final World w=new World()) {
            w.open();w.response();final RuntimeException exact=new RuntimeException("modeled "+stage);w.fault(stage,exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact);
            boolean after=stage.equals("host.reply.typed.write") || stage.equals("response.read");
            check(w.checkCalls()==(after?1:0) && w.events()==(after?1:0));w.clean();
            if(stage.equals("pin.decode"))for(final String binderStage:new String[]{"request.binder.write","host.request.binder.read"}) {
                final RuntimeException binderFault=new RuntimeException("modeled "+binderStage);w.fault(binderStage,binderFault);
                check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==binderFault);
                check(w.checkCalls()==0 && w.events()==0);w.clean();
            }
        }}
        scenarios++;try(final World w=new World()) {
            w.open();final RuntimeException primary=new RuntimeException("modeled original"),host=new RuntimeException("host PIN close"),reply=new RuntimeException("reply recycle"),request=new RuntimeException("request recycle");
            w.graph("fail",new Class<?>[]{Throwable.class},primary);w.fault("host.pin.close",host);w.fault("reply.recycle",reply);w.fault("request.recycle",request);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==primary);
            check(primary.getSuppressed().length==3 && primary.getSuppressed()[0]==host && primary.getSuppressed()[1]==reply && primary.getSuppressed()[2]==request);
            check(w.events()==1 && w.checkCalls()==1);w.clean();
        }
        // Actual code1 remains verify-only in this same newly compiled cohort.
        scenarios++;try(final World w=new World()) {
            w.open();w.response();Object value=w.worker(new Action(){public Object run()throws Throwable{return w.verify();}});
            check(w.responseType.getField("modelMarker").getInt(value)==907 && w.checkCalls()==0 && w.events()==0);
            check(w.counters()[12]==1 && w.observations()[0]==1 && w.observations()[7]==0 && w.observations()[8]==0);
            final RuntimeException exact=new RuntimeException("verify regression failure");w.graph("fail",new Class<?>[]{Throwable.class},exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return w.verify();}});}})==exact);
            check(w.checkCalls()==0 && w.events()==0 && w.observations()[0]==2);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.checkSet("callbackAction",unchecked(new Action(){public Object run()throws Throwable {
                call(w.clientType.getMethod("close"),w.client);return null;}}));
            check(w.worker()!=null);long transactions=w.counters()[8];
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}}) instanceof IllegalStateException);
            check(w.counters()[8]==transactions && w.checkCalls()==1);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.checkSet("callbackAction",unchecked(new Action(){public Object run()throws Throwable {
                w.checkSet("callbackAction",null);check(!w.idle() && !w.checkIdle());w.rpc();return null;}}));
            check(w.worker()!=null && w.events()==2 && w.checkCalls()==2);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            w.open();w.response();w.checkSet("callbackAction",unchecked(new Action(){public Object run()throws Throwable {
                check(!w.idle() && !w.checkIdle());w.closeEndpoint();return null;}}));
            check(w.worker()!=null && w.events()==1);long decodes=w.counters()[5];
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}}) instanceof IllegalStateException);
            check(w.counters()[5]==decodes && w.checkCalls()==1);w.checkSet("callbackAction",null);
            call(w.checkType.getMethod("closeAdapterIngress"),w.checkOwner);check(w.idle() && w.checkIdle());
            call(w.checkProbe.getMethod("fireLate"),null);check(w.events()==2 && w.idle() && w.checkIdle());w.clean();
        }
        // Derivation is metadata-only but has a real closed/main/nested fence.
        scenarios++;try(final World w=new World()) {
            call(w.ownerType.getMethod("closeAdapterIngress"),w.owner);
            check(failure(new Action(){public Object run()throws Throwable{return call(w.checkType.getMethod("prepare",w.ownerType),null,w.owner);}}) instanceof IllegalStateException);
            check(failure(new Action(){public Object run()throws Throwable{w.openOwner();return null;}}) instanceof IllegalStateException);
            check(w.checkCalls()==0);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return call(w.checkType.getMethod("prepare",w.ownerType),null,w.owner);}});}}) instanceof IllegalStateException);
            w.open();check(w.worker()==null && w.checkCalls()==1);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            final java.util.concurrent.atomic.AtomicInteger nested=new java.util.concurrent.atomic.AtomicInteger();
            w.graph("anchor",new Class<?>[]{Runnable.class},unchecked(new Action(){public Object run()throws Throwable {
                w.graph("anchor",new Class<?>[]{Runnable.class},(Object)null);nested.incrementAndGet();
                check(failure(new Action(){public Object run()throws Throwable{return call(w.checkType.getMethod("prepare",w.ownerType),null,w.owner);}}) instanceof IllegalStateException);return null;}}));
            Object extra=call(w.checkType.getMethod("prepare",w.ownerType),null,w.owner);check(nested.get()==1 && extra!=null);
            call(w.checkType.getMethod("closeAdapterIngress"),extra);w.open();check(w.worker()==null);w.clean();
        }
        scenarios++;try(final World w=new World()) {
            Object other=call(w.ownerType.getMethod("prepare",w.bindingObject.getClass()),null,w.bindingObject);
            check(failure(new Action(){public Object run()throws Throwable{return call(w.endpointType.getMethod("prepareWithCheck",w.ownerType,w.checkType),null,other,w.checkOwner);}}) instanceof IllegalStateException);
            call(w.ownerType.getMethod("closeAdapterIngress"),other);w.open();check(w.worker()==null);w.clean();
        }
        System.out.println("{\"status\":\"PASS_AUTHORED_RETAINED_PIN_CHECK_MODELS_ONLY\",\"scenarios\":"+scenarios+",\"checks\":"+checks+",\"completionCellUsed\":false}");
    }
}

