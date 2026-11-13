"""Regression checks for the real composition defects and sealed-byte guards.

Requires the exact provisioned framework and first PC-only metadata leaf.
No Android/OEM code is executed. Partial-alias tests are interval-model tests;
the other byte cases use actual DEX bytes sealed with valid SHA1/Adler fields.
"""
import copy
import json
import struct
import unittest
import zipfile

import compose_coloros_ui_removals as composer


class CompositionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dex = composer.utility()
        source = composer.PARENT / composer.PROFILES["framework"]["source"]
        if composer.digest(source) != composer.PROFILES["framework"]["sourceSha256"]:
            raise ValueError("Exact provisioned source framework required")
        with zipfile.ZipFile(source) as archive:
            cls.original = archive.read("classes6.dex")
        cls.patched = (composer.ROOT / "out/coloros-pin-metadata-leaf/classes6.pin-metadata-leaf.dex").read_bytes()
        cls.location, _ = cls.dex.locate(cls.original)

    def test_real_leaf_roundtrip(self):
        output, edits = composer.combine_dex(self.original, [("metadata", self.patched)], self.dex)
        self.assertEqual(output, self.patched)
        self.assertTrue(edits)

    def test_same_method_disjoint_real_byte_edits_rejected(self):
        other = bytearray(self.original)
        # Original PC52 is const/4 v0,1. This remains a valid const instruction
        # but overlaps method ownership, even though PC52 is outside PC38..51.
        offset = self.location["instructionsOffset"] + 2 * 52
        self.assertEqual(other[offset:offset + 2], b"\x12\x10")
        other[offset + 1] = 0
        other = self.dex.seal(other)
        self.dex.header(other)
        with self.assertRaisesRegex(ValueError, "same encoded method"):
            composer.combine_dex(self.original, [("metadata", self.patched), ("other", other)], self.dex)

    def test_noninstruction_real_byte_edit_rejected(self):
        other = bytearray(self.original)
        # Change the target's code-item register count, not its instructions.
        offset = self.location["codeOffset"]
        struct.pack_into("<H", other, offset, self.location["registers"] + 1)
        other = self.dex.seal(other)
        self.dex.header(other)
        with self.assertRaisesRegex(ValueError, "method owner"):
            composer.combine_dex(self.original, [("header-edit", other)], self.dex)

    def test_partial_alias_interval_regression(self):
        with self.assertRaisesRegex(ValueError, "non-aliased"):
            composer.instruction_owner([(1, 100, 120), (2, 110, 130)], 108, 112)

    def test_neighbor_interval_is_not_alias(self):
        self.assertEqual(composer.instruction_owner([(1, 100, 120), (2, 120, 130)], 108, 112), 1)

    def test_invalid_dex_integrity_rejected(self):
        other = bytearray(self.patched)
        other[self.location["instructionsOffset"] + 2 * 38] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA1"):
            composer.combine_dex(self.original, [("unsealed", other)], self.dex)

    def test_condition_types_and_boolean_identity(self):
        valid = {"sourceArchiveSha256": "base", "selected": False,
                 "coldStartOnly": True, "requiredSelectionConditions": ["retain actual policy"]}
        self.assertEqual(composer.component_conditions(valid, "base"), ["retain actual policy"])
        for key, value in [("selected", 0), ("coldStartOnly", 1),
                           ("requiredSelectionConditions", "policy"),
                           ("requiredSelectionConditions", [])]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(valid)
                changed[key] = value
                with self.assertRaises(ValueError):
                    composer.component_conditions(changed, "base")

    def test_dotdot_cannot_escape_output(self):
        out_root = (composer.ROOT / "out").resolve(strict=True)
        with self.assertRaisesRegex(ValueError, "escapes"):
            composer.local_artifact(composer.ROOT / "out/../firmware", out_root)

    def test_frozen_settings_conditions_are_all_retained(self):
        name = "inventory/coloros-settings-rpmb-leaf.json"
        expected = "8d5e0dba53221b6c5720a4bac7e3c7f062ba8a0a148d3835176ffcfc84f9375e"
        self.assertEqual(composer.digest(composer.ROOT / name), expected)
        receipt = json.loads((composer.ROOT / name).read_text(encoding="utf-8"))
        retained = composer.admitted_component_conditions(
            name, expected, receipt, receipt["sourceArchiveSha256"])
        self.assertEqual(retained, receipt["selectionConditions"])
        self.assertNotIn("requiredSelectionConditions", receipt)
        for other_name, other_sha in [(name, "0" * 64), ("unreviewed.json", expected)]:
            with self.subTest(name=other_name, sha=other_sha):
                with self.assertRaises(ValueError):
                    composer.admitted_component_conditions(
                        other_name, other_sha, receipt, receipt["sourceArchiveSha256"])

    def test_ambiguous_legacy_settings_alias_is_rejected(self):
        name = "inventory/coloros-settings-rpmb-leaf.json"
        expected = "8d5e0dba53221b6c5720a4bac7e3c7f062ba8a0a148d3835176ffcfc84f9375e"
        receipt = json.loads((composer.ROOT / name).read_text(encoding="utf-8"))
        receipt["requiredSelectionConditions"] = ["shortened conditions"]
        with self.assertRaisesRegex(ValueError, "unexpected condition alias"):
            composer.admitted_component_conditions(
                name, expected, receipt, receipt["sourceArchiveSha256"])


if __name__ == "__main__":
    unittest.main()
