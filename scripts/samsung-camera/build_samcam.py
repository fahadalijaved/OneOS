"""Rewrite Samsung Camera (and the One UI classes it needs) to run on a non-Samsung guest framework.

Every reference to a member of the guest's own (boot) classes that the guest lacks
(Samsung's sem* additions) becomes a call into Loneos/semcompat/Sem;, a generated
class of static shims; writes to such fields are dropped. The One UI classes the
camera reaches (Sem* managers, CSC/floating features, MotionPhoto...) are copied
from One UI's framework.jar / worker_wrapper_compat.jar into a compat tree.

Usage: build_samcam.py <nothing jar dirs> <camera smali roots> <compat smali roots> <out dir>
Writes <out>/camera/<root>/... (rewritten copies of changed files only),
<out>/compat/smali/... (reached One UI classes, rewritten, plus Sem.smali),
<out>/report.txt
"""
import os, re, sys, glob, collections, shutil

ARGS = sys.argv[1:5]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan.py")).read().split("def main():")[0])

nt_dirs, cam_roots, compat_roots, OUT = ARGS[0].split(","), ARGS[1].split(","), ARGS[2].split(","), ARGS[3]
nothing = load([p for d in nt_dirs for p in glob.glob(os.path.join(d, "*.jar"))])
PLATFORM = ("Landroid/", "Ljava/", "Ljavax/", "Ldalvik/", "Llibcore/", "Lcom/android/",
            "Lorg/apache/", "Lorg/json/", "Lorg/xml/", "Lorg/w3c/", "Lsun/")
SEM = "Loneos/semcompat/Sem;"


def index(roots):
    idx = {}
    for r in roots:
        for sd in sorted(glob.glob(os.path.join(r, "smali*"))):
            for root, _, files in os.walk(sd):
                for f in files:
                    if f.endswith(".smali"):
                        p = os.path.join(root, f)
                        idx.setdefault("L" + os.path.relpath(p, sd)[:-6] + ";", (r, sd, p))
    return idx


cam_idx, compat_idx = index(cam_roots), index(compat_roots)
REF = re.compile(r"(L[^;\s()]+;)->([^\s(:]+)(\([^)\s]*\)\S+|:\S+)")
TYPE = re.compile(r"L[A-Za-z0-9_$/\-]+;")
parsed = {}


def parse(path):
    if path not in parsed:
        sup, ifs, mem, types = None, [], set(), set()
        for line in open(path, errors="replace"):
            s = line.strip()
            if s.startswith(".super "):
                sup = s.split()[1]
            elif s.startswith(".implements "):
                ifs.append(s.split()[1])
            elif s.startswith(".method "):
                mem.add(s.split()[-1])
            elif s.startswith(".field "):
                mem.add(re.match(r"\.field\s+(?:[a-z\-]+\s+)*([^\s=]+:[^\s=]+)", s).group(1))
            elif not s.startswith((".", "#", "\"")):
                types.update(TYPE.findall(s))
        parsed[path] = (sup, ifs, mem, types)
    return parsed[path]


def defs_of(c):
    if c in nothing and (c.startswith(PLATFORM) or c not in cam_idx):
        return ("nothing",) + nothing[c][:3]
    for src, idx in (("camera", cam_idx), ("compat", compat_idx)):
        if c in idx:
            sup, ifs, mem, _ = parse(idx[c][2])
            return (src, sup, ifs, mem)
    return None


def resolve(c, m, seen=None):
    """'ok' if c or a supertype defines m; else the first guest (boot) class on the
    way that lacks it, or None when the hierarchy leaves everything we know."""
    seen = seen if seen is not None else set()
    if c in seen:
        return None
    seen.add(c)
    d = defs_of(c)
    if d is None:
        return None
    src, sup, ifs, mem = d
    if m in mem:
        return "ok"
    lacking = c if src == "nothing" else None
    for n in ([sup] if sup else []) + list(ifs):
        r = resolve(n, m, seen)
        if r == "ok":
            return "ok"
        if r and not lacking:
            lacking = r
    return lacking


# Which One UI classes get reached (types used by camera code, transitively).
reached, work = set(), collections.deque(sorted(cam_idx))
done = set()
while work:
    c = work.popleft()
    if c in done:
        continue
    done.add(c)
    d = defs_of(c)
    if not d or d[0] == "nothing":
        continue
    path = (cam_idx if d[0] == "camera" else compat_idx)[c][2]
    sup, ifs, mem, types = parse(path)
    for t in types | set(ifs) | ({sup} if sup else set()):
        dd = defs_of(t)
        if dd and dd[0] == "compat" and t not in done:
            reached.add(t)
            work.append(t)
    # Inner classes of a reached class travel with it.
for c in list(reached):
    base = c[:-1]
    for k in compat_idx:
        if k.startswith(base + "$") and k not in reached and defs_of(k)[0] == "compat":
            reached.add(k)

INV = re.compile(r"^(\s+)(invoke-(?:virtual|interface|super|direct|static))(/range)? \{([^}]*)\}, (L[^;\s]+;)->([^\s(]+)(\([^)]*\))(\S+)\s*$")
FLD = re.compile(r"^(\s+)([si](?:get|put)(?:-wide|-object|-boolean|-byte|-char|-short)?) ([^,]+(?:, [^,]+)?), (L[^;\s]+;)->([^\s:]+):(\S+)\s*$")
shims = {}   # name -> (static?, owner, member, params, ret, kind)


def jname(c):
    return c[1:-1].replace("/", "_").replace("$", "_")


def shim_name(owner, name, sig):
    base = "%s__%s" % (jname(owner).split("_", 2)[-1] if False else jname(owner), name)
    return base


def mr(t):
    return "move-result-wide" if t in ("J", "D") else ("move-result-object" if t[0] in "L[" else "move-result")


def rewrite(path):
    out, changed = [], 0
    for line in open(path, errors="replace").read().split("\n"):
        m = INV.match(line)
        if m:
            ind, op, rng, regs, cls, name, params, ret = m.groups()
            if cls == SEM:
                out.append(line); continue
            r = resolve(cls.lstrip("["), name + params + ret)
            if r and r != "ok":
                static = op == "invoke-static"
                nparams = params if static else "(" + r + params[1:]
                nm = shim_name(r, name, params + ret) + ("" if not static else "")
                shims[(nm, nparams + ret)] = (static, r, name, params, ret, "method")
                out.append("%sinvoke-static%s {%s}, %s->%s%s%s" % (ind, rng or "", regs, SEM, nm, nparams, ret))
                changed += 1
                continue
        f = FLD.match(line)
        if f:
            ind, op, regs, cls, name, typ = f.groups()
            r = resolve(cls.lstrip("["), name + ":" + typ)
            if r and r != "ok":
                regs_l = [x.strip() for x in regs.split(",")]
                if "put" in op:
                    out.append("%s# OneOS semcompat: dropped %s %s->%s" % (ind, op, r, name))
                elif op.startswith("sget"):
                    nm = "get_%s__%s" % (jname(r), name)
                    shims[(nm, "()" + typ)] = (True, r, name, "()", typ, "sfield")
                    out.append("%sinvoke-static {}, %s->%s()%s" % (ind, SEM, nm, typ))
                    out.append("")
                    out.append("%s%s %s" % (ind, mr(typ), regs_l[0]))
                else:
                    nm = "get_%s__%s" % (jname(r), name)
                    shims[(nm, "(%s)%s" % (r, typ))] = (False, r, name, "()", typ, "ifield")
                    out.append("%sinvoke-static/range {%s .. %s}, %s->%s(%s)%s" % (ind, regs_l[1], regs_l[1], SEM, nm, r, typ))
                    out.append("")
                    out.append("%s%s %s" % (ind, mr(typ), regs_l[0]))
                changed += 1
                continue
        out.append(line)
    return "\n".join(out), changed


stats = collections.Counter()
for c, (root, sd, p) in cam_idx.items():
    text, n = rewrite(p)
    if n:
        dst = os.path.join(OUT, "camera", os.path.basename(root), os.path.relpath(p, root))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w").write(text)
        stats["camera files"] += 1
        stats["camera rewrites"] += n
for c in sorted(reached):
    root, sd, p = compat_idx[c]
    text, n = rewrite(p)
    dst = os.path.join(OUT, "compat", "smali", os.path.relpath(p, sd))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w").write(text)
    stats["compat classes"] += 1
    stats["compat rewrites"] += n

with open(os.path.join(OUT, "shims.txt"), "w") as fh:
    for (nm, sig), v in sorted(shims.items()):
        fh.write("%s %s %s %s->%s%s%s %s\n" % ("S" if v[0] else "I", nm, sig, v[1], v[2], v[3], v[4], v[5]))
print(dict(stats), "shims:", len(shims))
