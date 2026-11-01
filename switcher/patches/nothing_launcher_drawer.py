"""More category boxes per row in Nothing OS's app drawer on a wide panel.

Nothing's launcher (NothingLauncher3) groups the drawer into category boxes
("Social", "Games", ...): com.nothing.launcher.allapps.smart. Two things fix
them at two per row on any screen:

- smart/e (the drawer's AllAppsGridAdapter) returns a constant 2 from
  getAppCountPerRow(), so each box spans half the grid;
- smart/z.n() (the "SmartProfile", built with every DeviceProfile) sizes a box
  from that: width = (available width - 2 * padding - gap) / 2, height
  width * 1.11, and the padding inside it from the width.

On the Fold's inner panel (2256 px, 859 dp) that is a box of about 1000 x 1100
px holding four normal-size icons (the owner, Nothing run 11: "Look at the size
of these boxes in drawer"). Both now take a column count from the width:
max(2, width in dp / 200), stored by z.n() in a new field oneosCols and read by
e.getAppCountPerRow(). The cover (411 dp) and phones keep 2, and with 2 every
value comes out as before. The inner panel gets 4, boxes of about phone size.
The grid's item decoration and the span sizer already work for any count.

Usage: nothing_launcher_drawer.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import sys

Z = "Lcom/nothing/launcher/allapps/smart/z;"
E = "Lcom/nothing/launcher/allapps/smart/e;"
FIELD = ".field public oneosCols:I"


def find(root, rel):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + rel)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {rel}, found {len(hits)}")
    return hits[0]


def method(lines, header):
    idx = [i for i, l in enumerate(lines) if l == header]
    if len(idx) != 1:
        sys.exit(f"{header} not found once")
    return idx[0], lines.index(".end method", idx[0])


def one(lines, start, end, text):
    hits = [i for i in range(start, end) if lines[i] == text]
    if len(hits) != 1:
        sys.exit(f"expected one '{text.strip()}' in the method, found {len(hits)}; left as it is")
    return hits[0]


def patch_z(path):
    lines = open(path).read().split("\n")
    if FIELD in lines:
        sys.exit("smart/z already has oneosCols")
    start, end = method(lines, ".method public final n(Landroid/content/Context;Lcom/android/launcher3/DeviceProfile;)V")
    if lines[start + 1] != "    .locals 7":
        sys.exit("smart/z.n() is not the build this patch was written for (.locals); left as it is")

    # The width split: (avail - 2a - b) / 2 becomes (avail - 2a - (N-1) b) / N.
    gap = one(lines, start, end, "    iget v1, p0, %s->b:I" % Z)
    if [l for l in lines[gap + 1:gap + 12] if l.strip() and not l.strip().startswith(".line")][:4] != [
            "    sub-int/2addr p1, v1", "    int-to-float p1, p1", "    int-to-float v1, v2", "    div-float/2addr p1, v1"]:
        sys.exit("smart/z.n(): the folder width is not (available - padding - gap) / 2; left as it is")
    # The gap actually left: avail - 2a - 2c becomes (avail - 2a - N c) / (N-1).
    cw = one(lines, start, end, "    iget v1, p0, %s->c:I" % Z)
    tail = [l for l in lines[cw + 1:cw + 12] if l.strip() and not l.strip().startswith(".line")][:3]
    if tail != ["    mul-int/2addr v1, v2", "    sub-int/2addr p1, v1", "    iput p1, p0, %s->b:I" % Z]:
        sys.exit("smart/z.n(): the panel gap is not available - padding - 2 * width; left as it is")
    anchor = one(lines, start, end, "    invoke-static {p2, v0}, Lkotlin/jvm/internal/y;->j(Ljava/lang/Object;Ljava/lang/String;)V")
    if not any("invoke-virtual {p1}, Landroid/content/Context;->getResources()" in l for l in lines[anchor + 1:anchor + 4]):
        sys.exit("smart/z.n(): the null checks are not followed by getResources(); left as it is")

    # Edit from the bottom up so the indices above stay right.
    mul = [i for i in range(cw + 1, end) if lines[i] == "    mul-int/2addr v1, v2"][0]
    put = [i for i in range(mul + 1, end) if lines[i] == "    iput p1, p0, %s->b:I" % Z][0]
    lines[put:put] = [
        "    add-int/lit8 v3, v3, -0x1",
        "",
        "    div-int/2addr p1, v3",
        "",
    ]
    lines[mul:mul + 1] = [
        "    iget v3, p0, %s->oneosCols:I" % Z,
        "",
        "    mul-int/2addr v1, v3",
    ]
    f2i = [i for i in range(gap + 1, end) if lines[i] == "    int-to-float v1, v2"][0]
    lines[f2i:f2i + 1] = [
        "    iget v1, p0, %s->oneosCols:I" % Z,
        "",
        "    int-to-float v1, v1",
    ]
    lines[gap + 1:gap + 1] = [
        "",
        "    iget v3, p0, %s->oneosCols:I" % Z,
        "",
        "    add-int/lit8 v3, v3, -0x1",
        "",
        "    mul-int/2addr v1, v3",
    ]
    lines[anchor + 1:anchor + 1] = """
    # OneOS: category boxes per row from the width, max(2, dp / 200) (nothing_launcher_drawer.py).
    invoke-virtual {p1}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v0

    iget v0, v0, Landroid/util/DisplayMetrics;->densityDpi:I

    invoke-virtual {p2}, Lcom/android/launcher3/DeviceProfile;->getDeviceProperties()Lcom/android/launcher3/deviceprofile/DeviceProperties;

    move-result-object v1

    invoke-virtual {v1}, Lcom/android/launcher3/deviceprofile/DeviceProperties;->getAvailableWidthPx()I

    move-result v1

    const/4 v2, 0x2

    const/16 v3, 0xa0

    if-lt v0, v3, :oneos_cols

    mul-int/lit16 v1, v1, 0xa0

    div-int v1, v1, v0

    div-int/lit16 v1, v1, 0xc8

    if-le v1, v2, :oneos_cols

    move v2, v1

    :oneos_cols
    iput v2, p0, %s->oneosCols:I""".replace("%s", Z).split("\n")

    fields = [i for i, l in enumerate(lines) if l.startswith(".field private n:I")]
    if len(fields) != 1:
        sys.exit("smart/z has no field n to put oneosCols after")
    lines[fields[0] + 1:fields[0] + 1] = ["", FIELD]
    open(path, "w").write("\n".join(lines))


def patch_e(path):
    lines = open(path).read().split("\n")
    start, end = method(lines, ".method public getAppCountPerRow()I")
    body = [l for l in lines[start + 1:end] if l.strip() and not l.strip().startswith(".line")]
    if body != ["    .locals 0", "    const/4 p0, 0x2", "    return p0"]:
        sys.exit("smart/e.getAppCountPerRow() is not the constant 2 this patch was written for; left as it is")
    lines[start + 1:end] = """    .locals 1

    # OneOS: the count smart/z worked out for this DeviceProfile (nothing_launcher_drawer.py).
    iget-object p0, p0, Lcom/android/launcher3/allapps/BaseAllAppsAdapter;->mActivityContext:Lcom/android/launcher3/views/ActivityContext;

    invoke-interface {p0}, Lcom/android/launcher3/views/ActivityContext;->getDeviceProfile()Lcom/android/launcher3/DeviceProfile;

    move-result-object p0

    invoke-virtual {p0}, Lcom/android/launcher3/DeviceProfile;->getSmartProfile()%s

    move-result-object p0

    const/4 v0, 0x2

    if-eqz p0, :oneos_two

    iget p0, p0, %s->oneosCols:I

    if-lt p0, v0, :oneos_two

    return p0

    :oneos_two
    return v0""".replace("%s", Z).split("\n")
    open(path, "w").write("\n".join(lines))


def main():
    root = sys.argv[1]
    zp = find(root, os.path.join("com", "nothing", "launcher", "allapps", "smart", "z.smali"))
    ep = find(root, os.path.join("com", "nothing", "launcher", "allapps", "smart", "e.smali"))
    zd = os.path.relpath(zp, root).split(os.sep)[0]
    if os.path.relpath(ep, root).split(os.sep)[0] != zd:
        sys.exit("smart/z and smart/e are in different dex files; left as they are")
    dp = find(root, os.path.join("com", "android", "launcher3", "DeviceProfile.smali"))
    if ".method public getSmartProfile()%s" % Z not in open(dp).read():
        sys.exit("DeviceProfile.getSmartProfile() is not there; left as it is")
    patch_z(zp)
    patch_e(ep)
    print(zd)


if __name__ == "__main__":
    main()
