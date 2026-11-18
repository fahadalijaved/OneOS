package com.android.internal.os;
public final class ZygoteInit {
 private static ClassLoader sCachedSystemServerClassLoader;
 public static void modelSet(ClassLoader loader){sCachedSystemServerClassLoader=loader;}
 public static ClassLoader getOrCreateSystemServerClassLoader(){throw new AssertionError("factory forbidden");}
}

