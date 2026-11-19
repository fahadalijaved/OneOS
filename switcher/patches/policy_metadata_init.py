"""A rebuilt framework.jar initializes its device-policy groups itself.

Android 17's android.app.admin.metadata.GeneratedPolicyMetadata is filled by the static
initializers of the policy-group classes (SecurityPolicies, CrossDevicePolicies, ...), each
calling addPolicySupplier. The image's boot image has those classes initialized; a patched
framework.jar (framework_patched.jar) no longer matches it, so nothing ran them and
DevicePolicyManagerService died at boot ("Policy identifier TASK_CONTINUITY_HANDOFF could not be
found", One UI 9.5 on the A36, run 6). ensureInitialized() now loads every such class first
(Class.forName initializes it; a class already initialized is not run twice).

Usage: policy_metadata_init.py <apktool -r dir of framework.jar>
Prints the smali_* directory it changed; nothing (and "not present" on stderr) when the
framework has no GeneratedPolicyMetadata.
"""
import os
import re
import sys

META = "Landroid/app/admin/metadata/GeneratedPolicyMetadata;"
CALL = META + "->addPolicySupplier(Ljava/util/function/Supplier;)V"
HEADER = ".method private static blacklist ensureInitialized()V"


def main(root):
    meta, groups = None, []
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            t = open(p, errors="replace").read()
            first = t.split("\n", 1)[0]
            if first.endswith(" " + META):
                meta = p
            elif CALL in t:
                m = re.match(r"\.class[^\n]* L([^;]+);", first)
                clinit = re.search(r"^\.method static constructor [^\n]*<clinit>\(\)V\n(.*?)^\.end method", t, re.M | re.S)
                if not m or not clinit or CALL not in clinit.group(1):
                    sys.exit(f"{p}: addPolicySupplier outside a static initializer; not patched")
                groups.append(m.group(1).replace("/", "."))
    if meta is None:
        print("policy_metadata_init: GeneratedPolicyMetadata not present", file=sys.stderr)
        return
    if not groups:
        # Nothing to run (HyperOS OS4.0.5 Global, 11-19): no group fills the registry from a static initializer,
        # so a missing boot image cannot leave it empty.
        print("policy_metadata_init: no policy group registers itself; not needed", file=sys.stderr)
        return
    text = open(meta).read()
    hdr = re.search(r"^\.method (?:private )?static (?:[a-z-]+ )*ensureInitialized\(\)V\n    \.locals (\d+)\n", text, re.M)
    if not hdr or text.count("ensureInitialized()V\n    .locals") != 1 or int(hdr.group(1)) < 1:
        sys.exit("policy_metadata_init: ensureInitialized()V not found once with a register; not patched")
    if "OneOS: policy groups" in text:
        print("policy_metadata_init: already patched", file=sys.stderr)
        return
    add = "\n    # OneOS: policy groups initialized here (no boot image for a patched framework.jar)\n"
    for g in sorted(groups):
        add += f'    const-string v0, "{g}"\n\n    invoke-static {{v0}}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;\n\n'
    text = text[:hdr.end()] + add + text[hdr.end():]
    open(meta, "w").write(text)
    print(f"policy_metadata_init: ensureInitialized loads {len(groups)} policy groups", file=sys.stderr)
    print(os.path.relpath(meta, root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
