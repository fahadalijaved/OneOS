package com.android.internal.os;
/** Authored cached-loader shape; no Zygote behavior. */
public class ZygoteInit {
 private static ClassLoader sCachedSystemServerClassLoader;
 public static void modelSet(ClassLoader c){sCachedSystemServerClassLoader=c;}
 public static ClassLoader getOrCreateSystemServerClassLoader(){fixture.FrameworkControl.forbidden++;throw new AssertionError("model lazy loader invoked");}
}
