import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/** Runs only the saved host class's side-effect-free profile parser on the PC. */
final class RetainedViewProfileProbe {
    private static final String[] KEYS = {"package", "signer", "apk", "code", "native", "bytes"};
    private static final String[] GETTERS = {
        "packageName", "signerSha256", "apkSha256", "versionCode", "nativeSha256", "nativeBytes"
    };

    public static void main(String[] fields) throws ReflectiveOperationException {
        if (fields.length != KEYS.length) throw new IllegalArgumentException("Exact profile fields required");
        Class<?> profile = Class.forName("com.appleexploit.oneos.security.authority.HostRootLinkProfileV2");
        Method parse = profile.getDeclaredMethod("parse", byte[].class, int.class);
        parse.setAccessible(true);

        StringBuilder document = new StringBuilder("version=2\n");
        for (int index = 0; index < KEYS.length; index++) {
            document.append(KEYS[index]).append('=').append(fields[index]).append('\n');
        }
        String exact = document.toString();
        Object parsed = parse(parse, exact);
        for (int index = 0; index < GETTERS.length; index++) {
            Method getter = profile.getDeclaredMethod(GETTERS[index]);
            getter.setAccessible(true);
            if (!fields[index].equals(String.valueOf(getter.invoke(parsed)))) {
                throw new AssertionError("Parsed identity differs: " + KEYS[index]);
            }
        }

        String[] rejected = {
            exact.replace("version=2", "version=1"),
            exact.replace("package=" + fields[0], "package=" + fields[0] + ".0probe"),
            exact.replace("signer=" + fields[1], "signer=" + fields[1].toUpperCase(Locale.ROOT)),
            exact.replace("code=" + fields[3], "code=0" + fields[3]),
            exact + "apk=" + fields[2] + "\n",
            exact.replace("bytes=" + fields[5], "bytes=2097153"),
        };
        for (String malformed : rejected) {
            try {
                parse(parse, malformed);
                throw new AssertionError("Malformed profile was admitted");
            } catch (InvocationTargetException rejectedInput) {
                if (!(rejectedInput.getCause() instanceof IOException)) throw rejectedInput;
            }
        }
        System.out.println("PASS exact V2 profile roundtrip and six format refusals");
    }

    private static Object parse(Method method, String document) throws ReflectiveOperationException {
        byte[] bytes = document.getBytes(StandardCharsets.US_ASCII);
        return method.invoke(null, bytes, bytes.length);
    }
}
