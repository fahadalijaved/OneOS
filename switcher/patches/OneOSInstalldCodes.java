package com.android.server.pm;

import android.os.RemoteException;
import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;

/**
 * The installd transaction codes of THIS phone, for OneOSInstalldProxy (patches/guest_installd_abi.py).
 *
 * One UI 9.5 renumbered IInstalld (67 methods, 85 on One UI 9.0; only 6 kept their code), so codes
 * baked into a set at build time were right on one One UI only. The proxy now asks code(index) for
 * each method it may send; index is the method's row in {@link #table()}, which the build fills
 * with "name signature" lines. The codes come from /data/system/oneos_installd_codes, which
 * guest_prepare.sh writes from the stage's host_installd.table (the table the app derived on this
 * phone and root checked against its fingerprint and jar): "name code signature" per line.
 *
 * Fail closed: a method this phone's installd lacks with the same signature, or any method when
 * the file cannot be read, throws RemoteException before anything is sent (the callers handle
 * installd failures), so a call never reaches another host method.
 */
public final class OneOSInstalldCodes {
    private static final String FILE = "/data/system/oneos_installd_codes";
    private static int[] sCodes;

    private OneOSInstalldCodes() {
    }

    /** One "name signature" line per method the proxy may send; written by the build. */
    private static String table() {
        return "@@ONEOS_INSTALLD_TABLE@@";
    }

    /** This phone's code for the proxy's method [index]; RemoteException when it has none. */
    public static int code(int index) throws RemoteException {
        int[] c = sCodes;
        if (c == null) {
            c = load();
        }
        int v = index >= 0 && index < c.length ? c[index] : 0;
        if (v <= 0) {
            throw new RemoteException("OneOS: installd method " + index + " is not on this phone's installd");
        }
        return v;
    }

    private static synchronized int[] load() {
        if (sCodes != null) {
            return sCodes;
        }
        String[] rows = table().split("\n");
        int[] c = new int[rows.length];
        HashMap<String, Integer> phone = new HashMap<>();
        boolean read = false;
        try (BufferedReader r = new BufferedReader(new FileReader(FILE))) {
            String l;
            while ((l = r.readLine()) != null) {
                String[] p = l.trim().split(" ");
                if (p.length == 3) {
                    try {
                        phone.put(p[0] + " " + p[2], Integer.parseInt(p[1]));
                    } catch (NumberFormatException e) {
                        Log.w("OneOS", "installd codes: bad line " + l);
                    }
                }
            }
            read = true;
        } catch (IOException e) {
            Log.e("OneOS", "installd codes: " + FILE + " not read, every installd call is refused", e);
        }
        int sent = 0;
        for (int i = 0; i < rows.length; i++) {
            Integer v = read ? phone.get(rows[i].trim()) : null;
            c[i] = v == null ? 0 : v;
            if (c[i] > 0) {
                sent++;
            }
        }
        Log.i("OneOS", "installd codes: " + sent + " of " + rows.length + " methods on this phone's installd ("
                + phone.size() + " in its table)");
        sCodes = c;
        return c;
    }
}
