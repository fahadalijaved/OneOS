"""Every method/field reference to a class defined in this smali tree must resolve in it (or its supers/interfaces outside it)."""
import os, re, sys
root = sys.argv[1]
classes = {}
REF = re.compile(r"(L[^;\s]+;)->([^\s(:]+)(\([^)]*\)\S+|:\S+)")
for d, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith(".smali"): continue
        t = open(os.path.join(d, f), errors="replace").read()
        m = re.match(r"\.class[^\n]* (L[^;]+;)", t)
        if not m: continue
        sup = re.search(r"^\.super (L[^;]+;)", t, re.M)
        ifs = re.findall(r"^\.implements (L[^;]+;)", t, re.M)
        meths = set(re.findall(r"^\.method[^\n]* (\S+\([^)]*\)\S+)$", t, re.M))
        flds = set(re.findall(r"^\.field[^\n]* ([^\s:]+:\S+?)(?: = .*)?$", t, re.M))
        classes[m.group(1)] = (sup.group(1) if sup else None, ifs, meths, flds, t)
def has(cls, member, field, seen=None):
    seen = seen or set()
    if cls in seen: return True
    seen.add(cls)
    c = classes.get(cls)
    if c is None: return True          # leaves the tree (framework, boot class path): not checked
    sup, ifs, meths, flds, _ = c
    if (member in flds) if field else (member in meths): return True
    if sup and has(sup, member, field, seen): return True
    return any(has(i, member, field, seen) for i in ifs) and not field or any(has(i, member, field, seen) for i in ifs)
bad = set()
for cls, (_, _, _, _, t) in classes.items():
    for line in t.split("\n"):
        s = line.strip()
        if not (s.startswith("invoke-") or s[:4] in ("iget", "iput", "sget", "sput")): continue
        m = REF.search(s)
        if not m: continue
        tcls, name, rest = m.groups()
        if tcls not in classes: continue
        field = rest.startswith(":")
        member = name + rest if not field else name + rest
        direct = name in ("<init>", "<clinit>") or s.startswith("invoke-direct")
        if direct and not field:
            if member not in classes[tcls][2]:
                bad.add(f"{cls} -> {tcls}->{member} (direct)")
            continue
        if not has(tcls, member, field):
            bad.add(f"{cls} -> {tcls}->{member}")
for b in sorted(bad): print(b)
print(f"{len(bad)} unresolved", file=sys.stderr)
