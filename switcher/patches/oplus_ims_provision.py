"""Outgoing calls over IMS on ColorOS and OxygenOS where the carrier asks for VoLTE provisioning.

ImsManagerExtImpl.isFeatureProvisionedOnDevice (oplus-framework.jar), with the
carrier's using_ims_provision_as_cap_bool set, asks the IMS service's ImsConfig
for the VoLTE provisioning item (10) and allows IMS voice only if it is 1.
Samsung's IMS service, which the guest uses, registers IMS but answers 0, so
GsmCdmaPhone found isImsUseEnabled=false and useImsForCall=false and dialled
every outgoing call as a circuit-switched GSM call, which LTE-only US carriers
do not have: Spectrum on the Z Fold8 (295249c3, 0.5.03: "can receive calls and
send texts" but not call out; isImsRegistered =true, "VoLTE provisioned value
= 0") and the S25+ US (c8be0b32). The Pixel system, on Android's own check,
calls out on the same phone and carrier. The branch is left out, so the method
answers as for every carrier without that setting: provisioned.

Usage: oplus_ims_provision.py <smali root dir>
Prints the smali_* directory (dex file) it changed; nothing if the class or
method is not in this framework (other systems).
"""
import os
import re
import sys

SIG = ".method public blacklist isFeatureProvisionedOnDevice(II)Z"
BRANCH = re.compile(
    r'(    const-string(?:/jumbo)? (v\d+), "using_ims_provision_as_cap_bool"\n'
    r'(?:.*\n){1,8}?'
    r'    move-result (v\d+)\n)'
    r'(\n)?'
    r'    if-nez \3, (:cond_\w+)\n', re.M)


def main():
    root = sys.argv[1]
    suffix = os.path.join("com", "android", "ims", "ImsManagerExtImpl.smali")
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + suffix)]
    if not hits:
        return
    if len(hits) != 1:
        sys.exit(f"expected one ImsManagerExtImpl.smali, found {len(hits)}")
    path = hits[0]
    smali = open(path).read()
    if "OneOS: IMS provisioning" in smali:
        sys.exit("ImsManagerExtImpl already patched")
    start = smali.find(SIG)
    if start < 0:
        sys.exit("ImsManagerExtImpl: isFeatureProvisionedOnDevice(II)Z not found")
    end = smali.find(".end method", start)
    body = smali[start:end]
    found = BRANCH.findall(body)
    if len(found) != 1:
        sys.exit(f"ImsManagerExtImpl.isFeatureProvisionedOnDevice: expected one using_ims_provision_as_cap_bool branch, found {len(found)}")
    # The branch's target must be the provisioning check (ImsConfig), its fall-through the "not enabled" answer.
    m = BRANCH.search(body)
    after = body[m.end():m.end() + 200]
    if not re.match(r"\s*(?:\.line \d+\s*)?goto(?:/16|/32)? :goto_\w+\n", after):
        sys.exit("ImsManagerExtImpl.isFeatureProvisionedOnDevice: the branch is not followed by its goto")
    if "getProvisionedValue" not in body[m.end():]:
        sys.exit("ImsManagerExtImpl.isFeatureProvisionedOnDevice: no ImsConfig provisioning check after the branch")
    body = BRANCH.sub(lambda mm: mm.group(1) + "\n    # OneOS: IMS provisioning branch left out (Samsung IMS answers 0)\n", body, count=1)
    smali = smali[:start] + body + smali[end:]
    open(path, "w").write(smali)
    print("ImsManagerExtImpl: VoLTE provisioning not required for IMS calls", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main()
