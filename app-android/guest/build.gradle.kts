import java.util.Properties

// OneOS inside the guest (Pixel, ColorOS): "Back to One UI" in one tap, from
// its screen or its Quick Settings tile. It only writes a request file in its
// own data folder (files/oneos_return); the session's watcher on the host
// (switcher/assets/oneos_switch.sh) sees it and returns. guest_prepare.sh
// installs it in every guest as a system app (/oem/app/OneOSGuest), from
// $STAGE/OneOSGuest.apk (scripts/make-overlays.sh copies the release build).
// SESL9 supplies the same native components on Pixel and ColorOS.
// No permission and no network access.
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
        versionCode = 6
        versionName = "0.6"
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

configurations.configureEach {
    exclude(group = "androidx.core", module = "core")
    exclude(group = "androidx.core", module = "core-ktx")
    exclude(group = "androidx.customview", module = "customview")
    exclude(group = "androidx.coordinatorlayout", module = "coordinatorlayout")
    exclude(group = "androidx.drawerlayout", module = "drawerlayout")
    exclude(group = "androidx.viewpager2", module = "viewpager2")
    exclude(group = "androidx.viewpager", module = "viewpager")
    exclude(group = "androidx.appcompat", module = "appcompat")
    // Play Services pulls stock Fragment, but One UI Design supplies the SESL
    // implementation under the same AndroidX package names.
    exclude(group = "androidx.fragment", module = "fragment")
    // SESL9 Core and Fragment include their Kotlin extensions.
    exclude(group = "sesl.androidx.core", module = "core-ktx")
    exclude(group = "androidx.fragment", module = "fragment-ktx")
    exclude(group = "androidx.preference", module = "preference")
    exclude(group = "androidx.recyclerview", module = "recyclerview")
    exclude(group = "androidx.swiperefreshlayout", module = "swiperefreshlayout")
    exclude(group = "androidx.slidingpanelayout", module = "slidingpanelayout")
    exclude(group = "com.google.android.material", module = "material")
}

dependencies {
    implementation(project(":core:model"))
    implementation(libs.oneui.icons)
    implementation(libs.oneui.design) {
        // The design library's optional barcode scanner is unused; keep OneOS offline.
        exclude(group = "com.google.android.gms", module = "play-services-mlkit-barcode-scanning")
        exclude(group = "com.google.mlkit", module = "barcode-scanning-common")
    }
    implementation(libs.bundles.sesl9)
}
