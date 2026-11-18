"""Read the fixed guest/host Binder startup evidence without loading OEM code."""
import ast
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
LEGACY = "firmware/installed-oneos-code-profile/static/assets/"
DONOR = "../firmware/donor/extracted/system/lib64/"
NATIVE = "firmware/guest-native-service-manager/"
PREP = "out/isolated-retained-view-controller/r-c88346bc/"
HOST = "out/retained-pin-host-cohort/r-15a49021/"
FORK = "compat/boot/com/android/internal/os/PreparedGuestSystemServerFork.java"
MOUNTINFO = "firmware/read-only-resume-20261106/mountinfo.stdout"
START = "out/guest-entry-exec-profile/PROFILE.json"
RETARGET = "inventory/guest-system-server-fork-retarget.json"
LSS = "out/guest-pin-check-systemserver-ingress/selected-publication.json"
DEX_PARSER = "tools/preserve_dex_code_headers.py"
PINS = {
    DEX_PARSER: "943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6",
    LEGACY + "guest_prepare.sh": "000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70",
    LEGACY + "guest_start.sh": "896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446",
    LEGACY + "oneos_switch.sh": "e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150",
    DONOR + "libbinder.so": "471001204af7c226bb104dcbf9aae7e74be431f4542f389bcc574489428ff8ad",
    DONOR + "libandroid_runtime.so": "edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279",
    NATIVE + "binder.json": "3bb8b03f60eb7ddf9ba8328bc1bae538ae80031e60d1348d44848ecec028ccfd",
    NATIVE + "runtime.json": "c3f42733634475bceeed4c73005dd607479ac23629a77b1b98e9c393c2df5864",
    PREP + "receipt.json": "ece49e0dd778ecd20f1c06a1cb54dc4ff94ca233e12823a8e583c485ad0e8e49",
    PREP + "native-src/guest_private_view_owner.c": "30d7dc8ddcf372f76c3384e43dc6ed806989edfd0fb72efc2f0886bab8c0b063",
    HOST + "receipt.json": "0260dffda000b95cfe2f4a9bf83afc939ae455f2724c6302a07de2d634abfab3",
    HOST + "source/RetainedClosedPinHostCapture.java": "d51ebee906bd08c41c65be0a3d271b2e14789a851cfabac400a2c933ae2ddcd8",
    HOST + "OneOS-Retained-Pin-Host-unsigned.apk": "60bd2b3d6f97cd281cf088747f5b6bc6dcf00bfd1853392b02f07aa148e8ee27",
    FORK: "201dd20fac8c11ea6643a82b3c464f8ae282300731ef120fab03612f3344babc",
    MOUNTINFO: "f696e0bd403d60c5ca7a0641b6df5deb96c027d9cd35e4ec78eb710915a7f157",
    START: "bcb875cdaca995f3802ef971b635003d696a9893041d549d2ff3157e9e70cdef",
    RETARGET: "d86d596770d64e9cc2569317d07c107cdd6d4d68b388be7a3b684dcaf5c11505",
    LSS: "5bd4e8cf9292e276c4d6d82a87630cd9c62ae10ea2e33e04dc3b80170506c2f2",
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(path, expected, limit=16 * 1024 * 1024):
    with (ROOT / path).open("rb") as source:
        data = source.read(limit + 1)
    need(len(data) <= limit and sha(data) == expected, f"Held input differs: {path}")
    return data


def signed(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def code_edge(blob, records, pc, symbol, target=None):
    owner, = (fn for fn in records["functions"]
              if fn["symbol"].startswith(symbol) and fn["address"] <= pc < fn["address"] + fn["bytes"])
    off = owner["fileOffset"]
    body = blob[off:off + owner["bytes"]]
    need(sha(body) == owner["sha256"], f"Held ELF code owner at {pc:#x}")
    ins, = (ins for ins in owner["instructions"] if ins["pc"] == pc)
    delta = pc - owner["address"]
    need(body[delta:delta + 4].hex() == ins["bytes"] and
         (target is None or ins.get("targetSymbol") == target), f"Held ELF instruction at {pc:#x}")
    return {"owner": owner["symbol"], **ins}


def default_driver(binder):
    # Independently resolve the ADR literal and the two direct branches in the
    # exact exported ProcessState::self and initWithDriver byte leaves.
    self_pc, alternative_pc = 0x85b18, 0x99220
    self_code = binder[self_pc:self_pc + 20]
    alt_code = binder[alternative_pc:alternative_pc + 12]
    need(sha(self_code) == "462c51bf3eddeea8d4a5c75a0c351b676827050a70e9dad5cca15f864157f2c2"
         and sha(alt_code) == "8247dff085a8f34d73d74d4dd79f191c9c2881f106c492e870e4486afe3abe07",
         "Driver entry byte leaf changed")
    adr, argument, jump = struct.unpack_from("<3I", self_code, 8)
    need(adr & 0x9f00001f == 0x10000000 and argument == 0x2a1f03e1, "Default ADR x0 / w1=0")
    offset = signed(((adr >> 5) & 0x7ffff) << 2 | ((adr >> 29) & 3), 21)
    literal = self_pc + 8 + offset
    need(literal == 0x2c9cc and binder[literal:literal + 12] == b"/dev/binder\0",
         "Exact default driver path")
    explicit_arg, explicit_jump = struct.unpack_from("<2I", alt_code, 4)
    need(explicit_arg == 0x52800021, "Explicit driver w1=1")
    for pc, word in ((self_pc + 16, jump), (alternative_pc + 8, explicit_jump)):
        need(word & 0xfc000000 == 0x14000000 and
             pc + 4 * signed(word & 0x3ffffff, 26) == 0x85b2c, "Both original entries reach init")
    return {"source": "/dev/binder", "sourceLiteralFileOffset": literal, "selfPc": self_pc,
            "initPc": 0x85b2c, "explicitDriverEntryPc": alternative_pc}


def host_class_defs(dex, parser_source):
    tree = ast.parse(parser_source, filename=DEX_PARSER)
    selected = [node for node in tree.body if getattr(node, "name", None) in {"need", "Dex039"}]
    need([node.name for node in selected] == ["need", "Dex039"], "Pinned DEX parser closure")
    namespace = {"hashlib": hashlib, "struct": struct, "zlib": zlib, "MAX_BYTES": 2 * 1024 * 1024}
    exec(compile(ast.Module(body=selected, type_ignores=[]), DEX_PARSER, "exec"), namespace)
    return {descriptor.decode("ascii") for descriptor in namespace["Dex039"](dex).classes}


def main():
    data = {path: capture(path, pin) for path, pin in PINS.items()}
    lines = []
    def line(path, no, token):
        text = data[path].decode("utf-8").splitlines()[no - 1]
        need(token in text, f"Expected source anchor at {path}:{no}")
        lines.append({"path": path, "line": no, "token": token})

    line(LEGACY + "guest_prepare.sh", 308, "if [ ! -e /dev/binderfs/binder ]; then")
    line(LEGACY + "guest_prepare.sh", 309, "mount -t binder binder /dev/binderfs")
    line(LEGACY + "guest_prepare.sh", 316, "mount --rbind /dev")
    line(LEGACY + "guest_prepare.sh", 317, "mount --make-rprivate")
    line(LEGACY + "guest_start.sh", 31, "mount -t proc proc /proc")
    line(LEGACY + "guest_start.sh", 646, "in the shared")
    line(LEGACY + "guest_start.sh", 1284, "exec /data/zygote_exec")
    line(LEGACY + "oneos_switch.sh", 1418, "unshare -m")
    mount_rows = [row.split() for row in data[MOUNTINFO].decode().splitlines()]
    binder_row, = (row for row in mount_rows if row[4] == "/dev/binderfs")
    dev_row, = (row for row in mount_rows if row[4] == "/dev")
    need(binder_row[1] == dev_row[0] and binder_row[binder_row.index("-") + 1] == "binder",
         "Saved host binderfs mount type and parent")

    gvo = PREP + "native-src/guest_private_view_owner.c"
    need(json.loads(data[PREP + "receipt.json"])["compiledSourcePins"]["guest_private_view_owner.c"]
         == PINS[gvo], "Isolated preparation source identity")
    line(gvo, 160, "/proc/self/fdinfo/%d")
    line(gvo, 262, "SCM_RIGHTS")
    line(gvo, 691, 'mount("gvo-v3-owned-dev",target,"tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC')
    line(gvo, 713, 'mkdirat(dev_write,"socket",0755)')
    need(not any(token in data[gvo] for token in (b"execve(", b"fexecve(", b'"/dev/binder"')),
         "Selected isolated FS preparer contains no checked guest-exec or Binder device edge")
    need(json.loads(data[START])["selected"] is False and
         json.loads(data[RETARGET])["runtimeSelected"] is False, "Launcher/fork evidence scope")
    need(b"private static volatile ChildRecord child;" in data[FORK] and
         b"Process.openPidFd(record.selfPid, 0)" in data[FORK] and
         b"record.runnable = actual" in data[FORK] and b"import android.os.IBinder" not in data[FORK],
         "Private fork occurrence carries only local process/Runnable custody")

    selected = json.loads(data[LSS])
    raw = capture(selected["raw"], selected["rawSha256"], selected["rawBytes"])
    lifecycle, = (row["body"] for row in map(json.loads, raw.splitlines()) if row["record"] == "method")
    actual = {ins["pc"]: ins.get("reference", "") for ins in lifecycle["instructions"]}
    need(actual[14] == "string=lock_settings" and "->publishBinderService(" in actual[19],
         "Ordinary guest LSS still publishes canonical lock_settings")

    binder = data[DONOR + "libbinder.so"]
    runtime = data[DONOR + "libandroid_runtime.so"]
    need(all(blob[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", blob, 18)[0] == 183
             for blob in (binder, runtime)), "Exact AArch64 ELF64 source inputs")
    b_rows = json.loads(data[NATIVE + "binder.json"])
    r_rows = json.loads(data[NATIVE + "runtime.json"])
    native_edges = [
        code_edge(runtime, r_rows, 0x13aa70, "_ZL42android_os_BinderInternal_getContextObject",
                  "_ZN7android12ProcessState4selfEv"),
        code_edge(runtime, r_rows, 0x13aa84, "_ZL42android_os_BinderInternal_getContextObject",
                  "_ZN7android12ProcessState16getContextObjectERKNS_2spINS_7IBinderEEE"),
        code_edge(binder, b_rows, 0x6beec, "_ZN7android12ProcessState16getContextObject"),
        code_edge(binder, b_rows, 0x6befc, "_ZN7android12ProcessState16getContextObject",
                  "_ZN7android12ProcessState23getStrongProxyForHandleEi"),
        code_edge(binder, b_rows, 0x992b0, "_ZN7android12ProcessState13childPostFork"),
        code_edge(binder, b_rows, 0x992b4, "_ZN7android12ProcessState13childPostFork", "close"),
    ]
    need(native_edges[2]["bytes"] == "e1031f2a" and native_edges[4]["operands"] == "w9, [x8, #0xf8]",
         "Physical handle0 and forked latch")

    host = json.loads(data[HOST + "receipt.json"])
    apk = data[HOST + "OneOS-Retained-Pin-Host-unsigned.apk"]
    with zipfile.ZipFile(io.BytesIO(apk)) as zipper:
        member, = (entry for entry in zipper.infolist() if entry.filename == "classes.dex")
        need(member.file_size <= 2 * 1024 * 1024, "Closed host DEX bound")
        dex = zipper.read(member)
    need(sha(apk) == host["apkSha256"] and sha(dex) == host["dexSha256"]
         and len(apk) == host["apkBytes"] and host["apkSigned"] is False
         and host["endpointPublished"] is False, "Latest unsigned closed-host cohort")
    definitions = host_class_defs(dex, data[DEX_PARSER])
    need(definitions == set(host["dexDefinitions"]), "Actual closed host DEX class definitions")
    owner = data[HOST + "source/RetainedClosedPinHostCapture.java"]
    need(any(name.endswith("/PreparedRetainedPinEndpoint;") for name in definitions)
         and b"endpoint = preparedEndpoint;" in owner and b"prepareWithCheck(" in owner
         and b"closeIngress()" in owner and b"openIngress" not in owner and b"publish" not in owner,
         "Closed endpoint is retained by source but has no sender")

    return {
        "status": "PASS_HELD_BINDER_STARTUP_SOURCE_PROOF",
        "delivery": "REFUSED_NO_SOURCE_OWNED_BINDER_INGRESS_AND_LIVE_OCCURRENCE",
        "inputPins": PINS,
        "verifiedLines": lines,
        "legacy": {"savedHostBinderMountId": int(binder_row[0]), "savedHostBinderMountParentId": int(dev_row[0]),
                   "sourceUsesHostDeviceTree": True, "separatePidNamespaceSelected": False,
                   "liveGuestDriverObserved": False},
        "donorDefaultDriver": default_driver(binder),
        "nativeEdges": native_edges,
        "isolated": {"binderDeviceProduced": False, "guestExecProduced": False},
        "guestBootCapture": {"retargetSelected": False, "binderReceived": False, "pidfdIsBinder": False},
        "closedHost": {"apkSha256": host["apkSha256"], "dexSha256": host["dexSha256"],
                       "definitionCount": len(definitions), "endpointDefinitionPresent": True, "endpointPublished": False},
        "phoneOrOemExecuted": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2))
    except (OSError, ValueError, KeyError, IndexError, struct.error, zipfile.BadZipFile) as error:
        sys.exit(f"Held Binder source proof refused: {error}")
