package io.github.libxposed.api;
/** Authored API-name protocol subset only; no actual Vector implementation. */
public interface XposedInterface {
 enum ExceptionMode {PASSTHROUGH}
 interface Hooker {Object intercept(Chain chain)throws Throwable;}
 interface Chain {
  java.lang.reflect.Executable getExecutable();Object getThisObject();java.util.List<Object> getArgs();Object getArg(int index);
  Object proceed()throws Throwable;Object proceed(Object[] args)throws Throwable;Object proceedWith(Object receiver)throws Throwable;Object proceedWith(Object receiver,Object[] args)throws Throwable;
 }
 interface HookHandle {java.lang.reflect.Executable getExecutable();void unhook();String getId();HookHandle replaceHook(Hooker hooker);}
 interface HookBuilder {HookBuilder setPriority(int priority);HookBuilder setExceptionMode(ExceptionMode mode);HookHandle intercept(Hooker hooker);HookBuilder setId(String id);}
 int getApiVersion();HookBuilder hook(java.lang.reflect.Executable executable);void log(int level,String tag,String message);
}
