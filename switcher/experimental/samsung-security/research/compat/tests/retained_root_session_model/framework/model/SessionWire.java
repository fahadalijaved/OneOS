package model;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/** Authored frame generator/observations, not a native or production decoder. */
public final class SessionWire {
    public static final int CALLER_PID=1234,CALLER_UID=10234,NATIVE_PID=2345;
    public static final String ADDRESS="oneos.rs.0123456789abcdef0123456789abcdef";
    public static byte[] frame(int kind,int sequence,int status) {
        byte[] bytes=new byte[64];ByteBuffer b=ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);
        b.put(new byte[]{'O','R','S','C'}).putShort((short)1).putShort((short)kind).putInt(sequence).putInt(status);
        return bytes;
    }
    public static byte[] offer() {
        byte[] bytes=frame(2,0,1);ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).putInt(16,SessionModel.nativePid);
        byte[] address=ADDRESS.getBytes(StandardCharsets.US_ASCII);System.arraycopy(address,0,bytes,20,address.length);return bytes;
    }
    public static byte[] identity() {
        byte[] bytes=frame(3,0,1);ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).putInt(16,SessionModel.nativePid);return bytes;
    }
    public static int kind(byte[] bytes) {return ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).getShort(6)&0xffff;}
    public static int sequence(byte[] bytes) {return ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).getInt(8);}
    public static boolean sourceInit(byte[] bytes) {
        byte[] expected=frame(1,0,0);ByteBuffer b=ByteBuffer.wrap(expected).order(ByteOrder.BIG_ENDIAN);
        b.putInt(16,SessionModel.callerPid).putInt(20,SessionModel.callerUid);return java.util.Arrays.equals(bytes,expected);
    }
}
