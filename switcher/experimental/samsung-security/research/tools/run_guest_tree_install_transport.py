#!/usr/bin/env python3
"""Own a direct binary install pipe. The executable launcher is inert-only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "out/guest-tree-install-transport"
IO = ROOT / "tools/build_guest_tree_verity.py"
IO_SHA = "6c6aee1d4d18bfe4cdc4475db7bab98aebd70de6974de22b88ea16e8755fd23e"
FEED = "tools/stream_guest_tree_install_feed.py"
FEED_SHA = "79136547e6bbbc71f9cb20fbfc95c5a82ec5411c40d041457fa06c446310d7a4"
INSTALLER_RECEIPT = "out/guest-tree-carrier-installer/r-e5d9aea8/receipt.json"
INSTALLER_RECEIPT_SHA = "9261d32b82a5226e5336da58ff71b4796d2ee466594a243f6c9dbd8e8a1d85e9"
INSTALLER_SHA = "7eac4c581619c4f7ab3031687666c1e2703d460b3e60fbd89eb81fd79148e6e5"
ACK = b"ONEOS_CARRIER_V1 PUBLISHED_CLOSED\n"
ACK_CAP = 64
DIAGNOSTIC_CAP = 32 * 1024
READ_CHUNK = 8192
TAIL_BYTES = 17
FIXTURE_BYTES = bytes(range(256)) * 4096 + b"\r\n\0\x1a\xff" * 17
FIXTURE_CASES = (
    "pass", "bad-receipt", "no-receipt", "producer-error", "target-error", "partial-ack",
    "duplicate-ack", "lost-ack", "crlf-ack", "diagnostic-overflow", "short-feed",
    "target-closed", "late-eof", "late-target-exit",
)


class InstallerPin(NamedTuple):
    receipt_path: str
    receipt_sha256: str
    artifact_path: str
    artifact_bytes: int
    artifact_sha256: str


_INSTALLER_PINS = {
    'v1': InstallerPin(INSTALLER_RECEIPT, INSTALLER_RECEIPT_SHA,
                       'out/guest-tree-carrier-installer/r-e5d9aea8/oneos_install_verified_carrier',
                       1387248, INSTALLER_SHA),
    'v2': InstallerPin('out/file-stage-static-exec-repair/installer/r-d8e4c3db/receipt.json',
                       'e9235bc97d51c84d7c43c1d965e52dbff246408d32dc80a2b517ac8ee87e2306',
                       'out/file-stage-static-exec-repair/installer/r-d8e4c3db/oneos_install_verified_carrier',
                       1350336, 'da4d6d886eb0f43ac7a206521d6e3ab56676e8942744e96f13d9ff0c20671aa9'),
}


def carrier_installer_pin(protocol='v1'):
    if type(protocol) is not str or protocol not in _INSTALLER_PINS:
        raise ValueError('Unknown carrier protocol')
    return _INSTALLER_PINS[protocol]


def installer_build_status(protocol='v1'):
    carrier_installer_pin(protocol)
    return ('PASS_CARRIER_INSTALLER_STATIC_EXEC_LINK_ONLY' if protocol == 'v2'
            else 'PASS_CARRIER_INSTALLER_STATIC_LINK_ONLY')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_record(record):
    return (json.dumps(record, indent=2) + "\n").encode("ascii")


def write_exclusive(path, raw):
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("Incomplete transport record write")
        stream.flush()
        os.fsync(stream.fileno())


def load_io():
    with IO.open("rb") as stream:
        raw = stream.read(64 * 1024 + 1)
    if sha(raw) != IO_SHA:
        raise ValueError("Checked I/O helper differs from selected bytes")
    module = {"__file__": str(IO), "__name__": "guest_tree_transport_checked_io"}
    exec(compile(raw, str(IO), "exec"), module)
    return module


def pinned(io, name, expected, maximum):
    path = io["ROOT"] / name
    with io["checked_input"](path, max_size=maximum) as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum or sha(raw) != expected:
        raise ValueError(f"Selected transport input differs: {name}")
    return raw


def selected_inputs(io, *, carrier_protocol='v1'):
    pin = carrier_installer_pin(carrier_protocol)
    pinned(io, FEED, FEED_SHA, 64 * 1024)
    raw = pinned(io, pin.receipt_path, pin.receipt_sha256, 256 * 1024)
    receipt = json.loads(raw.decode("ascii"), object_pairs_hook=io["unique_object"])
    artifact = receipt["artifact"]
    if (receipt["status"] != installer_build_status(carrier_protocol)
            or receipt["deviceEligible"] is not False or receipt["targetExecuted"] is not False
            or artifact != {"path": pin.artifact_path, "bytes": pin.artifact_bytes, "sha256": pin.artifact_sha256}):
        raise ValueError("Selected installer evidence is not the reviewed static artifact")
    image = pinned(io, pin.artifact_path, pin.artifact_sha256, 2 * 1024 * 1024)
    if len(image) != pin.artifact_bytes:
        raise ValueError("Selected installer size differs")
    return {"producerSourceSha256": FEED_SHA, "installerBuildReceiptSha256": pin.receipt_sha256,
            "installerArtifactSha256": pin.artifact_sha256, "deviceEligible": False}


def source_record(image, image_bytes, raw_sha, verity, tail, readback, verity_receipt, independent, io_sha):
    """Exact byte schema written by the reviewed producer before its final tail."""
    return canonical_record({
        "schema": "guest-tree-install-feed-source/v1",
        "status": "PC_SOURCE_AUTHENTICATED_TAIL_NOT_YET_RELEASED",
        "image": image,
        "imageBytes": image_bytes,
        "imageSha256": raw_sha,
        "fsVerityDigest": verity,
        "withheldTailBytes": tail,
        "namedAndHeldIdentityVerified": True,
        "readbackReceiptSha256": readback,
        "fsVerityReceiptSha256": verity_receipt,
        "independentDescriptorReceiptSha256": independent,
        "checkedIoSourceSha256": io_sha,
        "requiresProducerExitZeroAndReceiverAck": True,
    })


def selected_source_receipt():
    size = 13_890_850_816
    return source_record(
        "out/guest-tree-erofs-pc/r-3d0dc2ef/guest.erofs", size,
        "094ff7e7ac1148fab732719d2e04a943fbbcc0d7d0ae67ad62d898b552eb365d",
        "9b2b664582360dec660e3e25c840104c16b1e1a9cb4aadbf8f467e200c525ba9",
        size % (4 * 1024**2) or (4 * 1024**2),
        "92e2f8199da955cf4b8ddc15cf99b4ab978c133d3f9284535ad3c500fa0d5e6e",
        "7c185c512782ac04ebb32dad878d9f85d361b2edec4d3f18afb52c8591c2299a",
        "377ef52fe2d64215a8565f274a41ef5053af4b9c56b927155ec504310c112db6", IO_SHA)


def fixture_receipt():
    return source_record("INERT_ONLY", len(FIXTURE_BYTES), sha(FIXTURE_BYTES), "11" * 32,
                         TAIL_BYTES, "22" * 32, "33" * 32, "44" * 32, "55" * 32)


class Drain:
    """Read through EOF while retaining a bounded prefix and first failure."""

    def __init__(self, stream, cap):
        self.stream = stream
        self.cap = cap
        self.lock = threading.Lock()
        self.prefix = bytearray()
        self.total = 0
        self.done = False
        self.error = None
        self.thread = threading.Thread(target=self.read, daemon=False)

    def fail(self, error):
        with self.lock:
            if self.error is None:
                self.error = type(error).__name__

    def read(self):
        try:
            while True:
                raw = self.stream.read(READ_CHUNK)
                if not raw:
                    break
                with self.lock:
                    self.total += len(raw)
                    available = self.cap - len(self.prefix)
                    self.prefix.extend(raw[:available])
        except BaseException as error:
            self.fail(error)
        finally:
            try:
                self.stream.close()
            except BaseException as error:
                self.fail(error)
            with self.lock:
                self.done = True

    def snapshot(self):
        with self.lock:
            return bytes(self.prefix), self.total, self.done, self.error


class Transport:
    """One owner for both local process handles and all diagnostic readers."""

    def __init__(self, job, io, expected_source, selected):
        self.job = job
        self.io = io
        self.expected_source = expected_source
        self.selected = selected
        self.processes = {}
        self.drains = {}
        self.launch_error = None
        self.pipe_close_error = None
        self.attempt_persistence_error = None
        self.timeout_observations = 0
        self.final = None
        self.final_write_attempted = False

    def drain(self, name, stream, cap):
        reader = Drain(stream, cap)
        self.drains[name] = reader
        try:
            reader.thread.start()
        except BaseException as error:
            # A start failure does not prove the reader never started.
            reader.fail(error)
            raise

    def _connect_once(self, target, producer, env):
        if self.processes or self.launch_error:
            raise ValueError("Transport already attempted")
        options = dict(cwd=self.job, env=env, close_fds=True, shell=False, bufsize=0, text=False)
        pipe = None
        try:
            child = subprocess.Popen(target, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, **options)
            self.processes["target"] = child
            pipe = child.stdin
            self.drain("targetStdout", child.stdout, ACK_CAP)
            self.drain("targetStderr", child.stderr, DIAGNOSTIC_CAP)
            feeder = subprocess.Popen(producer, stdin=subprocess.DEVNULL, stdout=pipe,
                                      stderr=subprocess.PIPE, **options)
            self.processes["producer"] = feeder
            self.drain("producerStderr", feeder.stderr, DIAGNOSTIC_CAP)
        except BaseException as error:
            # Keep every returned process and reader. Constructor failure does
            # not supply no-child or no-target-effect evidence.
            self.launch_error = type(error).__name__
        finally:
            if pipe is not None:
                # Only the spawned producer may now keep the data pipe open.
                try:
                    pipe.close()
                except BaseException as error:
                    self.pipe_close_error = type(error).__name__
        record = {
            "scope": "INERT_LOCAL_PROCESS_EXIT_ONLY",
            "processes": {role: process.pid for role, process in self.processes.items()},
            "launchError": self.launch_error, "parentPipeCloseError": self.pipe_close_error,
        }
        try:
            write_exclusive(self.job / "transport-start.json", canonical_record(record))
        except OSError as error:
            self.attempt_persistence_error = type(error).__name__

    def source_receipt(self):
        path = self.job / "producer-source" / "source-receipt.json"
        try:
            with self.io["checked_input"](path, size=len(self.expected_source)) as stream:
                raw = stream.read(len(self.expected_source) + 1)
        except (OSError, ValueError) as error:
            return False, None, type(error).__name__
        return raw == self.expected_source, sha(raw), None

    def observe(self, seconds):
        if not 0 <= seconds <= 30:
            raise ValueError("Observation budget outside 0–30 seconds")
        if self.final is not None:
            return self.final
        deadline = time.monotonic() + seconds
        while True:
            processes = {role: {"pid": process.pid, "exitCode": process.poll()}
                         for role, process in self.processes.items()}
            captures = {name: reader.snapshot() for name, reader in self.drains.items()}
            if all(row["exitCode"] is not None for row in processes.values()) and all(
                row[2] for row in captures.values()
            ):
                return self.finish(processes, captures)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.timeout_observations += 1
                return self.report("INERT_HOLD_ACTIVE", processes, captures)
            time.sleep(min(0.02, remaining))

    def report(self, status, processes, captures):
        return {
            "schema": "guest-tree-install-transport/v1", "status": status,
            "scope": "INERT_LOCAL_PROCESS_EXIT_ONLY",
            "processes": processes, "selectedProductionInputsNotRun": self.selected,
            "diagnostics": {name: {"retainedPrefixHex": raw.hex(), "actualBytes": total,
                                   "overflow": total > len(raw), "eofAndClosed": done and not error,
                                   "error": error}
                            for name, (raw, total, done, error) in captures.items()},
            "launchError": self.launch_error, "parentPipeCloseError": self.pipe_close_error,
            "attemptPersistenceError": self.attempt_persistence_error,
            "timeoutObservations": self.timeout_observations,
            "killOrRetryAttempted": False, "targetAndroidExitObserved": False,
        }

    def finish(self, processes, captures):
        exact, receipt_sha, receipt_error = self.source_receipt()
        target = captures.get("targetStdout")
        exact_ack = target == (ACK, len(ACK), True, None)
        both_zero = len(processes) == 2 and all(row["exitCode"] == 0 for row in processes.values())
        silent = all(captures.get(name) == (b"", 0, True, None)
                     for name in ("producerStderr", "targetStderr"))
        passed = exact and exact_ack and both_zero and silent and not (
            self.launch_error or self.pipe_close_error or self.attempt_persistence_error
        )
        result = self.report("PASS_INERT_PIPE_ONLY" if passed else "INERT_TRANSFER_UNCONFIRMED",
                             processes, captures)
        result.update({"exactSourceReceipt": exact, "sourceReceiptSha256": receipt_sha,
                       "sourceReceiptError": receipt_error, "exactOneAck": exact_ack,
                       "bothActualLocalExitsZero": both_zero})
        if not self.final_write_attempted:
            self.final_write_attempted = True
            try:
                raw = canonical_record(result)
                record_path = self.job / "transport-result.json"
                write_exclusive(record_path, raw)
                with self.io["checked_input"](record_path, size=len(raw)) as record:
                    if record.read(len(raw) + 1) != raw:
                        raise OSError("Transport result readback differs")
            except (OSError, ValueError) as error:
                result["status"] = "INERT_TRANSFER_UNCONFIRMED"
                result["resultPersistenceError"] = type(error).__name__
        self.final = result
        return result


def run(case, directory):
    """Start a fixed inert selection and return the retained observation owner."""
    if case not in FIXTURE_CASES:
        raise ValueError("Unsupported inert transport case")
    io = load_io()
    selected = selected_inputs(io)
    path = io["inside_repo"](directory)
    if path.parent != BASE:
        raise ValueError("Inert run requires a fresh direct child of the transport evidence directory")
    io["checked_path"](BASE.parent, directory=True)
    BASE.mkdir(exist_ok=True)
    io["checked_path"](BASE, directory=True)
    job = io["claim_output"](directory)
    worker = job / "worker.py"
    source = Path(__file__).resolve().read_bytes()
    write_exclusive(worker, source)
    if worker.read_bytes() != source:
        raise ValueError("Staged inert worker differs")
    temp = job / "tmp"
    temp.mkdir()
    env = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR") if name in os.environ}
    env.update({name: str(temp) for name in ("TMP", "TEMP", "TMPDIR")})
    launcher = [sys.executable, "-I", "-B", str(worker), "--inert-worker", case]
    session = Transport(job, io, fixture_receipt(), selected)
    session._connect_once([*launcher, "target"], [*launcher, "producer"], env)
    return session


def inert_worker(case, role):
    script = Path(__file__).resolve()
    job = script.parent
    if (script.name != "worker.py" or job.parent.name != "guest-tree-install-transport"
            or job.parent.parent.name != "out" or case not in FIXTURE_CASES):
        return 2
    if os.name == "nt":
        import msvcrt
        for stream in (sys.stdin, sys.stdout):
            msvcrt.setmode(stream.fileno(), os.O_BINARY)
    if role == "producer":
        sink = sys.stdout.buffer
        if case == "short-feed":
            sink.write(FIXTURE_BYTES[:-TAIL_BYTES])
            sink.flush()
            return 4
        sink.write(FIXTURE_BYTES[:-TAIL_BYTES])
        sink.flush()
        if case != "no-receipt":
            folder = job / "producer-source"
            folder.mkdir()
            raw = fixture_receipt()
            if case == "bad-receipt":
                raw = raw.replace(b"INERT_ONLY", b"INERT_FAKE")
            write_exclusive(folder / "source-receipt.json", raw)
        sink.write(FIXTURE_BYTES[-TAIL_BYTES:])
        sink.flush()
        if case == "late-eof":
            time.sleep(0.6)
        return 7 if case == "producer-error" else 0

    if role != "target":
        return 2
    if case == "target-closed":
        sys.stdout.buffer.write(b"ONEOS_CARRIER_V1 HOLD\n")
        return 3
    if case == "diagnostic-overflow":
        sys.stderr.buffer.write(b"d" * (DIAGNOSTIC_CAP * 4))
        sys.stderr.buffer.flush()
    received = hashlib.sha256()
    size = 0
    for data in iter(lambda: sys.stdin.buffer.read(READ_CHUNK), b""):
        received.update(data)
        size += len(data)
    if size != len(FIXTURE_BYTES) or received.hexdigest() != sha(FIXTURE_BYTES):
        sys.stdout.buffer.write(b"ONEOS_CARRIER_V1 REFUSED_LOCAL_CLOSED\n")
        return 2
    reply = {
        "partial-ack": ACK[:-5], "duplicate-ack": ACK + ACK,
        "lost-ack": b"", "crlf-ack": ACK[:-1] + b"\r\n",
    }.get(case, ACK)
    sys.stdout.buffer.write(reply)
    sys.stdout.buffer.flush()
    if case == "late-target-exit":
        time.sleep(0.6)
    return 3 if case == "target-error" else 0


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--inert-worker":
        return inert_worker(sys.argv[2], sys.argv[3])
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--inert-case", choices=FIXTURE_CASES, required=True)
    cli.add_argument("--receipt-dir", required=True)
    args = cli.parse_args()
    try:
        owner = run(args.inert_case, args.receipt_dir)
        result = owner.observe(15)
        if result["status"] == "INERT_HOLD_ACTIVE":
            # Keep the same local owners while the fixed inert process exits.
            result = owner.observe(15)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS_INERT_PIPE_ONLY" else 1
    except (KeyError, OSError, ValueError) as error:
        print(f"Inert transport refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
