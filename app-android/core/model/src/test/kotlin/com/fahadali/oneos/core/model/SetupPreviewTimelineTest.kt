package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test

class SetupPreviewTimelineTest {
    private val timeline = SetupPreviewTimeline(9, 1_000)
    @Test fun completesOnlyAfterEveryStep() {
        assertEquals(SetupPreviewTimeline.Phase.RUNNING, timeline.at(8_999).phase)
        assertEquals(SetupPreviewTimeline.Snapshot(SetupPreviewTimeline.Phase.DONE, 9, null, 100), timeline.at(9_000))
        assertEquals(timeline.at(9_000), timeline.at(100_000))
    }
    @Test fun cancellationFreezesProgressAndCannotBecomeCompletionLater() {
        val cancelled = timeline.at(2_500, cancelledAtMs = 2_500)
        assertEquals(SetupPreviewTimeline.Phase.CANCELLED, cancelled.phase)
        assertEquals(2, cancelled.completedSteps)
        assertEquals(cancelled, timeline.at(100_000, cancelledAtMs = 2_500))
    }
    @Test fun restoringElapsedTimeKeepsTheSameStepAndProgress() {
        val restored = SetupPreviewTimeline(9, 1_000).at(4_500)
        assertEquals(timeline.at(4_500), restored)
        assertEquals(4, restored.currentStep)
        assertEquals(50, restored.percent)
    }
    @Test fun negativeClockInputCannotCreateInvalidProgress() {
        assertEquals(0, timeline.at(-1).percent)
        assertEquals(0, timeline.at(-1).completedSteps)
    }
}
