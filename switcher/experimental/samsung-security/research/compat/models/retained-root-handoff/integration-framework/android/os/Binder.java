package android.os;
import java.util.*;
import model.LinkModel;
/** Direct typed-token dispatch with synthetic UID contexts, not native Binder. */
public class Binder implements IBinder {
 private final int owner=LinkModel.uid.get();private String descriptor;private IInterface local;
 private final List<DeathRecipient> deaths=new ArrayList<DeathRecipient>();
 private static final ThreadLocal<Integer> caller=new ThreadLocal<Integer>(){protected Integer initialValue(){return 1000;}};
 private static final ThreadLocal<Long> identity=new ThreadLocal<Long>(){protected Long initialValue(){return 0x123456789abL;}};
 public static Throwable clearFailure,restoreFailure;public static Runnable afterRestore;
 public static void modelReset(){clears=restores=0;clearFailure=restoreFailure=null;afterRestore=null;identity.set(0x123456789abL);}
 public static long modelIdentity(){return identity.get();}
 public static int clears,restores;public static long lastRestored;
 public static int getCallingUid(){return caller.get();} public static int getCallingPid(){return 321;}
 public static void modelCaller(int value){caller.set(value);}
 public static long clearCallingIdentity(){clears++;Throwable e=clearFailure;clearFailure=null;modelThrow(e);long old=identity.get();identity.set(0L);return old;}public static void restoreCallingIdentity(long value){restores++;lastRestored=value;identity.set(value);Runnable h=afterRestore;afterRestore=null;if(h!=null)h.run();Throwable e=restoreFailure;restoreFailure=null;modelThrow(e);}
 public static void modelThrow(Throwable t){if(t!=null)LinkModel.raise(t);}
 public void attachInterface(IInterface value,String name){local=value;descriptor=name;}
 public String getInterfaceDescriptor(){return descriptor;}
 public IInterface queryLocalInterface(String name){return name.equals(descriptor)?local:null;}
 public boolean isBinderAlive(){return true;}
 public void linkToDeath(DeathRecipient r,int flags){deaths.add(r);}
 public boolean unlinkToDeath(DeathRecipient r,int flags){return deaths.remove(r);}
 public void modelDie(){for(DeathRecipient r:new ArrayList<DeathRecipient>(deaths))r.binderDied();}
 protected boolean onTransact(int code,Parcel data,Parcel reply,int flags)throws RemoteException{return false;}
 public final boolean transact(int code,Parcel data,Parcel reply,int flags)throws RemoteException {
  int priorUid=LinkModel.uid.get(),priorCaller=caller.get();caller.set(priorUid);LinkModel.uid.set(owner);LinkModel.observe();
  try{
   if("com.fahadali.oneos.IRetainedRootBroker.v2".equals(descriptor)){LinkModel.brokerCalls++;Parcel peek=data.borrow();peek.readString();peek.readInt();LinkModel.lastCallback=peek.readStrongBinder();}
   if("com.fahadali.oneos.IRetainedRootHost.v2".equals(descriptor)){LinkModel.callbackCalls++;if(code==1)LinkModel.capturedCalls++;else LinkModel.failedCalls++;Runnable hook=LinkModel.callbackHook;LinkModel.callbackHook=null;if(hook!=null)hook.run();}
   if("com.fahadali.oneos.IRetainedRootControl.v1".equals(descriptor)){LinkModel.controlCalls++;if(code==1)LinkModel.pingCalls++;if(code==2)LinkModel.closeCalls++;}
   Parcel request=data.borrow();Parcel response=reply==null?null:reply.blankBorrow();boolean ok=onTransact(code,request,response,flags);if("com.fahadali.oneos.IRetainedRootHost.v2".equals(descriptor)&&ok)LinkModel.callbackCompleted++;if(reply!=null)reply.receive(response);
   if("com.fahadali.oneos.IRetainedRootBroker.v2".equals(descriptor)&&LinkModel.waitCallbackBeforeBeginReturn){long end=System.nanoTime()+4000000000L;while(LinkModel.callbackCompleted==0&&System.nanoTime()<end)try{Thread.sleep(1);}catch(InterruptedException e){throw new AssertionError(e);}LinkModel.callbackBeforeBeginReturn=LinkModel.callbackCompleted>0;}
   Runnable h=LinkModel.afterTransact;LinkModel.afterTransact=null;if(h!=null)h.run();return ok;
  }finally{caller.set(priorCaller);LinkModel.uid.set(priorUid);}
 }
}
