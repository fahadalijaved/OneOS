import java.util.Properties

// OneOS inside the guest (Pixel, ColorOS): "Back to One UI" in one tap, from
// its screen or its Quick Settings tile. It only writes a request file in its
// own data folder (files/oneos_return); the session's watcher on the host
// (switcher/assets/oneos_switch.sh) sees it and returns. guest_prepare.sh
// installs it in every guest as a system app (/oem/app/OneOSGuest), from
// $STAGE/OneOSGuest.apk (scripts/make-overlays.sh copies the release build).
// Plain framework UI (DeviceDefault): it runs on Pixel and ColorOS, not One UI,
// so no SESL and no library at all. No permission, no network.
plugins {
    alias(libs.plugins.android.application)
}

// The OneOS release key, as :app signs with it (never in the repo; /srv/projects is shared).
val releaseKeys: Properties? =
    File(System.getProperty("user.home"), ".oneos-release/keystore.properties").takeIf { it.isFile }?.let { f ->
        Properties().apply { f.inputStream().use(::load) }
    }

android {
    namespace = "com.fahadali.oneos.guest"
    compileSdk { version = release(37) }

    defaultConfig {
        applicationId = "com.fahadali.oneos.guest"
        minSdk = 31
        targetSdk = 36
        // 0.2 (OneOS 0.4.30): How's it going?, the checklist for Send to the OneOS team.
        versionCode = 2
        versionName = "0.2"
    }

    signingConfigs {
        if (releaseKeys != null) {
            create("release") {
                storeFile = file(releaseKeys.getProperty("storeFile"))
                storePassword = releaseKeys.getProperty("storePassword")
                keyAlias = releaseKeys.getProperty("keyAlias")
                keyPassword = releaseKeys.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // R8 drops the unused Kotlin stdlib: the APK sits in the guest's /oem.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    lint {
        abortOnError = true
    }
}

kotlin {
    jvmToolchain(libs.versions.jvmToolchain.get().toInt())
}

// A release without the key would be an unsigned APK: refuse instead, as :app does.
tasks.matching { it.name == "packageRelease" }.configureEach {
    val hasKey = releaseKeys != null
    doFirst {
        check(hasKey) { "No release key: ~/.oneos-release/keystore.properties is missing (see app-android/README.md, section Build)." }
    }
}
