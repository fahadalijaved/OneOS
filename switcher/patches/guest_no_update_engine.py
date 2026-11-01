"""Keep the guest's StorageManagerService away from the phone's A/B updater.

update_engine is the phone's own updater and a shared binder service: a guest
that can reach it could be handed a payload for One UI's slots (the guest's
Play services system update, or a setup wizard's update check). oneos_switch.sh
therefore stops it for the session, and that has been the only thing standing
between a guest and the host's slots.

Nothing OS 5.0's StorageManagerService builds an android.os.UpdateEngine in its
constructor, whose constructor throws IllegalStateException("Failed to find
update_engine") when the service is not registered. With the updater stopped,
the guest's StorageManagerService never started ("BOOT FAILURE starting
StorageManagerService"), "mount" was never published, and system_server died
soon after in ArtManagerLocal's getStorageManager (first Nothing run,
2026-10-30). Pixel's build of the same class has no UpdateEngine at all.

The field's only use is handleSystemReady(), which binds a callback to watch
the phone's A/B update progress: a host operation a session has no business
following. So the field is set to null and the bind is skipped, which also
means the guest holds no handle on the updater even if something started it
again mid-session. Every other use of UpdateEngine in the image is untouched.

A build whose StorageManagerService has no mUpdateEngine field needs nothing
and is left alone (Pixel). One that has the field must match both sites
exactly, or this stops rather than half-patch it.

Usage: guest_no_update_engine.py <smali root dir>
Prints the smali_* directory (dex file) it changed, or nothing when the build
does not use UpdateEngine there.
"""
import os
import re
import sys

SUFFIX = os.path.join("com", "android", "server", "StorageManagerService.smali")
CLS = "Lcom/android/server/StorageManagerService;"
UE = "Landroid/os/UpdateEngine;"
FIELD = f"{CLS}->mUpdateEngine:{UE}"
R = r"[vp]\d+"
# Between two instructions smali keeps blank lines, .line/.local debug info and
# comments; none of them change what runs.
GAP = r"(?:[ \t]*(?:#[^\n]*|\.(?:line|local|end local|restart local|prologue)[^\n]*)?\n)*"
# mUpdateEngine = new UpdateEngine();  (the constructor)
MAKE = re.compile(
    rf"([ \t]*)new-instance (?P<r>{R}), {re.escape(UE)}\n"
    rf"{GAP}[ \t]*invoke-direct \{{(?P=r)\}}, {re.escape(UE)}-><init>\(\)V\n"
    rf"{GAP}([ \t]*)iput-object (?P=r), p0, {re.escape(FIELD)}\n"
)
# mUpdateEngine.bind(mUpdateEngineCallback, new Handler(...));  (handleSystemReady)
BIND = re.compile(
    rf"([ \t]*)iget-object (?P<e>{R}), p0, {re.escape(FIELD)}\n"
    rf"(?P<body>.*?)"
    rf"[ \t]*invoke-virtual \{{(?P=e), {R}, {R}\}}, {re.escape(UE)}->bind\("
    rf"Landroid/os/UpdateEngineCallback;Landroid/os/Handler;\)Z\n",
    re.S,
)


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + SUFFIX)]
    if len(hits) != 1:
        sys.exit(f"expected one StorageManagerService.smali, found {len(hits)}")
    path = hits[0]
    rel = os.path.relpath(path, root)
    with open(path) as f:
        text = f.read()
    if not re.search(r"^\.class .*" + re.escape(CLS) + r"$", text, re.M):
        sys.exit(f"{rel}: not {CLS}")
    if "oneos_no_update_engine" in text:
        sys.exit(f"{rel}: already patched")
    if f"mUpdateEngine:{UE}" not in text:
        print(f"{rel}: no UpdateEngine in StorageManagerService, nothing to do", file=sys.stderr)
        return
    make = MAKE.search(text)
    if not make:
        sys.exit(f"{rel}: mUpdateEngine is set some other way than `new UpdateEngine()`; not patched")
    if len(MAKE.findall(text)) != 1:
        sys.exit(f"{rel}: `new UpdateEngine()` stored in mUpdateEngine more than once; not patched")
    bind = BIND.search(text)
    if not bind:
        sys.exit(f"{rel}: mUpdateEngine is used for something other than bind(callback, handler); not patched")
    if len(BIND.findall(text)) != 1:
        sys.exit(f"{rel}: mUpdateEngine.bind called more than once; not patched")
    # The body between the iget and the bind only builds the two arguments; a
    # build that does anything else there is one this was not written for.
    body = bind.group("body")
    for line in body.split("\n"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith((".line", ".local", ".end local", ".restart local", ".prologue")):
            continue
        if re.fullmatch(rf"iget-object {R}, p0, {re.escape(CLS)}->m\w+:\S+", s):
            continue
        if re.fullmatch(r"new-instance " + R + r", Landroid/os/Handler;", s):
            continue
        if re.fullmatch(rf"invoke-virtual \{{{R}\}}, Landroid/content/Context;->getMainLooper\(\)Landroid/os/Looper;", s):
            continue
        if re.fullmatch(rf"move-result-object {R}", s):
            continue
        if re.fullmatch(rf"invoke-direct \{{{R}, {R}\}}, Landroid/os/Handler;-><init>\(Landroid/os/Looper;\)V", s):
            continue
        sys.exit(f"{rel}: unexpected instruction before mUpdateEngine.bind: {s!r}; not patched")

    reg = make.group("r")
    text = text[:make.start()] + (
        f"{make.group(1)}# OneOS: no handle on the phone's own A/B updater (update_engine is One UI's,\n"
        f"{make.group(1)}# and a session must never hand it a payload). The field stays null and\n"
        f"{make.group(1)}# handleSystemReady skips the bind below.\n"
        f"{make.group(1)}const/4 {reg}, 0x0\n"
        f"\n"
        f"{make.group(3)}iput-object {reg}, p0, {FIELD}\n"
    ) + text[make.end():]

    bind = BIND.search(text)  # offsets moved with the edit above
    text = text[:bind.start()] + (
        f"{bind.group(1)}iget-object {bind.group('e')}, p0, {FIELD}\n"
        f"\n"
        f"{bind.group(1)}if-eqz {bind.group('e')}, :oneos_no_update_engine\n"
        f"\n"
        + bind.group("body")
        + text[bind.start("body") + len(bind.group("body")):bind.end()]
        + f"\n{bind.group(1)}:oneos_no_update_engine\n"
    ) + text[bind.end():]

    with open(path, "w") as f:
        f.write(text)
    print(f"{rel}: StorageManagerService keeps no UpdateEngine ({reg} null) and does not bind to it", file=sys.stderr)
    print(rel.split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: guest_no_update_engine.py <smali root dir>")
    main(sys.argv[1])
