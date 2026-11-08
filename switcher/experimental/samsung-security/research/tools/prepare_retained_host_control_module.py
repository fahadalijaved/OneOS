"""Select the separate direct-host link in the unchanged real boot issuer.

Writes authored source only. Does not build, install or execute a module.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path("com/appleexploit/oneos/security/authority/RetainedPinHostModule.java")
BASE_SHA = "819990fd5ef76fc8a6509fffdd40665218218af3b7a5ddc97c36ba030f15cdbe"
EDITS = (
    (b"HostRootLinkProfile", b"HostRootLinkProfileV2"),
    (b"PreparedRetainedHostAppBinding", b"PreparedRetainedHostNativeBindingV2"),
)


def main():
    base = (ROOT / "compat/host-module" / RELATIVE).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise ValueError("Reviewed original boot issuer required")
    result = base
    for old, new in EDITS:
        if old not in result or new in result:
            raise ValueError("Exact link-selection substitution required")
        result = result.replace(old, new)
    inverse = result
    for old, new in reversed(EDITS):
        inverse = inverse.replace(new, old)
    if inverse != base:
        raise ValueError("Original boot issuer inverse mismatch")
    target = ROOT / "compat/handoff-host-module" / RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result)
    print(f"Prepared separate v2 host module: {hashlib.sha256(result).hexdigest()}")


if __name__ == "__main__":
    main()
