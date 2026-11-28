package com.fahadali.oneos.core.root;

/** App-to-host callback protocol for the retained preparation attempt only. */
public final class RetainedViewAppProtocol {
    public static final int APP_VIEW_PREPARE = 3;
    public static final int APP_VIEW_STOP = 4;
    public static final int APP_VIEW_STATUS = 5;

    public static final int UNAVAILABLE = 0;
    public static final int QUEUED = 1;
    /** Local observation of a mutation whose acknowledgment could not be verified. */
    public static final int UNCERTAIN = -1;

    public static final int STATUS_PENDING = 0;
    public static final int STATUS_PARTIAL = 1;
    public static final int STATUS_NEED_STAGE = 2;
    public static final int STATUS_REFUSED = 3;
    public static final int STATUS_CLOSING = 4;
    public static final int STATUS_CLEANUP_UNCONFIRMED = 5;
    public static final int STATUS_LOCAL_TERMINAL = 6;
    public static final int STATUS_LOCAL_CLEANUP_OBSERVED = 7;
    public static final int STATUS_STOPPED_BEFORE_DISPATCH = 8;
    public static final int STATUS_UNAVAILABLE = 9;

    private RetainedViewAppProtocol() {}

    public static boolean isMutationReply(int value) {
        return value == UNAVAILABLE || value == QUEUED;
    }

    public static boolean isStatus(int value) {
        return value >= STATUS_PENDING && value <= STATUS_UNAVAILABLE;
    }
}
