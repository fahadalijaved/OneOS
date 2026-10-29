package com.fahadali.oneos.core.model

import java.util.Locale

/**
 * The system an image is a build of. Guest data stays with its own system:
 * a stage's ColorOS data is never kept for the Pixel image, nor Pixel data
 * for a ColorOS image (StageStatus.beginModes, root's `begin keep`, 0.3.7).
 * Infinity-X (0.4.27) is its own: its data has OPPO's and LineageOS's
 * packages too, and its updater, com.infinity.updater, tells it apart.
 */
enum class SystemFamily { COLOROS, PIXEL, INFINITYX }

/**
 * One OneOS OS image as friends download it (a gzip of the ext4 system
 * image) and as root stages it (`$STAGE/system.raw`). Both hashes are pinned:
 * the app checks the .gz, root checks the unpacked bytes (AA4, XP2).
 */
data class ImageRef(
    val id: String,
    /** "ColorOS 17, Find X9 Ultra build": the technical label (All checks, the findings). */
    val label: String,
    /** "Find X9 Ultra": tells the builds of one system apart in technical messages. */
    val shortName: String,
    /**
     * The system's name as the user sees it, `{system}` in every plain text:
     * "ColorOS 17", "Pixel 11 Fold". Brand names live only here, in the
     * credits and in the legal line.
     */
    val name: String,
    /** Tells two images of the same [name] apart on the cards: "Find N6 build", "Find X9 Ultra build"; null = none needed. */
    val variant: String?,
    /** One line for its card: "Google's Pixel software." */
    val blurb: String,
    /** The shared link "Download" opens in the browser (no in-app download yet); null = none. */
    val downloadUrl: String?,
    /** Guest SDK; must equal the host's (a guest shares One UI's system services). */
    val sdk: Int,
    val buildId: String,
    /** File name of the upload. */
    val gzName: String,
    val gzBytes: Long,
    val gzSha256: String,
    /** Unpacked size and SHA-256, as staged in `$STAGE/system.raw`. */
    val rawBytes: Long,
    val rawSha256: String,
    /** Where a session has run with it; null = untested. */
    val testedOn: String?,
    /** CPU features the image may not start without (missing = WARN). */
    val cpuRequired: List<String>,
    /** CPU features only some OPPO app and media libraries use (missing = WARN that those features may crash). */
    val cpuUsedByApps: List<String>,
    /**
     * Play services and the Play Store are in the image (the Pixel image; the
     * ColorOS CN builds have none). The image's card says so; a launch may hide
     * them only when [gmsHideable].
     */
    val googleServices: Boolean,
    /**
     * Sessions present the image's own GmsCore: its file sets stage
     * `gmssystem_payload.img`, which guest_prepare.sh mounts and presents
     * (docs/pixel-guest.md, "Google services"). Then Google services cannot be
     * hidden for a launch: oneos_switch.sh refuses `ONEOS_GUEST_HIDE_GMS=1`
     * next to that payload while `ONEOS_GUEST_GMS` is on, and session.env
     * cannot turn that off. [PackageSetsTest] keeps this equal to the sets.
     */
    val presentsGms: Boolean = false,
    /** Whose system it is: its guest data is kept only for an image of the same family. */
    val family: SystemFamily,
) {
    /**
     * A launch may hide Google services (`ONEOS_GUEST_HIDE_GMS=1`, [SessionEnv],
     * root's `IMAGES_GMS`): the image has them and its sessions do not present them.
     */
    val gmsHideable: Boolean get() = googleServices && !presentsGms

    /** "Pixel 11 Fold (Android 17)", "ColorOS 17 · Find N6 build (Android 17)": unique on a phone ([ImagesTest]). */
    val displayName: String
        get() = "$nameWithVariant (Android ${AndroidRelease.name(sdk)})"

    /** "ColorOS 17 · Find N6 build", or just [name] when there is no [variant]. */
    val nameWithVariant: String get() = listOfNotNull(name, variant).joinToString(" · ")

    /** The gzip ISIZE trailer: the unpacked size mod 2^32 (RFC 1952), an early check before the hash. */
    val gzIsize: Long get() = rawBytes and 0xffff_ffffL

    fun gzMatches(bytes: Long, sha256: String): Boolean =
        bytes == gzBytes && sha256.lowercase(Locale.ROOT) == gzSha256

    fun rawMatches(bytes: Long, sha256: String): Boolean =
        bytes == rawBytes && sha256.lowercase(Locale.ROOT) == rawSha256
}

/**
 * The built-in image table. Sizes and hashes verified on the server on
 * 2026-10-22 (the Pixel 11 Fold image on 2026-10-24): the gunzip of each
 * upload is byte-identical to the server image. 0.3.7 dropped the Find X9
 * Ultra IN build (`coloros17-findx9u-in`); 0.4.11 takes it again.
 */
object Images {
    /** Where the images come from: the README (this repository does not host them). */
    const val SHARED_FOLDER_URL = "https://github.com/fahadalijaved/OneOS#where-the-images-come-from"

    /** What fixed texts say when no image is known: they never name a system. */
    const val OTHER_SYSTEM = "the other system"

    const val ID_FIND_N6 = "coloros17-findn6"
    const val ID_FIND_X9U = "coloros17-findx9u"
    const val ID_FIND_X9U_IN = "coloros17-findx9u-in"
    const val ID_PIXEL_YOGI = "pixel11fold-yogi"
    const val ID_PIXEL_KODIAK = "pixel11pro-kodiak"
    const val ID_PIXEL_KOMODO = "pixel9proxl-komodo"
    const val ID_INFINITYX = "infinityx41-findx9u"

    /** Where root stages the unpacked image. */
    const val STAGE_NAME = "system.raw"

    /** The ext4 superblock magic 0xEF53, little endian at byte 1080 of the unpacked image. */
    const val EXT4_MAGIC_OFFSET = 1080L
    const val EXT4_MAGIC = 0xEF53

    val FIND_N6 = ImageRef(
        id = ID_FIND_N6,
        label = "ColorOS 17, Find N6 build",
        shortName = "Find N6",
        name = "ColorOS 17",
        variant = "Find N6 build",
        blurb = "OPPO's system from the Find N6. No Google apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CP2A.260605.016",
        gzName = "OneOS_ColorOS17_FindN6_ZFold8.img.gz",
        gzBytes = 5_285_345_619L,
        gzSha256 = "4d371cbeb5da0b7c4b67ff44ce437ca56a244b0e3a93e1a696099ab6071d1809",
        rawBytes = 10_276_003_840L,
        rawSha256 = "bdf5ef00aee3333758afdde152a29e0d2ca7bdaf89029ccd74bad34eec5bf444",
        testedOn = "Z Fold (F8U)",
        // MysticGSI's build warning on linker64 (SVE/SVE2, SME); the Find N6
        // image has only run on a CPU that has them.
        cpuRequired = CpuRules.COLOROS_REQUIRED,
        cpuUsedByApps = emptyList(),
        googleServices = false,
        family = SystemFamily.COLOROS,
    )

    val FIND_X9U = ImageRef(
        id = ID_FIND_X9U,
        label = "ColorOS 17, Find X9 Ultra build",
        shortName = "Find X9 Ultra",
        name = "ColorOS 17",
        variant = "Find X9 Ultra build",
        blurb = "OPPO's system from the Find X9 Ultra. No Google apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CP2A.260605.016",
        gzName = "OneOS_ColorOS17_FindX9Ultra_S26U.img.gz",
        gzBytes = 5_290_346_735L,
        gzSha256 = "9796d27676dfd709ab4b26caf30fa19bc78ab2a24f5cf19e974a3e8708e919fe",
        rawBytes = 10_385_141_760L,
        rawSha256 = "302467fc4e77998e84c10e037326508a39ab9e4be34058b751f0a768c7ff23e7",
        testedOn = "Galaxy S25, S25 Ultra and S26 Ultra",
        // The scan of this image: SVE/SME only in bionic's guarded routines
        // (runtime-selected) and some OPPO app and media libraries.
        cpuRequired = emptyList(),
        cpuUsedByApps = listOf("sve2", "sme"),
        googleServices = false,
        family = SystemFamily.COLOROS,
    )

    /**
     * The global (India) build of the same phone, back in 0.4.11 (0.3.3-0.3.6
     * took it; 0.3.7 dropped it when its server build was deleted for space):
     * Google's mainline modules, Play services and the Play Store in
     * my_product (owner: "IN build is just better"; friends run it). The
     * upload of 2026-10-25 is the 0.3.3 file, byte for byte.
     */
    val FIND_X9U_IN = ImageRef(
        id = ID_FIND_X9U_IN,
        label = "ColorOS 17, Find X9 Ultra IN build",
        shortName = "Find X9 Ultra IN",
        name = "ColorOS 17",
        variant = "global build",
        blurb = "OPPO's global system from the Find X9 Ultra, with Google Play and the Play Store.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CP2A.260605.016",
        gzName = "OneOS_ColorOS17_FindX9Ultra_IN.img.gz",
        gzBytes = 5_882_128_321L,
        gzSha256 = "413380426cdff8b5e760f1424895fc5b43e7a6ffe5f889e0406e437590c0d04e",
        rawBytes = 12_069_945_344L,
        rawSha256 = "a36ef550f4b2530fb9c7c6d363180d9eb4437e0497ebc87292697e4bf2a580b0",
        testedOn = null,
        cpuRequired = emptyList(),
        cpuUsedByApps = listOf("sve2", "sme"),
        googleServices = true,
        family = SystemFamily.COLOROS,
    )

    /**
     * Google's Pixel 11 Fold system (yogi, `google/yogi/yogi:17/CD1A.261005.003.B1`),
     * built with MysticGSI (`scripts/build-gsi.sh --type pixel`,
     * `out/oneos-pixel-yogi.img`; docs/pixel-guest.md). Runs 41-44 booted it on
     * the Z Fold (F8U) from scripts/deploy-phone.sh; its set stages GmsCore.
     */
    val PIXEL_YOGI = ImageRef(
        id = ID_PIXEL_YOGI,
        label = "Pixel 11 Fold, yogi build",
        shortName = "Pixel 11 Fold",
        name = "Pixel 11 Fold",
        variant = null,
        blurb = "Google's system from the Pixel 11 Fold, with Google Play and Google's apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CD1A.261005.003.B1",
        gzName = "OneOS_Pixel11Fold_Full_ZFold8.img.gz",
        gzBytes = 3_288_346_862L,
        gzSha256 = "8fbe950c47629c439af0807fc6bbb2afa29308c65c215849bcfa7a01f6b9290d",
        rawBytes = 6_559_223_808L,
        rawSha256 = "8b303c37916288545b3b4a317c368d89680b5c3ce09873dc764381ddd0e32830",
        testedOn = "Z Fold (F8U)",
        // Disassembly of the image's /system/bin/bootstrap/linker64 (2026-10-24,
        // llvm-objdump; MysticGSI's build warning names MOPS and SME there, SVE/SVE2
        // in /system/bin/init): unguarded SVE in the loader itself (__linker_init,
        // ElfReader::Load, load_library, linker_memcpy) and SVE2 (MATCH in
        // android::base::Split, EOR3, XAR), so the image is built for an SVE2 CPU.
        // SME only in compiler-rt's SME state routines, each behind the CPU feature
        // bit, and MOPS only in the memmove/memset ifunc variants: it booted on the
        // F8U's SM8850, which has SVE, SVE2 and SME but no MOPS or SME2. No app or
        // library scan beyond the loader.
        cpuRequired = listOf("sve", "sve2"),
        cpuUsedByApps = emptyList(),
        googleServices = true,
        presentsGms = true,
        family = SystemFamily.PIXEL,
    )

    /**
     * Google's Pixel 11 Pro system (kodiak, `CD1A.261005.003.B1`, the same build
     * as the Pixel 11 Fold's), from 0.4.10 for the Galaxy S26 Ultra: the factory
     * image, MysticGSI `--type pixel --no-debloat`, then Pixel Camera,
     * PixelCameraServices, PixelDisplayService and grilservice removed, as for the
     * Fold's full image. Its system code uses SVE in every process (RefBase's
     * constructor), so only SM8850 phones take it. Untested.
     */
    val PIXEL_KODIAK = ImageRef(
        id = ID_PIXEL_KODIAK,
        label = "Pixel 11 Pro, kodiak build",
        shortName = "Pixel 11 Pro",
        name = "Pixel 11 Pro",
        variant = null,
        blurb = "Google's system from the Pixel 11 Pro, with Google Play and Google's apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CD1A.261005.003.B1",
        gzName = "OneOS_Pixel11Pro_Full_S26U.img.gz",
        gzBytes = 3_266_985_222L,
        gzSha256 = "ee9b6005a086627220841618ea2edaa278c4e153460f7f947fc7fc9dea8d727c",
        rawBytes = 6_529_871_872L,
        rawSha256 = "ac661a520263fa73a2b9996f19763350457b1558863d1dc15326a365ce1784c6",
        testedOn = null,
        cpuRequired = listOf("sve", "sve2"),
        cpuUsedByApps = emptyList(),
        googleServices = true,
        presentsGms = true,
        family = SystemFamily.PIXEL,
    )

    /**
     * Google's Pixel 9 Pro XL system (komodo, `google/komodo/komodo:17/CP3A.261005.005`),
     * from 0.4.22 for the phones without SVE (Galaxy S25 Ultra, S25, S25+, S24
     * Ultra): the factory image (owner's link), MysticGSI `--type pixel
     * --no-debloat`, then Pixel Camera, PixelCameraServices, PixelDisplayService
     * and grilservice removed, as for the Pixel 11 images. Disassembly
     * (llvm-objdump, 2026-10-26) finds no SVE in libutils, libbinder, libhwui,
     * libgui, libandroid_runtime, init, surfaceflinger, servicemanager,
     * app_process64 or the boot image; the loader's only SVE (two cntd, which
     * MysticGSI's build warning names) is in compiler-rt's SME state routines,
     * behind the CPU feature bit. No app or library scan beyond those. Untested.
     */
    val PIXEL_KOMODO = ImageRef(
        id = ID_PIXEL_KOMODO,
        label = "Pixel 9 Pro XL, komodo build",
        shortName = "Pixel 9 Pro XL",
        name = "Pixel 9 Pro XL",
        variant = null,
        blurb = "Google's system from the Pixel 9 Pro XL, with Google Play and Google's apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CP3A.261005.005",
        gzName = "OneOS_Pixel9ProXL_Full_S25U.img.gz",
        gzBytes = 2_925_465_896L,
        gzSha256 = "b49a3f8e8825241083d564c6e49118e59049f5bc887443e19411909e6d770266",
        rawBytes = 5_837_496_320L,
        rawSha256 = "2ef2dfe164dc6cac44c574696da474e71a01d9a769eda9c1a265d018c1d45a5c",
        testedOn = null,
        cpuRequired = emptyList(),
        cpuUsedByApps = emptyList(),
        googleServices = true,
        presentsGms = true,
        family = SystemFamily.PIXEL,
    )

    /**
     * Project Infinity-X 4.1 for the Find X9 Ultra (lighthouse,
     * `infinity_lighthouse-user`, CP2A.260605.016), from 0.4.27 on every phone:
     * a custom Android 17 built from source on LineageOS, with Google's apps
     * (Play services in a product gmssystem APEX, as Pixel 17 keeps it, so its
     * set stages the payload and sessions present it) and OPPO's framework jars of
     * ColorOS 16 (oplus-fwk.jar, oplus-services.jar) for its camera port. The
     * unofficial 2026-10-18 GAPPS build, made with MysticGSI (which takes it
     * for ColorOS) and not changed. Its own vold and service.incremental.so
     * (make-overlays.sh pins them for the guest vold as gvld); its duress-PIN
     * wipe and OPPO's extended wipe never run in the guest
     * (guest_no_wipe_secrets.py). Disassembly (llvm-objdump, 2026-10-29) finds
     * no SVE or SME in libutils, libbinder, libhwui, libgui,
     * libandroid_runtime, libc++, surfaceflinger, servicemanager,
     * app_process64 or init; only the loader's compiler-rt routines (cntd,
     * rdsvl), behind the CPU feature bit. OPPO's camera and gallery libraries
     * were not scanned. Untested.
     */
    val INFINITYX = ImageRef(
        id = ID_INFINITYX,
        label = "Infinity-X 4.1, Find X9 Ultra build",
        shortName = "Infinity-X",
        name = "Infinity-X 4.1",
        variant = null,
        blurb = "A custom Android 17 system made for the Find X9 Ultra, with Google Play and Google's apps.",
        downloadUrl = SHARED_FOLDER_URL,
        sdk = 37,
        buildId = "CP2A.260605.016",
        gzName = "OneOS_InfinityX_FindX9Ultra.img.gz",
        gzBytes = 3_321_412_981L,
        gzSha256 = "608bb8602dcc0c85fc80127a2f9713a695508438b8c2d31eef3df25d23109bb5",
        rawBytes = 6_677_426_176L,
        rawSha256 = "899ce57a069959b6463263074f35e5aadadeb7bb46f0c0a756d2ba64168545e2",
        testedOn = null,
        cpuRequired = emptyList(),
        cpuUsedByApps = listOf("sve2", "sme"),
        googleServices = true,
        presentsGms = true,
        family = SystemFamily.INFINITYX,
    )

    val ALL: List<ImageRef> = listOf(FIND_N6, FIND_X9U, FIND_X9U_IN, PIXEL_YOGI, PIXEL_KODIAK, PIXEL_KOMODO, INFINITYX)

    fun byId(id: String, images: List<ImageRef> = ALL): ImageRef? = images.firstOrNull { it.id == id }

    /**
     * Images earlier builds took and this one no longer sets up, for their
     * names only (an old stage's marker, a copy set aside, the last session, a
     * remembered download). None since 0.4.11: the Find X9 Ultra IN build,
     * dropped in 0.3.7, is back in [ALL].
     */
    val RETIRED: List<RetiredImage> = emptyList()

    /** "Find N6", a retired image's name, or the id itself when no build knew it. */
    fun shortName(id: String, images: List<ImageRef> = ALL, retired: List<RetiredImage> = RETIRED): String =
        byId(id, images)?.shortName ?: retired.firstOrNull { it.id == id }?.shortName ?: id

    /** The image whose .gz has exactly this size (`OpenableColumns.SIZE`). */
    fun byGzSize(bytes: Long, images: List<ImageRef> = ALL): ImageRef? = images.firstOrNull { it.gzBytes == bytes }

    fun byRawSize(bytes: Long, images: List<ImageRef> = ALL): ImageRef? = images.firstOrNull { it.rawBytes == bytes }

    /**
     * `{system}` in a plain text: [image]'s name ("ColorOS 17", "Pixel 11
     * Fold"), with its variant when [profile] takes another image of the same
     * name, so the two are never confused ("ColorOS 17 · Find N6 build"); "the
     * other system" when no image is known.
     */
    fun systemName(image: ImageRef?, profile: PhoneProfile? = null, images: List<ImageRef> = ALL): String {
        if (image == null) return OTHER_SYSTEM
        val twin = profile?.images(images).orEmpty().any { it.id != image.id && it.name == image.name }
        return if (twin) image.nameWithVariant else image.name
    }
}

/** An image an earlier build took ([Images.RETIRED]): its name and sizes, so it is told apart from a file that is no OneOS image. */
data class RetiredImage(val id: String, val shortName: String, val gzName: String, val gzBytes: Long, val rawBytes: Long)

/** What the app knows about the file the user picked (ImageActivity, AA1). */
data class ImageFileCheck(
    /** `OpenableColumns.DISPLAY_NAME`, for messages only. */
    val displayName: String?,
    /** `OpenableColumns.SIZE`; null when the provider does not say. */
    val bytes: Long?,
    /** SHA-256 of the whole stream; null until "Check file" has run. */
    val sha256: String? = null,
    /** Bytes read while hashing; null until hashed. */
    val hashedBytes: Long? = null,
)

/** The stage's `system.raw` as root's read-only check found it ("Use the image already on this phone"). */
data class StagedRaw(
    /** Its size now; null = there is none. */
    val bytes: Long?,
    /**
     * The SHA-256 root checked when it staged the file (`system.raw.id`), only
     * while the file is unchanged since (same size and dev:inode:size:mtime);
     * null = not known.
     */
    val verifiedSha256: String? = null,
)

enum class ImageState {
    /** Size and SHA-256 are an image this phone accepts. */
    VERIFIED,
    /** Size matches an image this phone accepts; not hashed yet. */
    NOT_CHECKED,
    /** A OneOS image, but not one this phone accepts. */
    WRONG_FOR_PHONE,
    /** Size or SHA-256 differ: damaged or incomplete download. */
    DAMAGED,
    /** The unpacked image; the app stages only the .img.gz. */
    UNCOMPRESSED,
    /** Not a OneOS image, or the size is unknown. */
    UNKNOWN,
}

data class ImageIdentity(val state: ImageState, val image: ImageRef?, val finding: Finding)

/**
 * Identifies the picked file against the images the phone's profile accepts
 * ([PhoneProfile.choices]) and says which one it is: by size first (cheap,
 * before any hashing), then by SHA-256 after "Check file". Only
 * [ImageState.VERIFIED] is OK; everything else is a BLOCK, and an image the
 * phone does not accept names the ones it does. [profile] null skips the
 * "right image for this phone" check (the profile gate refuses that phone anyway).
 */
object ImageIdentifier {
    const val ID = "gate-image"

    /** [Finding.reason]s of the picked .gz ([identify]). */
    const val R_SIZE_UNKNOWN = "size-unknown"
    const val R_UNCOMPRESSED = "uncompressed"
    const val R_NOT_OURS = "not-ours"
    const val R_WRONG_PHONE = "wrong-phone"
    const val R_NOT_CHECKED = "not-checked"
    const val R_DAMAGED = "damaged"

    /** The .gz of an image an earlier build took ([Images.RETIRED]). */
    const val R_RETIRED = "retired"

    /** [Finding.reason]s of the stage's system.raw ([identifyStaged]). */
    const val R_NO_RAW = "no-raw"
    const val R_RAW_NOT_OURS = "raw-not-ours"
    const val R_RAW_WRONG_PHONE = "raw-wrong-phone"
    const val R_RAW_DAMAGED = "raw-damaged"

    /** "Z Fold (F8U) takes the Find N6 image (….gz) or the Pixel 11 Fold image (….gz)". */
    fun accepts(profile: PhoneProfile?, images: List<ImageRef> = Images.ALL): String {
        val want = profile?.images(images).orEmpty()
        return if (profile != null && want.isNotEmpty()) {
            "${profile.label} takes " + want.joinToString(" or ") { "the ${it.shortName} image (${it.gzName})" }
        } else {
            "the OneOS images are ${images.joinToString(" and ") { it.gzName }}"
        }
    }

    fun identify(
        check: ImageFileCheck,
        profile: PhoneProfile?,
        images: List<ImageRef> = Images.ALL,
        retiredImages: List<RetiredImage> = Images.RETIRED,
    ): ImageIdentity {
        val name = check.displayName?.takeIf { it.isNotBlank() }?.let { "'${it.take(120)}'" } ?: "This file"
        val size = check.hashedBytes ?: check.bytes
        val wantText = accepts(profile, images)

        if (size == null) {
            return ImageIdentity(
                ImageState.UNKNOWN, null,
                block("Image size unknown", "$name has no size. Tap Check file to read it; $wantText.", R_SIZE_UNKNOWN),
            )
        }
        val bySize = images.filter { it.gzBytes == size }
        if (bySize.isEmpty()) {
            val raw = Images.byRawSize(size, images)
            val retired = retiredImages.firstOrNull { it.gzBytes == size }
            return if (raw == null && retired != null) {
                ImageIdentity(
                    ImageState.UNKNOWN, null,
                    block(
                        "Image no longer supported",
                        "$name has the size of the ${retired.shortName} image (${retired.gzName}), which this version of OneOS no longer sets up: $wantText.",
                        R_RETIRED,
                    ),
                )
            } else if (raw != null) {
                val pick = if (profile == null || profile.choice(raw.id) != null) "pick ${raw.gzName}" else wantText
                ImageIdentity(
                    ImageState.UNCOMPRESSED, raw,
                    block("Pick the .img.gz file", "$name is the unpacked ${raw.shortName} image. OneOS unpacks the image itself: $pick.", R_UNCOMPRESSED),
                )
            } else {
                ImageIdentity(
                    ImageState.UNKNOWN, null,
                    block("Not a OneOS image", "$name (${Units.bytes(size)}) is not a OneOS image: $wantText.", R_NOT_OURS),
                )
            }
        }
        val accepted = if (profile == null) bySize else bySize.filter { profile.choice(it.id) != null }
        val sha = check.sha256?.lowercase(Locale.ROOT)
        // Hashed: the image whose size and SHA-256 both match, if any.
        val exact = sha?.let { h -> bySize.firstOrNull { it.gzMatches(size, h) } }
        if (accepted.isEmpty() || (exact != null && exact !in accepted)) {
            val other = exact ?: bySize.first()
            return ImageIdentity(
                ImageState.WRONG_FOR_PHONE, other,
                block("Wrong image for this phone", "This is the ${other.shortName} image; $wantText.", R_WRONG_PHONE),
            )
        }
        val image = exact ?: accepted.first()
        if (sha == null) {
            return ImageIdentity(
                ImageState.NOT_CHECKED, image,
                block("Check the file first", "$name has the size of the ${image.shortName} image. Tap Check file to verify it.", R_NOT_CHECKED),
            )
        }
        if (exact == null || (check.bytes != null && check.bytes != size)) {
            return ImageIdentity(
                ImageState.DAMAGED, image,
                block(
                    "The file is damaged or incomplete",
                    "$name does not match the ${image.shortName} image (SHA-256 ${sha.take(12)}..., expected " +
                        "${image.gzSha256.take(12)}...). Download it again.",
                    R_DAMAGED,
                ),
            )
        }
        return ImageIdentity(
            ImageState.VERIFIED, image,
            Finding(
                ID, Level.OK, "${image.shortName} image verified",
                "${image.label}: ${image.gzName}, ${Units.bytes(image.gzBytes)}, SHA-256 matches.",
            ),
        )
    }

    /**
     * "Use the image already on this phone": the stage's system.raw against the
     * images [profile] accepts, by size and, while root still vouches for the
     * file (system.raw.id), by SHA-256. Its size is enough to prepare (OK,
     * [ImageState.NOT_CHECKED]): root hashes it in keep-raw before anything
     * uses it, and moves it to the attic when it differs.
     */
    fun identifyStaged(
        raw: StagedRaw,
        profile: PhoneProfile?,
        images: List<ImageRef> = Images.ALL,
        retiredImages: List<RetiredImage> = Images.RETIRED,
    ): ImageIdentity {
        val wantText = accepts(profile, images)
        val size = raw.bytes ?: return ImageIdentity(
            ImageState.UNKNOWN, null,
            block("No image on this phone", "The stage has no system.raw. Pick the downloaded file instead: $wantText.", R_NO_RAW),
        )
        val bySize = images.filter { it.rawBytes == size }
        if (bySize.isEmpty()) {
            val retired = retiredImages.firstOrNull { it.rawBytes == size }
            return ImageIdentity(
                ImageState.UNKNOWN, null,
                if (retired != null) {
                    block(
                        "Image no longer supported",
                        "system.raw in the stage has the size of the ${retired.shortName} image, which this version of OneOS no longer sets up. " +
                            "Pick the downloaded file instead: $wantText.",
                        R_RAW_NOT_OURS,
                    )
                } else {
                    block(
                        "Not a OneOS image on this phone",
                        "system.raw in the stage (${Units.bytes(size)}) is not a OneOS image. Pick the downloaded file instead: $wantText.",
                        R_RAW_NOT_OURS,
                    )
                },
            )
        }
        val accepted = if (profile == null) bySize else bySize.filter { profile.choice(it.id) != null }
        val sha = raw.verifiedSha256?.lowercase(Locale.ROOT)
        val exact = sha?.let { h -> bySize.firstOrNull { it.rawMatches(size, h) } }
        if (accepted.isEmpty() || (exact != null && exact !in accepted)) {
            val other = exact ?: bySize.first()
            return ImageIdentity(
                ImageState.WRONG_FOR_PHONE, other,
                block(
                    "Wrong image on this phone",
                    "system.raw in the stage is the ${other.shortName} image; $wantText. Pick the downloaded file instead.",
                    R_RAW_WRONG_PHONE,
                ),
            )
        }
        val image = exact ?: accepted.first()
        return when {
            sha != null && exact == null -> ImageIdentity(
                ImageState.DAMAGED, image,
                block(
                    "Not the ${image.shortName} image",
                    "system.raw has the ${image.shortName} image's size, but root staged it with another SHA-256 " +
                        "(${sha.take(12)}...). Pick ${image.gzName} instead.",
                    R_RAW_DAMAGED,
                ),
            )
            exact != null -> ImageIdentity(
                ImageState.VERIFIED, image,
                Finding(
                    ID, Level.OK, "${image.shortName} image already on this phone",
                    "system.raw is the ${image.shortName} image (${Units.bytes(size)}), checked by root when it was staged. " +
                        "Prepare has root check its SHA-256 again (about a minute).",
                ),
            )
            else -> ImageIdentity(
                ImageState.NOT_CHECKED, image,
                Finding(
                    ID, Level.OK, "${image.shortName} image already on this phone",
                    "system.raw has the size of the ${image.shortName} image (${Units.bytes(size)}). Prepare has root " +
                        "check its SHA-256 (about a minute); if it differs, it is moved to the attic and you pick the .gz.",
                ),
            )
        }
    }

    private fun block(title: String, detail: String, reason: String) = Finding(ID, Level.BLOCK, title, detail, reason)
}
