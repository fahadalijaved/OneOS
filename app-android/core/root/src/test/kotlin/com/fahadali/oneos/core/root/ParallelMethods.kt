package com.fahadali.oneos.core.root

import org.junit.runners.BlockJUnit4ClassRunner
import org.junit.runners.model.RunnerScheduler
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Runs a class's test methods on a thread pool. Gradle forks per class only, and
 * StageScriptTest's 43 methods (every one runs the root script under each shell)
 * took 47 min one after another. Each method gets its own instance and FakeRoot
 * (its own temp folder), so they do not share state. Threads: ONEOS_TEST_THREADS,
 * else the CPUs Java sees.
 */
class ParallelMethods(klass: Class<*>) : BlockJUnit4ClassRunner(klass) {
    init {
        val n = System.getenv("ONEOS_TEST_THREADS")?.toIntOrNull()?.coerceAtLeast(1)
            ?: Runtime.getRuntime().availableProcessors()
        val pool = Executors.newFixedThreadPool(n)
        setScheduler(object : RunnerScheduler {
            override fun schedule(childStatement: Runnable) {
                pool.submit(childStatement)
            }

            override fun finished() {
                pool.shutdown()
                pool.awaitTermination(4, TimeUnit.HOURS)
            }
        })
    }
}
