"""Check APEX XML rows against separately observed active module identities."""

from hashlib import sha256
import json
import re
import xml.etree.ElementTree as ET

from audit_guest_linkerconfig_apex_inputs import ROOT, pinned, require


HOST_XML = ('../firmware/samsung/os-mirror-20261104/metadata/apex-info.txt', 29548,
            '6c8ebe0b93c4f9147d568678fd7909d748ff17e4211eb71255fa0fc6a801e8af')
CANDIDATE_XML = ('out/guest-apex-active-inputs/r-27f937479ad7483a893a399d6f8b94eb/apex-active-inputs.candidate.xml',
                 1871, 'ab7771cd4badab76e784aab834c83c7382dc59f513405989a8298c765694454e')
ACTIVATION_FIELDS = ('moduleName', 'modulePath', 'preinstalledModulePath', 'versionCode',
                     'isFactory', 'provideSharedApexLibs', 'partition')
ROW_FIELDS = frozenset((*ACTIVATION_FIELDS, 'isActive', 'versionName', 'lastUpdateMillis'))
PARTITIONS = frozenset(('SYSTEM', 'SYSTEM_EXT', 'PRODUCT', 'VENDOR', 'ODM'))
MODULE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.+-]{0,127}')
PATH = re.compile(r'(?:/[A-Za-z0-9_.+@-]+)+')
DECIMAL = re.compile(r'0|[1-9][0-9]{0,18}')
DECLARATION = re.compile(r'''^<\?xml version=(["'])1\.0\1 encoding=(["'])(?:utf-8|UTF-8)\2\?>''')


class UnnamespacedTree(ET.TreeBuilder):
    def start_ns(self, prefix, uri):
        raise ValueError('APEX runtime XML cannot declare a namespace')


def layout_whitespace(text):
    return not (text or '').strip(' \t\r\n')


def canonical_number(value):
    return DECIMAL.fullmatch(value) is not None and int(value) <= 2**63 - 1


def parse_active_list(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 64 * 1024, 'APEX XML extent is out of bounds')
    text = raw.decode('utf-8', 'strict')
    body = DECLARATION.sub('', text, count=1)
    require(not any(markup in body for markup in ('<!', '<?', '&', '\0')) and not body.startswith('\ufeff'),
            'Unsupported APEX XML markup or encoding')
    try:
        root = ET.fromstring(body, parser=ET.XMLParser(target=UnnamespacedTree()))
    except ET.ParseError as error:
        raise ValueError('Malformed APEX XML') from error
    require(root.tag == 'apex-info-list' and not root.attrib and layout_whitespace(root.text)
            and 0 < len(root) <= 256, 'Unexpected APEX runtime list shape')
    active, module_paths = {}, set()
    for element in root:
        attrs = element.attrib
        require(element.tag == 'apex-info' and attrs.keys() == ROW_FIELDS and not len(element)
                and layout_whitespace(element.text) and layout_whitespace(element.tail), 'Invalid APEX runtime row')
        require(MODULE.fullmatch(attrs['moduleName']) is not None and attrs['partition'] in PARTITIONS,
                'Invalid APEX module name or partition')
        for name in ('modulePath', 'preinstalledModulePath'):
            path = attrs[name]
            require(len(path) <= 512 and PATH.fullmatch(path) is not None
                    and not {'.', '..'}.intersection(path.split('/')), 'Noncanonical APEX source path')
        require(attrs['modulePath'] not in module_paths, 'Repeated APEX source path')
        module_paths.add(attrs['modulePath'])
        require(all(attrs[name] in ('true', 'false') for name in ('isActive', 'isFactory', 'provideSharedApexLibs'))
                and canonical_number(attrs['versionCode']) and canonical_number(attrs['lastUpdateMillis'])
                and len(attrs['versionName']) <= 128, 'Invalid APEX row scalar')
        if attrs['isActive'] == 'true':
            name = attrs['moduleName']
            require(name not in active, 'Duplicate active APEX module')
            active[name] = {field: attrs[field] for field in ACTIVATION_FIELDS}
    require(active, 'No active APEX records')
    return active, len(root) - len(active)


def compare_active_list(raw, observed):
    """Compare content only. The caller establishes file and mount provenance."""
    active, inactive_count = parse_active_list(raw)
    require(type(observed) is dict and active.keys() == observed.keys(), 'Active module set differs from observed mounts')
    require(active == observed, 'An active APEX identity or activation field differs')
    return {'activeCount': len(active), 'inactiveCount': inactive_count, 'xmlSha256': sha256(raw).hexdigest(),
            'activeMetadataMatches': True, 'sameMountOccurrenceVerified': False, 'entryAdmission': None}


def review_saved_examples():
    host, candidate = (pinned(ROOT / path, size, digest)[0] for path, size, digest in (HOST_XML, CANDIDATE_XML))
    active, inactive = parse_active_list(host)
    require((len(active), inactive) == (58, 25), 'Unexpected held Samsung row counts')
    try:
        parse_active_list(candidate)
    except ValueError as error:
        require(str(error) == 'Unexpected APEX runtime list shape', 'Unexpected candidate refusal')
    else:
        raise ValueError('Candidate XML was incorrectly admitted as runtime XML')
    return {'status': 'HELD_XML_FORMAT_CHECKED_NO_GUEST_JOIN',
            'heldSamsung': {'active': len(active), 'inactive': inactive, 'sha256': HOST_XML[2]},
            'donorCandidateRejectedAsRuntimeXml': True, 'sameMountOccurrenceVerified': False,
            'effectiveGuestXml': None, 'generatedLinkerConfig': None, 'entryAdmission': None}


if __name__ == '__main__':
    print(json.dumps(review_saved_examples(), indent=2))
