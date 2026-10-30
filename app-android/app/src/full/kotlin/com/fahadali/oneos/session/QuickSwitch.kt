package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.root.OldStage

/**
 * Quick switch (0.4.30, owner: "if a user has staged an OS and then another.
 * When he comes back to OneUI he can quickly switch between either. Right
 * now it's a bigger task each time"). From Home, one tap on another system
 * set up earlier chains what Free up space's Use again and Home already do:
 *
 * 1. root `restore` puts that copy back ([OldStagesJob.restore]); the system
 *    set up now is kept as a copy with its apps and data, and the same checks
 *    as Use again run on both;
 * 2. the stage check reads the restored system;
 * 3. when its OneOS files are older than this app, Update runs (the system
 *    stays; only OneOS's files are written, about 2 minutes);
 * 4. the Switch confirm opens, as for any switch: the user still confirms the
 *    switch itself there, with every tick and check.
 *
 * Home drives the steps from its redraw ([com.fahadali.oneos.ui.StatusHomeFragment]),
 * acting only once the stage check has read the chosen system, so an older
 * result never starts anything. The target lives in memory: if the app stops
 * on the way, Home simply shows the system that is set up.
 */
object QuickSwitch {
    class Pending(val copy: String, val imageId: String) {
        /** Update was started for it: when the check still asks for one, stop rather than loop. */
        var updateStarted = false
    }

    @Volatile
    var pending: Pending? = null
        private set

    fun start(ctx: Context, copy: String, imageId: String) {
        if (pending != null || OldStagesJob.state.busy) return
        pending = Pending(copy, imageId)
        OldStagesJob.restore(ctx, OldStage(copy, 0, imageId, hasData = true, busy = false))
        // Another job held root (restore did not start): nothing to chain.
        if (OldStagesJob.state.phase != OldStagesJob.Phase.RESTORING) pending = null
    }

    fun cancel() {
        pending = null
    }
}
