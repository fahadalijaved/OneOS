#!/usr/bin/env python3
"""One UI 9.5 set r6: a <signer> stanza left empty by ignore_mac_permissions_package no longer stops boot.

One UI 9.5 (S26) has the flag ignore_mac_permissions_package on, so SELinuxMMAC.readSignerOrThrow drops every
<package> tag ("<package> tag found but flag ignore_mac_permissions_package is enabled. This tag will be
ignored."). The phone's own /vendor/etc/selinux/vendor_mac_permissions.xml on older Galaxies has signer
stanzas made only of <package> tags; with those dropped the stanza has neither a seinfo nor a package, the
"Only seinfo tag XOR package tags are allowed within a signer stanza." check throws, readInstallPolicy fails
and PackageManagerService stops system_server: "Unable to load SELinux MMAC policy" (11-19 reports 3aa2f42d
A07, 2f5486ae S23; earlier Fold8).

Such a stanza is dropped: readSignerOrThrow returns null for it and readInstallPolicy, its only caller, adds
nothing, so those apps fall through to the other stanzas and the default, as the flag means them to. (Kept
as an empty Policy it would sort as a duplicate of the platform's stanza with the same certificate, which
fails the whole policy too.) A stanza with both a seinfo and packages still throws. Fail-closed: the check
and the call must each be found exactly once in the expected shape.

    oneui_mmac_empty_signer.py <services smali dir>   -> prints the smali dir it changed
"""
import os
import re
import sys

CLS = "com/android/server/pm/SELinuxMMAC.smali"
MARK = "    # OneOS: a signer emptied by ignore_mac_permissions_package is dropped (oneui_mmac_empty_signer.py)\n"
CALL = re.compile(r"^    invoke-static \{(v\d+)\}, Lcom/android/server/pm/SELinuxMMAC;->readSignerOrThrow\(Lorg/xmlpull/v1/XmlPullParser;\)"
                  r"Lcom/android/server/pm/Policy;\n\n    move-result-object (v\d+)\n\n"
                  r"(    invoke-virtual \{v\d+, \2\}, Ljava/util/ArrayList;->add\(Ljava/lang/Object;\)Z\n\n    goto (:goto_\w+)\n)", re.M)
# :cond_b is reached when (seinfo == null) == pkgMap.isEmpty(): both empty or both set. The seinfo register is
# the one tested before the xor; the Policy is p0.
SHAPE = re.compile(
    r"^    if-nez (v\d+), (:cond_\w+)\n\n    const/4 (v\d+), 0x1\n\n    goto (:goto_\w+)\n\n    \2\n    const/4 \3, 0x0\n\n"
    r"    \4\n    invoke-interface \{(v\d+)\}, Ljava/util/Map;->isEmpty\(\)Z\n\n    move-result \5\n\n    xor-int/2addr \3, \5\n\n"
    r"    if-eqz \3, (:cond_\w+)\n\n    return-object p0\n\n    \6\n"
    r"(    const-string/jumbo p0, \"Only seinfo tag XOR package tags are allowed within a signer stanza\.\"\n)", re.M)


def main():
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(hits) != 1:
        sys.exit(f"oneui_mmac_empty_signer: {CLS} found in {hits or 'no smali dir'}")
    path = os.path.join(root, hits[0], CLS)
    src = open(path).read()
    if MARK in src:
        print(hits[0])
        return
    found = list(SHAPE.finditer(src))
    if len(found) != 1:
        sys.exit(f"oneui_mmac_empty_signer: the signer XOR check found {len(found)} times in the expected shape")
    calls = list(CALL.finditer(src))
    if len(calls) != 1:
        sys.exit(f"oneui_mmac_empty_signer: the readSignerOrThrow call found {len(calls)} times in the expected shape")
    m = found[0]
    seinfo = m.group(1)
    add = (MARK +
           f"    if-nez {seinfo}, :oneos_mmac_both_set\n\n"
           "    const/4 p0, 0x0\n\n"
           "    return-object p0\n\n"
           "    :oneos_mmac_both_set\n")
    c = calls[0]
    skip = MARK + f"    if-eqz {c.group(2)}, {c.group(4)}\n\n"
    # The call comes before the check in the file; insert at the later offset first.
    assert c.start(3) < m.start(7)
    src = src[:m.start(7)] + add + src[m.start(7):]
    src = src[:c.start(3)] + skip + src[c.start(3):]
    with open(path, "w") as f:
        f.write(src)
    print(hits[0])


if __name__ == "__main__":
    main()
