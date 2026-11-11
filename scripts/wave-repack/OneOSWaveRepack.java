/*
 * OneOSWaveRepack: append a replacement stored entry (classes3.dex) to a
 * signed APK without rebuilding the archive.
 *
 * This mirrors scripts/apk-replace-dex.py so the phone can rebuild ColorOS's
 * SystemUI from the image's own stock APK plus the small patched dex, instead
 * of downloading the whole 126 MB APK.
 *
 * It keeps every original byte, copies the stock file up to the APK Signing
 * Block, appends a new local entry, then writes the untouched signing block,
 * the patched central directory and a patched EOCD. The v1 META-INF signature
 * entries stay; like the Python tool, this is meant for system APKs whose
 * signatures are read, not verified, by PackageManager.
 *
 * Usage: OneOSWaveRepack <stock.apk> <entry-name> <new.dex> <out.apk>
 */

package com.oneos.wave;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public final class OneOSWaveRepack {
    private static final int EOCD_SIG = 0x06054b50;
    private static final int CD_SIG = 0x02014b50;
    private static final long MAX_EOCD_SEARCH = 65557L;
    private static final int COPY_CHUNK = 4 << 20;

    public static void main(String[] args) {
        if (args.length != 4) {
            System.err.println("usage: OneOSWaveRepack <stock.apk> <entry-name> <new.dex> <out.apk>");
            System.exit(2);
        }
        try {
            run(new File(args[0]), args[1], new File(args[2]), new File(args[3]));
        } catch (IOException e) {
            System.err.println("OneOSWaveRepack: " + e.getMessage());
            System.exit(1);
        }
    }

    private static void run(File stock, String entryName, File dexFile, File out)
            throws IOException {
        long stockLen = stock.length();
        if (stockLen <= 0) fail("stock APK is empty");
        long dexLen = dexFile.length();
        if (dexLen <= 0) fail("new dex is empty");
        if ((dexLen & 3) != 0) fail("new dex is not 4-byte aligned");

        final int tailLen = (int) Math.min(stockLen, MAX_EOCD_SEARCH + 22);
        byte[] tail = readAt(stock, stockLen - tailLen, tailLen);
        int e = -1;
        for (int i = tailLen - 22; i >= 0; i--) {
            if (le32(tail, i) == EOCD_SIG) {
                e = i;
                break;
            }
        }
        if (e < 0) fail("no EOCD in the last 64 KB");
        long eocdPos = stockLen - tailLen + e;
        if (eocdPos + 22 != stockLen) fail("EOCD is not at the end of the file");

        int disk = le16(tail, e + 4);
        int cdDisk = le16(tail, e + 6);
        int nDisk = le16(tail, e + 8);
        int nTotal = le16(tail, e + 10);
        long cdSize = le32(tail, e + 12);
        long cdOff = le32(tail, e + 16);
        int commentLen = le16(tail, e + 20);
        if (disk != 0 || cdDisk != 0 || nDisk != nTotal) fail("multi-disk or zip64 archive");
        if (commentLen != 0) fail("archive comment is not supported");
        if (cdOff + cdSize != eocdPos) fail("central directory is not adjacent to EOCD");
        if (cdSize > Integer.MAX_VALUE) fail("central directory is too large");

        byte[] magic = readAt(stock, cdOff - 16, 16);
        if (!new String(magic, StandardCharsets.US_ASCII).equals("APK Sig Block 42")) {
            fail("no APK Signing Block before the central directory");
        }
        long blkSize = le64(readAt(stock, cdOff - 24, 8), 0);
        long sigStart = cdOff - blkSize - 8;
        if (sigStart < 0) fail("signing block size is out of range");
        if (le64(readAt(stock, sigStart, 8), 0) != blkSize) {
            fail("signing block header does not match its size");
        }

        byte[] cd = readAt(stock, cdOff, (int) cdSize);
        int pos = 0;
        long lastEnd = 0;
        int rec = -1;
        int lho = -1;
        for (int i = 0; i < nTotal; i++) {
            if (pos + 46 > cd.length || le32(cd, pos) != CD_SIG) fail("bad central directory entry");
            int flags = le16(cd, pos + 8);
            int method = le16(cd, pos + 10);
            int nlen = le16(cd, pos + 28);
            int xlen = le16(cd, pos + 30);
            int mlen = le16(cd, pos + 32);
            long csize = le32(cd, pos + 20);
            int nameStart = pos + 46;
            if (nameStart + nlen + xlen + mlen > cd.length) fail("central directory overruns");
            String name = new String(cd, nameStart, nlen, StandardCharsets.UTF_8);
            long local = le32(cd, pos + 42);
            long end = local + 30 + nlen + xlen + csize;
            if (end > lastEnd) lastEnd = end;
            if (name.equals(entryName)) {
                if (rec >= 0) fail("entry appears twice: " + entryName);
                if (method != 0) fail("entry is compressed; only stored entries are supported");
                if ((flags & 0x41) != 0) fail("entry is encrypted");
                rec = pos;
                lho = (int) local;
            }
            pos += 46 + nlen + xlen + mlen;
        }
        if (rec < 0) fail("entry not found: " + entryName);
        if (pos != cd.length) fail("central directory size mismatch");
        if (lastEnd > sigStart) fail("entry data overlaps the APK Signing Block");

        byte[] nameBytes = entryName.getBytes(StandardCharsets.UTF_8);
        long off = sigStart;
        long align = (sigStart % 4096 == 0) ? 4096 : 4;
        long pad = (-(off + 30 + nameBytes.length + dexLen)) % align;
        if (pad < 0) pad += align;
        if (pad > 0xFFFF) fail("alignment padding does not fit a local header");
        if (((off + 30 + nameBytes.length + pad) & 3) != 0) fail("local header is not 4-byte aligned");

        byte[] localHdrIn = readAt(stock, lho, 30);
        CRC32 crc = new CRC32();
        byte[] buf = new byte[COPY_CHUNK];
        try (InputStream in = new java.io.FileInputStream(dexFile)) {
            int n;
            while ((n = in.read(buf)) > 0) crc.update(buf, 0, n);
        }
        long dexCrc = crc.getValue();

        ByteBuffer lfh = ByteBuffer.allocate(30 + nameBytes.length + (int) pad)
                .order(ByteOrder.LITTLE_ENDIAN);
        lfh.putInt(0x04034b50);
        lfh.putShort((short) le16(localHdrIn, 4));          // version needed
        lfh.putShort((short) (le16(localHdrIn, 6) & ~0x0008)); // flags, no data descriptor
        lfh.putShort((short) 0);                           // method: stored
        lfh.putShort((short) le16(localHdrIn, 10));         // mod time
        lfh.putShort((short) le16(localHdrIn, 12));         // mod date
        lfh.putInt((int) dexCrc);
        lfh.putInt((int) dexLen);
        lfh.putInt((int) dexLen);
        lfh.putShort((short) nameBytes.length);
        lfh.putShort((short) pad);
        lfh.put(nameBytes);
        for (int i = 0; i < pad; i++) lfh.put((byte) 0);
        lfh.flip();
        byte[] lfhBytes = new byte[lfh.remaining()];
        lfh.get(lfhBytes);

        put32(cd, rec + 16, (int) dexCrc);
        put32(cd, rec + 20, (int) dexLen);
        put32(cd, rec + 24, (int) dexLen);
        put32(cd, rec + 42, (int) off);

        long newCdOff = off + lfhBytes.length + dexLen + (cdOff - sigStart);
        if (newCdOff > Integer.MAX_VALUE) fail("output is too large for a 32-bit zip");
        byte[] eocd = new byte[22];
        System.arraycopy(tail, e, eocd, 0, 16);
        put32(eocd, 16, (int) newCdOff);
        put16(eocd, 20, 0);

        try (FileChannel in = new RandomAccessFile(stock, "r").getChannel();
             FileOutputStream fos = new FileOutputStream(out);
             FileChannel outCh = fos.getChannel()) {
            transfer(in, 0, sigStart, outCh);
            outCh.write(ByteBuffer.wrap(lfhBytes));
            try (FileChannel dexCh = new RandomAccessFile(dexFile, "r").getChannel()) {
                transfer(dexCh, 0, dexLen, outCh);
            }
            transfer(in, sigStart, cdOff - sigStart, outCh);
            outCh.write(ByteBuffer.wrap(cd));
            outCh.write(ByteBuffer.wrap(eocd));
            outCh.force(true);
        }

        verify(out, entryName, dexLen, dexCrc);
        System.out.println("OneOSWaveRepack: wrote " + out.getPath() + " (" + out.length() + " bytes)");
    }

    private static void verify(File out, String entryName, long dexLen, long dexCrc) throws IOException {
        try (ZipFile zip = new ZipFile(out)) {
            ZipEntry entry = zip.getEntry(entryName);
            if (entry == null) fail("rebuilt APK lost " + entryName);
            if (entry.getSize() != dexLen) fail("rebuilt APK has the wrong " + entryName + " size");
            if (entry.getCrc() != dexCrc) fail("rebuilt APK has the wrong " + entryName + " CRC");
            CRC32 crc = new CRC32();
            try (InputStream in = zip.getInputStream(entry)) {
                byte[] buf = new byte[COPY_CHUNK];
                int n;
                while ((n = in.read(buf)) > 0) crc.update(buf, 0, n);
            }
            if (crc.getValue() != dexCrc) fail("rebuilt " + entryName + " does not read back");
        }
    }

    private static void transfer(FileChannel in, long pos, long count, FileChannel out) throws IOException {
        long done = 0;
        while (done < count) {
            long n = in.transferTo(pos + done, count - done, out);
            if (n <= 0) fail("short read while copying the stock APK");
            done += n;
        }
    }

    private static byte[] readAt(File file, long pos, int len) throws IOException {
        if (pos < 0 || len < 0) fail("negative read");
        if (pos + len > file.length()) fail("read past the end of " + file.getName());
        ByteBuffer buf = ByteBuffer.allocate(len);
        try (FileChannel ch = new RandomAccessFile(file, "r").getChannel()) {
            while (buf.hasRemaining()) {
                int n = ch.read(buf, pos + buf.position());
                if (n < 0) fail("short read in " + file.getName());
            }
        }
        return buf.array();
    }

    private static int le16(byte[] b, int off) {
        return (b[off] & 0xff) | ((b[off + 1] & 0xff) << 8);
    }

    private static long le32(byte[] b, int off) {
        return ((long) (b[off] & 0xff))
                | ((long) (b[off + 1] & 0xff) << 8)
                | ((long) (b[off + 2] & 0xff) << 16)
                | ((long) (b[off + 3] & 0xff) << 24);
    }

    private static long le64(byte[] b, int off) {
        long v = 0;
        for (int i = 7; i >= 0; i--) v = (v << 8) | (b[off + i] & 0xffL);
        return v;
    }

    private static void put16(byte[] b, int off, int v) {
        b[off] = (byte) v;
        b[off + 1] = (byte) (v >> 8);
    }

    private static void put32(byte[] b, int off, int v) {
        b[off] = (byte) v;
        b[off + 1] = (byte) (v >> 8);
        b[off + 2] = (byte) (v >> 16);
        b[off + 3] = (byte) (v >> 24);
    }

    private static void fail(String message) throws IOException {
        throw new IOException(message);
    }

    private OneOSWaveRepack() {
    }
}
