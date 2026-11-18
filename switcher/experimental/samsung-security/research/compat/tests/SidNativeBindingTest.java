package com.appleexploit.oneos.security.compat;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Random;

/** Runs authored Windows JNI only, in a fresh process for every failure stage. */
public final class SidNativeBindingTest {
    private static int checks;

    private static native void configureFailure0(int stage);
    private static native int anchors0(Class<?> helper, Class<?> target);

    private static final class StaticTarget {
        private static native long nativeSidFromPasswordHandle(byte[] handle);
    }

    private static final class JavaTarget {
        private long nativeSidFromPasswordHandle(byte[] handle) { return 0; }
    }

    private static final class PublicTarget {
        public native long nativeSidFromPasswordHandle(byte[] handle);
    }

    private static void require(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    private static void requireRepeatRefused(String path) throws Exception {
        try {
            SidNativeBinding.loadAndBindOnce(path, SidSyntheticTarget.class);
            throw new AssertionError("Java retry accepted");
        } catch (IllegalStateException expected) {
            checks++;
        }
        Method nativeBind = SidNativeBinding.class.getDeclaredMethod("bind0", Class.class);
        nativeBind.setAccessible(true);
        try {
            nativeBind.invoke(null, SidSyntheticTarget.class);
            throw new AssertionError("native retry accepted");
        } catch (InvocationTargetException expected) {
            require(expected.getCause() instanceof IllegalStateException, "native retry refused");
        }
    }

    private static void validResults() {
        SidSyntheticTarget target = new SidSyntheticTarget();
        byte[] fixed = {(byte) 0xfa, 8, 7, 6, 5, 4, 3, 2, 1};
        require(target.extract(fixed) == 0x0102030405060708L, "native fixed vector");
        Random random = new Random(0x4a4e495349444cL);
        for (int i = 0; i < 10000; ++i) {
            byte[] input = new byte[9 + random.nextInt(504)];
            random.nextBytes(input);
            byte[] before = input.clone();
            require(target.extract(input) == PasswordHandleSid.extract(input), "Java oracle equality");
            require(Arrays.equals(before, input), "native nonmutation");
        }
        byte[] zero = new byte[9];
        require(target.extract(zero) == 0, "legitimate zero pattern");
        Arrays.fill(zero, (byte) 0xff);
        require(target.extract(zero) == -1L, "all-one pattern");
        Arrays.fill(zero, (byte) 0);
        zero[8] = (byte) 0x80;
        require(target.extract(zero) == Long.MIN_VALUE, "sign bit preserved");
        try {
            target.extract(null);
            throw new AssertionError("native null accepted");
        } catch (NullPointerException expected) {
            require(expected.getMessage() == null, "native null has no message");
        }
        for (int length = 0; length < 9; ++length) {
            byte[] shortInput = new byte[length];
            byte[] before = shortInput.clone();
            try {
                target.extract(shortInput);
                throw new AssertionError("native short accepted");
            } catch (IllegalArgumentException expected) {
                require("Password handle is too short".equals(expected.getMessage()),
                        "native constant malformed message");
                require(Arrays.equals(before, shortInput), "rejected native nonmutation");
            }
        }
    }

    public static void main(String[] args) throws Exception {
        String path = args[0];
        int stage = Integer.parseInt(args[1]);
        // Own helper and own tests share this JVM's application loader.
        System.load(path);
        configureFailure0(stage);
        require(anchors0(SidNativeBinding.class, SidSyntheticTarget.class) == 0,
                "fresh native image has no anchors");
        if (stage == 0) {
            for (Class<?> invalid : new Class<?>[] {StaticTarget.class, JavaTarget.class,
                    PublicTarget.class, Object.class}) {
                try {
                    SidNativeBinding.loadAndBindOnce(path, invalid);
                    throw new AssertionError("wrong declaration accepted");
                } catch (IllegalArgumentException expected) {
                    checks++;
                }
                require(anchors0(SidNativeBinding.class, SidSyntheticTarget.class) == 0,
                        "preflight does not enter native binding");
            }
            SidNativeBinding.loadAndBindOnce(path, SidSyntheticTarget.class);
            require(anchors0(SidNativeBinding.class, SidSyntheticTarget.class) == 63,
                    "exact helper and target GlobalRefs plus ready");
            validResults();
        } else {
            try {
                SidNativeBinding.loadAndBindOnce(path, SidSyntheticTarget.class);
                throw new AssertionError("failure stage succeeded");
            } catch (OutOfMemoryError expected) {
                require(stage <= 2, "only anchor stages simulate OOM");
            } catch (IllegalStateException expected) {
                require(stage >= 3, "only registration stages use state error");
            }
            int expected = stage == 1 ? 4 : stage == 2 ? 21 : 55;
            require(anchors0(SidNativeBinding.class, SidSyntheticTarget.class) == expected,
                    "bounded anchors retained after failure");
            if (stage == 4) {
                try {
                    new SidSyntheticTarget().extract(new byte[9]);
                    throw new AssertionError("uncertain binding authorized read");
                } catch (IllegalStateException refused) {
                    checks++;
                }
            }
        }
        requireRepeatRefused(path);
        Field helperOwner = SidNativeBinding.class.getDeclaredField("HELPER_OWNER");
        Field targetOwner = SidNativeBinding.class.getDeclaredField("targetOwner");
        helperOwner.setAccessible(true);
        targetOwner.setAccessible(true);
        require(helperOwner.get(null) == SidNativeBinding.class, "Java helper owner retained");
        require(targetOwner.get(null) == SidSyntheticTarget.class, "Java target owner retained");
        int mask = anchors0(SidNativeBinding.class, SidSyntheticTarget.class);
        System.out.println("{\"pass\":true,\"stage\":" + stage + ",\"checks\":" + checks
                + ",\"anchorsMask\":" + mask + ",\"ownJniExecuted\":true,\"oemExecuted\":false}");
    }
}
