package com.android.server;

import java.io.FileInputStream;
import java.io.IOException;

/**
 * HyperOS's quick charge type on a Galaxy (patches/miui_quick_charge.py).
 *
 * MiuiBatteryServiceImpl asks Xiaomi's charger service (miui.util.IMiCharge, vendor.xiaomi.hardware.micharge)
 * for the quick charge type that SystemUI's charging animation and the "Super charging" text go by. A Galaxy
 * has no such service, so the answer is empty and every charger is a plain one (owner's A36, HyperOS 4 Global,
 * 11-20: 45 W Super Fast Charging, no animation). When the service gives nothing, this answers from Samsung's
 * own nodes in /sys/class/power_supply/battery:
 * <ul>
 * <li>Super Fast Charging (charging_type with APDO, or direct_charging_status 1): 3, Xiaomi's super charge</li>
 * <li>Fast charging (HV, AFC, QC, PDIC, or charge_type Fast): 1, quick charge</li>
 * <li>Otherwise what the service said</li>
 * </ul>
 * Never throws.
 */
public final class OneOSMiCharge {
    private static final String BATTERY = "/sys/class/power_supply/battery/";

    private OneOSMiCharge() {
    }

    /** The service's answer when it has one (a number above 0), else Samsung's charger as Xiaomi's type. */
    public static String quickChargeType(String fromService) {
        try {
            if (fromService != null) {
                String s = fromService.trim();
                if (!s.isEmpty()) {
                    try {
                        if (Integer.parseInt(s) > 0) {
                            return fromService;
                        }
                    } catch (NumberFormatException e) {
                        return fromService;
                    }
                }
            }
            String status = read(BATTERY + "status");
            if (status == null || !(status.equalsIgnoreCase("Charging") || status.equalsIgnoreCase("Full"))) {
                return fromService;
            }
            String type = read(BATTERY + "charging_type");
            if (type == null) {
                return fromService;
            }
            String t = type.toUpperCase(java.util.Locale.ROOT);
            if (t.contains("APDO") || "1".equals(read(BATTERY + "direct_charging_status"))) {
                return "3";
            }
            if (t.contains("HV") || t.contains("AFC") || t.contains("QC") || t.contains("PDIC")
                    || "Fast".equalsIgnoreCase(read(BATTERY + "charge_type"))) {
                return "1";
            }
            return fromService;
        } catch (Throwable e) {
            return fromService;
        }
    }

    private static String read(String path) {
        try (FileInputStream in = new FileInputStream(path)) {
            byte[] b = new byte[64];
            int n = in.read(b);
            return n <= 0 ? "" : new String(b, 0, n, java.nio.charset.StandardCharsets.US_ASCII).trim();
        } catch (IOException | RuntimeException e) {
            return null;
        }
    }
}
