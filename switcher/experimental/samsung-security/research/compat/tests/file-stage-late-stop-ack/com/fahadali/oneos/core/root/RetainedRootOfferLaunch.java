package com.fahadali.oneos.core.root;

import com.fahadali.oneos.BuildConfig;

/** Modeled offer boundary. The real Service still owns startup and callback delivery. */
final class RetainedRootOfferLaunch {
    static final int NATIVE_PID = 315;
    static final String ADDRESS = RetainedHostControlProtocol.NATIVE_NAME_PREFIX
            + "0123456789abcdef0123456789abcdef";
    private boolean started;

    static RetainedRootOfferLaunch prepare(RetainedRootHostServiceV2.Caller caller,
            String sha, long bytes) {
        if (caller.pid() != 314 || caller.uid() != 1000
                || !BuildConfig.RETAINED_VIEW_CONTROLLER_SHA256.equals(sha)
                || bytes != BuildConfig.RETAINED_VIEW_CONTROLLER_BYTES) {
            throw new IllegalArgumentException("Modeled launch did not receive BEGIN identity");
        }
        return new RetainedRootOfferLaunch();
    }

    void start() {
        if (started) throw new IllegalStateException("Repeated modeled launch");
        started = true;
    }

    Offer awaitOffer() {
        if (!started) throw new IllegalStateException("Modeled launch not started");
        return new Offer();
    }

    static final class Offer {
        int nativePid() { return NATIVE_PID; }
        String address() { return ADDRESS; }
    }
}
