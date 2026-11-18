package com.fahadali.oneos.session

/** Main-owner UI projection for a single already-recorded preparation occurrence. */
internal class ViewPreparationStatus(private val occurrence: ViewPreparationOccurrence) {
    enum class Preparation { PENDING, PARTIAL, NEED_STAGE, REFUSED, UNAVAILABLE }
    enum class Cleanup { NONE, PENDING, LOCAL_TERMINAL, CONFIRMED, UNCONFIRMED }
    enum class CloseObservation { HOLD, LOCAL_TERMINAL, CLEANUP_CONFIRMED, STOP_CONFIRMED, UNCONFIRMED }
    enum class Message {
        PREPARING, PARTIAL_OBSERVED, NEED_STAGE, REFUSED, RESULT_UNAVAILABLE,
        STOPPING, CLEANING_UP, LOCALLY_CLOSED, CLEANUP_UNCONFIRMED, CANCELLED,
    }

    class StopPrompt internal constructor()

    data class Snapshot(
        val preparation: Preparation,
        val cleanup: Cleanup,
        val message: Message,
        val stopEnabled: Boolean,
        val confirmationOpen: Boolean,
    )

    private var preparation = Preparation.PENDING
    private var cleanup = Cleanup.NONE
    private var prompt: StopPrompt? = null
    private var stopRequested = false
    private var stopConfirmed = false

    val snapshot: Snapshot
        get() = Snapshot(preparation, cleanup, message(), canStop() && prompt == null, prompt != null)

    fun showStopConfirmation(): StopPrompt? {
        if (!canStop()) return null
        return prompt ?: StopPrompt().also { prompt = it }
    }

    /** Negative button, Back or outside dismissal for this exact dialog. */
    fun keepGoing(actual: StopPrompt): Boolean {
        if (actual !== prompt) return false
        prompt = null
        return true
    }

    /** Returns the same occurrence once for the caller to request close. */
    fun confirmStop(actual: StopPrompt): ViewPreparationOccurrence? {
        if (actual !== prompt || !canStop()) return null
        prompt = null
        stopRequested = true
        cleanup = Cleanup.PENDING
        return occurrence
    }

    /** Accepts only the first preparation disposition of the retained occurrence. */
    fun observePreparation(actual: ViewPreparationOccurrence, observed: Preparation): Boolean {
        if (actual !== occurrence || preparation != Preparation.PENDING || cleanupSettled()
            || observed == Preparation.PENDING
        ) return false

        preparation = observed
        when (observed) {
            Preparation.NEED_STAGE, Preparation.REFUSED -> {
                prompt = null
                if (cleanup == Cleanup.NONE) cleanup = Cleanup.PENDING
            }
            Preparation.UNAVAILABLE -> {
                prompt = null
                cleanup = Cleanup.UNCONFIRMED
            }
            else -> Unit
        }
        return true
    }

    /** A close request and a local terminal frame are separate from cleanup confirmation. */
    fun observeClose(actual: ViewPreparationOccurrence, observed: CloseObservation): Boolean {
        if (actual !== occurrence || cleanupSettled()) return false
        val next = when (observed) {
            CloseObservation.HOLD -> {
                if (cleanup != Cleanup.NONE) return false
                Cleanup.PENDING
            }
            CloseObservation.LOCAL_TERMINAL -> Cleanup.LOCAL_TERMINAL
            CloseObservation.CLEANUP_CONFIRMED -> Cleanup.CONFIRMED
            CloseObservation.STOP_CONFIRMED -> {
                if (!stopRequested || preparation == Preparation.NEED_STAGE
                    || preparation == Preparation.REFUSED
                ) return false
                stopConfirmed = true
                Cleanup.CONFIRMED
            }
            CloseObservation.UNCONFIRMED -> Cleanup.UNCONFIRMED
        }
        if (cleanup == next) return false
        cleanup = next
        prompt = null
        return true
    }

    private fun canStop() = cleanup == Cleanup.NONE &&
        (preparation == Preparation.PENDING || preparation == Preparation.PARTIAL)

    private fun cleanupSettled() = cleanup == Cleanup.CONFIRMED || cleanup == Cleanup.UNCONFIRMED

    private fun message(): Message = when {
        preparation == Preparation.NEED_STAGE -> Message.NEED_STAGE
        preparation == Preparation.REFUSED -> Message.REFUSED
        preparation == Preparation.UNAVAILABLE -> Message.RESULT_UNAVAILABLE
        cleanup == Cleanup.UNCONFIRMED -> Message.CLEANUP_UNCONFIRMED
        stopConfirmed -> Message.CANCELLED
        cleanup == Cleanup.CONFIRMED -> Message.LOCALLY_CLOSED
        cleanup != Cleanup.NONE -> if (stopRequested) Message.STOPPING else Message.CLEANING_UP
        preparation == Preparation.PARTIAL -> Message.PARTIAL_OBSERVED
        else -> Message.PREPARING
    }
}
