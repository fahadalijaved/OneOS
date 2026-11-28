package com.fahadali.oneos.core.root;

import java.io.IOException;

/** Closed-only direct-host transport. These bytes grant no security authority. */
public final class RetainedHostControlProtocol {
    public static final int VERSION = 2;
    public static final String SERVICE_CLASS = "com.fahadali.oneos.core.root.RetainedRootHostServiceV2";
    public static final String BROKER = "com.fahadali.oneos.IRetainedRootBroker.v2";
    public static final String CALLBACK = "com.fahadali.oneos.IRetainedRootHost.v2";
    public static final String NATIVE_NAME_PREFIX = "oneos.orh.";
    public static final int BEGIN = 1, OFFER = 1, FAILED = 2;
    public static final int QUEUED = 1, UNAVAILABLE = 1;
    public static final int FRAME_BYTES = 64, PAYLOAD_OFFSET = 16, NAME_BYTES = 42;
    public static final int INIT = 1, NATIVE_OFFER = 2, IDENTITY = 3;
    public static final int PING = 4, PONG = 5, CLOSE = 6, CLOSED = 7;
    public static final int COMMIT = 8, COMMITTED = 9;
    public static final int REQUEST = 0, ADMISSION_CLOSED = 1, LOCAL_CLOSED = 2, REFUSED = 3;

    private RetainedHostControlProtocol() { }

    public static byte[] frame(int kind, long sequence, int status) {
        if (kind < INIT || kind > COMMITTED || sequence < 0 || sequence > 0xffffffffL
                || status < REQUEST || status > REFUSED) {
            throw new IllegalArgumentException("Bounded direct-host frame required");
        }
        byte[] value = new byte[FRAME_BYTES];
        value[0] = 'O'; value[1] = 'R'; value[2] = 'S'; value[3] = 'H';
        value[5] = VERSION;
        value[7] = (byte) kind;
        putU32(value, 8, sequence);
        putU32(value, 12, status);
        return value;
    }

    public static void check(byte[] value, int kind, long sequence, int status) throws IOException {
        if (value == null || value.length != FRAME_BYTES || value[0] != 'O'
                || value[1] != 'R' || value[2] != 'S' || value[3] != 'H'
                || value[4] != 0 || (value[5] & 255) != VERSION || value[6] != 0
                || (value[7] & 255) != kind || readU32(value, 8) != sequence
                || readU32(value, 12) != status) {
            throw new IOException("Direct-host frame mismatch");
        }
    }

    public static void putU32(byte[] value, int offset, long number) {
        if (value == null || offset < 0 || offset > value.length - 4
                || number < 0 || number > 0xffffffffL) {
            throw new IllegalArgumentException("Bounded unsigned field required");
        }
        value[offset] = (byte) (number >>> 24);
        value[offset + 1] = (byte) (number >>> 16);
        value[offset + 2] = (byte) (number >>> 8);
        value[offset + 3] = (byte) number;
    }

    public static long readU32(byte[] value, int offset) {
        if (value == null || offset < 0 || offset > value.length - 4) {
            throw new IllegalArgumentException("Bounded unsigned field required");
        }
        return ((long) (value[offset] & 255) << 24)
                | ((long) (value[offset + 1] & 255) << 16)
                | ((long) (value[offset + 2] & 255) << 8) | (value[offset + 3] & 255);
    }

    public static int positivePid(long value) throws IOException {
        if (value < 1 || value > Integer.MAX_VALUE) throw new IOException("Invalid native PID");
        return (int) value;
    }

    public static void zeroTail(byte[] value, int offset) throws IOException {
        if (value == null || offset < 0 || offset > value.length) {
            throw new IOException("Invalid reserved-byte range");
        }
        for (int n = offset; n < value.length; n++) {
            if (value[n] != 0) throw new IOException("Nonzero reserved bytes");
        }
    }

    public static void validateOffer(int pid, String name) throws IOException {
        positivePid(pid);
        if (name == null || name.length() != NAME_BYTES || !name.startsWith(NATIVE_NAME_PREFIX)) {
            throw new IOException("Invalid direct-host address");
        }
        for (int n = NATIVE_NAME_PREFIX.length(); n < name.length(); n++) {
            char c = name.charAt(n);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) {
                throw new IOException("Invalid direct-host address");
            }
        }
    }
}
