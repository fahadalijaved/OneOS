package com.fahadali.oneos.core.device

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorManager
import android.hardware.display.DisplayManager
import android.hardware.input.InputManager
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.util.DisplayMetrics
import android.view.Display
import com.fahadali.oneos.core.model.BatteryInfo
import com.fahadali.oneos.core.model.CpuInfo
import com.fahadali.oneos.core.model.CpuInfoParser
import com.fahadali.oneos.core.model.DeviceFacts
import com.fahadali.oneos.core.model.FormFactorRules
import com.fahadali.oneos.core.model.FormSignals
import com.fahadali.oneos.core.model.Panel
import com.fahadali.oneos.core.model.RootSignals
import com.fahadali.oneos.core.model.SocProps
import com.fahadali.oneos.core.model.SocRules
import com.fahadali.oneos.core.model.StorageInfo
import java.io.File

/**
 * Collects the host facts an app can read without root
 * (docs/app/compat-safety-logs.md section 1.1). Read-only: system properties,
 * Android APIs, and /proc reads where SELinux allows them. It never writes a
 * file, sets a prop or runs anything as root. Call it off the main thread.
 */
class FactProbe(
    context: Context,
    private val props: PropReader = PropReader(),
) {
    private val app = context.applicationContext

    fun collect(root: RootSignals): DeviceFacts {
        val model = props.get("ro.product.model").ifEmpty { Build.MODEL.orEmpty() }
        val (panels, complete) = panels()
        val form = FormFactorRules.resolve(
            FormSignals(
                model = model,
                panels = panels,
                panelsComplete = complete,
                hingeSensor = hingeSensor(),
                inputDeviceNames = inputDeviceNames(),
            ),
        )
        val socProps = SocProps(
            manufacturer = props.get("ro.soc.manufacturer").ifEmpty { Build.SOC_MANUFACTURER.orEmpty() },
            model = props.get("ro.soc.model").ifEmpty { Build.SOC_MODEL.orEmpty() },
            platform = props.get("ro.board.platform"),
            hardware = props.get("ro.hardware").ifEmpty { Build.HARDWARE.orEmpty() },
            chipname = props.get("ro.hardware.chipname"),
            egl = props.get("ro.hardware.egl"),
        )
        return DeviceFacts(
            brand = props.get("ro.product.brand").ifEmpty { Build.BRAND.orEmpty() },
            manufacturer = props.get("ro.product.manufacturer").ifEmpty { Build.MANUFACTURER.orEmpty() },
            model = model,
            device = props.first("ro.product.device", "ro.product.vendor.device").ifEmpty { Build.DEVICE.orEmpty() },
            soc = SocRules.resolve(socProps),
            socProps = socProps,
            oneUiRaw = props.get("ro.build.version.oneui"),
            androidRelease = Build.VERSION.RELEASE.orEmpty(),
            sdk = Build.VERSION.SDK_INT,
            buildId = Build.ID.orEmpty(),
            fingerprint = Build.FINGERPRINT.orEmpty(),
            vendorApiLevel = props.first("ro.vendor.api_level", "ro.board.api_level"),
            abis64 = Build.SUPPORTED_64_BIT_ABIS.toList(),
            form = form,
            panels = panels,
            panelsComplete = complete,
            root = root,
            storage = storage(),
            battery = battery(),
            flashLocked = props.get("ro.boot.flash.locked"),
            verifiedBootState = props.get("ro.boot.verifiedbootstate"),
            screenLockSet = screenLockSet(app),
            kernel = System.getProperty("os.version").orEmpty(),
            cpu = cpu(),
            bootloader = Build.BOOTLOADER.orEmpty().takeIf { it.isNotEmpty() && it != Build.UNKNOWN } ?: props.get("ro.bootloader"),
            vendorModel = props.get("ro.product.vendor.model"),
        )
    }

    /** `/proc/cpuinfo` (apps may read it): cores and the features the ColorOS images need. */
    private fun cpu(): CpuInfo? = runCatching { File("/proc/cpuinfo").readText() }
        .getOrNull()
        ?.let(CpuInfoParser::parse)
        ?.takeIf { it.cores.isNotEmpty() }

    /**
     * Built-in panels. On Android 16 QPR2+ the built-in category also lists the
     * panel that is off right now (a Fold's cover screen while open), so the
     * list is complete; before that only active displays are visible.
     */
    private fun panels(): Pair<List<Panel>, Boolean> {
        val dm = app.getSystemService(DisplayManager::class.java) ?: return emptyList<Panel>() to false
        if (Build.VERSION.SDK_INT >= 36 && Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1) {
            val builtIn = runCatching { dm.getDisplays(DisplayManager.DISPLAY_CATEGORY_BUILT_IN_DISPLAYS) }
                .getOrNull().orEmpty()
            val mapped = builtIn.mapNotNull(::toPanelOrNull)
            // Complete only when every built-in display could be read.
            if (mapped.isNotEmpty()) return mapped to (mapped.size == builtIn.size)
        }
        val active = runCatching { dm.displays }.getOrNull().orEmpty()
            .filter { it.flags and (Display.FLAG_PRIVATE or Display.FLAG_PRESENTATION) == 0 }
        return active.mapNotNull(::toPanelOrNull) to false
    }

    /** Null when the display cannot be read (a disabled panel can throw from `getMode()`). */
    private fun toPanelOrNull(d: Display): Panel? = runCatching { toPanel(d) }.getOrNull()

    private fun toPanel(d: Display): Panel {
        val mode = d.mode
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        d.getRealMetrics(metrics)
        return Panel(
            displayId = d.displayId,
            name = d.name.orEmpty(),
            widthPx = mode.physicalWidth,
            heightPx = mode.physicalHeight,
            xdpi = metrics.xdpi,
            ydpi = metrics.ydpi,
        )
    }

    /** Hinge angle sensor (all Z Fold / Z Flip have one); null if it cannot be read. */
    private fun hingeSensor(): Boolean? = runCatching {
        val feature = app.packageManager.hasSystemFeature(PackageManager.FEATURE_SENSOR_HINGE_ANGLE)
        val sensor = app.getSystemService(SensorManager::class.java)
            ?.getDefaultSensor(Sensor.TYPE_HINGE_ANGLE) != null
        feature || sensor
    }.getOrNull()

    /**
     * Input device names (the Fold lid switch is `flip`). InputManager first;
     * /proc/bus/input/devices only if SELinux lets the app read it.
     */
    private fun inputDeviceNames(): List<String> {
        val names = mutableListOf<String>()
        runCatching {
            val im = app.getSystemService(InputManager::class.java)
            if (im != null) {
                for (id in im.inputDeviceIds) im.getInputDevice(id)?.name?.let(names::add)
            }
        }
        runCatching {
            File("/proc/bus/input/devices").useLines { lines ->
                lines.filter { it.startsWith("N: Name=") }
                    .map { it.removePrefix("N: Name=").trim().trim('"') }
                    .forEach(names::add)
            }
        }
        return names.distinct()
    }

    /**
     * [base] with what changes by the minute read again: free space, the
     * battery and the screen lock. Cheap (no display or input scan), for Home
     * on every resume; the rest of [base] stays.
     */
    fun refresh(base: DeviceFacts): DeviceFacts =
        base.copy(storage = storage() ?: base.storage, battery = battery() ?: base.battery, screenLockSet = screenLockSet(app))

    private fun storage(): StorageInfo? = runCatching {
        val fs = StatFs(Environment.getDataDirectory().path)
        StorageInfo(freeBytes = fs.availableBytes, totalBytes = fs.totalBytes)
    }.getOrNull()

    private fun battery(): BatteryInfo? = runCatching {
        val bm = app.getSystemService(BatteryManager::class.java) ?: return null
        val level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        // Sticky broadcast read with a null receiver: nothing is registered.
        val sticky = app.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val temp = sticky?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)
            ?.takeIf { it != Int.MIN_VALUE }
            ?.let { it / 10f }
        BatteryInfo(levelPercent = level, charging = bm.isCharging, temperatureC = temp)
    }.getOrNull()

    companion object {
        /**
         * `KeyguardManager.isDeviceSecure()`: a PIN, pattern or password is set
         * (fingerprint and face unlock need one). Public API, read-only, no
         * permission, cheap enough for the main thread; null if it cannot be read.
         */
        fun screenLockSet(context: Context): Boolean? = runCatching {
            context.getSystemService(KeyguardManager::class.java)?.isDeviceSecure
        }.getOrNull()
    }
}
