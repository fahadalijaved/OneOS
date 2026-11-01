#!/usr/bin/env python3
"""Keep Flux hit rectangles and raw touches in screen coordinates."""
import hashlib
from pathlib import Path
import sys
RELATIVE = 'smali_classes5/com/oplus/wallpapers/business/themeedit/toolkit/view/ClickOnlyLayout.smali'
BEFORE = 'bc6d08d80513ad3c1d1d7c23cba2f26f7a2a0e53ee961648d54c25dfc0538d6e'
AFTER = 'c19386e644031fbe3e1ce6f5ca451d10e82920fc51663cf8f30a1e6b4710680c'
OLD = 'invoke-virtual {p1, p0}, Landroid/view/View;->getGlobalVisibleRect(Landroid/graphics/Rect;)Z'
NEW = 'invoke-static {p1, p0}, Lcom/oplus/wallpapers/business/themeedit/toolkit/view/ClickOnlyLayout;->oneosScreenVisibleRect(Landroid/view/View;Landroid/graphics/Rect;)Z'
HELPER = '\n.method private static oneosScreenVisibleRect(Landroid/view/View;Landroid/graphics/Rect;)Z\n    .locals 3\n    invoke-virtual {p0, p1}, Landroid/view/View;->getGlobalVisibleRect(Landroid/graphics/Rect;)Z\n    move-result v0\n    if-eqz v0, :oneos_rect_done\n    invoke-virtual {p0}, Landroid/view/View;->getRootView()Landroid/view/View;\n    move-result-object p0\n    const/4 v1, 0x2\n    new-array v1, v1, [I\n    invoke-virtual {p0, v1}, Landroid/view/View;->getLocationOnScreen([I)V\n    const/4 v2, 0x0\n    aget v2, v1, v2\n    const/4 p0, 0x1\n    aget p0, v1, p0\n    invoke-virtual {p1, v2, p0}, Landroid/graphics/Rect;->offset(II)V\n    :oneos_rect_done\n    return v0\n.end method\n'

def patch(root):
    path = Path(root) / RELATIVE
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest == AFTER:
        return
    if digest != BEFORE or data.decode().count(OLD) != 2:
        raise ValueError('Unsupported Flux editor donor; refusing patch')
    result = (data.decode().replace(OLD, NEW) + HELPER).encode()
    assert hashlib.sha256(result).hexdigest() == AFTER
    temp = path.with_suffix('.smali.tmp')
    temp.write_bytes(result)
    temp.replace(path)

if __name__ == '__main__':
    patch(sys.argv[1])
