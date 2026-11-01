#!/usr/bin/env python3
"""Apply the pinned Find N6 cover-only vertical status-bar alignment fix."""
import hashlib
from pathlib import Path
import sys

RELATIVE = 'smali_classes4/com/oplus/systemui/statusbar/phone/StatusBarPaddingProvider.smali'
BEFORE = '5fbb1dcac7b9e414547b72f136c6d71d03d435dd94e7f06c80a78f680002d20c'
AFTER = 'f94124709f83e1712ce31f90c262731a6bedcb67d03cad85612d8ca48e428808'
INSERT = '\n    # Cover screen: center in the complete status bar, retaining horizontal cutout clearance.\n    iget-object v0, p0, Lcom/oplus/systemui/statusbar/phone/StatusBarPaddingProvider;->context:Landroid/content/Context;\n    invoke-virtual {v0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;\n    move-result-object v0\n    invoke-virtual {v0}, Landroid/content/res/Resources;->getConfiguration()Landroid/content/res/Configuration;\n    move-result-object v0\n    iget v0, v0, Landroid/content/res/Configuration;->screenWidthDp:I\n    const/16 v1, 0x258\n    if-ge v0, v1, :oneos_original_vertical_padding\n    const/4 v0, 0x0\n    invoke-static {v0}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;\n    move-result-object v0\n    new-instance v1, Lkotlin/Pair;\n    invoke-direct {v1, v0, v0}, Lkotlin/Pair;-><init>(Ljava/lang/Object;Ljava/lang/Object;)V\n    return-object v1\n    :oneos_original_vertical_padding\n'
ANCHOR = '.method public final updatePaddingTopBottom(IZ)Lkotlin/Pair;\n    .locals 5\n'

def patch(root):
    path = Path(root) / RELATIVE
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest == AFTER:
        return
    if digest != BEFORE:
        raise ValueError('StatusBarPaddingProvider differs from the supported donor')
    text = data.decode()
    if text.count(ANCHOR) != 1:
        raise ValueError('Vertical padding method anchor differs')
    result = text.replace(ANCHOR, ANCHOR + INSERT).encode()
    if hashlib.sha256(result).hexdigest() != AFTER:
        raise ValueError('Patched class hash differs')
    temporary = path.with_suffix('.smali.tmp')
    temporary.write_bytes(result)
    temporary.replace(path)

if __name__ == '__main__':
    patch(sys.argv[1])
