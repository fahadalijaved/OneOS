package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.root.RootScript.BeginMode

/**
 * What setup does with the stage and where the system comes from, picked
 * from the stage itself instead of asked (the UX redesign, section 1.3):
 * nothing there starts new; OneOS's own stage with the same system keeps its
 * apps and data; anything else is set aside as an old copy (never deleted;
 * root refuses to keep another system's data anyway). Keeping a stage whose
 * system.raw root verified as this system reuses it, so an app update needs
 * no download (root re-hashes it in `keep-raw`). Advanced › Set up again
 * still offers the choice ([StageStatus.beginModes]).
 */
data class SetupPlan(
    val mode: BeginMode,
    val source: Source,
    val kind: Kind,
    /**
     * Set aside with its apps and data ([BeginMode.ASIDE] of a stage that has
     * guest data): the image it was made with (its marker's), or null when not
     * known (a stage OneOS did not finish or did not prepare).
     */
    val asideImageId: String?,
    /** [BeginMode.ASIDE] of a stage that holds a system's apps and data (the confirm says so). */
    val setsAsideData: Boolean,
) {
    enum class Source {
        /** The .img.gz the user downloaded and picked. */
        DOWNLOAD,

        /** The system already installed in the stage (root re-hashes it before reuse). */
        ON_PHONE,
    }

    enum class Kind {
        /** Nothing set up yet. */
        NEW,

        /** The same system, set up by another app version or with another file set. */
        UPDATE,

        /** The same system again (its files changed, or a setup that did not finish). */
        REPAIR,

        /** Another system (or a stage OneOS did not prepare) is set aside first. */
        REPLACE,
    }

    val needsDownload: Boolean get() = source == Source.DOWNLOAD

    val keepsData: Boolean get() = mode == BeginMode.KEEP

    companion object {
        /**
         * The plan for setting up [image] over [status]; null when the stage
         * path is not a folder (a link or a file: setup refuses). [hasDownload]:
         * the user picked the .gz, so an installed system that root has not
         * vouched for is not reused.
         */
        fun decide(status: StageStatus, image: ImageRef, profile: PhoneProfile?, appVersionCode: Int?, hasDownload: Boolean): SetupPlan? {
            val modes = status.beginModes(image.id)
            if (modes.isEmpty()) return null
            if (modes == listOf(BeginMode.NEW)) return SetupPlan(BeginMode.NEW, Source.DOWNLOAD, Kind.NEW, null, setsAsideData = false)
            val marker = status.marker?.takeIf { status.ours } ?: status.pendingUpdate?.takeIf { status.partial }
            val sameOurs = marker != null && marker.imageId == image.id && (profile == null || marker.profileId == profile.id)
            // A preparation of OneOS's that stopped: keep it only while nothing in it can be another system's:
            // no data, or this image's own system's data (ColorOS or Pixel, 0.3.7) with system.raw root verified as it.
            val partialSafe = status.partial && (
                status.guest == GuestData.NONE || status.guest == GuestData.EMPTY ||
                    (status.guest.family == image.family && status.rawVerifiedSha256 == image.rawSha256)
                )
            val keep = BeginMode.KEEP in modes && (sameOurs || partialSafe)
            if (!keep) {
                val data = status.guest != GuestData.NONE && status.guest != GuestData.EMPTY
                return SetupPlan(BeginMode.ASIDE, Source.DOWNLOAD, Kind.REPLACE, marker?.imageId?.takeIf { data }, setsAsideData = data)
            }
            val verified = status.rawVerifiedSha256 == image.rawSha256
            val sameSize = status.rawSize == image.rawBytes
            val source = if (verified || (status.pendingUpdate != null && sameOurs && sameSize) || (!hasDownload && sameSize)) Source.ON_PHONE else Source.DOWNLOAD
            val wantSet = profile?.choice(image.id)?.packageSetId
            val kind = when {
                status.pendingUpdate != null && sameOurs -> Kind.UPDATE
                marker == null -> Kind.REPAIR
                appVersionCode != null && marker.versionCode != appVersionCode -> Kind.UPDATE
                wantSet != null && marker.setId != wantSet -> Kind.UPDATE
                else -> Kind.REPAIR
            }
            return SetupPlan(BeginMode.KEEP, source, kind, null, setsAsideData = false)
        }

        /**
         * Setting [image] up again keeps the stage and reuses the system
         * installed in it, which root verified: no download (update or repair).
         */
        fun reusesInstalled(status: StageStatus, image: ImageRef, profile: PhoneProfile?, appVersionCode: Int?): Boolean {
            val p = decide(status, image, profile, appVersionCode, hasDownload = false) ?: return false
            return p.keepsData && p.source == Source.ON_PHONE && (status.rawVerifiedSha256 == image.rawSha256 ||
                (status.partial && status.pendingUpdate?.imageId == image.id && status.rawSize == image.rawBytes))
        }

        /**
         * Home's "Finish updating" needs no download: the same system, set up
         * by another app version or file set, and root verified its system.raw.
         */
        fun updateWithoutDownload(status: StageStatus, image: ImageRef, profile: PhoneProfile?, appVersionCode: Int?): Boolean =
            reusesInstalled(status, image, profile, appVersionCode) &&
                decide(status, image, profile, appVersionCode, hasDownload = false)?.kind == Kind.UPDATE
    }
}
