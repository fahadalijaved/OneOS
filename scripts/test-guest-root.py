#!/usr/bin/env python3
"""Execute the actual native bundle parser on the build host with adversarial input.
Android privilege, ptrace and seccomp behavior still require a physical device.
"""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "switcher/native/guest_root.c").read_text()

def function(name):
    start = SOURCE.index("static int " + name + "(")
    pos = SOURCE.index("{", start)
    depth = 1
    end = pos + 1
    while depth:
        depth += (SOURCE[end] == "{") - (SOURCE[end] == "}")
        end += 1
    return SOURCE[start:end]

def bundle(entries):
    data = bytearray(b"ONEOS1\n")
    for path, value in entries:
        name = path.encode()
        data += f"{len(name)} {len(value)} 4755\n".encode() + name + value
    return bytes(data) + b"0 0 0\n"

class NativeBundleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="oneos-native-test-")
        cls.binary = Path(cls.temp.name) / "unpack"
        source = Path(cls.temp.name) / "unpack.c"
        source.write_text("""#define _GNU_SOURCE
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
""" + function("write_all") + function("unpack") + "\nint main(int n,char **v){return n==2?unpack(v[1]):1;}\n")
        subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_parser(self, value, setup=None):
        with tempfile.TemporaryDirectory(prefix="oneos-extract-") as temp:
            root = Path(temp) / "module"
            root.mkdir()
            if setup:
                setup(root)
            result = subprocess.run([self.binary, root], input=value, capture_output=True)
            contents = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
            modes = {str(p.relative_to(root)): stat.S_IMODE(p.stat().st_mode) for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
            return result.returncode, contents, modes

    def test_extracts_files_without_executing_payload_or_setuid(self):
        code, files, modes = self.run_parser(bundle([("system/etc/example", b"payload"), ("customize.sh", b"exit 99")]))
        self.assertEqual(code, 0)
        self.assertEqual(files["system/etc/example"], b"payload")
        self.assertFalse(any(mode & 0o7000 for mode in modes.values()))

    def test_rejects_traversal_absolute_nul_and_empty_components(self):
        for path in ("../escape", "/tmp/escape", "system/../../escape", "a//b", "a/./b", "a/\0b"):
            with self.subTest(path=path):
                self.assertNotEqual(self.run_parser(bundle([(path, b"payload")]))[0], 0)

    def test_rejects_duplicate_and_truncated_entries(self):
        self.assertNotEqual(self.run_parser(bundle([("a", b"one"), ("a", b"two")]))[0], 0)
        self.assertNotEqual(self.run_parser(b"ONEOS1\n1 100 644\naonlythree")[0], 0)
        self.assertNotEqual(self.run_parser(bundle([]) + b"unexpected")[0], 0)

    def test_does_not_follow_directory_symlinks(self):
        with tempfile.TemporaryDirectory() as other:
            code, _, _ = self.run_parser(bundle([("link/escape", b"payload")]), lambda root: (root / "link").symlink_to(other))
            self.assertNotEqual(code, 0)
            self.assertFalse((Path(other) / "escape").exists())

    def test_bundled_framework_has_valid_normalized_layout(self):
        code, files, _ = self.run_parser((ROOT / "switcher/assets/guest_vector.bundle").read_bytes())
        self.assertEqual(code, 0)
        self.assertEqual(files[".oneos-framework"], b"vector")
        for name in ("daemon", "daemon.apk", "manager.apk", "framework/vector.dex", "zygisk/arm64-v8a.so", "bin/dex2oat64"):
            self.assertTrue(files[name], name)

if __name__ == "__main__":
    unittest.main()
