package com.fahadali.oneos.core.model

/**
 * The four phones of the redacted findings bundles: the owner's Z Fold
 * (SM-F976B), the S26 Ultra (SM-S948U) and the S25 Ultra (SM-S938B) of
 * 2026-10-22, and the Galaxy S25 (SM-S931B, 0.2.1-probe) of 2026-10-23.
 * Only small text files are copied into
 * src/test/resources/bundles/<phone>/: props/key.txt, cpu/cpuinfo.txt,
 * installd/table.txt, the input device names of
 * input/proc_bus_input_devices.txt and five carrier props of getprop.txt
 * (sales and country codes only). Panels, hinge, screen lock and free space
 * are the values the bundles' report.json lists.
 */
object Bundles {
    class Phone(
        val name: String,
        val props: Map<String, String>,
        val cpu: CpuInfo,
        val inputs: List<String>,
        val carrierProps: Map<String, String>,
        /** installd/table.txt (format 1). */
        val table: String,
        val facts: DeviceFacts,
    ) {
        val installd: InstalldDerivation by lazy {
            val block = InstalldExpected.methodsBlock(table) ?: error("$name table.txt is not a valid table")
            val src = table.lines()[2].split(' ')
            InstalldDerivation(
                methods = InstalldTableFormat.parseLegacy(block),
                sourceJar = src[1],
                sourceEntry = "classes3.dex",
                sourceSha256 = src[2],
                inputs = listOf("installd/system_framework_framework.jar/classes3.dex"),
                error = null,
            )
        }
    }

    fun text(path: String): String =
        Bundles::class.java.getResource("/$path")?.readText() ?: error("missing test resource $path")

    private fun keyProps(text: String): Map<String, String> = text.lineSequence()
        .mapNotNull { l -> l.indexOf('=').takeIf { it > 0 }?.let { l.substring(0, it) to l.substring(it + 1) } }
        .toMap()

    private fun load(
        name: String,
        panels: List<Panel>,
        hinge: Boolean,
        screenLock: Boolean,
        freeKib: Long,
        totalKib: Long,
        managerPackage: String,
    ): Phone {
        val p = keyProps(text("bundles/$name/key.txt"))
        val cpu = CpuInfoParser.parse(text("bundles/$name/cpuinfo.txt"))
        val inputs = text("bundles/$name/input_names.txt").lines().filter { it.isNotBlank() }
        val carrierProps = Getprop.parse(text("bundles/$name/carrier.txt"))
        val soc = SocProps(
            manufacturer = p["ro.soc.manufacturer"].orEmpty(),
            model = p["ro.soc.model"].orEmpty(),
            platform = p["ro.board.platform"].orEmpty(),
            hardware = p["ro.hardware"].orEmpty(),
            egl = p["ro.hardware.egl"].orEmpty(),
        )
        val model = p.getValue("ro.product.model")
        val facts = DeviceFacts(
            brand = p.getValue("ro.product.brand"),
            manufacturer = p.getValue("ro.product.manufacturer"),
            model = model,
            device = p.getValue("ro.product.device"),
            soc = SocRules.resolve(soc),
            socProps = soc,
            oneUiRaw = p.getValue("ro.build.version.oneui"),
            androidRelease = p.getValue("ro.build.version.release"),
            sdk = p.getValue("ro.build.version.sdk").toInt(),
            buildId = p.getValue("ro.build.id"),
            fingerprint = p.getValue("ro.build.fingerprint"),
            vendorApiLevel = p.getValue("ro.vendor.api_level"),
            abis64 = p.getValue("ro.product.cpu.abilist64").split(','),
            form = FormFactorRules.resolve(FormSignals(model, panels, true, hinge, inputs)),
            panels = panels,
            panelsComplete = true,
            root = RootSignals(
                managerPackages = listOf(managerPackage),
                probe = SuProbeResult(SuState.GRANTED, 0, "u:r:ksu:s0", "uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0"),
            ),
            storage = StorageInfo(freeKib * 1024, totalKib * 1024),
            battery = BatteryInfo(80, false, 30f),
            flashLocked = p["ro.boot.flash.locked"].orEmpty(),
            verifiedBootState = p["ro.boot.verifiedbootstate"].orEmpty(),
            screenLockSet = screenLock,
            kernel = "",
            cpu = cpu,
            carrier = CarrierRules.from(carrierProps),
        )
        return Phone(name, p, cpu, inputs, carrierProps, text("bundles/$name/table.txt"), facts)
    }

    val F8U: Phone by lazy {
        load(
            "f8u",
            listOf(Panel(0, "Built-in Screen", 1080, 2520, 422.03f, 421.11f), Panel(1, "Built-in Screen", 2256, 2504, 421.34f, 421.2f)),
            hinge = true, screenLock = false, freeKib = 407_528_208, totalKib = 481_533_952, managerPackage = "me.weishu.kernelsu",
        )
    }

    val S26U: Phone by lazy {
        load(
            "s26u",
            listOf(Panel(0, "Built-in Screen", 1440, 3120, 501.04f, 498.42f)),
            hinge = false, screenLock = true, freeKib = 823_765_808, totalKib = 981_022_720, managerPackage = "com.rifsxd.ksunext",
        )
    }

    val S25U: Phone by lazy {
        load(
            "s25u",
            listOf(Panel(0, "Built-in Screen", 1080, 2340, 375.78f, 376.18f)),
            hinge = false, screenLock = false, freeKib = 161_720_924, totalKib = 228_849_664, managerPackage = "me.weishu.kernelsu",
        )
    }

    /** Galaxy S25 (base): one 1080 x 2340 panel, KernelSU Next, no screen lock. */
    val S25: Phone by lazy {
        load(
            "s25",
            listOf(Panel(0, "Built-in Screen", 1080, 2340, 415.63635f, 418.5634f)),
            hinge = false, screenLock = false, freeKib = 62_194_996, totalKib = 104_560_640, managerPackage = "com.rifsxd.ksunext",
        )
    }

    /** Galaxy Z Fold4 (SM-F936B, q4q): cover 904 x 2316, main 1812 x 2176, KernelSU. */
    val Q4Q: Phone by lazy {
        load(
            "q4q",
            listOf(
                Panel(0, "Màn hình tích hợp", 904, 2316, 402.835f, 402.92f),
                Panel(1, "Màn hình tích hợp", 1812, 2176, 377.252f, 375.989f),
            ),
            hinge = true, screenLock = true, freeKib = 106_316_460, totalKib = 231_930_844, managerPackage = "me.weishu.kernelsu",
        )
    }

    val ALL: List<Phone> get() = listOf(F8U, S26U, S25U, S25)
}
