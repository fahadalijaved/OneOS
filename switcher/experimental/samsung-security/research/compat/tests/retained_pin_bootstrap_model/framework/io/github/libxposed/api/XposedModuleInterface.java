package io.github.libxposed.api;
/** Only lifecycle interfaces reached by the actual first-party module. */
public interface XposedModuleInterface {
 interface ModuleLoadedParam {boolean isSystemServer();String getProcessName();}
 interface SystemServerStartingParam {ClassLoader getClassLoader();}
 interface HotReloadingParam {android.os.Bundle getExtras();void setSavedInstanceState(Object value);}
 void onModuleLoaded(ModuleLoadedParam param);void onSystemServerStarting(SystemServerStartingParam param);boolean onHotReloading(HotReloadingParam param);
}
