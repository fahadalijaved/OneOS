// Pure Kotlin/JVM: device-fact parsing, the compatibility rules, the probe
// list audit, the probe stream, redaction and the findings bundle. No Android
// classes, so the same code can later run on the build server (patch-cli) and
// is unit tested on the JVM.
plugins {
    alias(libs.plugins.kotlin.jvm)
}

kotlin {
    jvmToolchain(libs.versions.jvmToolchain.get().toInt())
}

dependencies {
    testImplementation(libs.junit)
}

// The tests audit the probe files the app ships (one list of root commands),
// compare the installd table format with the F8U fixture (the table the guard
// jars carry), check that every session.env knob is one the session scripts
// read, and that the checked-in package lists name the package sets.
val probeAssets = rootProject.layout.projectDirectory.dir("app/src/main/assets/probe")
val installdFixture = rootProject.layout.projectDirectory.file("../switcher/patches/host_installd.txt")
val switcherAssets = rootProject.layout.projectDirectory.dir("../switcher/assets")
val packagesDir = rootProject.layout.projectDirectory.dir("packages")

tasks.test {
    inputs.dir(probeAssets).withPropertyName("probeAssets")
    inputs.file(installdFixture).withPropertyName("installdFixture")
    inputs.files(fileTree(switcherAssets) { include("*.sh") }).withPropertyName("switcherScripts")
    inputs.files(fileTree(packagesDir) { include("*.sha256", "series.txt") }).withPropertyName("packageLists")
    systemProperty("oneos.probeDir", probeAssets.asFile.path)
    systemProperty("oneos.installdFixture", installdFixture.asFile.path)
    systemProperty("oneos.switcherAssets", switcherAssets.asFile.path)
    systemProperty("oneos.packagesDir", packagesDir.asFile.path)
}
