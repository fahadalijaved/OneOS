package model;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/** Peer-input fixtures from the frozen ORSH/v2 wire contract, never source custody. */
public final class HandoffWire {
    private HandoffWire() { }
    public static byte[] reply(int kind, int sequence, int status) {
        byte[] bytes = new byte[64];
        ByteBuffer out = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);
        out.put(new byte[]{'O','R','S','H'}).putShort((short)2).putShort((short)kind);
        out.putInt(sequence).putInt(status);
        return bytes;
    }
    public static byte[] offer(int nativePid, String abstractName) {
        byte[] name = abstractName.getBytes(StandardCharsets.US_ASCII);
        if (name.length != 42) throw new IllegalArgumentException("42-byte fixture address required");
        for (byte value : name) if ((value & 255) < 33 || (value & 255) > 126)
            throw new IllegalArgumentException("printable fixture address required");
        byte[] bytes = reply(2, 0, 1);
        ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).putInt(16, nativePid);
        System.arraycopy(name, 0, bytes, 20, name.length);
        return bytes;
    }
    public static byte[] identity(int nativePid) {
        byte[] bytes = reply(3, 0, 1);
        ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).putInt(16, nativePid);
        return bytes;
    }
    public static byte[] corrupt(byte[] original, int offset, int value) {
        byte[] copy = original.clone();
        if (offset < 0 || offset >= copy.length) throw new IllegalArgumentException("fixture offset");
        copy[offset] = (byte)value;
        return copy;
    }
}
