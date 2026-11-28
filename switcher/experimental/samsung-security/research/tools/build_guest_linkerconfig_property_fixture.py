"""Build source-backed, offline linkerconfig property readback fixtures."""

import json
import struct
from uuid import uuid4

from build_guest_tree_property_areas import (
    AREA_SIZE, INITIAL_USED, MAGIC, ROOT, VERSION, add_seed, decode_area, held_definitions,
)
from check_guest_tree_materialization_plan import pin, plain, read_small, require


BASE = ROOT / 'out/guest-tree-property-areas/donor-v1'
OUT = ROOT / 'out/guest-linkerconfig-property-fixture'
PROPERTY = 'ro.debuggable'
CONTEXT = 'u:object_r:userdebug_or_eng_prop:s0'


def build():
    inputs = []

    def load(path, size, sha256):
        raw = read_small(path, size, sha256)
        require(len(raw) == size, f'Input extent changed: {path}')
        inputs.append(pin(path, raw))
        return raw

    seed = json.loads(load(BASE / 'receipt.json', 35402,
        '77aebe69b1012dd6baaa7bd2abee1fccd5d4daa4f298664c1fab3cb7fe129d38'))
    row, = [row for row in seed['unseededCriticalKeys'] if row['key'] == PROPERTY]
    require(row['context'] == CONTEXT and row['metadataType'] == 'bool' and row['storedValue'] is None,
            'Expected an unseeded donor debug boolean')

    source = '../firmware/donor/extracted/system/build.prop'
    declaration_pin = seed['pins'][source]
    # Check the actual declarations separately from the saved context lookup.
    path = ROOT.parent / 'firmware/donor/extracted/system/build.prop'
    raw = load(path, declaration_pin['bytes'], declaration_pin['sha256'])
    name = PROPERTY.encode('ascii')
    declarations = []
    for number, line in enumerate(raw.splitlines(), 1):
        key, separator, value = line.partition(b'=')
        if separator and key == name:
            declarations.append({'source': source, 'line': number, 'value': value.decode('ascii')})
    require(declarations == row['declarations'] and [item['value'] for item in declarations] == ['1', '1'],
            'Donor debug declarations changed')

    writer_source = load(ROOT / 'tools/prepare_guest_tree_property_inputs.py', 12327,
        '543ff2a0690ba38f7c22136fe96fb2093a216c86df89229e8501e992d49ccb87')
    definitions = held_definitions(writer_source, {'AreaFixture'}, {'AREA_SIZE', 'HEADER_SIZE', 'INITIAL_USED'},
        {'KEYS': (PROPERTY,), 'MAGIC': MAGIC, 'VERSION': VERSION, 'struct': struct, 'require': require})
    area = definitions['AreaFixture']()
    value = declarations[0]['value']
    add_seed(area, PROPERTY, value)
    debug = bytes(area.bytes)
    require(decode_area(debug, 0) == {PROPERTY: (value, 'short')}, 'Unexpected debug area records')

    serial_pin = seed['members']['serial.fixture.bin']
    base_serial = load(BASE / 'serial.fixture.bin', AREA_SIZE, serial_pin['sha256'])
    prior_count = len(seed['selectedInsertionOrder'])
    require(decode_area(base_serial, prior_count) == {}, 'Unexpected base serial area records')
    serial = bytearray(base_serial)
    struct.pack_into('<I', serial, 4, prior_count + 1)
    require(decode_area(serial, prior_count + 1) == {}, 'Unexpected successor serial area records')

    run = plain(OUT / ('r-' + uuid4().hex[:8]))
    run.mkdir(parents=True)
    files = {}
    for name, raw, context in (('debug.fixture.bin', debug, CONTEXT),
                               ('serial.fixture.bin', serial, 'properties_serial')):
        path = run / name
        with path.open('xb') as output:
            output.write(raw)
        require(read_small(path, AREA_SIZE) == raw, 'Written fixture changed')
        files[name] = {**pin(path, raw), 'intendedContextBasename': context}

    receipt = run / 'receipt.json'
    receipt.write_bytes((json.dumps({
        'status': 'SOURCE_BACKED_READBACK_FIXTURES_ONLY', 'inputs': inputs, 'files': files,
        'property': PROPERTY, 'declaredValue': value, 'declarations': declarations,
        'serial': prior_count + 1, 'effectiveValue': None, 'runtimeAdmitted': False,
    }, indent=2) + '\n').encode('utf-8'))
    return receipt


if __name__ == '__main__':
    print(build().relative_to(ROOT).as_posix())
