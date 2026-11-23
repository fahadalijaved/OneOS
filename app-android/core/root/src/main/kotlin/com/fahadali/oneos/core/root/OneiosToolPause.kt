package com.fahadali.oneos.core.root

/**
 * Who holds a running request of `oneios-tool serve`: the user (Pause on the screen) and Android's network (the
 * default network went away). The tool is told `pause` when the first of them holds it and `resume` when the last
 * lets go, so a network that comes back never resumes what the user paused, and the user's Resume while the
 * network is down leaves the request held. This is the only state the app keeps of a pause: whether to wait,
 * retry or keep the downloaded parts is the tool's (its README, "pause"). [send] writes the request line; it gets
 * `true` for pause, `false` for resume.
 */
class OneiosToolPause(private val send: (pause: Boolean) -> Unit) {
    @Volatile var byUser = false
        private set

    @Volatile var byNetwork = false
        private set

    val held: Boolean get() = byUser || byNetwork

    @Synchronized fun userPause() = change { byUser = true }

    @Synchronized fun userResume() = change { byUser = false }

    @Synchronized fun networkLost() = change { byNetwork = true }

    @Synchronized fun networkBack() = change { byNetwork = false }

    private fun change(what: () -> Unit) {
        val was = held
        what()
        if (held != was) send(held)
    }
}
