package com.fahadali.oneos.core.model

/**
 * Experimental tester builds. Only an APK built with `-Poneos.a17OnA16=true` (versionName `-oneui8testN`) sets
 * [a17OnA16]: One UI 9.5 ([Images.ID_ONEUI95], Android 17, SDK 37) on phones still on One UI 8.0/8.5 (Android 16,
 * SDK 36). Every other build, and every unit test that does not ask for it, keeps the rule that a guest is the
 * phone's Android version.
 *
 * Why this one pair can be tried: the One UI 9.5 set's guard jars read the phone's installd codes at runtime by
 * name and signature and refuse a call the phone's table does not have (OneOSInstalldCodes, guest_installd_abi.py),
 * and IGateKeeperService codes 1-6 are the same in AOSP Android 16 and One UI 9.5 (7 and 8 are new, refused by an
 * Android 16 host). The set's camera codes are One UI 9.0's, so the session keeps the camera off on such a phone
 * (guest_prepare.sh), and the guest reports its own Android version (guest_props.sh).
 */
object Experimental {
    /**
     * Set once by the app (OneOsApplication, from BuildConfig.A17_ON_A16) before anything reads [Profiles.BUILT_IN],
     * which is built from it. False in every normal build.
     */
    @Volatile
    var a17OnA16: Boolean = false

    /**
     * 0.5.51 testing APK only (-Poneos.colorOsOnA16=true, BuildConfig.COLOROS_ON_A16): with [a17OnA16], the S22 series
     * also offers ColorOS 17 on One UI 8 ([Profiles.withColorOsOnA16]). Set with [a17OnA16], before [Profiles.BUILT_IN].
     */
    @Volatile
    var colorOsOnA16: Boolean = false

    /** The phone's SDK the tester build accepts under an SDK 37 image (One UI 8.0 and 8.5). */
    const val A16_HOST_SDK = 36

    /** The image's SDK it accepts there. */
    const val A17_IMAGE_SDK = 37

    /**
     * One UI 9.5 on a One UI 8 phone, in a build with [on]; and 0.5.51 (owner: ColorOS for the S22s) ColorOS 17 Find X9
     * Ultra IN, only with its One UI 8 set [PackageSets.ID_X9U_IN_1105_A16] ([setId], the choice's set): its plain set
     * lacks the image's Android 17 modules One UI 8 cannot lend.
     */
    fun a17OnA16Pair(hostSdk: Int, image: ImageRef?, on: Boolean = a17OnA16, setId: String? = null): Boolean =
        on && hostSdk == A16_HOST_SDK && image != null && image.sdk == A17_IMAGE_SDK &&
            (image.id == Images.ID_ONEUI95 || (image.id == Images.ID_FIND_X9U_IN_1105 && setId == PackageSets.ID_X9U_IN_1105_A16))

    /** [profile] offers One UI 9.5 to this SDK [hostSdk] phone in a build with [on] (no system chosen yet). */
    fun a17OnA16Offered(hostSdk: Int, profile: PhoneProfile?, on: Boolean = a17OnA16, images: List<ImageRef> = Images.ALL): Boolean =
        profile != null && profile.choices.any { a17OnA16Pair(hostSdk, Images.byId(it.imageId, images), on, it.packageSetId) }
}
