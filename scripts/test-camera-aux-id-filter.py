#!/usr/bin/env python3
import importlib.util
import os
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCHER = os.path.join(ROOT, "switcher", "patches", "camera_aux_id_filter.py")
SPEC = importlib.util.spec_from_file_location("camera_aux_id_filter", PATCHER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


METHOD = """.class public final Landroid/hardware/camera2/CameraManager$CameraManagerGlobal;
.super Ljava/lang/Object;

.method private extractCameraIdListLocked(II)[Ljava/lang/String;
    .locals 7

    invoke-static {}, Landroid/hardware/Camera;->shouldExposeAuxCamera()Z

    move-result v1

    .line 2518
    const/4 v2, 0x2

    if-eqz v1, :cond_0

    iget-object v1, p0, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal;->mDeviceStatus:Landroid/util/ArrayMap;

    invoke-virtual {v1}, Landroid/util/ArrayMap;->size()I

    move-result v1

    goto :goto_0

    :cond_0
    move v1, v2

    .line 2519
    :goto_0
    const/4 v3, 0x0

    move v4, v3

    :goto_1
    if-ge v4, v1, :cond_4

    iget-object v5, p0, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal;->mDeviceStatus:Landroid/util/ArrayMap;

    invoke-virtual {v5, v4}, Landroid/util/ArrayMap;->valueAt(I)Ljava/lang/Object;

    move-result-object v5

    check-cast v5, Ljava/lang/Integer;

    iget-object v6, p0, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal;->mDeviceStatus:Landroid/util/ArrayMap;

    invoke-virtual {v6, v4}, Landroid/util/ArrayMap;->keyAt(I)Ljava/lang/Object;

    move-result-object v6

    check-cast v6, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;

    if-eqz v5, :cond_3

    if-eq v5, v2, :cond_3

    invoke-direct {p0, p1, p2, v6}, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal;->shouldHideCamera(IILandroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;)Z

    move-result v5

    if-eqz v5, :cond_2

    goto :goto_2

    :cond_2
    invoke-static {v6}, Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;->-$$Nest$fgetmCameraId(Landroid/hardware/camera2/CameraManager$CameraManagerGlobal$DeviceCameraInfo;)Ljava/lang/String;

    move-result-object v5

    invoke-interface {v0, v5}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    :cond_3
    :goto_2
    add-int/lit8 v4, v4, 0x1

    goto :goto_1

    :cond_4
    return-object p1
.end method
"""


class CameraAuxIdFilterTest(unittest.TestCase):
    def fixture(self, text=METHOD):
        temp = tempfile.TemporaryDirectory()
        directory = os.path.join(temp.name, "smali_classes2", "android", "hardware", "camera2")
        os.makedirs(directory)
        path = os.path.join(directory, "CameraManager$CameraManagerGlobal.smali")
        with open(path, "w", encoding="utf-8", newline="") as output:
            output.write(text)
        return temp, path

    def test_filters_ids_instead_of_truncating_map(self):
        temp, path = self.fixture()
        self.addCleanup(temp.cleanup)
        self.assertEqual("smali_classes2", MODULE.patch(temp.name))
        with open(path, encoding="utf-8") as source:
            patched = source.read()
        self.assertIn(".locals 10", patched)
        self.assertIn("move-result v7", patched)
        # The policy is forced off for every caller: a third-party app must not
        # take the first map entry (a wide or aux camera) as its default.
        self.assertNotIn("currentOpPackageName", patched)
        self.assertNotIn("com.android.systemui", patched)
        self.assertIn("const/4 v7, 0x0", patched)
        self.assertIn('const-string v9, "0"', patched)
        self.assertIn('const-string v9, "1"', patched)
        self.assertIn("if-eqz v9, :goto_2", patched)
        self.assertNotIn("move v1, v2", patched)

    def test_is_idempotent(self):
        temp, path = self.fixture()
        self.addCleanup(temp.cleanup)
        MODULE.patch(temp.name)
        with open(path, encoding="utf-8") as source:
            once = source.read()
        self.assertIsNone(MODULE.patch(temp.name))
        with open(path, encoding="utf-8") as source:
            twice = source.read()
        self.assertEqual(once, twice)

    def test_refuses_unknown_shape(self):
        temp, _ = self.fixture(METHOD.replace("move v1, v2", "const/4 v1, 0x2"))
        self.addCleanup(temp.cleanup)
        with self.assertRaises(SystemExit):
            MODULE.patch(temp.name)


if __name__ == "__main__":
    unittest.main()
