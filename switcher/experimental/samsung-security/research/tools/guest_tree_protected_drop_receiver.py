"""Connect the fixed drop script and binary transfer on one raw shell-v2 socket."""

import secrets
import socket
import struct
import time

from check_file_stage_device_preflight import ENDPOINT, require, timeout
from guest_tree_carrier_receiver import (
    expect_frame, observe_target, online_transport, shell_service, validate_parent,
)
from guest_tree_protected_drop_script import drop_command
from guest_tree_protected_drop_transfer import ProtectedDropTransfer
from run_guest_tree_install_transport import carrier_installer_pin


class ProtectedDropReceiver:
    """Single-owner connection. The caller retains it on uncertain progress."""

    def __init__(self, sock, parent, nonce, *, carrier_protocol="v1"):
        self._socket = sock
        self._parent = parent
        self._nonce = nonce
        self._transfer = ProtectedDropTransfer(sock, carrier_protocol=carrier_protocol)
        self._carrier_protocol = carrier_protocol
        self._published_identity = None
        self.state = 'waiting_for_grant'

    def grant(self, *, approved_v2_installer=None):
        """Send the one grant after the caller has authorization to write."""
        require(self.state == 'waiting_for_grant', 'Protected-drop grant is unavailable')
        if self._carrier_protocol == 'v2':
            expected = carrier_installer_pin('v2').artifact_sha256
            require(type(approved_v2_installer) is str and approved_v2_installer == expected
                    and self._transfer.snapshot()['installerSha256'] == expected,
                    'V2 grant requires the approved exact installer')
        else:
            require(approved_v2_installer is None, 'V2 approval cannot authorize a V1 grant')
        self.state = 'grant_attempted'
        deadline = time.monotonic() + 12
        line = f'ONEOS_PROTECTED_DROP_GRANT_V1 {self._nonce}\n'.encode('ascii')
        timeout(self._socket, deadline)
        self._socket.sendall(struct.pack('<BI', 0, len(line)) + line)
        expect_frame(self._socket, f'ONEOS_PROTECTED_DROP_READY_V1 {self._nonce}\n'.encode('ascii'), deadline)
        self.state = 'ready_for_transfer'

    def transfer(self, seconds):
        require(self.state == 'ready_for_transfer', 'Protected drop has not entered transfer')
        self.state = 'retained_transfer'
        result = self._transfer.run(seconds)
        identity = result['dropIdentity']
        if result['status'] == 'COMPLETE_PROTECTED_DROP_TRANSPORT_ONLY':
            expected_device = self._parent.local_stat.split('|')[-2]
            require(identity.split(':', 1)[0] == expected_device, 'Published drop is on a different filesystem')
            self._published_identity = identity
            self.state = 'terminal_transport'
        return result

    def close_after_transport(self):
        require(self.state == 'terminal_transport', 'Protected-drop terminal closure is unconfirmed')
        self.state = 'closing_terminal_transport'
        self._socket.close()
        self.state = 'closed_terminal_transport'

    def close_before_grant(self):
        require(self.state == 'waiting_for_grant', 'Protected-drop effects may have started')
        self.state = 'closed_before_grant'
        self._socket.close()

    def carrier_target(self):
        """Reobserve the exact published generation before handing it to the carrier."""
        require(self.state == 'closed_terminal_transport', 'Protected drop has no closed publication')
        target = observe_target(self._parent, self._published_identity, carrier_protocol=self._carrier_protocol)
        self.state = 'carrier_target_issued'
        return target


def open_protected_drop(parent, *, carrier_protocol="v1"):
    """Open a waiting shell and verify local artifacts without sending a grant."""
    validate_parent(parent)
    nonce = secrets.token_hex(16)
    command = drop_command(parent.boot_digest, parent.namespace, parent.actor_context,
                           parent.data_stat, parent.local_stat, nonce, carrier_protocol=carrier_protocol)
    require(online_transport() == parent.transport, 'Current ADB transport differs from the observed target')
    deadline = time.monotonic() + 12
    sock = socket.create_connection(ENDPOINT, timeout=5)
    try:
        shell_service(sock, parent.transport, command, deadline)
        expect_frame(sock, f'ONEOS_PROTECTED_DROP_HELLO_V1 {nonce}\n'.encode('ascii'), deadline)
        return ProtectedDropReceiver(sock, parent, nonce, carrier_protocol=carrier_protocol)
    except BaseException:
        sock.close()
        raise
