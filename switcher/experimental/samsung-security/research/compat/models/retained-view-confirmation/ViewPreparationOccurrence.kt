package com.fahadali.oneos.session

import com.fahadali.oneos.core.model.LaunchCommitGuard

/** Inert local occurrence for the fixture's explicit view-only confirmation. */
internal class ViewPreparationOccurrence private constructor() {
    companion object {
        /**
         * At the proposed LaunchJob cut, call this after the actual fresh checks
         * in place of the stock commit, then return from the view-only branch.
         */
        internal fun recordAtCommitCut(guard: LaunchCommitGuard): ViewPreparationOccurrence? {
            val occurrence = ViewPreparationOccurrence()
            return if (guard.commit()) occurrence else null
        }
    }
}
