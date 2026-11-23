import java.io.File
import java.util.Properties

// Credentials for the tribalfs GitHub Packages repos (below). The environment
// (GH_PACKAGES_USER, GH_PACKAGES_TOKEN) wins; local credentials outside the
// checkout (~/.config/twidget/github.properties) are the fallback.
val githubPropertiesFile = File(
    System.getProperty("user.home"),
    ".config/twidget/github.properties",
)
val githubProperties = Properties().apply {
    githubPropertiesFile.takeIf { it.isFile }?.inputStream()?.use { load(it) }
}
// Environment variables override any stale local properties; never store tokens in git.
val ghPackagesUser: String =
    System.getenv("GH_PACKAGES_USER")?.takeIf { it.isNotBlank() }
        ?: githubProperties.getProperty("ghUsername").orEmpty()
val ghPackagesToken: String =
    System.getenv("GH_PACKAGES_TOKEN")?.takeIf { it.isNotBlank() }
        ?: githubProperties.getProperty("ghAccessToken").orEmpty()

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

// Tribalfs publishes the pinned SESL9 and One UI design artifacts to three
// separate GitHub Packages Maven registries, not Maven Central. A GitHub PAT
// (classic) with read:packages is required even for public packages.
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://jitpack.io") {
            // Tribalfs is published on GitHub Packages, not on JitPack.
            content {
                excludeGroup("io.github.tribalfs")
                excludeGroupByRegex("sesl[.].*")
            }
        }
        // Match each group to its actual publisher repo, not tribalfs/*.
        maven("https://maven.pkg.github.com/tribalfs/oneui-design") {
            content { includeGroup("io.github.tribalfs") }
            credentials { username = ghPackagesUser; password = ghPackagesToken }
        }
        maven("https://maven.pkg.github.com/tribalfs/sesl-androidx") {
            content { includeGroupByRegex("sesl[.]androidx[.].*") }
            credentials { username = ghPackagesUser; password = ghPackagesToken }
        }
        maven("https://maven.pkg.github.com/tribalfs/sesl-material-components-android") {
            content { includeGroup("sesl.com.google.android.material") }
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
