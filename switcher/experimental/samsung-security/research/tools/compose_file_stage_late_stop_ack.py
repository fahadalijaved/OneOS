"""Retain the exact tester attempt's verified Stop queue acknowledgment."""

from run_guest_tree_install_transport import load_io, pinned


BASE = 'out/file-stage-readiness-build/r-98658bf067/app/src/'
PINS = {
    'PrepareActivity.java': 'd9e4c23210dc28fc621c89cbbe3d49030e274a902c6ae82118b276ac823cefeb',
    'RetainedRootHostServiceV2.java': '7f7af6595b3fc718696428ab81d05518936974945010f4e5138ebe07157c6b09',
}

EDITS = {
    'RetainedRootHostServiceV2.java': (
        (b'        public int status() { return owner.callView(RetainedViewAppProtocol.APP_VIEW_STATUS); }\n',
         b'        public int status() { return owner.callView(RetainedViewAppProtocol.APP_VIEW_STATUS); }\n'
         b'\n'
         b'        /** Historical queue receipt for this exact attempt, with no Binder call. */\n'
         b'        public boolean stopAcknowledged() { return owner.stopAcknowledged(this); }\n'),
        (b'        private ViewCall viewStop;\n',
         b'        private ViewCall viewStop;\n'
         b'        private boolean viewStopAcknowledged;\n'),
        (b'        int callView(int code) {\n',
         b'        boolean stopAcknowledged(ViewAttempt attempt) {\n'
         b'            synchronized (lock) {\n'
         b'                return viewAttempt == attempt && viewStopAcknowledged;\n'
         b'            }\n'
         b'        }\n'
         b'\n'
         b'        int callView(int code) {\n'),
        (b'                        if (call == viewStop) viewStop = null;\n'
         b'                        else viewCall = null;\n',
         b'                        if (call == viewStop) {\n'
         b'                            viewStopAcknowledged = result == RetainedViewAppProtocol.QUEUED\n'
         b'                                    && viewCurrentLocked();\n'
         b'                            viewStop = null;\n'
         b'                        } else viewCall = null;\n'),
    ),
    'PrepareActivity.java': (
        (b'                        workerTerminal = workerTerminal || terminalStatus(sample);\n'
         b'                        main.post(new Runnable() {\n'
         b'                            @Override public void run() { refreshing = false; observe(sample); }\n',
         b'                        workerTerminal = workerTerminal || terminalStatus(sample);\n'
         b'                        final boolean acknowledged = attempt.stopAcknowledged();\n'
         b'                        main.post(new Runnable() {\n'
         b'                            @Override public void run() {\n'
         b'                                if (stopRequested && acknowledged) stopReply = RetainedViewAppProtocol.QUEUED;\n'
         b'                                refreshing = false;\n'
         b'                                observe(sample);\n'
         b'                            }\n'),
    ),
}


def derive():
    io = load_io()
    result = {}
    for name, digest in PINS.items():
        original = pinned(io, BASE + name, digest, 32 * 1024)
        successor = original
        for before, after in EDITS[name]:
            if successor.count(before) != 1 or after in successor:
                raise ValueError(f'Late Stop acknowledgment source anchor differs: {name}')
            successor = successor.replace(before, after, 1)
        inverse = successor
        for before, after in reversed(EDITS[name]):
            if inverse.count(after) != 1:
                raise ValueError(f'Late Stop acknowledgment source inverse differs: {name}')
            inverse = inverse.replace(after, before, 1)
        if inverse != original:
            raise ValueError(f'Late Stop acknowledgment source inverse failed: {name}')
        result[name] = successor
    return result
