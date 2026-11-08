package com.android.server;
/** Authored map only. No original service lookup is implemented. */
public final class LocalServices {
 private static final android.util.ArrayMap<Class<?>,Object> sLocalServiceObjects=new android.util.ArrayMap<Class<?>,Object>();
 public static java.util.Map<Class<?>,Object> entries=sLocalServiceObjects;
 public static android.util.ArrayMap<Class<?>,Object> modelMap(){return sLocalServiceObjects;}
 public static Object getService(Class<?> key){fixture.FrameworkControl.forbidden++;throw new AssertionError("model getService invoked");}
}
