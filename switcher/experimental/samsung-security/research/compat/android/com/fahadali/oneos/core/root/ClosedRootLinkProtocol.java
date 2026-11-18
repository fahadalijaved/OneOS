package com.fahadali.oneos.core.root;

/** Closed control association only. No credential, guest or authority operation. */
public final class ClosedRootLinkProtocol {
    public static final int VERSION = 1;
    public static final String SERVICE_CLASS = "com.fahadali.oneos.core.root.RetainedRootHostService";
    public static final String BROKER = "com.fahadali.oneos.IRetainedRootBroker.v1";
    public static final String CALLBACK = "com.fahadali.oneos.IRetainedRootHost.v1";
    public static final String CONTROL = "com.fahadali.oneos.IRetainedRootControl.v1";
    public static final int BEGIN = 1;
    public static final int CAPTURED = 1, FAILED = 2;
    public static final int PING = 1, REQUEST_CLOSE = 2, QUERY_STATE = 3;
    public static final int QUEUED = 1;
    public static final int UNAVAILABLE = 1;
    public static final int STARTING = 0, ADMISSION_CLOSED = 1, CLOSING = 2;
    public static final int CLOSED = 3, UNRESOLVED = 4;
    private ClosedRootLinkProtocol() { }
}
