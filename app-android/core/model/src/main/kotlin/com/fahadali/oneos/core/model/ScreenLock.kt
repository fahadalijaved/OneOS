package com.fahadali.oneos.core.model

/**
 * Screen lock (owner rule, 2026-10-22). If something goes wrong and the phone
 * boot-loops, a phone with a PIN, pattern, password, fingerprint or face lock
 * may not get into Download Mode to recover, so the lock has to be removed
 * before switching.
 *
 * The fact is `KeyguardManager.isDeviceSecure()` (public API, read-only, no
 * permission), read by :core:device `FactProbe` into
 * [DeviceFacts.screenLockSet]. Fingerprint and face unlock always sit on top of
 * a PIN, pattern or password, so they count too; None and Swipe do not.
 *
 * The device report is advisory: a set lock is WARN there ([finding]). At
 * switch time it is BLOCK ([switchGate], gate G16, docs/app/DESIGN.md section
 * 4.3), read again right before Switch, and nothing can override it; a lock
 * that cannot be read is BLOCK too.
 */
object ScreenLockRule {
    const val ID_SET = "screen-lock-set"
    const val ID_OFF = "screen-lock-off"
    const val ID_UNKNOWN = "screen-lock-unknown"

    /** The switch-time gate (G16). */
    const val ID_GATE = "gate-screen-lock"

    /** [Finding.reason]: a lock is set; it could not be read. */
    const val R_SET = "set"
    const val R_UNKNOWN = "unknown"

    /** [Finding.reason]: a lock is set and the owner turned the Advanced switch on. */
    const val R_SET_ALLOWED = "set-allowed"

    /**
     * [deviceSecure]: `KeyguardManager.isDeviceSecure()` read right before Switch, null when it could not be read.
     * [allowed] (0.4.32): the owner turned Advanced's "Switch with a screen lock set" on, so a lock warns
     * instead of blocking. An unreadable lock state still blocks: not knowing is not a choice.
     */
    fun switchGate(deviceSecure: Boolean?, allowed: Boolean = false): Finding = when (deviceSecure) {
        true -> if (allowed) Finding(
            ID_GATE, Level.WARN, "Switching with a screen lock set",
            "A PIN, pattern, password, fingerprint or face lock is on, and you turned this on in Advanced. " +
                "Your One UI data is encrypted behind that lock: if a session leaves the phone unable to " +
                "accept it, the way back is a factory reset, which erases the phone. That has happened to a " +
                "tester. Turn the switch off in Advanced to go back to removing the lock first.",
            R_SET_ALLOWED,
        ) else Finding(
            ID_GATE, Level.BLOCK, "Remove the screen lock to switch",
            "A PIN, pattern, password, fingerprint or face lock is on. If the phone boot-loops, a locked " +
                "phone may not get into Download Mode to recover. Set Screen lock type to None or Swipe in " +
                "Settings, then come back. Advanced has a switch to do it anyway, at your own risk.",
            R_SET,
        )
        false -> Finding(ID_GATE, Level.OK, "No screen lock", "Keep it off while you use OneOS.")
        null -> Finding(
            ID_GATE, Level.BLOCK, "Screen lock not checked",
            "Could not read whether a screen lock is set, so switching stays off. Set Screen lock type to " +
                "None or Swipe in Settings and try again.",
            R_UNKNOWN,
        )
    }

    /** [deviceSecure]: `KeyguardManager.isDeviceSecure()`, null when it could not be read. */
    fun finding(deviceSecure: Boolean?): Finding = when (deviceSecure) {
        true -> Finding(
            ID_SET, Level.WARN, "Screen lock is set - remove it before switching",
            "A PIN, pattern, password, fingerprint or face lock is on. If something goes wrong and " +
                "the phone boot-loops, a locked phone may not get into Download Mode to recover. " +
                "Set Screen lock type to None or Swipe in Settings. Switching will not start while a lock is set.",
            R_SET,
        )
        false -> Finding(
            ID_OFF, Level.OK, "No screen lock",
            "Keep it off while you use OneOS, so Download Mode stays reachable if the phone boot-loops.",
        )
        null -> Finding(
            ID_UNKNOWN, Level.WARN, "Screen lock not checked",
            "Could not read whether a screen lock is set. Remove any PIN, pattern, password, " +
                "fingerprint or face lock before switching.",
            R_UNKNOWN,
        )
    }
}
