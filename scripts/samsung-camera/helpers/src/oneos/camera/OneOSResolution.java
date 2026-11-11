package oneos.camera;

import java.util.function.BiFunction;

/**
 * One UI's camera in a guest on a phone it was not built for: a picture size or a stored size id
 * that its size table has no entry for (Galaxy A34: "8000x6000", its 48 MP size; Galaxy A16: id -1,
 * "no size of this camera"). The table's two lookups threw IllegalArgumentException
 * "getResolution : argument is invalid - ..." and the camera died at launch, each time from another
 * caller. fix_a_series_resolution_lookup.py sends both misses here before the throw.
 *
 * The table's entries are read by their names, which the camera keeps: RESOLUTION_&lt;W&gt;X&lt;H&gt;
 * and RESOLUTION_&lt;W&gt;X&lt;H&gt;_&lt;N&gt;FPS. Nothing here touches Android classes: the same
 * code runs in the script test on the build server.
 *
 * The camera reaches this class through the field LOOKUP and BiFunction.apply, not through a static
 * method: the dex file with the size table (classes2.dex) has 65535 of its 65536 method references
 * in use, and a field plus an interface method it already calls cost none.
 *
 * A few of the camera's methods call a lookup to find out whether a value exists and catch the
 * exception (restoring a settings backup tries one size after another). They must go on getting
 * it: the patcher writes their names into CATCHERS, and a miss whose caller is one of them gets no
 * stand-in.
 */
public final class OneOSResolution implements BiFunction<Object, Object, Object> {
    /** apply(the id as an Integer or the "WxH" text, the table's values()): the entry to use, or null. */
    public static final BiFunction<Object, Object, Object> LOOKUP = new OneOSResolution();
    /**
     * " class.method class.method ": the callers that handle a miss themselves. The patcher puts the
     * list in place of the marker in its copy of this class; as it stands here there are none.
     */
    static String CATCHERS = " @oneos-callers-that-catch@ ";
    private static final String PREFIX = "RESOLUTION_";
    private static final String DEFAULT = "RESOLUTION_4000X3000";
    private static String said = "";

    private OneOSResolution() {}

    @Override
    public Object apply(Object key, Object table) {
        try {
            if (!(table instanceof Enum<?>[])) return null;
            boolean id = key instanceof Integer;
            if (!id && !(key instanceof String)) return null;
            String what = (id ? "id " : "size ") + key;
            String caller = caller(table.getClass().getComponentType().getName());
            if (caller == null) return null;
            if (CATCHERS.contains(" " + caller + " ")) {
                say(what, caller + " deals with that itself");
                return null;
            }
            Enum<?> got = id ? unknownId((Enum<?>[]) table) : nearest((String) key, (Enum<?>[]) table);
            say(what, got == null ? "nothing to offer, the camera's own error follows" : "using " + got.name());
            return got;
        } catch (RuntimeException e) {
            return null;
        }
    }

    /**
     * "te.c0.T": the method that called the table's lookup, or null when this was not called from a
     * method of the table (then there is no lookup to answer for). The frames are this class's, then
     * the lookup's, then the caller's.
     */
    private static String caller(String tableClass) {
        StackTraceElement[] st = new Throwable().getStackTrace();
        String me = OneOSResolution.class.getName();
        int i = 0;
        while (i < st.length && me.equals(st[i].getClassName())) i++;
        if (i + 1 >= st.length || !tableClass.equals(st[i].getClassName())) return null;
        return st[i + 1].getClassName() + "." + st[i + 1].getMethodName();
    }

    /**
     * The entry for a size the table does not have: the same shape (4:3 stays 4:3) with the nearest
     * pixel count, or without one of that shape the nearest pixel count; of equal ones the first in
     * the table, as the camera's own lookup takes the first. The same shape is the sides' ratio
     * within 1 %: Samsung's 16:9 sizes are 4000x2252 and 8160x4592. null (the camera throws as
     * before) when the text is not a size or the table has no entry that reads as one.
     */
    static Enum<?> nearest(String wanted, Enum<?>[] table) {
        long[] w = size(wanted, 0);
        if (w == null) return null;
        Enum<?> best = null;
        boolean bestShape = false;
        long bestGap = 0;
        for (Enum<?> e : table) {
            if (e == null || !e.name().startsWith(PREFIX)) continue;
            long[] k = size(e.name(), PREFIX.length());
            if (k == null) continue;
            boolean shape = Math.abs(k[0] * w[1] - k[1] * w[0]) * 100 <= k[1] * w[0];
            long gap = Math.abs(k[0] * k[1] - w[0] * w[1]);
            if (best == null || (shape && !bestShape) || (shape == bestShape && gap < bestGap)) {
                best = e;
                bestShape = shape;
                bestGap = gap;
            }
        }
        return best;
    }

    /**
     * The entry for a stored id the table does not have (-1: no size of this camera): the plain 4:3
     * size every Samsung camera has, so that a caller asking for its shape or its special cases gets
     * an ordinary answer. null (the camera throws as before) when the table has no such entry.
     */
    static Enum<?> unknownId(Enum<?>[] table) {
        for (Enum<?> e : table) {
            if (e != null && DEFAULT.equals(e.name())) return e;
        }
        return null;
    }

    /** "8000x6000", or the same after the prefix of a name ("8160X6120", "1920X1080_60FPS"). */
    private static long[] size(String s, int from) {
        if (s == null) return null;
        int end = s.indexOf('_', from);
        if (end < 0) end = s.length();
        int x = -1;
        for (int i = from; i < end; i++) {
            char c = s.charAt(i);
            if (c == 'x' || c == 'X') {
                if (x >= 0) return null;
                x = i;
            } else if (c < '0' || c > '9') {
                return null;
            }
        }
        // Up to five digits each way: the products stay far inside a long.
        if (x <= from || x >= end - 1 || x - from > 5 || end - 1 - x > 5) return null;
        long w = Long.parseLong(s.substring(from, x));
        long h = Long.parseLong(s.substring(x + 1, end));
        return w > 0 && h > 0 ? new long[] {w, h} : null;
    }

    /** One line per different miss in the log (System.err is the app's W/System.err), not one per call. */
    private static synchronized void say(String what, String outcome) {
        String line = "OneOSCamera: no entry for " + what + " in this camera's size table: " + outcome;
        if (said.contains("\n" + line + "\n") || said.length() > 4000) return;
        said += "\n" + line + "\n";
        System.err.println(line);
    }
}
