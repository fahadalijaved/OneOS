package com.fahadali.oneos.ui

import android.content.Context
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.PlainMessage
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.session.StageCheck

/** OneOS's existing update/repair findings, shared by the picker and pre-boot page. */
internal object ImageMaintenance {
    private val actions = setOf(FixAction.UPDATE, FixAction.REPAIR, FixAction.SET_UP_AGAIN)

    fun identifiedImage(result: StageCheck.Result): ImageRef? {
        val stage = result.status
        stage.marker?.takeIf { stage.ours }?.imageId?.let(Images::byId)?.let { return it }
        if (!stage.partial) return null
        stage.pendingUpdate?.takeIf { it.profileId == Profiles.resolve(result.facts).profile?.id }
            ?.imageId?.let(Images::byId)?.let { return it }
        val verified = stage.rawVerifiedSha256
        return Profiles.resolve(result.facts).profile?.images()?.firstOrNull { verified != null && it.rawSha256 == verified }
    }

    fun message(ctx: Context, image: ImageRef, result: StageCheck.Result?, report: GateReport? = null): PlainMessage? {
        if (result == null || identifiedImage(result)?.id != image.id) return null
        if (result.status.pendingUpdate != null && result.status.partial) return PlainMessage(
            ctx.getString(R.string.update_interrupted_title, image.name),
            ctx.getString(R.string.update_interrupted_summary),
            FixAction.UPDATE, ctx.getString(R.string.retry_update), Level.BLOCK,
        )
        if (result.status.partial) return PlainMessage(
            ctx.getString(R.string.environment_restage_title, image.name),
            ctx.getString(R.string.environment_restage_summary),
            if (com.fahadali.oneos.core.root.SetupPlan.reusesInstalled(result.status, image,
                    Profiles.resolve(result.facts).profile, com.fahadali.oneos.BuildConfig.VERSION_CODE)) FixAction.REPAIR
            else FixAction.SET_UP_AGAIN,
            ctx.getString(R.string.catalog_update), Level.BLOCK,
        )
        val checked = report ?: StageCheck.gates(ctx, result, GatePhase.SWITCH)
        return checked.find(SwitchGates.ID_IMAGE)?.finding?.let { Plain.of(it, checked, result.facts) }
            ?.takeIf { it.action in actions }
    }
}
