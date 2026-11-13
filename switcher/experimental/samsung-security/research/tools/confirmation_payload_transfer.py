"""Stream the fixed confirmation artifacts on one bound shell-v2 connection."""

import re
import struct
import time

import check_file_stage_device_preflight as preflight
import guest_tree_carrier_receiver as carrier
from confirmation_tester_cohort import CONFIRMATION_PUBLISHER_BYTES, CONFIRMATION_TESTER_BYTES
from guest_tree_shell_v2_transfer import CLOSE_STDIN, MAX_PAYLOAD, STDIN


def call(target, command, *, payload=None, ready=None):
    """Return the terminal reply after EOF, with the expected READY consumed.

    The caller owns authorization, artifact hashes and terminal interpretation.
    A transport failure after opening may leave remote effects.
    """
    if payload is None:
        preflight.require(ready is None, 'A READY frame requires a confirmation payload')
    else:
        preflight.require(type(payload) is bytes and len(payload) in
                          (CONFIRMATION_PUBLISHER_BYTES, CONFIRMATION_TESTER_BYTES),
                          'Unexpected confirmation payload size or type')
        preflight.require(type(ready) is bytes and re.fullmatch(rb'[ -~]{1,255}\n', ready),
                          'Expected one bounded confirmation READY line')

    deadline = time.monotonic() + 90
    with carrier._open_bound_observation(target, command) as sock:
        if payload is not None:
            carrier.expect_frame(sock, ready, deadline)
            for offset in range(0, len(payload), MAX_PAYLOAD):
                chunk = payload[offset:offset + MAX_PAYLOAD]
                preflight.timeout(sock, deadline)
                sock.sendall(struct.pack('<BI', STDIN, len(chunk)) + chunk)
            preflight.timeout(sock, deadline)
            sock.sendall(struct.pack('<BI', CLOSE_STDIN, 0))
        return preflight.shell_reply(sock, deadline)
