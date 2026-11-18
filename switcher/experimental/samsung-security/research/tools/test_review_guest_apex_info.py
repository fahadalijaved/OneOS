import unittest
import xml.etree.ElementTree as ET

from review_guest_apex_info import (
    ACTIVATION_FIELDS, HOST_XML, ROOT, compare_active_list, parse_active_list, pinned, review_saved_examples,
)


def row(**changes):
    return {
        'moduleName': 'com.android.runtime',
        'modulePath': '/system/apex/com.android.runtime.apex',
        'preinstalledModulePath': '/system/apex/com.android.runtime.apex',
        'versionCode': '1', 'versionName': '', 'isFactory': 'true', 'isActive': 'true',
        'lastUpdateMillis': '0', 'provideSharedApexLibs': 'false', 'partition': 'SYSTEM',
        **changes,
    }


def document(*rows):
    root = ET.Element('apex-info-list')
    for attributes in rows:
        ET.SubElement(root, 'apex-info', attributes)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def observed(*rows):
    return {attributes['moduleName']: {field: attributes[field] for field in ACTIVATION_FIELDS}
            for attributes in rows}


class ApexInfoReviewTest(unittest.TestCase):
    def test_saved_examples(self):
        report = review_saved_examples()
        self.assertEqual((report['heldSamsung']['active'], report['heldSamsung']['inactive']), (58, 25))
        self.assertTrue(report['donorCandidateRejectedAsRuntimeXml'])
        self.assertFalse(report['sameMountOccurrenceVerified'])

    def test_inactive_same_name_and_version_is_allowed(self):
        active = row(modulePath='/dev/block/dm-100', isFactory='false')
        inactive = row(isActive='false')
        result = compare_active_list(document(inactive, active), observed(active))
        self.assertEqual((result['activeCount'], result['inactiveCount']), (1, 1))
        self.assertFalse(result['sameMountOccurrenceVerified'])
        self.assertIsNone(result['entryAdmission'])

    def test_duplicate_active_name_is_refused_even_with_distinct_source(self):
        raw = document(row(), row(modulePath='/dev/block/dm-100', partition='VENDOR'))
        with self.assertRaisesRegex(ValueError, 'Duplicate active APEX module'):
            parse_active_list(raw)

    def test_exact_active_set_required(self):
        actual = row()
        extra = row(moduleName='com.android.i18n', modulePath='/dev/block/dm-101')
        foreign = pinned(ROOT / HOST_XML[0], HOST_XML[1], HOST_XML[2])[0]
        for xml, inventory in ((document(actual, extra), observed(actual)),
                               (document(actual), observed(actual, extra)), (foreign, observed(actual))):
            with self.subTest(rows=len(inventory)), self.assertRaisesRegex(ValueError, 'Active module set differs'):
                compare_active_list(xml, inventory)

    def test_same_name_requires_independent_activation_fields(self):
        expected = observed(row())
        for key, replacement in (('modulePath', '/dev/block/dm-100'), ('partition', 'VENDOR'),
                                 ('preinstalledModulePath', '/vendor/apex/com.android.runtime.apex'),
                                 ('versionCode', '2'), ('isFactory', 'false'), ('provideSharedApexLibs', 'true')):
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'activation field differs'):
                compare_active_list(document(row(**{key: replacement})), expected)

    def test_refuses_ambiguous_markup_and_noncanonical_scalars(self):
        for xml in (b'<apex-info-list/>', b'<!DOCTYPE apex-info-list><apex-info-list/>',
                    b'<?probe?><apex-info-list/>', document(row(versionCode='1junk')),
                    document(row(isActive='TRUE')), document(row(modulePath='/vendor/../system/apex/runtime.apex')),
                    document(row()).replace(b'com.android.runtime', b'com&#46;android.runtime', 1),
                    document(row()).decode().encode('utf-16')):
            with self.subTest(size=len(xml)), self.assertRaises(ValueError):
                parse_active_list(xml)

    def test_refuses_unused_namespaces_and_non_xml_layout_whitespace(self):
        xml = document(row())
        for raw in (xml.replace(b'<apex-info-list>', b'<apex-info-list xmlns="">'),
                    xml.replace(b'<apex-info-list>', b'<apex-info-list xmlns:x="urn:unused">'),
                    xml.replace(b'<apex-info ', b'<apex-info xmlns:x="urn:unused" ')):
            with self.assertRaisesRegex(ValueError, 'cannot declare a namespace'):
                parse_active_list(raw)
        with self.assertRaisesRegex(ValueError, 'Unexpected APEX runtime list shape'):
            parse_active_list(xml.replace(b'<apex-info-list>', '<apex-info-list>\u00a0'.encode('utf-8')))


if __name__ == '__main__':
    unittest.main()
