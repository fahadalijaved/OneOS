#!/usr/bin/env python3
"""Pinned donor correction for clock scaling inside embedded Flux editor."""
import hashlib
from pathlib import Path
import sys
RELATIVE = 'smali_classes5/com/oplus/wallpapers/business/themeedit/toolkit/utils/ClockEditExtKt.smali'
BEFORE = '85bf4c9d9ea570c7d24058bc6bebc210cf07d90bb9f9bd1fcbbc70423e85295f'
AFTER = 'a5ff3d183c0eea1013da00b993bd9d1057c2af82458fa417811f884c97ca431e'
OLD = '    :cond_2\n    move v7, v0\n\n    move v8, v1\n'
NEW = '    :cond_2\n    # Scale the clock canvas, not the embedded Activity window.\n    invoke-virtual {p0}, Landroid/view/View;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;\n    move-result-object v2\n    if-eqz v2, :oneos_clock_canvas_fallback\n    iget v3, v2, Landroid/view/ViewGroup$LayoutParams;->width:I\n    iget v4, v2, Landroid/view/ViewGroup$LayoutParams;->height:I\n    if-lez v3, :oneos_clock_canvas_fallback\n    if-lez v4, :oneos_clock_canvas_fallback\n    move v0, v3\n    move v1, v4\n    :oneos_clock_canvas_fallback\n    move v7, v0\n\n    move v8, v1\n'

def patch(root):
    path = Path(root) / RELATIVE
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest == AFTER:
        return
    if digest != BEFORE or data.decode().count(OLD) != 1:
        raise ValueError('Unsupported Flux editor donor; refusing patch')
    result = data.decode().replace(OLD, NEW).encode()
    assert hashlib.sha256(result).hexdigest() == AFTER
    temp = path.with_suffix('.smali.tmp')
    temp.write_bytes(result)
    temp.replace(path)

if __name__ == '__main__':
    patch(sys.argv[1])
