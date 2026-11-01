"""Draw Nothing OS's quick settings at the screen's own density on a tablet-size panel.

Nothing's quick settings (com.nothing.systemui.qs, a Compose panel) are not
drawn at the display's density. CellLayoutKt.getQsRenderDensityDpi() makes one
up: the shorter side of the screen in pixels * 160 / 420, so the panel always
lays out as if the screen were 420 dp wide. NTFixedDensityScope builds the
panel's Density and Configuration from it, and CellLayout its cell size
(CELL_SIZE_PX, 94 dp) and padding. On a Nothing phone (1080 px at about 420
dpi) that is the real density, give or take. On the Z Fold's inner panel
(2256 x 2504 px, 420 dpi) it is 859 dpi: every tile drawn twice as large, the
panel's height only 466 of those "dp", and the lower half of it off the screen
(the owner, Nothing runs 8 to 10: "it's too big for our screen, half of the
stuff is cut"). Resource overlays cannot reach it: the sizes are constants in
the code and the qualifiers resolve against that made-up configuration (sw420),
so OneOSTabletQs.apk's sw600dp dimens never applied (run 10: the overlay was
enabled at the highest priority and nothing changed).

The patched method keeps Nothing's value unless the screen is at least 600 dp
wide at the system's own density (Resources.getSystem(), the same metrics the
method already reads); there it returns that density, so the panel is drawn
like the rest of the UI. The cover (1080 px) and every phone keep Nothing's
value.

Usage: nothing_qs_density.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import sys

CLASS = os.path.join("com", "nothing", "systemui", "qs", "workspace", "workspace", "CellLayoutKt.smali")
HEADER = ".method public static final getQsRenderDensityDpi()I"
CELL = "Lcom/nothing/systemui/qs/workspace/workspace/CellLayoutKt;"
# The body as Nothing OS 5.0 (Metroid, AQ3A.250924.001) has it, without .line
# and blank lines: anything else is a build this patch was not written for.
OLD = [
    "    .locals 2",
    "    invoke-static {}, %s->physicalPortraitWidthPx()I" % CELL,
    "    move-result v0",
    "    int-to-float v0, v0",
    "    const/high16 v1, 0x43200000    # 160.0f",
    "    mul-float/2addr v0, v1",
    "    const/high16 v1, 0x43d20000    # 420.0f",
    "    div-float/2addr v0, v1",
    "    float-to-int v0, v0",
    "    return v0",
]
NEW = """    .locals 4

    # OneOS: the system density on a panel of sw600dp and up (nothing_qs_density.py).
    invoke-static {}, %(cell)s->physicalPortraitWidthPx()I

    move-result v0

    invoke-static {}, Landroid/content/res/Resources;->getSystem()Landroid/content/res/Resources;

    move-result-object v1

    invoke-virtual {v1}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v1

    iget v1, v1, Landroid/util/DisplayMetrics;->densityDpi:I

    const/16 v2, 0xa0

    if-lt v1, v2, :oneos_nothing

    mul-int/lit16 v2, v0, 0xa0

    div-int v2, v2, v1

    const/16 v3, 0x258

    if-lt v2, v3, :oneos_nothing

    return v1

    :oneos_nothing
    int-to-float v0, v0

    const/high16 v1, 0x43200000    # 160.0f

    mul-float/2addr v0, v1

    const/high16 v1, 0x43d20000    # 420.0f

    div-float/2addr v0, v1

    float-to-int v0, v0

    return v0
""" % {"cell": CELL}


def main():
    root = sys.argv[1]
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + CLASS)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {CLASS}, found {len(hits)}")
    path = hits[0]
    lines = open(path).read().split("\n")
    idx = [i for i, l in enumerate(lines) if l == HEADER]
    if len(idx) != 1:
        sys.exit("CellLayoutKt.getQsRenderDensityDpi()I not found")
    start = idx[0]
    end = lines.index(".end method", start)
    body = [l for l in lines[start + 1:end] if l.strip() and not l.strip().startswith(".line")]
    if body != OLD:
        sys.exit("CellLayoutKt.getQsRenderDensityDpi() is not the shortest side * 160 / 420 "
                 "this patch was written for; left as it is")
    # physicalPortraitWidthPx() must still be the static min(widthPixels, heightPixels)
    # of Resources.getSystem(), whose densityDpi the new body reads alongside it.
    pw = [i for i, l in enumerate(lines) if l == ".method public static final physicalPortraitWidthPx()I"]
    if len(pw) != 1:
        sys.exit("CellLayoutKt.physicalPortraitWidthPx()I not found")
    pw_body = "\n".join(lines[pw[0]:lines.index(".end method", pw[0])])
    for need in ("Landroid/content/res/Resources;->getSystem()", "Landroid/util/DisplayMetrics;->widthPixels:I",
                 "Landroid/util/DisplayMetrics;->heightPixels:I", "Ljava/lang/Math;->min(II)I"):
        if need not in pw_body:
            sys.exit(f"CellLayoutKt.physicalPortraitWidthPx() no longer reads {need}; left as it is")
    lines[start + 1:end] = NEW.rstrip("\n").split("\n")
    open(path, "w").write("\n".join(lines))
    rel = os.path.relpath(path, root)
    print(rel.split(os.sep)[0])


if __name__ == "__main__":
    main()
