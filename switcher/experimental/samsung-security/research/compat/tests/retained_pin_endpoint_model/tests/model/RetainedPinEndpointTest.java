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
public final class RetainedPinEndpointTest {
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
        Class<?> graph,probe,ownerType,endpointType,clientType,pinType,responseType,control,binderType;
        Object owner,endpoint,client,guestPin;
        World()throws Throwable {
            try{
                ClassLoader platform=RetainedPinEndpointTest.class.getClassLoader().getParent();
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
                Object actualBinding=call(binding.getMethod("captureExisting",r,family),null,registry,actualFamily);
                ownerType=Class.forName(A+"PreparedRetainedPinOperationOwner",true,m);
                owner=call(ownerType.getMethod("prepare",binding),null,actualBinding);
                endpointType=Class.forName(A+"PreparedRetainedPinEndpoint",true,m);
                endpoint=call(endpointType.getMethod("prepare",ownerType),null,owner);
                clientType=Class.forName(T+"PreparedRetainedPinEndpointClient",true,m);
                client=call(clientType.getMethod("prepare",Class.forName("android.os.IBinder",false,f)),null,endpoint);
                pinType=Class.forName("com.android.internal.widget.LockscreenCredential",true,f);
                responseType=Class.forName("com.android.internal.widget.VerifyCredentialResponse",true,f);
                probe=Class.forName("model.EndpointProbe",true,f);
                binderType=Class.forName("android.os.Binder",true,f);
                control=Class.forName(A+"EndpointFixtureControl",true,m);
                guestPin=pin(true);
            }catch(Throwable t){throw cleanup(t);}
        }
        Object graph(String name,Class<?>[] types,Object...args)throws Throwable{return call(graph.getMethod(name,types),null,args);}
        Object graph(String name)throws Throwable{return graph(name,new Class<?>[0]);}
        Object pin(boolean value)throws Throwable{return call(pinType.getMethod("modelCreate",boolean.class,boolean.class),null,value,false);}
        void openOwner()throws Throwable{call(control.getMethod("openOwner",ownerType),null,owner);}
        void openEndpoint()throws Throwable{call(control.getMethod("openEndpoint",endpointType),null,endpoint);}
        void open()throws Throwable{openOwner();openEndpoint();}
        void closeEndpoint()throws Throwable{call(endpointType.getMethod("closeIngress"),endpoint);}
        boolean idle()throws Throwable{return(Boolean)call(endpointType.getMethod("localRpcStacksIdle"),endpoint);}
        boolean ownerIdle()throws Throwable{return(Boolean)call(ownerType.getMethod("adapterCallsIdle"),owner);}
        Object rpc(Object pin)throws Throwable{return call(clientType.getMethod("verifyPin",pinType),client,pin);}
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
            check(idle()&&ownerIdle());
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
                if(owner!=null)try{call(ownerType.getMethod("closeAdapterIngress"),owner);}catch(Throwable t){primary=preserve(primary,t);}
                for(URLClassLoader l:new URLClassLoader[]{m,c,f})if(l!=null)try{l.close();}catch(Throwable t){primary=preserve(primary,t);}
            }
            return primary;
        }
        public void close()throws Exception{Throwable t=cleanup(null);if(t!=null)RetainedPinEndpointTest.<Exception>raise(t);}
    }
    private static Runnable unchecked(final Action action){return new Runnable(){public void run(){try{action.run();}catch(Throwable t){RetainedPinEndpointTest.<RuntimeException>raise(t);}}};}
    private static void await(CountDownLatch latch)throws InterruptedException{check(latch.await(3,TimeUnit.SECONDS));}

    public static void main(String[] args)throws Throwable{
        if(args.length!=5)throw new AssertionError("five isolated paths required");paths=args;
        // Closed endpoint does not decode, even when the shared Owner is open.
        scenarios++;try(final World w=new World()){
            w.openOwner();check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})instanceof IllegalStateException);
            check(w.counters()[5]==0&&w.observations()[0]==0);w.clean();
            call(w.clientType.getMethod("close"),w.client);
            long calls=w.counters()[8];failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(w.counters()[8]==calls);
        }
        // One original worker invocation, internal user/flags and distinct decoded PIN.
        scenarios++;try(final World w=new World()){
            w.open();w.response();Object result=w.worker();long[] v=w.counters();long[] obs=w.observations();
            check(result!=null&&w.responseType.getField("modelMarker").getInt(result)==907);
            check(obs[0]==1&&obs[7]==0&&obs[8]==0&&obs[9]==0x123456789abL);
            check(v[8]==1&&v[12]==1&&v[13]==32&&v[14]==1&&v[11]==1);
            Object decoded=w.probe.getField("lastDecoded").get(null);
            check(decoded!=w.guestPin&&(Boolean)call(w.pinType.getMethod("modelClosed"),decoded));
            check((Boolean)call(w.pinType.getMethod("modelZeroized"),decoded)&&v[6]==1);
            check(w.graph("originalThread")!=Thread.currentThread());w.clean();
        }
        scenarios++;try(final World w=new World()){
            w.open();check(w.worker()==null);check(w.observations()[0]==1&&w.counters()[10]==0);w.clean();
        }
        // Public validation/caller restrictions before any serialization.
        scenarios++;try(final World w=new World()){
            w.open();Object nonPin=w.pin(false);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return w.rpc(null);}});}})instanceof IllegalArgumentException);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker(new Action(){public Object run()throws Throwable{return w.rpc(nonPin);}});}})instanceof IllegalArgumentException);
            check(w.worker(new Action(){public Object run()throws Throwable{call(w.binderType.getMethod("modelCaller",int.class),null,2000);return failure(new Action(){public Object run()throws Throwable{return w.rpc();}});}})instanceof SecurityException);
            Class.forName("model.BootstrapProbe",true,w.f).getField("uid").setInt(null,2000);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})instanceof SecurityException);
            check(w.counters()[0]==0&&w.observations()[0]==0);w.clean();
        }
        // Main-thread endpoint decode is cleaned, but Owner refuses original work.
        scenarios++;try(final World w=new World()){
            w.open();check(failure(new Action(){public Object run()throws Throwable{return w.rpc();}})instanceof IllegalStateException);
            check(w.counters()[5]==1&&w.counters()[6]==1&&w.observations()[0]==0);w.clean();
        }
        // Every meaningful client acquisition/serializer/transport/reader fault.
        String[] stages={"request.obtain","request.sensitive","reply.obtain","request.token.write","request.int.write","request.typed.write","pin.write","transact","reply.exception.read","reply.typed.read","response.read","reply.trailing"};
        for(final String stage:stages){scenarios++;try(final World w=new World()){
            w.open();w.response();final RuntimeException exact=new RuntimeException("authored "+stage);w.fault(stage,exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact);
            check(w.observations()[0]<=1&&w.counters()[8]<=1);w.clean();
        }}
        // Host refusal/decode checks: malformed/version/flags/UID/creator faults.
        for(final String variant:new String[]{"version","flags","uid","trailing","creator"}){scenarios++;try(final World w=new World()){
            w.open();if(variant.equals("version"))w.set("versionOverride",Integer.valueOf(2));
            if(variant.equals("flags"))w.set("flagsOverride",Integer.valueOf(0));
            if(variant.equals("uid"))w.set("serverUid",Integer.valueOf(2000));
            if(variant.equals("trailing"))w.set("trailingRequest",Boolean.TRUE);
            if(variant.equals("creator"))w.fault("pin.decode",new RuntimeException("authored creator"));
            failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(w.observations()[0]==0);check(w.counters()[6]==(variant.equals("trailing")?1:0));w.clean();
        }}
        scenarios++;try(final World w=new World()){
            w.open();w.set("returnFalse",Boolean.TRUE);Throwable t=failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(t.getClass().getName().equals("android.os.RemoteException")&&w.observations()[0]==0);w.clean();
        }
        scenarios++;try(final World w=new World()){
            w.open();w.response();w.set("trailingResponse",Boolean.TRUE);
            failure(new Action(){public Object run()throws Throwable{return w.worker();}});check(w.observations()[0]==1&&w.counters()[8]==1);w.clean();
        }
        // Exact LOCAL failure identity; this authored direct dispatch is not IPC identity.
        for(final int kind:new int[]{0,1,2,3}){scenarios++;try(final World w=new World()){
            w.open();final Throwable original=kind==0?new RuntimeException("authored original"):
                kind==1?new AssertionError("authored original"):
                kind==2?(Throwable)Class.forName("android.os.RemoteException",true,w.f).getConstructor(String.class).newInstance("authored original"):
                new Exception("authored checked");
            w.graph("fail",new Class<?>[]{Throwable.class},original);
            Throwable actual=failure(new Action(){public Object run()throws Throwable{return w.worker();}});
            check(kind==3?actual.getClass().getName().equals("android.os.RemoteException")&&actual.getCause()==original:actual==original);
            check(w.observations()[0]==1&&w.counters()[6]==1);w.clean();
        }}
        // Reply construction and decoded-PIN close errors preserve exact primary.
        for(final String stage:new String[]{"host.reply.exception.write","host.reply.typed.write","response.write","host.pin.close"}){scenarios++;try(final World w=new World()){
            w.open();w.response();final RuntimeException exact=new RuntimeException(stage);w.fault(stage,exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact);
            check(w.observations()[0]==1&&w.counters()[6]==1);w.clean();
        }}
        scenarios++;try(final World w=new World()){
            w.open();final RuntimeException primary=new RuntimeException("primary"),host=new RuntimeException("host cleanup"),reply=new RuntimeException("reply cleanup"),request=new RuntimeException("request cleanup");
            w.graph("fail",new Class<?>[]{Throwable.class},primary);w.fault("host.pin.close",host);w.fault("reply.recycle",reply);w.fault("request.recycle",request);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==primary);
            check(primary.getSuppressed().length==3&&primary.getSuppressed()[0]==host&&primary.getSuppressed()[1]==reply&&primary.getSuppressed()[2]==request);w.clean();
        }
        scenarios++;try(final World w=new World()){
            w.open();final RuntimeException exact=new RuntimeException("self");w.graph("fail",new Class<?>[]{Throwable.class},exact);
            w.fault("host.pin.close",exact);w.fault("reply.recycle",exact);w.fault("request.recycle",exact);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==exact&&exact.getSuppressed().length==0);w.clean();
        }
        scenarios++;try(final World w=new World()){
            w.open();final RuntimeException first=new RuntimeException("reply cleanup"),second=new RuntimeException("request cleanup");
            w.fault("reply.recycle",first);w.fault("request.recycle",second);
            check(failure(new Action(){public Object run()throws Throwable{return w.worker();}})==first&&first.getSuppressed().length==1&&first.getSuppressed()[0]==second);w.clean();
        }
        // Closing at each admitted stage allows that frame, then refuses next decode.
        for(final String stage:new String[]{"pin.decode","response.write"}){scenarios++;try(final World w=new World()){
            w.open();w.response();w.hook(stage,unchecked(new Action(){public Object run()throws Throwable{check(!w.idle());w.closeEndpoint();return null;}}));
            check(w.worker()!=null);long decodes=w.counters()[5];
            failure(new Action(){public Object run()throws Throwable{return w.worker();}});check(w.counters()[5]==decodes);w.clean();
        }}
        scenarios++;try(final World w=new World()){
            w.open();w.graph("inside",new Class<?>[]{Runnable.class},unchecked(new Action(){public Object run()throws Throwable{check(!w.idle()&&!w.ownerIdle());w.closeEndpoint();return null;}}));
            w.worker();w.graph("inside",new Class<?>[]{Runnable.class},(Object)null);
            // Endpoint close did not close the shared Owner.
            w.worker(new Action(){public Object run()throws Throwable{return call(w.ownerType.getMethod("verifyPin",w.pinType),w.owner,w.pin(true));}});
            check(w.observations()[0]==2);w.clean();
        }
        // Owner idle while endpoint reply writer remains paused in its Java stack.
        scenarios++;try(final World w=new World()){
            w.open();w.response();final CountDownLatch entered=new CountDownLatch(1),release=w.release();
            w.hook("response.write",unchecked(new Action(){public Object run()throws Throwable{entered.countDown();check(release.await(3,TimeUnit.SECONDS));return null;}}));
            Job job=w.start(new Action(){public Object run()throws Throwable{return w.rpc();}});await(entered);
            check(w.ownerIdle()&&!w.idle());w.closeEndpoint();release.countDown();job.join();check(job.error.get()==null);w.clean();
        }
        // A simulated FRAMEWORK tail deliberately outlives the endpoint Java counter.
        scenarios++;try(final World w=new World()){
            w.open();w.hook("framework.after.onTransact",unchecked(new Action(){public Object run()throws Throwable{check(w.idle()&&w.ownerIdle());return null;}}));w.worker();w.clean();
        }
        // Same-worker reentry and two concurrent frames own independent Call records.
        scenarios++;try(final World w=new World()){
            w.open();w.graph("inside",new Class<?>[]{Runnable.class},unchecked(new Action(){public Object run()throws Throwable{
                w.graph("inside",new Class<?>[]{Runnable.class},(Object)null);check(!w.idle()&&!w.ownerIdle());w.rpc();return null;}}));
            w.worker();check(w.observations()[0]==2);w.clean();
        }
        scenarios++;try(final World w=new World()){
            w.open();final CountDownLatch entered=new CountDownLatch(2),release=w.release();
            w.graph("inside",new Class<?>[]{Runnable.class},unchecked(new Action(){public Object run()throws Throwable{entered.countDown();check(release.await(3,TimeUnit.SECONDS));return null;}}));
            Job a=w.start(new Action(){public Object run()throws Throwable{return w.rpc();}}),b=w.start(new Action(){public Object run()throws Throwable{return w.rpc();}});
            await(entered);check(!w.idle()&&!w.ownerIdle());w.closeEndpoint();release.countDown();a.join();b.join();check(a.error.get()==null&&b.error.get()==null);check(w.observations()[0]==2);w.clean();
        }
        System.out.println("{\"status\":\"PASS_AUTHORED_RETAINED_PIN_ENDPOINT_MODELS_ONLY\",\"scenarios\":"+scenarios+",\"checks\":"+checks+"}");
    }
}
