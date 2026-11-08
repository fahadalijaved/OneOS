package com.android.internal.os;

/** Compiler-only actual ABI. Never a runtime implementation or program DEX input. */
public class ZygoteInit {
    private ZygoteInit() { }
    public static Runnable zygoteInit(int targetSdk, long[] disabled, long[] enabled,
            String[] argv, ClassLoader loader) {
        throw new AssertionError("compiler declaration only");
    }
}
