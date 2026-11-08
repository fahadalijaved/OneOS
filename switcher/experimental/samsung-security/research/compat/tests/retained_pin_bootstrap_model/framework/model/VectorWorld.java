package model;
import io.github.libxposed.api.XposedInterface;
import io.github.libxposed.api.XposedModuleInterface;
import java.lang.reflect.Executable;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.List;
/** Own hook protocol, NOT Vector registration or Android execution evidence. */
public final class VectorWorld {
 public static int installs,unhooks,logs;
 public static boolean badAck,throwLogs;
 public static XposedInterface.ExceptionMode requestedMode;
 public static XposedInterface.Hooker hooker;
 public static Executable target;
 public static final List<String> codes=new ArrayList<String>();
 public static Runnable logWork;
 public static void report(int level,String tag,String code){
  if(level!=6||!tag.equals("OneOSPinHostBootstrap"))throw new AssertionError("literal ERROR report profile");
  logs++;codes.add(code);if(logWork!=null){Runnable work=logWork;logWork=null;work.run();}
  if(throwLogs)throw new AssertionError("authored logger failure");
 }
 public static final class Loaded implements XposedModuleInterface.ModuleLoadedParam {public boolean isSystemServer(){return true;}public String getProcessName(){return "system_server";}}
 public static final class Starting implements XposedModuleInterface.SystemServerStartingParam {private final ClassLoader loader;public Starting(ClassLoader loader){this.loader=loader;}public ClassLoader getClassLoader(){return loader;}}
 public static final class Builder implements XposedInterface.HookBuilder {
  private final Executable executable;public Builder(Executable executable){this.executable=executable;}
  public XposedInterface.HookBuilder setPriority(int p){return this;}public XposedInterface.HookBuilder setId(String id){return this;}
  public XposedInterface.HookBuilder setExceptionMode(XposedInterface.ExceptionMode mode){requestedMode=mode;return this;}
  public XposedInterface.HookHandle intercept(XposedInterface.Hooker value){installs++;target=executable;hooker=value;return new Handle(executable);}
 }
 public static final class Handle implements XposedInterface.HookHandle {
  private final Executable executable;Handle(Executable executable){this.executable=executable;}
  public Executable getExecutable(){return badAck?null:executable;}public void unhook(){unhooks++;}
  public String getId(){return "authored-only";}public XposedInterface.HookHandle replaceHook(XposedInterface.Hooker value){throw new AssertionError("rearm forbidden");}
 }
 public static final class Chain implements XposedInterface.Chain {
  public final Method method;public final Object receiver;public final Object[] args;public int proceeded;public boolean metadataFault;
  public Chain(Method method,Object receiver,Object timing,int phase){this.method=method;this.receiver=receiver;args=new Object[]{timing,Integer.valueOf(phase)};}
  public Executable getExecutable(){if(metadataFault)BootstrapProbe.raise(BootstrapProbe.observerFailure);return method;}
  public Object getThisObject(){return receiver;}public List<Object> getArgs(){return java.util.Arrays.asList(args);}public Object getArg(int i){return args[i];}
  public Object proceed()throws Throwable{proceeded++;try{return method.invoke(receiver,args);}catch(InvocationTargetException failure){throw failure.getCause();}}
  public Object proceed(Object[] a){throw new AssertionError("argument substitution forbidden");}
  public Object proceedWith(Object r){throw new AssertionError("receiver substitution forbidden");}
  public Object proceedWith(Object r,Object[] a){throw new AssertionError("substitution forbidden");}
 }
 public static Object dispatch(Chain chain)throws Throwable{return hooker==null?chain.proceed():hooker.intercept(chain);}
}
