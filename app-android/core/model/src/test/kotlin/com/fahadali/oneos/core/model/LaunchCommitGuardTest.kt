package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test

class LaunchCommitGuardTest {
    @Test fun cancellationPreventsRootHandoff() {
        val guard = LaunchCommitGuard()
        assertTrue(guard.cancel())
        assertFalse(guard.commit())
        assertTrue(guard.isCancelled())
    }
    @Test fun committedLaunchCannotReportCancelled() {
        val guard = LaunchCommitGuard()
        assertTrue(guard.commit())
        assertFalse(guard.cancel())
        assertFalse(guard.isCancelled())
    }
    @Test fun racingCancelAndCommitHaveExactlyOneWinner() {
        repeat(100) {
            val guard = LaunchCommitGuard()
            val start = java.util.concurrent.CountDownLatch(1)
            var cancelled = false
            var committed = false
            val a = Thread { start.await(); cancelled = guard.cancel() }
            val b = Thread { start.await(); committed = guard.commit() }
            a.start(); b.start(); start.countDown(); a.join(); b.join()
            assertTrue(cancelled xor committed)
            assertEquals(cancelled, guard.isCancelled())
        }
    }
}
