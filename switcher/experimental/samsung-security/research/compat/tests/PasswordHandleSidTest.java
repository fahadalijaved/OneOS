package com.appleexploit.oneos.security.compat;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.Random;

/** PC-only checks over synthetic arrays. No Android or OEM classes are loaded. */
public final class PasswordHandleSidTest {
    private static int checks;
    private static int validInputs;
    private static int rejectedInputs;

    private static void require(boolean condition, String name) {
        checks++;
        if (!condition) {
            throw new AssertionError(name);
        }
    }

    private static void checkValid(byte[] handle, long expected, String name) {
        byte[] before = handle.clone();
        long actual = PasswordHandleSid.extract(handle);
        require(actual == expected, name + " result");
        require(Arrays.equals(handle, before), name + " nonmutation");
        validInputs++;
    }

    private static void fixedVectors() {
        checkValid(new byte[] {(byte) 0xfe, 8, 7, 6, 5, 4, 3, 2, 1},
                0x0102030405060708L, "fixed offset/endian vector");
        checkValid(new byte[] {71, 0, 0, 0, 0, 0, 0, 0, (byte) 0x80},
                Long.MIN_VALUE, "high bit");
        checkValid(new byte[] {71, (byte) 0x80, 0, 0, 0, 0, 0, 0, 0},
                128L, "unsigned byte");
        long[] values = {0L, 1L, -1L, Long.MIN_VALUE, Long.MAX_VALUE,
                0x0123456789abcdefL, 0xfedcba9876543210L,
                0xaaaaaaaaaaaaaaaaL, 0x5555555555555555L};
        for (long value : values) {
            for (int length : new int[] {9, 10, 32, 128, 257}) {
                byte[] handle = new byte[length];
                Arrays.fill(handle, (byte) 0x93);
                ByteBuffer.wrap(handle).order(ByteOrder.LITTLE_ENDIAN).putLong(1, value);
                checkValid(handle, value, "synthetic edge pattern");
            }
        }
        byte[] bits = new byte[9];
        bits[0] = (byte) 0xff;
        for (int bit = 0; bit < 64; bit++) {
            Arrays.fill(bits, 1, bits.length, (byte) 0);
            bits[1 + bit / 8] = (byte) (1 << (bit % 8));
            long oracle = ByteBuffer.wrap(bits).order(ByteOrder.LITTLE_ENDIAN).getLong(1);
            checkValid(bits, oracle, "single-bit independent oracle");
        }
    }

    private static void independentOracle() {
        Random random = new Random(0x5349444f5241434cL);
        for (int sample = 0; sample < 20000; sample++) {
            byte[] handle = new byte[9 + random.nextInt(504)];
            random.nextBytes(handle);
            long oracle = ByteBuffer.wrap(handle).order(ByteOrder.LITTLE_ENDIAN).getLong(1);
            checkValid(handle, oracle, "random ByteBuffer oracle");
            // Header and trailing bytes are outside the exact extracted field.
            handle[0] ^= (byte) 0xff;
            Arrays.fill(handle, 9, handle.length, (byte) sample);
            checkValid(handle, oracle, "unrelated bytes ignored");
        }
        // Every possible version/header byte preserves the same SID bit pattern.
        byte[] handle = {0, 8, 7, 6, 5, 4, 3, 2, 1};
        for (int header = 0; header < 256; header++) {
            handle[0] = (byte) header;
            checkValid(handle, 0x0102030405060708L, "header does not authorize SID");
        }
    }

    private static void malformedInputs() {
        try {
            PasswordHandleSid.extract(null);
            throw new AssertionError("null accepted");
        } catch (NullPointerException expected) {
            require(expected.getMessage() == null, "null exception has no data/message");
            rejectedInputs++;
        }
        for (int length = 0; length < 9; length++) {
            byte[] handle = new byte[length];
            Arrays.fill(handle, (byte) 0xd7);
            byte[] before = handle.clone();
            try {
                PasswordHandleSid.extract(handle);
                throw new AssertionError("short input accepted");
            } catch (IllegalArgumentException expected) {
                require(expected.getClass() == IllegalArgumentException.class,
                        "explicit malformed exception");
                require("Password handle is too short".equals(expected.getMessage()),
                        "constant malformed message");
                require(Arrays.equals(handle, before), "malformed nonmutation");
                rejectedInputs++;
            }
        }
    }

    private static void retentionShape() throws Exception {
        Class<?> type = PasswordHandleSid.class;
        require(Modifier.isFinal(type.getModifiers()), "final helper");
        require(type.getDeclaredFields().length == 0, "no retained fields");
        Constructor<?>[] constructors = type.getDeclaredConstructors();
        require(constructors.length == 1 && Modifier.isPrivate(constructors[0].getModifiers()),
                "no public instances");
        Method[] methods = type.getDeclaredMethods();
        require(methods.length == 1, "single metadata entry point");
        Method extract = type.getDeclaredMethod("extract", byte[].class);
        require(Modifier.isPublic(extract.getModifiers())
                && Modifier.isStatic(extract.getModifiers())
                && extract.getReturnType() == long.class, "primitive stateless API");
    }

    public static void main(String[] args) throws Exception {
        fixedVectors();
        independentOracle();
        malformedInputs();
        retentionShape();
        System.out.println("{\"pass\":true,\"checks\":" + checks
                + ",\"validSyntheticInputs\":" + validInputs
                + ",\"rejectedSyntheticInputs\":" + rejectedInputs
                + ",\"oemExecuted\":false,\"androidExecuted\":false}");
    }
}
