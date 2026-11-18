package com.fahadali.oneos.session

import com.fahadali.oneos.core.model.LaunchCommitGuard
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

private fun record(guard: LaunchCommitGuard) = ViewPreparationOccurrence.recordAtCommitCut(guard)

private fun race(first: () -> Unit, second: () -> Unit) {
    val ready = CountDownLatch(2)
    val release = CountDownLatch(1)
    val problem = AtomicReference<Throwable>()
    val workers = listOf(first, second).map { action ->
        Thread {
            try {
                ready.countDown()
                check(release.await(5, TimeUnit.SECONDS))
                action()
            } catch (failure: Throwable) {
                problem.compareAndSet(null, failure)
            }
        }.apply { isDaemon = true }
    }
    workers.forEach(Thread::start)
    try {
        check(ready.await(5, TimeUnit.SECONDS))
    } finally {
        release.countDown()
    }
    workers.forEach { it.join(5000) }
    check(workers.none(Thread::isAlive))
    problem.get()?.let { throw it }
}

fun main() {
    val open = LaunchCommitGuard()
    val occurrence = checkNotNull(record(open))
    // Model a listener immediately reentering on the same confirmation.
    val listener = {
        check(record(open) == null)
        check(!open.cancel())
    }
    listener()
    check(!open.commit())
    println("PASS one occurrence blocks reentry, cancellation and stock commit after claim")

    val cancelled = LaunchCommitGuard()
    check(cancelled.cancel())
    check(cancelled.isCancelled())
    check(record(cancelled) == null)
    check(record(cancelled) == null)
    println("PASS cancellation before the cut stays terminal")

    val stock = LaunchCommitGuard()
    check(stock.commit())
    check(record(stock) == null)
    println("PASS a stock commit cannot be claimed as a view occurrence")

    val competing = LaunchCommitGuard()
    val claims = AtomicInteger()
    val claim: () -> Unit = { if (record(competing) != null) claims.incrementAndGet() }
    race(claim, claim)
    check(claims.get() == 1)
    println("PASS two workers cannot earn two occurrences")

    repeat(16) {
        val guard = LaunchCommitGuard()
        val decisions = AtomicInteger()
        race(
            { if (guard.cancel()) decisions.incrementAndGet() },
            { if (record(guard) != null) decisions.incrementAndGet() },
        )
        check(decisions.get() == 1)
        check(record(guard) == null)
    }
    println("PASS cancellation and claim are mutually exclusive")

    check(checkNotNull(record(LaunchCommitGuard())) !== occurrence)
    println("PASS distinct confirmation guards do not share an occurrence")
}
