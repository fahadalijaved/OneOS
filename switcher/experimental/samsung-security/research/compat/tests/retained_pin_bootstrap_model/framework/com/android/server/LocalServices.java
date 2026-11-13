package com.android.server;
/** Authored map/observer seam; no real publication, callback or source authority. */
public final class LocalServices {
 private static final android.util.ArrayMap<Class<?>,Object> sLocalServiceObjects=new android.util.ArrayMap<Class<?>,Object>();
 public static java.util.Map<Class<?>,Object> entries=sLocalServiceObjects;
 public static Throwable fault,modelLocalFault;public static int calls,modelLocalLookups;
 public static Runnable modelObserver;
 public static Object getService(Class<?> key) {
  calls++;model.BootstrapProbe.lookup();if(modelObserver!=null)modelObserver.run();
  if(fault!=null){Throwable t=fault;fault=null;if(t instanceof RuntimeException)throw(RuntimeException)t;if(t instanceof Error)throw(Error)t;}
  if(key==null)throw new AssertionError("uncached modeled root key");
  synchronized(sLocalServiceObjects){return sLocalServiceObjects.get(key);}
 }
 public static android.util.ArrayMap<Class<?>,Object> modelMap(){return sLocalServiceObjects;}
 public static void modelClear(){synchronized(sLocalServiceObjects){sLocalServiceObjects.clear();entries=sLocalServiceObjects;}fault=null;modelLocalFault=null;calls=0;modelLocalLookups=0;modelObserver=null;}
}
