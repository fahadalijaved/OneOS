package fixture;
import com.android.server.LocalServices;
/** Authored dependency/fault controls, NOT Android behavior or admission. */
public final class FrameworkControl {
 public static int constructions,forbidden;
 private static Class<?> localKey,policyKey;
 private static Runnable graphHook;
 public static void initialize(ClassLoader core,Thread main){com.android.internal.os.ZygoteInit.modelSet(core);android.os.Looper.modelSet(main);}
 public static void keys(Class<?> local,Class<?> policy){localKey=local;policyKey=policy;}
 public static void publish(Object local,Object policy,Object wms){synchronized(LocalServices.modelMap()){LocalServices.entries.put(localKey,local);LocalServices.entries.put(policyKey,policy);}android.view.WindowManagerGlobal.modelSet(wms);}
 public static void onCollectionRead(Object key){}
 public static void armGraphHook(Runnable hook){graphHook=hook;}
 public static void onPlacement(){
  if(Thread.holdsLock(LocalServices.modelMap()))throw new AssertionError("external placement under map lock");
  if(graphHook==null)return;
  boolean graph=false,bind=false;
  for(StackTraceElement frame:Thread.currentThread().getStackTrace()){
   if(frame.getClassName().equals("com.appleexploit.oneos.security.authority.PreparedGuestKeyguardGraphCapture")&&frame.getMethodName().equals("checkStillBound"))graph=true;
   if(frame.getClassName().equals("com.appleexploit.oneos.security.authority.PreparedGuestPolicyInitCompletion")&&frame.getMethodName().equals("bindGraph"))bind=true;
  }
  // Explicit authored stack-selected dependency injection. NOT source authentication.
  if(graph&&bind){Runnable hook=graphHook;graphHook=null;hook.run();}
 }
 public static final class ServiceValue implements com.android.internal.policy.IKeyguardService {}
}
