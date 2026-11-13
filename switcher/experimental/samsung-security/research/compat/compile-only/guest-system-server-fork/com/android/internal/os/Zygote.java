package com.android.internal.os;

/** Compiler-only actual ABI. Never a runtime implementation or program DEX input. */
public final class Zygote {
    private Zygote() { }
    static int forkSystemServer(int uid, int gid, int[] gids, int runtimeFlags,
            int[][] rlimits, long permitted, long effective) {
        throw new AssertionError("compiler declaration only");
    }
}
