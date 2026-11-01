import java.io.File
import java.util.Properties

// Credentials for the tribalfs/oneui-design GitHub Packages repo. Local
// credentials live outside the checkout under ~/.config/twidget. CI falls
// back to environment variables.
val githubPropertiesFile = File(
    System.getProperty("user.home"),
    ".config/twidget/github.properties",
)
val githubProperties = Properties().apply {
    githubPropertiesFile.takeIf { it.isFile }?.inputStream()?.use { load(it) }
}
val ghPackagesUser: String =
    githubProperties.getProperty("ghUsername") ?: System.getenv("GH_PACKAGES_USER") ?: ""
val ghPackagesToken: String =
    githubProperties.getProperty("ghAccessToken") ?: System.getenv("GH_PACKAGES_TOKEN") ?: ""

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

// SESL (io.github.oneuiproject.sesl:*) and the One UI design library are on
// Maven Central: no GitHub Packages token needed (docs/app/DESIGN.md, top).
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://jitpack.io")
        maven("https://maven.pkg.github.com/tribalfs/*") {
            credentials { username = ghPackagesUser; password = ghPackagesToken }
        }
    }
}

rootProject.name = "OneOS"

include(":app")
// OneOS inside the guest: "Back to One UI" (guest/build.gradle.kts).
include(":guest")
include(":core:model")
include(":core:device")
include(":core:root")
include(":core:safety")
