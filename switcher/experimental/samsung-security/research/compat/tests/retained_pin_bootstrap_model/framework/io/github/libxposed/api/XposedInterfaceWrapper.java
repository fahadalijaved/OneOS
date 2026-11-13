package io.github.libxposed.api;
/** Authored Vector seam; no framework or hook installation is performed. */
public abstract class XposedInterfaceWrapper implements XposedInterface {
 public int getApiVersion(){return model.BootstrapProbe.apiVersion;}
 public HookBuilder hook(java.lang.reflect.Executable executable){return new model.VectorWorld.Builder(executable);}
 public void log(int level,String tag,String message){model.VectorWorld.report(level,tag,message);}
}
