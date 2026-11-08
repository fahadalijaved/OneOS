package com.fahadali.oneos.core.root;

import java.io.IOException;

/** The actual birth boundary; no caller-supplied process or shell program. */
final class RetainedRootSessionSpawn {
    private RetainedRootSessionSpawn() { }

    static Process start(String sha256, long bytes) throws IOException {
        return new ProcessBuilder("su", "-c", RetainedRootCommand.build(sha256, bytes)).start();
    }
}
