package com.android.server;

import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

/**
 * The IOemNetd transaction codes of THIS phone's netd, for a One UI guest (patches/guest_oemnetd_abi.py).
 *
 * netd is One UI's process; Samsung's IOemNetd is numbered differently on each One UI (212 methods on
 * 9.0, 234 on 9.5, renumbered from code 13 on). The build knows the tables of the One UI versions in
 * {@link #table()}: one line per guest proxy method, "code-on-9.0 code-on-9.5" (0 = not there), and
 * the first line names the versions ("90000 90500"). guest_prepare.sh writes this phone's
 * ro.build.version.oneui to /data/system/oneos_oemnetd_host. Any method the phone's One UI lacks, a
 * One UI version the build has no table for, or no file: UNUSED_CODE, which netd answers with
 * "unknown transaction" without running anything (the caller reads default values).
 */
public final class OneOSOemNetdCodes {
    private static final String FILE = "/data/system/oneos_oemnetd_host";
    private static final int UNUSED_CODE = 0xFFFFF0;
    private static int[] sCodes;

    private OneOSOemNetdCodes() {
    }

    /** First line: the One UI versions of the columns; then one line per proxy method. Written by the build. */
    private static String table() {
        return "@@ONEOS_OEMNETD_TABLE@@";
    }

    public static int code(int index) {
        int[] c = sCodes;
        if (c == null) {
            c = load();
        }
        return index >= 0 && index < c.length && c[index] > 0 ? c[index] : UNUSED_CODE;
    }

    private static synchronized int[] load() {
        if (sCodes != null) {
            return sCodes;
        }
        String host = "";
        try (BufferedReader r = new BufferedReader(new FileReader(FILE))) {
            String l = r.readLine();
            host = l == null ? "" : l.trim();
        } catch (IOException e) {
            Log.e("OneOS", "IOemNetd codes: " + FILE + " not read, no IOemNetd call reaches netd", e);
        }
        String[] rows = table().split("\n");
        String[] versions = rows[0].trim().split(" ");
        int col = -1;
        for (int i = 0; i < versions.length; i++) {
            if (versions[i].equals(host)) {
                col = i;
            }
        }
        int[] c = new int[rows.length - 1];
        int sent = 0;
        for (int i = 1; i < rows.length && col >= 0; i++) {
            String[] p = rows[i].trim().split(" ");
            if (p.length == versions.length) {
                try {
                    c[i - 1] = Integer.parseInt(p[col]);
                } catch (NumberFormatException e) {
                    c[i - 1] = 0;
                }
                if (c[i - 1] > 0) {
                    sent++;
                }
            }
        }
        Log.i("OneOS", "IOemNetd codes: One UI " + (host.isEmpty() ? "unknown" : host) + ", " + sent + " of "
                + c.length + " methods " + (col >= 0 ? "on this phone's netd" : "(no table for it: none sent)"));
        sCodes = c;
        return c;
    }
}
