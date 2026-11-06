package oneos.camera;

import java.io.IOException;

/**
 * The rotation of an MP4's video track, written into its track header (tkhd matrix) in place:
 * 36 bytes, the file's size and every other byte unchanged. Only a header still at the identity
 * matrix is written (a recorder that took the orientation itself is left alone). The matrices are
 * Android's MPEG4Writer's (writeCompositionMatrix) for 90, 180 and 270 degrees. java.io only.
 */
public final class OneOSMp4 {
    /** Positional reads and writes on the file. */
    public interface Io {
        int read(long pos, byte[] b, int n) throws IOException;
        void write(long pos, byte[] b) throws IOException;
        long size() throws IOException;
    }

    private static final int MOOV = 0x6d6f6f76, TRAK = 0x7472616b, TKHD = 0x746b6864, MDIA = 0x6d646961, HDLR = 0x68646c72, VIDE = 0x76696465;
    private static final int[] IDENTITY = {0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000};

    private OneOSMp4() {}

    /** True when a video track's header was written; false when there is none at the identity matrix. */
    public static boolean setRotation(Io io, int degrees) throws IOException {
        int[] m = matrix(degrees);
        if (m == null) return false;
        long[] moov = child(io, 0, io.size(), MOOV);
        if (moov == null) return false;
        boolean done = false;
        for (long p = moov[1]; p + 8 <= moov[2]; ) {
            long[] b = box(io, p, moov[2]);
            if (b == null) break;
            if (b[3] == TRAK && isVideo(io, b)) done |= write(io, b, m);
            p = b[2];
        }
        return done;
    }

    static int[] matrix(int degrees) {
        switch (((degrees % 360) + 360) % 360) {
            case 90: return new int[] {0, 0x10000, 0, -0x10000, 0, 0, 0, 0, 0x40000000};
            case 180: return new int[] {-0x10000, 0, 0, 0, -0x10000, 0, 0, 0, 0x40000000};
            case 270: return new int[] {0, -0x10000, 0, 0x10000, 0, 0, 0, 0, 0x40000000};
            default: return null;
        }
    }

    /** {start, payload start, end, type} of the box at pos, or null. */
    static long[] box(Io io, long pos, long limit) throws IOException {
        byte[] h = new byte[8];
        if (io.read(pos, h, 8) < 8) return null;
        long size = u32(h, 0);
        long type = u32(h, 4);
        long hdr = 8;
        if (size == 1) {
            if (io.read(pos + 8, h, 8) < 8) return null;
            size = (u32(h, 0) << 32) | u32(h, 4);
            hdr = 16;
        } else if (size == 0) {
            size = limit - pos;
        }
        if (size < hdr || pos + size > limit) return null;
        return new long[] {pos, pos + hdr, pos + size, type};
    }

    static long[] child(Io io, long from, long to, int type) throws IOException {
        for (long p = from; p + 8 <= to; ) {
            long[] b = box(io, p, to);
            if (b == null) return null;
            if (b[3] == type) return b;
            p = b[2];
        }
        return null;
    }

    static boolean isVideo(Io io, long[] trak) throws IOException {
        long[] mdia = child(io, trak[1], trak[2], MDIA);
        long[] hdlr = mdia == null ? null : child(io, mdia[1], mdia[2], HDLR);
        if (hdlr == null || hdlr[1] + 12 > hdlr[2]) return false;
        byte[] t = new byte[4];
        return io.read(hdlr[1] + 8, t, 4) == 4 && u32(t, 0) == VIDE;
    }

    static boolean write(Io io, long[] trak, int[] m) throws IOException {
        long[] tkhd = child(io, trak[1], trak[2], TKHD);
        if (tkhd == null) return false;
        byte[] v = new byte[1];
        if (io.read(tkhd[1], v, 1) < 1) return false;
        long off = tkhd[1] + (v[0] == 1 ? 36 : 24) + 16;
        if (off + 36 > tkhd[2]) return false;
        byte[] cur = new byte[36];
        if (io.read(off, cur, 36) < 36) return false;
        for (int i = 0; i < 9; i++) if ((int) u32(cur, i * 4) != IDENTITY[i]) return false;
        byte[] out = new byte[36];
        for (int i = 0; i < 9; i++) {
            out[i * 4] = (byte) (m[i] >>> 24);
            out[i * 4 + 1] = (byte) (m[i] >>> 16);
            out[i * 4 + 2] = (byte) (m[i] >>> 8);
            out[i * 4 + 3] = (byte) m[i];
        }
        io.write(off, out);
        return true;
    }

    private static long u32(byte[] b, int o) {
        return ((b[o] & 0xffL) << 24) | ((b[o + 1] & 0xffL) << 16) | ((b[o + 2] & 0xffL) << 8) | (b[o + 3] & 0xffL);
    }
}
