package com.fahadali.oneos.core.model

data class StorageInfo(val freeBytes: Long, val totalBytes: Long)

data class BatteryInfo(
    val levelPercent: Int,
    val charging: Boolean,
    /** Battery temperature in °C; null when not reported. */
    val temperatureC: Float?,
)

/**
 * The host facts of docs/app/compat-safety-logs.md section 1.1 that an app can
 * read without root. Filled by :core:device `FactProbe`; plain data so the
 * rules can be tested on the JVM.
 */
data class DeviceFacts(
    val brand: String,
    val manufacturer: String,
    val model: String,
    /** Codename, `ro.product.device` (`q8q` on the F8U). */
    val device: String,
    val soc: SocInfo,
    val socProps: SocProps,
    /** Raw `ro.build.version.oneui`. */
    val oneUiRaw: String,
    val androidRelease: String,
    val sdk: Int,
    val buildId: String,
    val fingerprint: String,
    /** `ro.vendor.api_level` (falls back to `ro.board.api_level`). */
    val vendorApiLevel: String,
    val abis64: List<String>,
    val form: FormResult,
    val panels: List<Panel>,
    /** True when [panels] is the full built-in list, not only the active display(s). */
    val panelsComplete: Boolean,
    val root: RootSignals,
    val storage: StorageInfo?,
    val battery: BatteryInfo?,
    /** `ro.boot.flash.locked`: `1` locked, `0` unlocked, empty when hidden. */
    val flashLocked: String,
    /** `ro.boot.verifiedbootstate`: `green`, `orange`, ... */
    val verifiedBootState: String,
    /**
     * `KeyguardManager.isDeviceSecure()`: a PIN, pattern or password (and the
     * fingerprint/face unlock on top of it) is set. Null when it could not be read.
     */
    val screenLockSet: Boolean?,
    val kernel: String,
    /** `/proc/cpuinfo`, parsed; null when it could not be read. */
    val cpu: CpuInfo? = null,
    /** Carrier props for the VoLTE-only warning ([CarrierRules.from]); null when not read. */
    val carrier: CarrierInfo? = null,
    /** `ro.bootloader` ([android.os.Build.BOOTLOADER]): starts with the real model code ([CustomRomRule]). */
    val bootloader: String = "",
    /** `ro.product.vendor.model`; empty when it could not be read. */
    val vendorModel: String = "",
) {
    /** A custom ROM ([CustomRomRule]): no switching, no reports. Null on stock One UI. */
    val customRom: Finding? get() = CustomRomRule.check(CustomRomRule.Signals(model, bootloader, vendorModel, oneUiRaw))
    val oneUi: OneUiVersion? get() = OneUiVersion.parse(oneUiRaw)
    val family: ModelFamily get() = ModelFamily.of(model)
    val rootKind: RootKind get() = RootRules.kind(root)
    val isSamsung: Boolean
        get() = brand.equals("samsung", ignoreCase = true) ||
            manufacturer.equals("samsung", ignoreCase = true)
}
