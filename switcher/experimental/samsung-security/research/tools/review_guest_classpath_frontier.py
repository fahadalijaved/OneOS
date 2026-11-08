"""Evaluate the known donor classpath candidates without selecting an APEX view."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from audit_samsung_boot_classpath_cohort import fragment
from check_guest_classpath_selection import ENUM, PATTERNS, ROOT, filter_row, read_held, require


BASE = ('out/guest-classpath-inputs/receipt.json', 28361,
        '9f4a847728ece4f2b31652497991eda4d59fe1559b88feeafefd0396fcaba7a4')
SELECTION = ('out/guest-classpath-selection/receipt.json', 42906,
             '38fb09fdf184b9edbad2b1846a18d706ed09a4ccf0ef2c567b1fbf3f0fff5acb')
GLOB = ('out/guest-classpath-selection/donor-glob-order.json', 3325,
        '0e9649cc40d7aca92b25e6f3069aed637f86d5cc3ce8ace4cbc697326ab26bf0')
FRONTIER = ('out/guest-tree-apex-inputs/actual-source-check.json', 45786,
            'f090a965b2013c0dfa5b38b40edc722bbd8ee215de3676d255ed2b22a4da53bc')
EXTENDED = frozenset(('com.android.compos', 'com.android.npumanager',
                      'com.android.telephonycore', 'com.android.virt', 'com.android.webapp'))
NUMERIC_APEX_VERSION = re.compile(r'[^/]+@[0-9]+')
APEX_ORIGIN = re.compile(r'(/apex/[^@/]+)(?:@[^@/]+)?/')


def pinned(path, size, digest):
    data = read_held(ROOT / path, size)
    require(len(data) == size and sha256(data).hexdigest() == digest, 'Held input differs: ' + path)
    return data


def artifact(row, limit):
    require(type(row['bytes']) is int and 0 < row['bytes'] <= limit, 'Artifact extent exceeds bound')
    return pinned(row['path'], row['bytes'], row['sha256'])


def fragment_matches(paths, pattern, suffix):
    if pattern != '/apex/*':
        path = pattern + suffix
        return [path] if path in paths else []

    matches = []
    for path in paths:
        if not path.startswith('/apex/') or not path.endswith(suffix):
            continue
        module = path[len('/apex/'):-len(suffix)]
        if not module or '/' in module or module.startswith('.') or NUMERIC_APEX_VERSION.fullmatch(module):
            continue
        matches.append(path)
    return sorted(matches, key=lambda path: path.encode('ascii'))


def scenarios(fragments, jars, sdk):
    require(len(fragments) == len({row['path'] for row in fragments}), 'Duplicate fragment path')
    by_path = {row['path']: row['orderedGroups'] for row in fragments}
    visited = set()
    references = set()
    order, included, excluded = {}, {key: [] for key in ENUM}, {key: [] for key in ENUM}
    for keys, patterns, suffix in PATTERNS:
        name = suffix.rsplit('/', 1)[1]
        order[name] = []
        for pattern in patterns:
            for path in fragment_matches(by_path, pattern, suffix):
                if path in visited:
                    continue
                groups = by_path[path]
                require(set(groups) == set(keys), 'Wrong classpath fragment categories')
                ordinals = [row['ordinal'] for rows in groups.values() for row in rows]
                require(all(type(ordinal) is int for ordinal in ordinals)
                        and sorted(ordinals) == list(range(len(ordinals))), 'Incomplete or duplicate protobuf ordinals')
                module_prefix = None
                if path.startswith('/apex/'):
                    origin = APEX_ORIGIN.match(path)
                    require(origin is not None, 'Unsupported APEX fragment origin')
                    module_prefix = origin[1] + '/'
                visited.add(path)
                order[name].append(path)
                for key, rows in groups.items():
                    ordinals = [entry['ordinal'] for entry in rows]
                    require(ordinals == sorted(ordinals), 'Protobuf ordinal order changed')
                    for entry in rows:
                        jar = entry['path']
                        require(module_prefix is None or jar.startswith(module_prefix), 'Foreign APEX JAR in fragment')
                        require('fragment' not in entry and 'result' not in entry, 'Entry overlaps derived metadata')
                        require(jar in jars and entry['classpathRaw'] == ENUM[key]
                                and (key, jar) not in references, 'Jar identity or classpath category differs')
                        references.add((key, jar))
                        result = filter_row(entry, sdk)
                        bucket = included if result == 'INCLUDED' else excluded
                        bucket[key].append({'fragment': path, 'result': result, **entry})
    require(visited == set(by_path), 'A held fragment was omitted')
    return {'sdk': sdk, 'codename': 'REL', 'counts': {key: len(rows) for key, rows in included.items()},
            'relativeFragmentOrder': order, 'includedRows': included, 'excludedRows': excluded}


def expected_exports(scenario):
    lines = []
    for key in ENUM:
        paths = ':'.join(row['path'] for row in scenario['includedRows'][key])
        lines.append(f'export {key} {paths}\n')
    return ''.join(lines).encode('ascii')


def derive():
    base, selection, glob, frontier = (json.loads(pinned(*pin)) for pin in (BASE, SELECTION, GLOB, FRONTIER))
    require(base['complete'] is False and frontier['runtimeApexInfoList'] is None
            and glob['effectiveRuntimePathOrder'] is None and glob['baseReceiptSha256'] == SELECTION[2]
            and glob['flags'] == 8 and glob['targetExecuted'] is False, 'Unexpected static evidence profile')
    libc = artifact(glob['donorLibc'], 2 * 1024 * 1024)
    for row in glob['donorLibcAnchors']:
        offset, raw = int(row['pc'], 16), bytes.fromhex(row['bytes'])
        require(raw and libc[offset:offset + len(raw)] == raw, 'Held glob instruction differs')

    jars = dict(base['heldJarObjects'])
    fragments = list(base['fragments'])
    candidates = frontier['candidates']
    require(set(candidates) == EXTENDED and not (EXTENDED & base['heldModuleCandidates'].keys()),
            'Unexpected extended stable module set')
    for module, candidate in candidates.items():
        root = '/apex/' + module
        require(candidate['proposedTreeRoot'] == root and candidate['activeAliasAdmitted'] is False,
                'Extended input must remain an unselected stable candidate')
        for row in candidate['classpathFragments']:
            proof, entry = row['fragment'], row['entry']
            name = proof['path'].rsplit('/', 1)[1]
            keys = next((keys for keys, _, suffix in PATTERNS if suffix.endswith('/' + name)), ())
            key = next((key for key in keys if ENUM[key] == entry['classpathRaw']), None)
            jar = entry['path']
            require(key is not None and jar.startswith(root + '/javalib/') and jar not in jars
                    and proof['path'].endswith('/files/etc/classpaths/' + name)
                    and row['jar']['path'].endswith('/files/' + jar.removeprefix(root + '/')),
                    'Extended fragment or jar does not belong to the exact module')
            require(fragment(artifact(proof, 8192)) == [entry], 'Extended fragment entry differs')
            artifact(row['jar'], 16 * 1024 * 1024)
            jars[jar] = row['jar']
            fragments.append({'path': root + '/etc/classpaths/' + name,
                              'orderedGroups': {k: [entry] if k == key else [] for k in keys}})
    require(len(fragments) == 12 and len(jars) == 36, 'Unexpected number of held inputs')

    releases = {}
    for sdk, prior_key in ((37, 'donorDeclarationScenario'), (36, 'counterfactualSdk36Scenario')):
        require(scenarios(base['fragments'], base['heldJarObjects'], sdk) == selection[prior_key],
                'Five-fragment predecessor did not reproduce')
        releases[str(sdk)] = scenarios(fragments, jars, sdk)
    return {'schema': 'guest-classpath-frontier-scenario/v1', 'status': 'HELD_NINE_MODULE_SCENARIO_ONLY',
            'inputs': [{'path': path, 'bytes': size, 'sha256': digest} for path, size, digest in
                       (BASE, SELECTION, GLOB, FRONTIER)],
            'modules': sorted(set(base['heldModuleCandidates']) | EXTENDED), 'fragmentCount': len(fragments),
            'distinctJarCount': len(jars), 'releaseScenarios': releases,
            'activeAliasesVerified': False, 'runtimeClasspath': None, 'exportedEnvironment': None,
            'targetExecuted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-exports', type=Path, help='Compare an export file as data with the held scenario')
    parser.add_argument('--sdk', choices=('36', '37'), default='37', help='Held REL scenario for --check-exports')
    args = parser.parse_args()
    try:
        receipt = derive()
        if args.check_exports is None:
            print(json.dumps(receipt, indent=2))
            return
        expected = expected_exports(receipt['releaseScenarios'][args.sdk])
        raw = read_held(args.check_exports, len(expected))
        require(raw == expected, 'Export bytes differ from the held classpath scenario')
        print(json.dumps({'status': 'MATCHES_HELD_SCENARIO_ONLY', 'sdk': int(args.sdk),
                          'sha256': sha256(raw).hexdigest(), 'bytes': len(raw), 'runtimeAdmitted': False}))
    except (OSError, ValueError) as error:
        parser.exit(2, f'Refused: {error}\n')


if __name__ == '__main__':
    main()
