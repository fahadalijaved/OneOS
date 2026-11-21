// Android library: root-manager detection without root (installed manager
// apps, su binaries on disk), the `su -c id` check, RootProbeRunner (the
// read-only lists: `su -c "sh probe.sh <list>"`, every command in a list the
// app ships), and, from build 2, the write path: RootScript (the launcher of
// app/src/full/assets/root/oneos_root.sh), RootShell (su with a streamed
// stdin), StageStatus, the log redaction and the audit of the root script.
// Both app editions link it; only OneOS (full) ships the root script.
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.fahadali.oneos.core.root"
    compileSdk { version = release(37) }
    defaultConfig {
        minSdk = 31
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
}

kotlin {
    jvmToolchain(libs.versions.jvmToolchain.get().toInt())
}

dependencies {
    api(project(":core:model"))
    testImplementation(libs.junit)
    // The tests import a real .tar.zst through the root script (OneiosImportTest); the jar carries the PC's natives.
    testImplementation(libs.zstd.jni)
}

// The tests audit the root script and the read-only lists the app ships, run
// the script under dash and busybox ash against a fake root folder, and check
// its built-in tables against the model and the session scripts.
// src/main: the probe runner and its list (both editions); src/full: the root
// script and the stage, installd and log lists (OneOS only).
val appAssets = rootProject.layout.projectDirectory.dir("app/src/main/assets")
val fullAssets = rootProject.layout.projectDirectory.dir("app/src/full/assets")
val appSources = rootProject.layout.projectDirectory.dir("app/src")
val switcherAssets = rootProject.layout.projectDirectory.dir("../switcher/assets")
val installdFixture = rootProject.layout.projectDirectory.file("../switcher/patches/host_installd.txt")
val runLogs = rootProject.layout.projectDirectory.dir("../out/logs")
val packagesDir = rootProject.layout.projectDirectory.dir("packages")

tasks.withType<Test>().configureEach {
    inputs.dir(appAssets).withPropertyName("appAssets")
    inputs.dir(fullAssets).withPropertyName("fullAssets")
    inputs.dir(appSources).withPropertyName("appSources")
    inputs.file(rootProject.layout.projectDirectory.file("app/build.gradle.kts")).withPropertyName("appBuild")
    inputs.files(fileTree(switcherAssets) { include("*.sh") }).withPropertyName("switcherScripts")
    inputs.file(installdFixture).withPropertyName("installdFixture")
    inputs.dir(packagesDir).withPropertyName("packages")
    systemProperty("oneos.appAssets", appAssets.asFile.path)
    systemProperty("oneos.fullAssets", fullAssets.asFile.path)
    systemProperty("oneos.appSources", appSources.asFile.path)
    systemProperty("oneos.switcherAssets", switcherAssets.asFile.path)
    systemProperty("oneos.installdFixture", installdFixture.asFile.path)
    systemProperty("oneos.runLogs", runLogs.asFile.path)
    systemProperty("oneos.packagesDir", packagesDir.asFile.path)
}
