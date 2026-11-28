package io.github.libxposed.api;
/** Authored no-op lifecycle superclass, not the original libXposed implementation. */
public abstract class XposedModule extends XposedInterfaceWrapper implements XposedModuleInterface {
 public void onModuleLoaded(ModuleLoadedParam param){}
 public void onSystemServerStarting(SystemServerStartingParam param){}
 public boolean onHotReloading(HotReloadingParam param){return false;}
}
