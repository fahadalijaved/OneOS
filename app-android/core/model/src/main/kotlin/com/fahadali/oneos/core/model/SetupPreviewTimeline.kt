package com.fahadali.oneos.core.model

/** Pure UI timing. This model has no context, files, root services or job references. */
class SetupPreviewTimeline(val stepCount: Int, val stepDurationMs: Long = 1_100L) {
    init { require(stepCount > 0); require(stepDurationMs > 0) }
    enum class Phase { RUNNING, DONE, CANCELLED }
    data class Snapshot(val phase: Phase, val completedSteps: Int, val currentStep: Int?, val percent: Int)
    val durationMs: Long get() = stepCount * stepDurationMs
    fun at(elapsedMs: Long, cancelledAtMs: Long? = null): Snapshot {
        val elapsed = (cancelledAtMs ?: elapsedMs).coerceIn(0, durationMs)
        val complete = elapsed == durationMs
        val phase = when { complete -> Phase.DONE; cancelledAtMs != null -> Phase.CANCELLED; else -> Phase.RUNNING }
        val done = (elapsed / stepDurationMs).toInt()
        return Snapshot(phase, done, if (complete) null else done, (elapsed * 100 / durationMs).toInt())
    }
}
