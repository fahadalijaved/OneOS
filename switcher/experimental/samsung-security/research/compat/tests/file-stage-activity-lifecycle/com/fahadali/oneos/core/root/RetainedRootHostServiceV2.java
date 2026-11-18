package com.fahadali.oneos.core.root;

import android.os.Binder;
import android.os.IBinder;

/** Modeled launcher boundary with one broker and one opaque attempt. */
public final class RetainedRootHostServiceV2 {
    public static final IBinder BROKER = new Binder();
    private static final ViewAttempt ATTEMPT = new ViewAttempt();
    public static volatile int claims, prepares, stops, statusReads;
    public static volatile int sample = RetainedViewAppProtocol.STATUS_PARTIAL;

    public static ViewAttempt claimView(IBinder actual) {
        if (actual != BROKER) throw new AssertionError("wrong modeled broker");
        claims++;
        return ATTEMPT;
    }

    public static final class ViewAttempt {
        private ViewAttempt() { }

        public int prepare() {
            prepares++;
            return RetainedViewAppProtocol.QUEUED;
        }

        public int stop() {
            stops++;
            return RetainedViewAppProtocol.QUEUED;
        }

        public int status() {
            statusReads++;
            return prepares == 0 ? RetainedViewAppProtocol.STATUS_READY_TO_PREPARE : sample;
        }

        public boolean stopAcknowledged() { return stops != 0; }
    }
}
