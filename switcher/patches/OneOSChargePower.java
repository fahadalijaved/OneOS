package com.android.server;

import android.hardware.health.HealthInfo;

import java.io.FileInputStream;
import java.io.IOException;

/**
 * The charger's power for the guest's BatteryService (patches/battery_charge_power.py).
 *
 * A Galaxy's kernel publishes no current_max or voltage_max for its chargers, so the health HAL reports
 * maxChargingCurrentMicroamps and maxChargingVoltageMicrovolts as 0 and every guest system takes a Samsung
 * fast charger for a slow one: no "Charging rapidly", no fast-charging animation (owner's A36 on HyperOS 4
 * Global, 11-20: 45 W Super Fast Charging, direct charging on, "Max charging current: 0"). One UI itself reads
 * Samsung's own nodes. With a charger online and no maximum from the HAL, this fills one in from
 * /sys/class/power_supply/battery/charging_type and direct_charging_status:
 * <ul>
 * <li>Super Fast Charging (PPS: charging_type with APDO, or direct charging on): 10 V, 2.5 A (25 W)</li>
 * <li>Fast charging (AFC, QC 2.0, a fixed PD profile: HV, AFC, QC, PDIC, or charge_type Fast): 9 V, 1.67 A (15 W)</li>
 * <li>Any other charger: 5 V, 1.2 A (6 W), Android's normal "Charging"</li>
 * </ul>
 * Android's thresholds (config_chargingSlowlyThreshold 5 W, config_chargingFastThreshold 7.5 W) then pick the
 * speed. A phone that reports a maximum itself, or a non-Samsung one (no such nodes), is left alone.
 * Never throws: BatteryService.update runs on the health HAL's callback.
 */
public final class OneOSChargePower {
    private static final String BATTERY = "/sys/class/power_supply/battery/";

    private OneOSChargePower() {
    }

    public static void fill(HealthInfo h) {
        try {
            if (h == null || h.maxChargingCurrentMicroamps > 0) {
                return;
            }
            if (!(h.chargerAcOnline || h.chargerUsbOnline || h.chargerDockOnline)) {
                return;
            }
            String type = read(BATTERY + "charging_type");
            if (type == null) {
                return;
            }
            String t = type.toUpperCase(java.util.Locale.ROOT);
            String dc = read(BATTERY + "direct_charging_status");
            String chargeType = read(BATTERY + "charge_type");
            if (t.contains("APDO") || "1".equals(dc)) {
                h.maxChargingVoltageMicrovolts = 10000000;
                h.maxChargingCurrentMicroamps = 2500000;
            } else if (t.contains("HV") || t.contains("AFC") || t.contains("QC") || t.contains("PDIC")
                    || "Fast".equalsIgnoreCase(chargeType)) {
                h.maxChargingVoltageMicrovolts = 9000000;
                h.maxChargingCurrentMicroamps = 1670000;
            } else if (t.contains("NONE") || t.contains("UNKNOWN") || t.isEmpty()) {
                return;
            } else {
                h.maxChargingVoltageMicrovolts = 5000000;
                h.maxChargingCurrentMicroamps = 1200000;
            }
        } catch (Throwable e) {
            // Leave the HAL's values as they are.
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
