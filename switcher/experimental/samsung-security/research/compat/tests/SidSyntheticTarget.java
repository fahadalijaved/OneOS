package com.appleexploit.oneos.security.compat;

/** Authored target only. Contains no OEM code or security authority. */
public final class SidSyntheticTarget {
    private native long nativeSidFromPasswordHandle(byte[] handle);

    public long extract(byte[] handle) {
        return nativeSidFromPasswordHandle(handle);
    }
}
