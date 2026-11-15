package com.android.server.locksettings;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * OneOS: the guest's own screen lock (PIN, password or pattern), kept in the guest's data.
 *
 * The guest shares the phone's gatekeeper, weaver and keystore daemon, so its framework never
 * sets a real screen lock (patches/guest_no_gatekeeper.py). This class is the whole of the lock
 * a guest can have instead: one small record in the guest's /data/system that the guest's
 * LockSettingsService asks (patches/guest_local_lock.py). Nothing here talks to a HAL or a
 * daemon, and nothing of One UI's is read or written.
 *
 * What it is: a lock for the guest's lock screen while the guest runs. What it is not: device
 * encryption or a hardware-backed secret. The guest's data is a plain folder on the phone, and a
 * restart of the phone goes back to One UI, where root can remove the record (that is also the
 * way out of a forgotten lock). The record keeps a salted, slow hash, never the credential.
 *
 * Record, one ASCII line: "1 <type> <iterations> <salt hex> <hash hex>", written to a temporary
 * file, synced and renamed. hash = PBKDF2-HMAC-SHA256 over the lower-case hex of
 * SHA-256(credential), 32 bytes. A record that cannot be read counts as no lock.
 *
 * Tries, one ASCII line: "<failures> <deadline, wall clock ms>". The count goes up before a guess
 * is evaluated and is cleared by a match, as the gatekeeper does it, and the waits are the
 * gatekeeper's: 30 s after the 5th and 10th failure, 30 s after each from the 11th, doubling
 * every ten from the 30th, one day from the 140th. A wait runs on the elapsed-realtime clock;
 * after a restart of the guest the stored wall-clock deadline is used, never longer than the
 * wait that belongs to the count.
 *
 * Pure java.* and javax.crypto: the same source runs on a desktop JVM for its tests
 * (scripts/test-guest-local-lock.py). Clocks and the folder come from the caller. No method here
 * throws.
 */
public final class OneOSGuestLock {
    /** verify(): no guest lock is set; the caller takes the framework's own path. */
    public static final long NOT_SET = -1L;
    /** verify(): the credential matched. */
    public static final long MATCH = 0L;
    // verify() > 0: a wrong guess; (result - 1) ms to wait before the next one, may be 0.
    // verify() < -1: not looked at, a wait is running; (-result - 2) ms are left.

    /** change(): no guest lock and nothing to set; the caller takes the framework's own path. */
    public static final int CHANGE_NOT_HANDLED = -1;
    public static final int CHANGE_REFUSED = 0;
    public static final int CHANGE_DONE = 1;

    // LockPatternUtils.CREDENTIAL_TYPE_*.
    static final int TYPE_NONE = -1;
    static final int TYPE_PATTERN = 1;
    static final int TYPE_PIN = 3;
    static final int TYPE_PASSWORD = 4;

    static final int ITERATIONS = 100000;
    static final int MIN_LENGTH = 4;
    static final String RECORD = "oneos_guest_lock";
    static final String TRIES = "oneos_guest_lock.tries";
    private static final int MAX_FAILURES = 1000000;

    private static File sDir = new File("/data/system");
    private static volatile boolean sLoaded;
    private static volatile int sType = TYPE_NONE;
    private static int sIterations;
    private static byte[] sSalt;
    private static byte[] sHash;
    private static boolean sTriesLoaded;
    private static int sFailures;
    /** Elapsed-realtime ms until which no guess is looked at; 0 when no wait is running. */
    private static long sLockedUntil;

    private OneOSGuestLock() {
    }

    /** Tests: another folder, and everything read again. */
    static synchronized void useDir(File dir) {
        sDir = dir;
        sLoaded = false;
        sType = TYPE_NONE;
        sSalt = null;
        sHash = null;
        sTriesLoaded = false;
        sFailures = 0;
        sLockedUntil = 0;
    }

    /**
     * What ILockSettings.getCredentialType() answers: the guest lock's type for user 0 when one
     * is set, else the framework's own answer.
     */
    public static int credentialType(int userId, int nativeType) {
        if (userId != 0) {
            return nativeType;
        }
        try {
            if (!sLoaded) {
                synchronized (OneOSGuestLock.class) {
                    loadRecord();
                }
            }
            int type = sType;
            return type != TYPE_NONE ? type : nativeType;
        } catch (Throwable t) {
            return nativeType;
        }
    }

    /** The wait that follows the given number of failures in a row, in ms. */
    static long timeoutMs(int failures) {
        if (failures <= 0) {
            return 0L;
        }
        if (failures <= 10) {
            return failures % 5 == 0 ? 30000L : 0L;
        }
        if (failures < 30) {
            return 30000L;
        }
        if (failures < 140) {
            return 30000L << ((failures - 30) / 10);
        }
        return 86400000L;
    }

    /**
     * One guess at user 0's guest lock. See NOT_SET, MATCH and the two ranges above.
     *
     * @param elapsed SystemClock.elapsedRealtime()
     * @param wall    System.currentTimeMillis()
     */
    public static synchronized long verify(byte[] credential, long elapsed, long wall) {
        try {
            loadRecord();
            if (sType == TYPE_NONE) {
                return NOT_SET;
            }
            loadTries(elapsed, wall);
            long left = sLockedUntil - elapsed;
            if (sLockedUntil != 0 && left > 0) {
                return -2L - left;
            }
            sLockedUntil = 0;
            if (credential == null || credential.length == 0) {
                return 1L;
            }
            int failures = sFailures < MAX_FAILURES ? sFailures + 1 : MAX_FAILURES;
            long timeout = timeoutMs(failures);
            sFailures = failures;
            sLockedUntil = timeout > 0 ? elapsed + timeout : 0;
            writeTries(failures, timeout > 0 ? wall + timeout : 0);
            byte[] hash = derive(credential, sSalt, sIterations);
            boolean match = MessageDigest.isEqual(hash, sHash);
            Arrays.fill(hash, (byte) 0);
            if (!match) {
                return 1L + timeout;
            }
            sFailures = 0;
            sLockedUntil = 0;
            new File(sDir, TRIES).delete();
            return MATCH;
        } catch (Throwable t) {
            return 1L;
        }
    }

    /**
     * Sets, changes or removes user 0's guest lock. With a lock set, the saved credential has to
     * match first (one guess, counted like any other).
     *
     * @param newType LockPatternUtils.CREDENTIAL_TYPE_* of the new credential; NONE removes
     */
    public static synchronized int change(int newType, byte[] newCredential,
            byte[] savedCredential, long elapsed, long wall) {
        try {
            loadRecord();
            boolean remove = newType == TYPE_NONE || newCredential == null
                    || newCredential.length == 0;
            if (sType == TYPE_NONE) {
                if (remove) {
                    return CHANGE_NOT_HANDLED;
                }
            } else if (verify(savedCredential, elapsed, wall) != MATCH) {
                return CHANGE_REFUSED;
            }
            if (remove) {
                return forget() ? CHANGE_DONE : CHANGE_REFUSED;
            }
            if (newType != TYPE_PATTERN && newType != TYPE_PIN && newType != TYPE_PASSWORD) {
                return CHANGE_REFUSED;
            }
            if (newCredential.length < MIN_LENGTH) {
                return CHANGE_REFUSED;
            }
            byte[] salt = new byte[16];
            new SecureRandom().nextBytes(salt);
            byte[] hash = derive(newCredential, salt, ITERATIONS);
            String line = "1 " + newType + " " + ITERATIONS + " " + hex(salt) + " " + hex(hash)
                    + "\n";
            Arrays.fill(hash, (byte) 0);
            if (!writeFile(RECORD, line, true)) {
                return CHANGE_REFUSED;
            }
            // What is on the disk is what the next unlock gets: read it back and try it.
            sLoaded = false;
            loadRecord();
            boolean good = sType == newType;
            if (good) {
                byte[] again = derive(newCredential, sSalt, sIterations);
                good = MessageDigest.isEqual(again, sHash);
                Arrays.fill(again, (byte) 0);
            }
            if (!good) {
                forget();
                return CHANGE_REFUSED;
            }
            sFailures = 0;
            sLockedUntil = 0;
            new File(sDir, TRIES).delete();
            return CHANGE_DONE;
        } catch (Throwable t) {
            return CHANGE_REFUSED;
        }
    }

    private static boolean forget() {
        File record = new File(sDir, RECORD);
        record.delete();
        if (record.exists()) {
            return false;
        }
        new File(sDir, TRIES).delete();
        new File(sDir, RECORD + ".tmp").delete();
        sType = TYPE_NONE;
        sSalt = null;
        sHash = null;
        sFailures = 0;
        sLockedUntil = 0;
        sLoaded = true;
        return true;
    }

    private static void loadRecord() {
        if (sLoaded) {
            return;
        }
        int type = TYPE_NONE;
        int iterations = 0;
        byte[] salt = null;
        byte[] hash = null;
        try {
            String text = readFile(RECORD);
            if (text != null) {
                String[] f = text.trim().split(" ");
                if (f.length == 5 && f[0].equals("1")) {
                    int t = Integer.parseInt(f[1]);
                    int n = Integer.parseInt(f[2]);
                    byte[] s = unhex(f[3]);
                    byte[] h = unhex(f[4]);
                    if ((t == TYPE_PATTERN || t == TYPE_PIN || t == TYPE_PASSWORD)
                            && n >= 1000 && n <= 10000000
                            && s != null && s.length == 16 && h != null && h.length == 32) {
                        type = t;
                        iterations = n;
                        salt = s;
                        hash = h;
                    }
                }
            }
        } catch (Throwable t) {
            type = TYPE_NONE;
        }
        sIterations = iterations;
        sSalt = salt;
        sHash = hash;
        sType = type;
        sLoaded = true;
    }

    private static void loadTries(long elapsed, long wall) {
        if (sTriesLoaded) {
            return;
        }
        sTriesLoaded = true;
        int failures = 0;
        long deadline = 0;
        try {
            String text = readFile(TRIES);
            if (text != null) {
                String[] f = text.trim().split(" ");
                if (f.length == 2) {
                    failures = Integer.parseInt(f[0]);
                    deadline = Long.parseLong(f[1]);
                }
            }
        } catch (Throwable t) {
            failures = 0;
            deadline = 0;
        }
        if (failures < 0) {
            failures = 0;
        }
        if (failures > MAX_FAILURES) {
            failures = MAX_FAILURES;
        }
        long left = deadline > 0 ? deadline - wall : 0;
        long most = timeoutMs(failures);
        if (left > most) {
            left = most;
        }
        sFailures = failures;
        sLockedUntil = left > 0 ? elapsed + left : 0;
    }

    private static void writeTries(int failures, long deadline) {
        writeFile(TRIES, failures + " " + deadline + "\n", false);
    }

    /** PBKDF2-HMAC-SHA256, one 32-byte block, over the hex of SHA-256(credential). */
    static byte[] derive(byte[] credential, byte[] salt, int iterations) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(credential);
        byte[] key = hex(digest).getBytes("US-ASCII");
        Arrays.fill(digest, (byte) 0);
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        Arrays.fill(key, (byte) 0);
        mac.update(salt);
        mac.update(new byte[] {0, 0, 0, 1});
        byte[] u = new byte[32];
        mac.doFinal(u, 0);
        byte[] out = u.clone();
        for (int i = 1; i < iterations; i++) {
            mac.update(u);
            mac.doFinal(u, 0);
            for (int j = 0; j < 32; j++) {
                out[j] ^= u[j];
            }
        }
        Arrays.fill(u, (byte) 0);
        return out;
    }

    private static String readFile(String name) {
        File file = new File(sDir, name);
        if (!file.isFile() || file.length() > 512) {
            return null;
        }
        FileInputStream in = null;
        try {
            in = new FileInputStream(file);
            byte[] buf = new byte[512];
            int n = 0;
            while (n < buf.length) {
                int r = in.read(buf, n, buf.length - n);
                if (r <= 0) {
                    break;
                }
                n += r;
            }
            return new String(buf, 0, n, "US-ASCII");
        } catch (Throwable t) {
            return null;
        } finally {
            if (in != null) {
                try {
                    in.close();
                } catch (Throwable t) {
                    // Nothing to do.
                }
            }
        }
    }

    /** Temporary file, optional sync, rename: the old content or the new, never half of one. */
    private static boolean writeFile(String name, String text, boolean sync) {
        File tmp = new File(sDir, name + ".tmp");
        File file = new File(sDir, name);
        FileOutputStream out = null;
        try {
            tmp.delete();
            out = new FileOutputStream(tmp);
            tmp.setReadable(false, false);
            tmp.setWritable(false, false);
            tmp.setReadable(true, true);
            tmp.setWritable(true, true);
            out.write(text.getBytes("US-ASCII"));
            out.flush();
            if (sync) {
                out.getFD().sync();
            }
            out.close();
            out = null;
            if (tmp.renameTo(file)) {
                return true;
            }
            tmp.delete();
            return false;
        } catch (Throwable t) {
            tmp.delete();
            return false;
        } finally {
            if (out != null) {
                try {
                    out.close();
                } catch (Throwable t) {
                    // Nothing to do.
                }
            }
        }
    }

    private static String hex(byte[] bytes) {
        char[] digits = "0123456789abcdef".toCharArray();
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            out[2 * i] = digits[(bytes[i] >> 4) & 15];
            out[2 * i + 1] = digits[bytes[i] & 15];
        }
        return new String(out);
    }

    private static byte[] unhex(String text) {
        if (text.length() % 2 != 0) {
            return null;
        }
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int hi = Character.digit(text.charAt(2 * i), 16);
            int lo = Character.digit(text.charAt(2 * i + 1), 16);
            if (hi < 0 || lo < 0) {
                return null;
            }
            out[i] = (byte) (hi * 16 + lo);
        }
        return out;
    }
}
