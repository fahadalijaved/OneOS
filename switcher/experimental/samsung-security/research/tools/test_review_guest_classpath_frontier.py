import unittest

from check_guest_classpath_selection import BOOT, BOOT_SUFFIX, ENUM, SERVER_SUFFIX
from review_guest_classpath_frontier import expected_exports, fragment_matches, scenarios


class FragmentMatchesTest(unittest.TestCase):
    def test_wildcard_is_one_visible_direct_component(self):
        stable = "/apex/com.android.art" + BOOT_SUFFIX
        paths = [
            "/apex/com.android.art/nested" + BOOT_SUFFIX,
            "/apex/.hidden" + BOOT_SUFFIX,
            "/apex/" + BOOT_SUFFIX,
            "/apex/.." + BOOT_SUFFIX,
            "/other/apex/com.android.art" + BOOT_SUFFIX,
            "/apex/com.android.art" + SERVER_SUFFIX,
            stable + ".bak",
            stable,
        ]
        self.assertEqual(fragment_matches(paths, "/apex/*", BOOT_SUFFIX), [stable])

    def test_numeric_versions_are_skipped_only_at_the_end(self):
        names = ["x@2a", "x@001", "x@+2", "x@2@001", "x@2@a", "x@0", "x@", "x"]
        paths = ["/apex/" + name + BOOT_SUFFIX for name in names]
        expected = ["/apex/" + name + BOOT_SUFFIX for name in ("x", "x@+2", "x@", "x@2@a", "x@2a")]
        self.assertEqual(fragment_matches(paths, "/apex/*", BOOT_SUFFIX), expected)

    def test_ascii_sort_is_lexical_and_case_sensitive(self):
        paths = ["/apex/" + name + BOOT_SUFFIX for name in ("a2", "a", "a10", "Z", "B")]
        expected = ["/apex/" + name + BOOT_SUFFIX for name in ("B", "Z", "a", "a10", "a2")]
        self.assertEqual(fragment_matches(paths, "/apex/*", BOOT_SUFFIX), expected)

    def test_literal_matches_only_its_exact_existing_fragment(self):
        fixed = "/system" + BOOT_SUFFIX
        paths = ["/system/nested" + BOOT_SUFFIX, "/system" + SERVER_SUFFIX, fixed]
        self.assertEqual(fragment_matches(paths, "/system", BOOT_SUFFIX), [fixed])
        self.assertEqual(fragment_matches(paths[:-1], "/system", BOOT_SUFFIX), [])

    def test_art_fixed_fragment_precedes_system_and_is_not_repeated(self):
        boot = BOOT[0]
        roots = ("/apex/com.android.z", "/system", "/apex/com.android.art", "/apex/com.android.a")
        fragments, jars = [], {}
        for root in roots:
            jar = root + "/javalib/fixture.jar"
            jars[jar] = {}
            fragments.append({
                "path": root + BOOT_SUFFIX,
                "orderedGroups": {
                    boot: [{"ordinal": 0, "path": jar, "classpathRaw": ENUM[boot], "minSdkRaw": "", "maxSdkRaw": ""}],
                    BOOT[1]: [],
                },
            })
        expected_roots = ("/apex/com.android.art", "/system", "/apex/com.android.a", "/apex/com.android.z")
        result = scenarios(fragments, jars, 37)
        self.assertEqual(result["relativeFragmentOrder"]["bootclasspath.pb"],
                         [root + BOOT_SUFFIX for root in expected_roots])
        self.assertEqual([row["path"] for row in result["includedRows"][boot]],
                         [root + "/javalib/fixture.jar" for root in expected_roots])
        self.assertEqual(result["counts"][boot], 4)

    def test_rejects_cross_group_duplicate_ordinal_and_foreign_jar(self):
        root = "/apex/com.android.art"
        for other_root, ordinal in ((root, 0), ("/apex/com.android.art.foreign", 1)):
            with self.subTest(other_root=other_root, ordinal=ordinal):
                jars = (root + "/javalib/first.jar", other_root + "/javalib/second.jar")
                groups = {key: [{"ordinal": index, "path": jar, "classpathRaw": ENUM[key],
                                 "minSdkRaw": "", "maxSdkRaw": ""}]
                          for key, index, jar in zip(BOOT, (0, ordinal), jars)}
                fragments = [{"path": root + BOOT_SUFFIX, "orderedGroups": groups}]
                with self.assertRaises(ValueError):
                    scenarios(fragments, dict.fromkeys(jars), 37)

    def test_tagged_fragment_uses_stable_jar_origin(self):
        boot = BOOT[0]
        jar = '/apex/com.android.art/javalib/core.jar'
        path = '/apex/com.android.art@tag' + BOOT_SUFFIX
        entry = {'ordinal': 0, 'path': jar, 'classpathRaw': ENUM[boot], 'minSdkRaw': '', 'maxSdkRaw': ''}
        fragments = [{'path': path, 'orderedGroups': {boot: [entry], BOOT[1]: []}}]
        self.assertEqual(scenarios(fragments, {jar: {}}, 37)['counts'][boot], 1)
        for field in ('fragment', 'result'):
            with self.subTest(field=field):
                fragments[0]['orderedGroups'][boot] = [{**entry, field: 'forged'}]
                with self.assertRaises(ValueError):
                    scenarios(fragments, {jar: {}}, 37)


class ExpectedExportsTest(unittest.TestCase):
    def test_fixed_key_order_and_jar_order_with_empty_values(self):
        scenario = {"includedRows": {
            "STANDALONE_SYSTEMSERVER_JARS": [],
            "SYSTEMSERVERCLASSPATH": [{"path": "/system/framework/services.jar"}],
            "DEX2OATBOOTCLASSPATH": [],
            "BOOTCLASSPATH": [{"path": "/apex/art/javalib/z.jar"}, {"path": "/system/framework/a.jar"}],
        }}
        self.assertEqual(expected_exports(scenario), (
            b"export BOOTCLASSPATH /apex/art/javalib/z.jar:/system/framework/a.jar\n"
            b"export DEX2OATBOOTCLASSPATH \n"
            b"export SYSTEMSERVERCLASSPATH /system/framework/services.jar\n"
            b"export STANDALONE_SYSTEMSERVER_JARS \n"
        ))


if __name__ == "__main__":
    unittest.main()
