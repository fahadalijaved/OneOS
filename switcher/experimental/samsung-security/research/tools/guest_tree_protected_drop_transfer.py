"""Send the two selected artifacts on an already authorized protected-drop shell."""

import hashlib
import json
import math
import re
import select
import socket
import struct
import threading
import time

from check_file_stage_device_preflight import DROP_ARTIFACTS, drop_artifacts, exact, timeout
from guest_tree_shell_v2_transfer import CLOSE_STDIN, DIAGNOSTIC_LIMIT, EXIT, MAX_PAYLOAD, STDERR, STDIN, STDOUT
from run_guest_tree_install_transport import (
    INSTALLER_RECEIPT, INSTALLER_RECEIPT_SHA, INSTALLER_SHA, carrier_installer_pin, installer_build_status, load_io,
)


INSTALLER = "out/guest-tree-carrier-installer/r-e5d9aea8/oneos_install_verified_carrier"
PUBLISHER = "out/file-stage-readiness-publisher/r-9501bd2615/oneos_publish_verified_host_profile"
PUBLISHER_RECEIPT = "out/file-stage-readiness-publisher/r-9501bd2615/receipt.json"
PUBLISHER_RECEIPT_SHA = "d44b6fc77090ccc163628b29660b54e2e40b70fc52fdaa101cf66390eeb1d7eb"
PUBLISHER_STATUS = "PASS_PC_MATCHED_READINESS_PUBLISHER_STATIC_LINK_ONLY"
_, INSTALLER_BYTES, EXPECTED_INSTALLER_SHA = DROP_ARTIFACTS['deploy_installer']
_, PUBLISHER_BYTES, PUBLISHER_SHA = DROP_ARTIFACTS['deploy_publisher']
PAYLOAD_BYTES = INSTALLER_BYTES + PUBLISHER_BYTES
ACK_PREFIX = b"ONEOS_PROTECTED_DROP_V1 PUBLISHED_CLOSED "
ACK_LIMIT = len(ACK_PREFIX) + 42
ACK = re.compile(re.escape(ACK_PREFIX) + rb"([1-9][0-9]{0,19}):([1-9][0-9]{0,19})\n")
HEADER = struct.Struct("<BI")


def publisher_pin(carrier_protocol='v1'):
    carrier_installer_pin(carrier_protocol)
    if carrier_protocol == 'v2':
        run = 'out/file-stage-static-exec-repair/app/r-f6d89caa/'
        return (run + 'oneos_publish_verified_host_profile', run + 'receipt.json',
                'd0ba19cb763fba7e500493c62452c5550e78a32bdd8db2dc979565f093767e08',
                'PASS_PC_MATCHED_READINESS_STATIC_EXEC_PUBLISHER_ONLY')
    return PUBLISHER, PUBLISHER_RECEIPT, PUBLISHER_RECEIPT_SHA, PUBLISHER_STATUS


class _Refused(Exception):
    pass


def _capture(io, path, size, digest, receipt_path, receipt_digest, status, *, receipt_limit=64 * 1024):
    with io["checked_input"](io["ROOT"] / receipt_path, max_size=receipt_limit) as stream:
        raw = stream.read(receipt_limit + 1)
    if hashlib.sha256(raw).hexdigest() != receipt_digest:
        raise ValueError("Selected protected-drop build receipt differs")
    receipt = json.loads(raw.decode("ascii"), object_pairs_hook=io["unique_object"])
    if (receipt["status"] != status or receipt["deviceEligible"] is not False
            or receipt["artifact"] != {"path": path, "bytes": size, "sha256": digest}):
        raise ValueError("Protected-drop build receipt describes a different artifact")
    with io["checked_input"](io["ROOT"] / path, size=size) as stream:
        data = stream.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Selected protected-drop artifact bytes differ")
    return data


class ProtectedDropTransfer:
    """Retain one socket and exact artifact snapshots before the caller sends GRANT.

    The caller owns target selection, authorization and the HELLO/GRANT/READY
    exchange. After READY, run once on this same exclusive socket. Retain this
    object when progress is uncertain. Terminal credit covers this transfer.
    """

    def __init__(self, sock, *, carrier_protocol="v1"):
        if not isinstance(sock, socket.socket):
            raise ValueError("An already-connected raw shell-v2 socket is required")
        sock.getpeername()
        artifacts = drop_artifacts(carrier_protocol)
        installer = carrier_installer_pin(carrier_protocol)
        _, installer_bytes, installer_sha = artifacts['deploy_installer']
        _, publisher_bytes, publisher_sha = artifacts['deploy_publisher']
        if (installer.artifact_bytes, installer.artifact_sha256) != (installer_bytes, installer_sha):
            raise ValueError("Selected artifacts differ between transport and protected drop")
        publisher, receipt, receipt_sha, status = publisher_pin(carrier_protocol)
        io = load_io()
        self._parts = (
            _capture(io, installer.artifact_path, installer_bytes, installer_sha,
                     installer.receipt_path, installer.receipt_sha256, installer_build_status(carrier_protocol)),
            _capture(io, publisher, publisher_bytes, publisher_sha, receipt, receipt_sha, status,
                     receipt_limit=(80 if carrier_protocol == 'v2' else 64) * 1024),
        )
        self._installer_sha = installer_sha
        self._publisher_sha = publisher_sha
        self._payload_bytes = installer_bytes + publisher_bytes
        self.socket = sock
        self._claim = threading.Lock()
        self._started = False
        self._sent = 0
        self._wire_kind = None
        self._wire_offset = 0
        self._closed_input = False
        self._stdout = bytearray()
        self._stderr_bytes = 0
        self._exit = None
        self._eof = False
        self._identity = None
        self._failure = None

    def _send(self, kind, data, deadline):
        wire = memoryview(HEADER.pack(kind, len(data)) + data)
        self._wire_kind = kind
        self._wire_offset = 0
        while self._wire_offset < len(wire):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            readable, writable, _ = select.select([self.socket], [self.socket], [], remaining)
            if readable:
                raise _Refused("PEER_READY_BEFORE_CLOSE_STDIN")
            if not writable or time.monotonic() >= deadline:
                raise TimeoutError
            try:
                sent = self.socket.send(wire[self._wire_offset:])
            except BlockingIOError:
                continue
            if not 0 < sent <= len(wire) - self._wire_offset:
                raise _Refused("SHELL_WRITE_NO_PROGRESS")
            prior = self._wire_offset
            self._wire_offset += sent
            if kind == STDIN:
                self._sent += max(0, self._wire_offset - HEADER.size) - max(0, prior - HEADER.size)
        self._wire_kind = None
        self._wire_offset = 0

    def _read_terminal(self, deadline):
        try:
            while self._exit is None:
                kind, size = HEADER.unpack(exact(self.socket, HEADER.size, deadline))
                if kind == STDOUT and 0 < size <= ACK_LIMIT - len(self._stdout):
                    self._stdout.extend(exact(self.socket, size, deadline))
                elif kind == STDERR and 0 < size <= DIAGNOSTIC_LIMIT - self._stderr_bytes:
                    self._stderr_bytes += len(exact(self.socket, size, deadline))
                elif kind == EXIT and size == 1:
                    self._exit = exact(self.socket, 1, deadline)[0]
                else:
                    raise _Refused("SHELL_FRAME_PROFILE_REFUSED")
        except EOFError:
            self._eof = True
            raise _Refused("SHELL_EOF_BEFORE_COMPLETE_EXIT") from None
        timeout(self.socket, deadline)
        if self.socket.recv(1):
            raise _Refused("SHELL_BYTES_AFTER_EXIT")
        self._eof = True
        match = ACK.fullmatch(self._stdout)
        if (self._exit != 0 or self._stderr_bytes or match is None
                or any(int(part) >= 2**64 for part in match.groups())):
            raise _Refused("REMOTE_TERMINAL_RESULT_REFUSED")
        self._identity = b":".join(match.groups()).decode("ascii")

    def snapshot(self):
        identity = self._identity
        return {
            "status": ("TRANSFER_UNCONFIRMED" if self._failure else
                       "COMPLETE_PROTECTED_DROP_TRANSPORT_ONLY" if identity else
                       "IN_PROGRESS" if self._started else "UNSTARTED"),
            "failure": self._failure,
            "installerSha256": self._installer_sha,
            "publisherSha256": self._publisher_sha,
            "expectedPayloadBytes": self._payload_bytes,
            "stdinPayloadBytesSent": self._sent,
            "pendingWireKind": self._wire_kind,
            "pendingWireBytesSent": self._wire_offset,
            "closeStdinSent": self._closed_input,
            "remoteExit": self._exit,
            "remoteEof": self._eof,
            "remoteStderrBytes": self._stderr_bytes,
            "dropIdentity": identity,
            "publisherOrCleanupCredit": False,
        }

    def run(self, seconds):
        if type(seconds) not in (int, float) or not 0 < seconds <= 600 or not math.isfinite(seconds):
            raise ValueError("Invalid protected-drop transfer budget")
        with self._claim:
            if self._started:
                raise ValueError("Protected-drop transfer is one-shot")
            self._started = True
        deadline = time.monotonic() + seconds
        try:
            self.socket.setblocking(False)
            for artifact in self._parts:
                for start in range(0, len(artifact), MAX_PAYLOAD):
                    self._send(STDIN, artifact[start:start + MAX_PAYLOAD], deadline)
            self._send(CLOSE_STDIN, b"", deadline)
            self._closed_input = True
            self._read_terminal(deadline)
        except _Refused as error:
            self._failure = str(error)
        except TimeoutError:
            self._failure = "TRANSFER_DEADLINE"
        except BaseException as error:
            self._failure = "TRANSFER_IO_OR_INTERRUPTION:" + type(error).__name__
        return self.snapshot()
