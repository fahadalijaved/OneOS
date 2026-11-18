package com.fahadali.oneos.core.root;

/** Closed root-session framing only; this class issues no authority. */
final class RetainedRootProtocol {
    static final int FRAME_BYTES = 64;
    static final int PAYLOAD = 16;
    static final int VERSION = 1;
    static final int INIT = 1, OFFER = 2, IDENTITY = 3, PING = 4;
    static final int PONG = 5, CLOSE = 6, CLOSED = 7, ERROR = 255;
    static final int REQUEST = 0, ADMISSION_CLOSED = 1, LOCAL_CLOSED = 2, REFUSED = 3;
    private RetainedRootProtocol() { }
}
