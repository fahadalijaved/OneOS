#!/usr/bin/env python3
"""Own one already-connected raw shell-v2 stream and its retained PC producer."""

import hashlib
import io
import math
import queue
import re
import select
import socket
import struct
import subprocess
import threading
import time


_HEADER = struct.Struct("<BI")
MAX_FRAME = 64 * 1024
MAX_PAYLOAD = MAX_FRAME - _HEADER.size
MAX_RECEIPT = 64 * 1024
DIAGNOSTIC_LIMIT = 32 * 1024
ACK = b"ONEOS_CARRIER_V1 PUBLISHED_CLOSED\n"
WITNESS_PREFIX = b"ONEOS_CARRIER_V2 PUBLISHED_CLOSED "
READBACK_PREFIX = b"ONEOS_CARRIER_READBACK_V1 VERIFIED_CLOSED "
WITNESS_LIMIT = 223
_UNSIGNED = rb"(0|[1-9][0-9]{0,19})"
_SIGNED = rb"(0|-?[1-9][0-9]{0,18})"
_IDENTITY_FIELDS = b" ".join([_UNSIGNED] * 5 + [_SIGNED, _UNSIGNED, _SIGNED, _UNSIGNED]) + b"\n"
_WITNESS = re.compile(WITNESS_PREFIX + _IDENTITY_FIELDS)
_READBACK = re.compile(READBACK_PREFIX + _IDENTITY_FIELDS)
STDIN, STDOUT, STDERR, EXIT, CLOSE_STDIN = range(5)
_EOF = object()


class _Refused(Exception):
    pass


def _parse_identity(frame, raw, expected_bytes):
    match = frame.fullmatch(raw) if type(raw) is bytes and len(raw) <= WITNESS_LIMIT else None
    if match is None:
        raise ValueError("Invalid carrier file identity frame")
    mount, major, minor, inode, size, msec, mnsec, csec, cnsec = map(int, match.groups())
    if (not 0 < mount < 2**64 or not 0 < inode < 2**64
            or not 0 <= major < 2**32 or not 0 <= minor < 2**32
            or type(expected_bytes) is not int or size != expected_bytes or not 0 < size < 2**63
            or not -(2**63) <= msec < 2**63 or not -(2**63) <= csec < 2**63
            or mnsec >= 10**9 or cnsec >= 10**9):
        raise ValueError("Carrier file identity fields differ from the profile")
    return dict(mountId=mount, deviceMajor=major, deviceMinor=minor, inode=inode, bytes=size,
                mtimeSec=msec, mtimeNs=mnsec, ctimeSec=csec, ctimeNs=cnsec)


def parse_publication_witness(raw: bytes, expected_bytes: int) -> dict:
    """Decode the installer's historical publication identity."""
    return _parse_identity(_WITNESS, raw, expected_bytes)


def verify_carrier_readback(raw: bytes, publication: dict, expected_bytes: int) -> dict:
    """Join frames after the caller confirms provenance, boot, namespace, and terminal status."""
    current = _parse_identity(_READBACK, raw, expected_bytes)
    if (type(publication) is not dict or current != publication
            or any(type(value) is not int for value in publication.values())):
        raise ValueError("Carrier readback differs from the publication identity")
    return current


class ShellV2Transfer:
    """Run a fixed carrier attempt. The caller retains this object on every result.

    The connected socket is exclusive to this attempt, with no remaining hello
    bytes or competing reader. The reviewed adapter owns device and producer
    selection. The local callback reads the actual bounded, stable producer
    receipt and returns bytes. This class never launches a process, closes the
    socket, signals a child, retries a transfer, or grants publisher cleanup.
    """

    def __init__(self, sock, producer, expected_bytes, expected_source_receipt, read_source_receipt,
                 *, publication_witness=False):
        if not isinstance(sock, socket.socket) or not isinstance(producer, subprocess.Popen):
            raise ValueError("Actual connected socket and retained Popen are required")
        if not all(isinstance(pipe, (io.RawIOBase, io.BufferedIOBase))
                   for pipe in (producer.stdout, producer.stderr)):
            raise ValueError("Retained producer requires binary stdout and stderr pipes")
        if type(expected_bytes) is not int or not 0 < expected_bytes <= 64 * 1024**3:
            raise ValueError("Expected carrier length is outside the selected bound")
        if type(expected_source_receipt) is not bytes or not 0 < len(expected_source_receipt) <= MAX_RECEIPT:
            raise ValueError("Exact bounded source receipt bytes are required")
        if not callable(read_source_receipt):
            raise ValueError("Local receipt readback callback is required")
        if type(publication_witness) is not bool:
            raise ValueError("Invalid carrier terminal profile")
        self.socket = sock
        self.producer = producer
        self.expected_bytes = expected_bytes
        self.expected_source_receipt = expected_source_receipt
        self.read_source_receipt = read_source_receipt

        self._started = False
        self._claim = threading.Lock()
        self._stopped = threading.Event()
        self._out = queue.Queue(maxsize=3)
        self._err = queue.Queue(maxsize=1)
        self._receipt = queue.Queue(maxsize=1)
        self._threads = []
        self._received = 0
        self._producer_eof = False
        self._producer_exit = None
        self._producer_stderr = None
        self._receipt_started = False
        self._receipt_hash = None
        self._tail = None
        self._tail_sent = False
        self._close_sent = False
        self._pending = None
        self._offset = 0
        self._sent = 0
        self._incoming = bytearray()
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._remote_exit = None
        self._remote_eof = False
        self._failure = None
        self._completed = False
        self._publication_witness = publication_witness
        self._witness = None

    def _start_thread(self, work):
        worker = threading.Thread(target=work, daemon=True)
        self._threads.append(worker)
        worker.start()

    def _enqueue(self, value):
        while not self._stopped.is_set():
            try:
                self._out.put(value, timeout=0.05)
                return True
            except queue.Full:
                continue
        return False

    def _read_producer(self):
        stream = self.producer.stdout
        pending = bytearray()
        try:
            while not self._stopped.is_set():
                wanted = MAX_PAYLOAD - len(pending)
                data = stream.read(wanted)
                if type(data) is not bytes or len(data) > wanted:
                    raise OSError("Unexpected producer read result")
                if not data:
                    stream.close()
                    if pending and not self._enqueue(bytes(pending)):
                        return
                    self._enqueue(_EOF)
                    return
                pending.extend(data)
                if len(pending) == MAX_PAYLOAD:
                    if not self._enqueue(bytes(pending)):
                        return
                    pending.clear()
        except BaseException as error:
            self._enqueue(error)

    def _read_producer_diagnostics(self):
        stream = self.producer.stderr
        prefix = bytearray()
        total = 0
        error = None
        try:
            while True:
                data = stream.read(8192)
                if type(data) is not bytes:
                    raise OSError("Unexpected diagnostic read result")
                if not data:
                    break
                total += len(data)
                prefix.extend(data[:DIAGNOSTIC_LIMIT - len(prefix)])
        except BaseException as failure:
            error = type(failure).__name__
        finally:
            try:
                stream.close()
            except BaseException as failure:
                error = error or type(failure).__name__
        self._err.put((bytes(prefix), total, error))

    def _read_receipt(self):
        try:
            raw = self.read_source_receipt()
            if type(raw) is not bytes or not 0 < len(raw) <= MAX_RECEIPT:
                raise ValueError("Callback did not return actual bounded receipt bytes")
            self._receipt.put(raw)
        except BaseException as error:
            self._receipt.put(error)

    def _stage_frame(self, kind, data, tail=False):
        self._pending = (_HEADER.pack(kind, len(data)) + data, kind, tail)
        self._offset = 0

    def _send_ready(self):
        wire, kind, tail = self._pending
        try:
            sent = self.socket.send(memoryview(wire)[self._offset:])
        except BlockingIOError:
            return
        if not 0 < sent <= len(wire) - self._offset:
            raise _Refused("SHELL_WRITE_NO_PROGRESS")
        prior_payload = max(0, self._offset - _HEADER.size)
        self._offset += sent
        if kind == STDIN:
            self._sent += max(0, self._offset - _HEADER.size) - prior_payload
        if self._offset == len(wire):
            self._pending = None
            self._offset = 0
            if tail:
                self._tail_sent = True
            if kind == CLOSE_STDIN:
                self._close_sent = True

    def _advance_input(self):
        self._producer_exit = self.producer.poll()
        if self._producer_exit not in (None, 0):
            raise _Refused("PRODUCER_NONZERO_EXIT")
        if self._producer_stderr is None:
            try:
                self._producer_stderr = self._err.get_nowait()
            except queue.Empty:
                pass
        if self._producer_stderr is not None:
            _, total, error = self._producer_stderr
            if total or error:
                raise _Refused("PRODUCER_DIAGNOSTIC_OR_CLOSE_FAILURE")
        if self._pending is not None or self._close_sent:
            return
        if self._tail_sent:
            self._stage_frame(CLOSE_STDIN, b"")
            return
        if not self._producer_eof:
            try:
                event = self._out.get_nowait()
            except queue.Empty:
                return
            if isinstance(event, BaseException):
                raise _Refused("PRODUCER_PIPE_READ_OR_CLOSE_FAILURE")
            if event is _EOF:
                self._producer_eof = True
                if self._received != self.expected_bytes or self._tail is None:
                    raise _Refused("PRODUCER_SHORT_INPUT")
            else:
                self._received += len(event)
                if self._received > self.expected_bytes:
                    raise _Refused("PRODUCER_EXTRA_INPUT")
                if self._received == self.expected_bytes:
                    self._tail = event
                else:
                    self._stage_frame(STDIN, event)
                return

        if self._producer_exit != 0 or self._producer_stderr is None:
            return
        if not self._receipt_started:
            self._receipt_started = True
            self._start_thread(self._read_receipt)
            return
        try:
            raw = self._receipt.get_nowait()
        except queue.Empty:
            return
        if isinstance(raw, BaseException) or raw != self.expected_source_receipt:
            raise _Refused("SOURCE_RECEIPT_REFUSED")
        self._receipt_hash = hashlib.sha256(raw).hexdigest()
        self._stage_frame(STDIN, self._tail, tail=True)

    def _parse_incoming(self):
        while len(self._incoming) >= _HEADER.size:
            if self._remote_exit is not None:
                raise _Refused("SHELL_BYTES_AFTER_EXIT")
            kind, length = _HEADER.unpack_from(self._incoming)
            if (kind not in (STDOUT, STDERR, EXIT) or not 0 < length <= MAX_PAYLOAD
                    or (kind == EXIT and length != 1)):
                raise _Refused("SHELL_FRAME_PROFILE_REFUSED")
            finish = _HEADER.size + length
            if len(self._incoming) < finish:
                return
            data = self._incoming[_HEADER.size:finish]
            del self._incoming[:finish]
            if kind == EXIT:
                self._remote_exit = data[0]
                if not self._close_sent:
                    raise _Refused("REMOTE_EXIT_BEFORE_CLOSE_STDIN")
            elif kind == STDOUT:
                limit = WITNESS_LIMIT if self._publication_witness else len(ACK)
                if len(self._stdout) + length > limit:
                    raise _Refused("REMOTE_STDOUT_LIMIT")
                self._stdout.extend(data)
                prefix = WITNESS_PREFIX if self._publication_witness else ACK
                prefix_ok = prefix.startswith(self._stdout) or (
                    self._publication_witness and self._stdout.startswith(prefix))
                if not self._close_sent or not prefix_ok:
                    raise _Refused("REMOTE_ACK_PROFILE_REFUSED")
            elif len(self._stderr) + length > DIAGNOSTIC_LIMIT:
                raise _Refused("REMOTE_STDERR_LIMIT")
            else:
                self._stderr.extend(data)
        if self._remote_exit is not None and self._incoming:
            raise _Refused("SHELL_BYTES_AFTER_EXIT")

    def _receive_ready(self):
        try:
            raw = self.socket.recv(MAX_FRAME)
        except BlockingIOError:
            return
        if not raw:
            self._remote_eof = True
            if self._incoming:
                raise _Refused("SHELL_TRUNCATED_FRAME_AT_EOF")
            if self._remote_exit is None:
                raise _Refused("SHELL_EOF_WITHOUT_EXIT")
            return
        if self._remote_exit is not None:
            raise _Refused("SHELL_BYTES_AFTER_EXIT")
        self._incoming.extend(raw)
        self._parse_incoming()

    def snapshot(self):
        """Report bounded observations without new reads, sends, or waits."""
        pending = self._pending
        stderr = self._producer_stderr
        result = {
            "status": ("TRANSFER_UNCONFIRMED" if self._failure else
                       "COMPLETE_SHELL_V2_TRANSFER_ONLY" if self._completed else "IN_PROGRESS"),
            "failure": self._failure,
            "producerPid": self.producer.pid,
            "producerExit": self._producer_exit,
            "producerStdoutEof": self._producer_eof,
            "producerBytesObserved": self._received,
            "producerStderrBytes": stderr[1] if stderr else None,
            "producerStderrPrefixHex": stderr[0].hex() if stderr else None,
            "sourceReceiptSha256": self._receipt_hash,
            "expectedBytes": self.expected_bytes,
            "stdinPayloadBytesSent": self._sent,
            "pendingWireKind": pending[1] if pending else None,
            "pendingWireBytesSent": self._offset,
            "tailSent": self._tail_sent,
            "closeStdinSent": self._close_sent,
            "remoteStdoutHex": self._stdout.hex(),
            "remoteStderrHex": self._stderr.hex(),
            "remoteExit": self._remote_exit,
            "remoteEof": self._remote_eof,
            "unparsedRemoteBytes": len(self._incoming),
            "publisherOrCleanupCredit": False,
        }
        if self._completed and self._witness is not None:
            result["publicationWitness"] = self._witness.copy()
        return result

    def verify_readback(self, code, stdout, stderr, *, eof):
        """Compare the exact witness from this transfer to a separate bound shell reply."""
        if not self._completed or self._witness is None:
            raise ValueError("Carrier transfer has no completed publication witness")
        if type(code) is not int or code != 0 or type(stderr) is not bytes or stderr or eof is not True:
            raise ValueError("Carrier readback terminal is unconfirmed")
        return verify_carrier_readback(stdout, self._witness, self.expected_bytes)

    def run(self, seconds):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 24 * 3600:
            raise ValueError("Invalid absolute transfer budget")
        with self._claim:
            if self._started:
                raise ValueError("Transfer is one-shot")
            self._started = True
        deadline = time.monotonic() + seconds
        try:
            self.socket.getpeername()
            self.socket.setblocking(False)
            self._start_thread(self._read_producer)
            self._start_thread(self._read_producer_diagnostics)
            while not self._remote_eof:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _Refused("TRANSFER_DEADLINE")
                self._advance_input()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _Refused("TRANSFER_DEADLINE")
                readable, writable, _ = select.select(
                    [self.socket], [self.socket] if self._pending else [], [], min(remaining, 0.02)
                )
                if time.monotonic() >= deadline:
                    raise _Refused("TRANSFER_DEADLINE")
                if readable:
                    self._receive_ready()
                if writable and not self._remote_eof:
                    if time.monotonic() >= deadline:
                        raise _Refused("TRANSFER_DEADLINE")
                    self._send_ready()
            if (not self._close_sent or self._sent != self.expected_bytes or not self._tail_sent
                    or self._receipt_hash is None or self._remote_exit != 0
                    or self._stderr):
                raise _Refused("REMOTE_TERMINAL_RESULT_REFUSED")
            if self._publication_witness:
                try:
                    self._witness = parse_publication_witness(bytes(self._stdout), self.expected_bytes)
                except ValueError as error:
                    raise _Refused("REMOTE_WITNESS_REFUSED") from error
            elif self._stdout != ACK:
                raise _Refused("REMOTE_TERMINAL_RESULT_REFUSED")
            self._completed = True
        except _Refused as error:
            self._failure = str(error)
        except BaseException as error:
            # The owner remains attached after interruption or an ambiguous
            # socket/thread failure. No inferred no-effect or signal is issued.
            self._failure = "TRANSFER_IO_OR_INTERRUPTION:" + type(error).__name__
        finally:
            self._stopped.set()
        return self.snapshot()
