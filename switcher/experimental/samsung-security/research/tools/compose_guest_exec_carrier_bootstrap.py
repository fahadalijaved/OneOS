"""Add the exact bootstrap file check to the separate research child."""

from hashlib import sha256
import json
import re
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-exec-carrier-research-build/r-1328c8a4"
BASE_RECEIPT = "37cb7b29ba9f19dc5d23e33c11a29febf5d4910df004dc5b274775262d56eeec"
DONOR_ENV = ROOT.parent / "firmware/donor/extracted/init.environ.rc"
ENV_SHA256 = "84085163a12f27c76724173ce3491825deafe1e13a7af7bf0fd6e793378f3774"
CONTROLLER = "guest_tree_control_owner.c"
ENV_HEADER = "guest_native_bootstrap_env.h"


def environment_header(raw):
    entries = {}
    groups = []
    for line in raw.decode("ascii").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if line == "on early-init":
            groups.append(0)
            continue
        match = re.fullmatch(r"    export ([A-Z][A-Z0-9_]*) (1|/[a-z0-9_.]+(?:/[a-z0-9_.]+)*)", line)
        if not groups or not match:
            raise ValueError("Unexpected donor environment declaration")
        name, value = match.groups()
        if name in entries or name.startswith("LD_") or name == "BIONIC_APPCOMPAT_OVERRIDE":
            raise ValueError(f"Unadmitted environment name {name}")
        if (value == "1") != (name == "ANDROID_BOOTLOGO") or {".", ".."}.intersection(value.split("/")):
            raise ValueError(f"Unexpected donor environment value for {name}")
        entries[name] = value
        groups[-1] += 1
    if groups != [10, 16]:
        raise ValueError("Unexpected early export count")

    lines = [
        "#ifndef ONEOS_GUEST_NATIVE_BOOTSTRAP_ENV_H",
        "#define ONEOS_GUEST_NATIVE_BOOTSTRAP_ENV_H",
        "",
        "#include <stddef.h>",
        "",
        "/* Pinned donor declarations for the research readback. */",
        "static const char *const guest_bootstrap_probe_env[] = {",
    ]
    vector = [name + "=" + value for name, value in entries.items()]
    lines.extend(f"    {json.dumps(entry)}," for entry in vector)
    lines.extend(("    NULL,", "};", "", "#endif", ""))
    packed = ("\0".join(vector) + "\0").encode("ascii")
    return "\n".join(lines).encode("ascii"), packed, len(entries)


def controller(raw):
    include = '#include "guest_linkerconfig_target.h"'
    begin = "static int prepare_child_entry(struct guest_zygote_control_fds *fds,"
    retirement = """            || guest_zygote_retire_inherited_view(fds, view, entry) < 0
            || child_entry_window() < 0) {"""
    check = """static int check_child_bootstrap(const struct guest_linkerconfig_generation_start *target) {
    struct statvfs flags;
    if (fstatvfs(target->root_fd, &flags) < 0) return -1;
    if (flags.f_flag & ST_NOEXEC) { errno = EACCES; return -1; }
    struct guest_native_early_loader_sample sample;
    int close_error = 0;
    const size_t count = sizeof(guest_bootstrap_probe_env) / sizeof(guest_bootstrap_probe_env[0]) - 1;
    if (guest_native_early_loader_open_readback(GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP, target, NULL,
                guest_bootstrap_probe_env, count, &sample, &close_error) < 0) return -1;
    if (close_error) { errno = close_error; return -1; }
    if (sample.placement.object_count != 33) { errno = EPROTO; return -1; }
    if (sample.placement.noexec_objects) { errno = EACCES; return -1; }
    return 0;
}

"""
    return overlay(raw, [
        (include, include + '\n#include "guest_native_early_loader_open.h"\n#include "' + ENV_HEADER + '"'),
        ("#include <sys/socket.h>", "#include <sys/socket.h>\n#include <sys/statvfs.h>"),
        (begin, check + begin),
        (retirement, """            || guest_zygote_retire_inherited_view(fds, view, entry) < 0
            || child_entry_window() < 0
            || check_child_bootstrap(target) < 0
            || child_entry_window() < 0) {"""),
        ("    init_wire(packet, W_CHILD_PREPARED, S_READBACK);",
         "    if (child_entry_window() < 0) return -1;\n    init_wire(packet, W_CHILD_PREPARED, S_READBACK);"),
    ])


def main():
    prior = json.loads(read_small(BASE / "receipt.json", 224 * 1024, BASE_RECEIPT))
    pin = prior["sourcePins"][CONTROLLER]
    c = controller(read_small(BASE / "src" / CONTROLLER, 64 * 1024, pin))
    h, packed, exports = environment_header(read_small(DONOR_ENV, 8 * 1024, ENV_SHA256))
    outputs = {CONTROLLER: c, ENV_HEADER: h}
    run = ROOT / "out/guest-exec-carrier-bootstrap-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_EXEC_CARRIER_BOOTSTRAP_PREFLIGHT_SOURCE",
        "baseReceiptSha256": BASE_RECEIPT, "inputSha256": pin,
        "donorEnvSha256": ENV_SHA256, "proposedExportCount": exports,
        "proposedEnvBytes": len(packed), "proposedEnvSha256": sha256(packed).hexdigest(),
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
        "inverse": True, "wireChange": False, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
