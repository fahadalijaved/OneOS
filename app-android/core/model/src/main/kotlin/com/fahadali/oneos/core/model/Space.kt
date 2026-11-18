package com.fahadali.oneos.core.model

/**
 * Free space a session needs (gate G9, docs/app/DESIGN.md section 4.3, AA17).
 * Staging: the image's unpacked size + its files + 8 GiB staged data + 1 GiB
 * logs + 2 GiB margin (the downloaded .gz is already on disk). At launch the
 * image is staged, so only data + logs + margin ([LAUNCH_BYTES]) must be free.
 */
object SpaceRule {
    const val GIB: Long = 1L shl 30

    /** The Find N6 image: the device report's size when no profile matches. */
    const val TYPICAL_IMAGE_BYTES: Long = 10_276_003_840L
    const val STAGED_DATA_BYTES: Long = 8 * GIB
    const val LOGS_BYTES: Long = 1 * GIB
    const val MARGIN_BYTES: Long = 2 * GIB

    /** Free at launch: data + logs + margin, 11 GiB. */
    const val LAUNCH_BYTES: Long = STAGED_DATA_BYTES + LOGS_BYTES + MARGIN_BYTES

    /** Margin when the guest data is already staged: nothing new is written but the session's logs. */
    const val STAGED_MARGIN_BYTES: Long = 1 * GIB

    /** Free at launch when the system is already set up with its data: logs + margin, 2 GiB. */
    const val LAUNCH_STAGED_BYTES: Long = LOGS_BYTES + STAGED_MARGIN_BYTES

    /** Free needed to switch: [LAUNCH_STAGED_BYTES] when the guest's data is already in the stage, else [LAUNCH_BYTES]. */
    fun launch(dataStaged: Boolean): Long = if (dataStaged) LAUNCH_STAGED_BYTES else LAUNCH_BYTES

    /** An image of [imageBytes] + data + logs + margin (the probe builds' rule, files not counted). */
    fun required(imageBytes: Long = TYPICAL_IMAGE_BYTES): Long = imageBytes + LAUNCH_BYTES

    /** To stage [image] with [set]: unpacked image + files + data + logs + margin. */
    fun toStage(image: ImageRef, set: PackageSet?): Long = image.rawBytes + (set?.approxBytes ?: 0L) + LAUNCH_BYTES
}
