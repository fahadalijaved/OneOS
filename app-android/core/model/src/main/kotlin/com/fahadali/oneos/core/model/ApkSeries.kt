package com.fahadali.oneos.core.model

/**
 * The OneOS downloads by phone series (0.4.25, owner: "start repacking apks
 * per device or at least series"). The all-in-one APK carried every package
 * set (1.37 GB at 0.4.24); a series APK carries only the sets its phones'
 * systems use, about 0.6 GB. app/build.gradle.kts builds one with
 * -Poneos.series=<id> from app-android/packages/series.txt, which lists the
 * same sets as [setIds] (ApkSeriesTest); the version name then ends in
 * "-<id>" (OneOS-0.4.25-fold.apk). Without the property it packs every set.
 * Every profile is in exactly one series.
 */
enum class ApkSeries(val id: String, val label: String, val profileIds: List<String>) {
    FOLD("fold", "Galaxy Z Fold", listOf(Profiles.ID_F8U, Profiles.ID_FOLD8, Profiles.ID_FOLD7, Profiles.ID_FOLD6, Profiles.ID_FOLD5)),
    S26(
        "s26",
        "Galaxy S26 series and Z Flip8",
        listOf(
            Profiles.ID_S_ULTRA_8850, Profiles.ID_S_PLUS_8850, Profiles.ID_S_8850, Profiles.ID_S_8850_JP, Profiles.ID_S_PLUS_9965,
            Profiles.ID_FLIP8, Profiles.ID_S_9965,
        ),
    ),
    S25(
        "s25",
        "Galaxy S25, S25 Edge, S25 FE, S24, S24 FE, S23, Z Flip7, Z Flip6, Z Flip5, the A series, and the phones on One UI 8 (S23 FE, S22, A, E)",
        listOf(
            Profiles.ID_S_ULTRA_8750, Profiles.ID_S_PLUS_8750, Profiles.ID_S_8750, Profiles.ID_S_ULTRA_8650,
            Profiles.ID_S_8550, Profiles.ID_S_PLUS_8550, Profiles.ID_FLIP7, Profiles.ID_A56, Profiles.ID_A57, Profiles.ID_FLIP5,
            Profiles.ID_A07, Profiles.ID_A36, Profiles.ID_S_ULTRA_8550, Profiles.ID_FLIP6, Profiles.ID_S_9945,
            Profiles.ID_S_EDGE_8750, Profiles.ID_S_FE_9945, Profiles.ID_A26, Profiles.ID_A17, Profiles.ID_A16, Profiles.ID_A16_4G, Profiles.ID_A16_S166, Profiles.ID_A35, Profiles.ID_A54, Profiles.ID_A27, Profiles.ID_A17_5G, Profiles.ID_FLIP7_FE, Profiles.ID_S_8650,
            // 0.4.67: the phones still on One UI 8 (OxygenOS 16 only).
            Profiles.ID_A06, Profiles.ID_A07_5G, Profiles.ID_A15, Profiles.ID_A24, Profiles.ID_A25, Profiles.ID_A33, Profiles.ID_A34,
            Profiles.ID_A53, Profiles.ID_E55, Profiles.ID_S_FE_9925, Profiles.ID_S_FE_8450, Profiles.ID_S_PLUS_9925,
            Profiles.ID_S_ULTRA_9925, Profiles.ID_S_ULTRA_8450,
            // 0.4.68: the Galaxy A55 5G and S25 FE (One UI 9), the Galaxy S22 with Snapdragon (One UI 8).
            Profiles.ID_A55, Profiles.ID_S25_FE, Profiles.ID_S_8450,
            // 0.4.70: the Galaxy M55s (One UI 8.5).
            Profiles.ID_M55S,
            // 0.4.74: the au Galaxy S22 Ultra (SCG14, One UI 8).
            Profiles.ID_S_ULTRA_8450_JP,
            // 0.4.83: the Galaxy S24+ with Exynos.
            Profiles.ID_S_PLUS_9945,
            // 0.4.92: the au Galaxy S23 Ultra (SCG20, One UI 9).
            Profiles.ID_S_ULTRA_8550_JP,
            // 0.4.93: the Galaxy S22 with Exynos (One UI 8.0) and the Galaxy A16 5G with MediaTek (One UI 8.5).
            Profiles.ID_S_9925, Profiles.ID_A16_MTK,
            // 0.4.93: the au Galaxy S23 (SCG19, One UI 9).
            Profiles.ID_S_8550_JP,
        ),
    ),
    ;

    /** The sets this series' APK carries: every set its phones' systems use. */
    fun setIds(profiles: List<PhoneProfile> = Profiles.BUILT_IN): Set<String> =
        profileIds.mapNotNull { id -> profiles.firstOrNull { it.id == id } }
            .flatMap { p -> p.choices.map { it.packageSetId } }
            .toSortedSet()

    companion object {
        fun byId(id: String?): ApkSeries? = entries.firstOrNull { it.id == id }

        /** The series a profile's phones download. */
        fun of(profileId: String): ApkSeries? = entries.firstOrNull { profileId in it.profileIds }
    }
}
