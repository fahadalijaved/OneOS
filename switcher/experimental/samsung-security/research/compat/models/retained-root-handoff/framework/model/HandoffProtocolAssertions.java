package model;

import com.fahadali.oneos.core.root.RetainedHostControlProtocol;
import java.io.IOException;
import java.util.Arrays;

/** Actual shared codec public API assertions. They confer no process/custody proof. */
public final class HandoffProtocolAssertions {
    private static int checks;
    private interface Action { void run() throws Throwable; }
    private static void yes(boolean value) { checks++; if (!value) throw new AssertionError("handoff protocol assertion " + checks); }
    private static void refuses(Action action) throws Throwable {
        Throwable found = null;
        try { action.run(); } catch (Throwable failure) { found = failure; }
        yes(found instanceof IOException || found instanceof IllegalArgumentException);
    }
    public static int run() throws Throwable {
        byte[] committed = RetainedHostControlProtocol.frame(9, 1, 1);
        RetainedHostControlProtocol.check(committed, 9, 1, 1);
        RetainedHostControlProtocol.zeroTail(committed, 16);
        yes(Arrays.equals(committed, HandoffWire.reply(9, 1, 1)));
        for (int offset : new int[]{0, 4, 6, 7, 8, 12}) {
            final byte[] wrong = HandoffWire.corrupt(committed, offset, (committed[offset] & 255) ^ 1);
            refuses(() -> RetainedHostControlProtocol.check(wrong, 9, 1, 1));
        }
        refuses(() -> RetainedHostControlProtocol.check(Arrays.copyOf(committed, 63), 9, 1, 1));
        refuses(() -> RetainedHostControlProtocol.check(Arrays.copyOf(committed, 65), 9, 1, 1));
        final byte[] nonzero = HandoffWire.corrupt(committed, 63, 1);
        refuses(() -> RetainedHostControlProtocol.zeroTail(nonzero, 16));
        byte[] field = new byte[4];
        RetainedHostControlProtocol.putU32(field, 0, 0xffffffffL);
        yes(RetainedHostControlProtocol.readU32(field, 0) == 0xffffffffL);
        refuses(() -> RetainedHostControlProtocol.putU32(field, 0, 0x100000000L));
        refuses(() -> RetainedHostControlProtocol.positivePid(0));
        refuses(() -> RetainedHostControlProtocol.positivePid(0x80000000L));
        yes(RetainedHostControlProtocol.positivePid(Integer.MAX_VALUE) == Integer.MAX_VALUE);
        String good = "oneos.orh." + "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        RetainedHostControlProtocol.validateOffer(321, good);
        refuses(() -> RetainedHostControlProtocol.validateOffer(321, good.substring(1)));
        refuses(() -> RetainedHostControlProtocol.validateOffer(321, good.substring(0, 41) + "G"));
        return checks;
    }
}
