package com.fahadali.oneos.core.root;

import java.io.IOException;

/** Actual source-owned birth boundary, separately replaceable only in authored models. */
final class RetainedRootOfferSpawn {
    private RetainedRootOfferSpawn() { }
    static Process start(String sha256, long bytes) throws IOException {
        return new ProcessBuilder("su", "-c", RetainedRootOfferCommand.build(sha256, bytes)).start();
    }
}
