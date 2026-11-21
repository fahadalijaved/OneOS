import android.os.IBinder;
import android.os.Parcel;

import java.io.File;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/**
 * OneOS (0.5.17): one key=value pair to AudioFlinger through the guest's own AudioSystem.setParameters, so the
 * binder call number is always this build's. guest_start.sh sent `service call media.audio_flinger 18`, which is
 * setParameters only in some builds (OxygenOS 16 on the A17: 20; a tester's module found it): there the Bluetooth
 * stream recovery and the call SIM slot did nothing. Run in the guest: app_process ... OneOSAudioParam "key=value".
 * Exits non-zero when the call could not be made, so the script can fall back.
 *
 * 0.5.33: `OneOSAudioParam --io 13,21 key=value` sends the pair to those output streams (AudioFlinger's
 * setParameters with an io handle), which AudioSystem.setParameters cannot: it always means io 0, the device.
 * Samsung's stream keys ("l_...") need it. The call number is read from this guest's own
 * audioflinger-aidl-cpp.so: the constant BpAudioFlingerService::setParameters moves into w1 right before its
 * transact (18 on One UI 8 on the A36). It is used only when getParameters' constant is the next number (the AIDL
 * order: setParameters, then getParameters), so a misread never calls another method; otherwise it exits 3.
 */
public final class OneOSAudioParam {
    private static final String KV = "[A-Za-z0-9_.]{1,64}=[A-Za-z0-9_.,-]{0,64}";
    private static final String SET = "_ZN7android5media21BpAudioFlingerService13setParametersEi";
    private static final String GET = "_ZN7android5media21BpAudioFlingerService13getParametersEi";

    public static void main(String[] args) throws Exception {
        if (args.length == 3 && args[0].equals("--io") && args[1].matches("[0-9]{1,6}(,[0-9]{1,6}){0,15}") && args[2].matches(KV)) {
            System.exit(toStreams(args[1], args[2]));
        }
        if (args.length != 1 || !args[0].matches(KV)) {
            System.out.println("usage: OneOSAudioParam key=value | OneOSAudioParam --io <io>[,<io>...] key=value");
            System.exit(2);
        }
        Class<?> as = Class.forName("android.media.AudioSystem");
        int r = (Integer) as.getMethod("setParameters", String.class).invoke(null, args[0]);
        System.out.println("AudioSystem.setParameters " + args[0] + ": " + r);
        System.exit(r == 0 ? 0 : 1);
    }

    private static int toStreams(String ios, String kv) throws Exception {
        int code = -1;
        String from = null;
        for (String lib : new String[] {"/system/lib64/audioflinger-aidl-cpp.so", "/system/lib64/libaudioclient.so"}) {
            if (!new File(lib).isFile()) continue;
            int set = transactCode(lib, SET), get = transactCode(lib, GET);
            if (set > 0 && get == set + 1) { code = set; from = lib; break; }
            if (set > 0 || get > 0) System.out.println(lib + ": setParameters " + set + ", getParameters " + get + ": not used");
        }
        if (code < 0) {
            System.out.println("setParameters call number not found");
            return 3;
        }
        IBinder af = (IBinder) Class.forName("android.os.ServiceManager").getMethod("getService", String.class)
            .invoke(null, "media.audio_flinger");
        if (af == null) {
            System.out.println("media.audio_flinger not found");
            return 1;
        }
        int bad = 0;
        StringBuilder out = new StringBuilder("setParameters (" + code + ", " + new File(from).getName() + ") " + kv + ":");
        for (String s : ios.split(",")) {
            int io = Integer.parseInt(s);
            Parcel d = Parcel.obtain(), r = Parcel.obtain();
            try {
                d.writeInterfaceToken("android.media.IAudioFlingerService");
                d.writeInt(io);
                d.writeString(kv);
                af.transact(code, d, r, 0);
                r.readException();
                out.append(" io ").append(io).append(" ok");
            } catch (Exception e) {
                bad++;
                out.append(" io ").append(io).append(" ").append(e.getClass().getSimpleName()).append(": ").append(e.getMessage());
            } finally {
                d.recycle();
                r.recycle();
            }
        }
        System.out.println(out);
        return bad == 0 ? 0 : 1;
    }

    /** The w1 constant right before the first indirect call in the named function of an arm64 ELF, or -1. */
    static int transactCode(String path, String prefix) {
        try (RandomAccessFile f = new RandomAccessFile(path, "r")) {
            if (f.length() > 64L << 20) return -1;
            byte[] all = new byte[(int) f.length()];
            f.readFully(all);
            ByteBuffer b = ByteBuffer.wrap(all).order(ByteOrder.LITTLE_ENDIAN);
            if (b.getInt(0) != 0x464c457f || all[4] != 2 || b.getShort(0x12) != 183) return -1; // ELF64, AArch64
            long shoff = b.getLong(0x28);
            int shentsize = b.getShort(0x3a) & 0xffff, shnum = b.getShort(0x3c) & 0xffff;
            long phoff = b.getLong(0x20);
            int phentsize = b.getShort(0x36) & 0xffff, phnum = b.getShort(0x38) & 0xffff;
            for (int i = 0; i < shnum; i++) {
                int sh = (int) (shoff + (long) i * shentsize);
                if (b.getInt(sh + 4) != 11) continue; // SHT_DYNSYM
                long symoff = b.getLong(sh + 0x18), symsize = b.getLong(sh + 0x20), ent = b.getLong(sh + 0x38);
                int strsh = (int) (shoff + (long) b.getInt(sh + 0x28) * shentsize);
                long stroff = b.getLong(strsh + 0x18);
                byte[] want = prefix.getBytes(StandardCharsets.US_ASCII);
                for (long s = symoff; s + 24 <= symoff + symsize; s += ent) {
                    int name = (int) (stroff + (b.getInt((int) s) & 0xffffffffL));
                    long value = b.getLong((int) s + 8), size = b.getLong((int) s + 16);
                    if (value == 0 || !startsWith(all, name, want)) continue;
                    long off = -1;
                    for (int p = 0; p < phnum; p++) {
                        int ph = (int) (phoff + (long) p * phentsize);
                        if (b.getInt(ph) != 1) continue; // PT_LOAD
                        long po = b.getLong(ph + 8), pv = b.getLong(ph + 0x10), pf = b.getLong(ph + 0x20);
                        if (value >= pv && value < pv + pf) off = po + (value - pv);
                    }
                    if (off < 0) return -1;
                    long end = off + Math.min(size > 0 ? size : 0x800, 0x800);
                    int movAt = -100, imm = -1, n = 0;
                    for (long a = off; a + 4 <= end && a + 4 <= all.length; a += 4, n++) {
                        int insn = b.getInt((int) a);
                        if ((insn & 0xffe0001f) == 0x52800001) { movAt = n; imm = (insn >>> 5) & 0xffff; } // movz w1, #imm
                        boolean blr = (insn & 0xfffffc1f) == 0xd63f0000 || (insn & 0xfefff800) == 0xd63f0800; // blr / blraa(z)
                        if (blr && n - movAt <= 3 && imm > 0 && imm < 1000) return imm;
                    }
                    return -1;
                }
            }
        } catch (Exception e) {
            return -1;
        }
        return -1;
    }

    private static boolean startsWith(byte[] all, int at, byte[] want) {
        if (at < 0 || at + want.length > all.length) return false;
        for (int i = 0; i < want.length; i++) if (all[at + i] != want[i]) return false;
        return true;
    }
}
