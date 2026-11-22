package com.fahadali.oneos.ui

import android.content.Context
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.R
import com.fahadali.oneos.session.GuestFeatures

internal fun showGuestFeatureFlags(ctx: Context, imageId: String, flags: List<GuestFeatures.Flag>) {
    AlertDialog.Builder(ctx)
        .setTitle(R.string.system_features)
        .setMultiChoiceItems(
            flags.map { ctx.getString(it.label) }.toTypedArray(),
            flags.map { GuestFeatures.enabled(ctx, imageId, it) }.toBooleanArray(),
        ) { _, index, checked ->
            GuestFeatures.setEnabled(ctx, imageId, flags[index], checked)
        }
        .setPositiveButton(android.R.string.ok, null)
        .show()
}
