package com.fahadali.oneos.core.model

/** Cancellation is accepted only before the irreversible root-launch handoff. */
class LaunchCommitGuard {
    private enum class State { OPEN, CANCELLED, COMMITTED }
    private var state = State.OPEN
    @Synchronized fun cancel(): Boolean {
        if (state != State.OPEN) return false
        state = State.CANCELLED
        return true
    }
    @Synchronized fun commit(): Boolean {
        if (state != State.OPEN) return false
        state = State.COMMITTED
        return true
    }
    @Synchronized fun isCancelled(): Boolean = state == State.CANCELLED
}
