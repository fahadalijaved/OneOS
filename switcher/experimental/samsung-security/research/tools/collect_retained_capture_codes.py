"""Privacy-bounded, read-only snapshots for the exact retained-capture v2 test.

Default/--help/--fixtures make no phone calls. --collect requires a separate
root-coordinated admission file under this project's out/ directory.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import runpy
import struct
import uuid

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'tools/collect_security_profile.py'
PROFILE_SHA = '1da6a75fa2301865bcf42a36c82bc99de2b7d37063696fcc21fce512a25d1fac'
ADB = ROOT.parent / 'out/toolchain/android-sdk/platform-tools/adb.exe'
ADB_SHA = 'b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f'
FORMAT_PROOF = ROOT / 'out/retained-logcat-proto-preflight/20261106T055234395228Z-4b94fa41707b468d8755380ec5ab6c6d/observation.json'
FORMAT_SHA = '81d4892abca7a41ce0f2af448cd104ddcb73f5c19e0473c2b3d3dd237cfc437d'
HELP_PROOF = ROOT / 'out/retained-logcat-readonly-format/20261106T052738684808Z-5a51855fb48e481591d123ef7aad65f4/help.txt'
HELP_SHA = '16073b898c31b84e00b02cf5783e0b5c476ada8314b7de0b4d34294a76d3d448'
PROTO_SOURCE = ROOT / 'firmware/collector-proto-framing/windows-https-9ba34df880ea4dcf896759f22acbf7af'
SOURCE_PINS = {'source.json': 'f513f1bcea987a916814b17c6fb3beaeb221aa621c6ae19102257d43fab6a3f8',
               'logcat.proto': 'd709478babea7dc534dec1bfde154f1d73bc0f72e44212ba8f34d0382b3ddabd',
               'logcat.cpp': '9b2ae4d65e2fe6e690ceb1574f128ca0ea4b9c74e4d72f5f35d2d90c2239316c'}
HISTORICAL_TOOL = ROOT / 'out/collect-retained-capture-codes/history/b94-threadtime-hold-20261106T055732682307Z-ced1d2c0b2a54104bf571bfb7530ebb3/tools/collect_retained_capture_codes.py'
HISTORICAL_SHA = 'b94a34465de8d0a59e535eefd4d9079c5271af1960d39335ac7679efebbf6256'
LIMIT = 65536
MAX_RECORDS = 128
MAX_INTERVAL_SECONDS = 120
TAG = b'OneOSRetainedCaptureV2'
# Selected primary processLogBuffer tagLen includes exactly the terminal NUL.
PROTO_TAG = TAG + b'\0'
PACKAGE = b'com.appleexploit.oneos.security.retainedcapture'
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
CODES = ('HOOK_INSTALLED', 'INSTALL_REFUSED', 'PERMIT_REFUSED', 'REGISTRY_BOUND',
         'REGISTRY_REFUSED', 'FAMILY_BOUND', 'FAMILY_REFUSED')
MESSAGES = {c.encode(): c for c in CODES}
MESSAGES.update({PACKAGE + b': ' + c.encode(): c for c in CODES})
UTC_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z')


class Refused(ValueError):
    """Fixed-code failures: never render untrusted input or command output."""


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def utc(value):
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise Refused('INPUT')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise Refused('INPUT') from None


def admission(value):
    keys = {'schema', 'serverPort', 'serial', 'newSystemServerPid', 'previousSystemServerPid',
            'systemServerStartTimeTicks', 'startUtc', 'endUtc'}
    if not isinstance(value, dict) or set(value) != keys or value['schema'] != 'retained-capture-code-admission/v1':
        raise Refused('INPUT')
    if type(value['serverPort']) is not int or value['serverPort'] != 5038:
        raise Refused('INPUT')
    serial = value['serial']
    if not isinstance(serial, str) or not re.fullmatch(r'[A-Za-z0-9\[][A-Za-z0-9_.:\[\]-]{0,159}', serial):
        raise Refused('INPUT')
    for key in ('newSystemServerPid', 'previousSystemServerPid'):
        if type(value[key]) is not int or not 1 <= value[key] <= 9999999:
            raise Refused('INPUT')
    if value['newSystemServerPid'] == value['previousSystemServerPid']:
        raise Refused('AMBIGUOUS_PID')
    ticks = value['systemServerStartTimeTicks']
    if not isinstance(ticks, str) or not re.fullmatch(r'[1-9][0-9]{0,19}', ticks):
        raise Refused('INPUT')
    start, end = utc(value['startUtc']), utc(value['endUtc'])
    if start <= EPOCH or not 0 < (end-start).total_seconds() <= MAX_INTERVAL_SECONDS:
        raise Refused('INPUT')
    return {**value, '_start': start, '_end': end}


def epoch_ns(when):
    delta = when-EPOCH
    return (delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000


def logcat_args(config):
    start = config['_start']
    # Always decimal .mmm: an integer -T token would select a line count.
    token = str(epoch_ns(start)//1000000000)+'.'+str(start.microsecond//1000).zfill(3)
    return ('shell', 'logcat', '--proto', '-b', 'main', '-d',
            '--pid='+str(config['newSystemServerPid']), '-T', token,
            '-m', '128', '-s', 'OneOSRetainedCaptureV2:E')


def uint64(data, offset):
    """Canonical bounded protobuf uint64; no overlong or overflowing encodings."""
    value = 0
    for index in range(10):
        if offset >= len(data):
            raise Refused('PROTO_TRUNCATED')
        byte = data[offset]; offset += 1
        if index == 9 and byte > 1:
            raise Refused('PROTO_PROFILE')
        value |= (byte & 127) << (7*index)
        if byte < 128:
            if index and byte == 0:
                raise Refused('PROTO_PROFILE')
            return value, offset
    raise Refused('PROTO_PROFILE')


def decode_entry(data):
    # Proto3 absent scalar/bytes fields have the declared zero/empty semantics.
    # Only an omitted nsec can participate in a valid selected diagnostic entry;
    # zero PID/UID/priority/tag/message never becomes successful admission.
    fields = {n: 0 for n in range(1, 7)}
    fields.update({7: b'', 8: b''})
    seen = set(); offset = 0
    while offset < len(data):
        key, offset = uint64(data, offset)
        field, wire = key >> 3, key & 7
        if field not in range(1, 10) or field in seen or wire != (0 if field <= 6 else 2):
            raise Refused('PROTO_PROFILE')
        seen.add(field)
        if wire == 0:
            fields[field], offset = uint64(data, offset)
        else:
            length, offset = uint64(data, offset)
            if length > len(data)-offset:
                raise Refused('PROTO_TRUNCATED')
            if field != 9:
                fields[field] = data[offset:offset+length]
            else:
                # Validate the declared string type without keeping its value.
                try:
                    data[offset:offset+length].decode('utf-8', 'strict')
                except UnicodeError:
                    raise Refused('PROTO_PROFILE') from None
            # Known optional process_name is never kept or published.
            offset += length
    if fields[2] >= 1000000000:
        raise Refused('PROTO_PROFILE')
    return fields


def decode_stream(data):
    if not isinstance(data, bytes) or len(data) > LIMIT:
        raise Refused('OUTPUT_LIMIT')
    entries = []; offset = 0
    while offset < len(data):
        if len(entries) == MAX_RECORDS:
            raise Refused('RECORD_LIMIT')
        if len(data)-offset < 8:
            raise Refused('PROTO_TRUNCATED')
        length = struct.unpack_from('<Q', data, offset)[0]; offset += 8
        if not 0 < length <= LIMIT-8:
            raise Refused('PROTO_PROFILE')
        if length > len(data)-offset:
            raise Refused('PROTO_TRUNCATED')
        entries.append(decode_entry(data[offset:offset+length])); offset += length
    return entries


def parse_snapshot(data, config):
    """Validate the COMPLETE framed stream before considering any records."""
    entries = decode_stream(data)
    records = []
    discarded = Counter()
    for entry in entries:
        pid, tid = entry[5], entry[6]
        if pid != config['newSystemServerPid']:
            discarded['wrong_pid'] += 1
            continue
        if not 1 <= tid <= 9999999 or entry[3] != 6 or entry[4] != 1000 or entry[7] != PROTO_TAG:
            discarded['wrong_metadata_or_tag'] += 1
            continue
        code = MESSAGES.get(entry[8])
        if code is None:
            discarded['unknown_message'] += 1
            continue
        when_ns = entry[1]*1000000000+entry[2]
        if not epoch_ns(config['_start']) <= when_ns <= epoch_ns(config['_end']):
            discarded['outside_interval'] += 1
            continue
        seconds = EPOCH+timedelta(seconds=entry[1])
        stamp = seconds.strftime('%Y-%m-%dT%H:%M:%S')+'.'+str(entry[2]).zfill(9)+'Z'
        records.append({'timestamp': stamp, 'pid': pid, 'tid': tid, 'code': code})
    return {'status': 'CODES_OBSERVED_NOT_AUTHORITY' if records else 'INCONCLUSIVE_NO_ADMITTED_CODES',
            'records': records, 'discardCounts': dict(discarded), 'runtimeOrSecurityAccepted': False}


def new_work(stem):
    base = ROOT / 'out' / stem
    nested_out = (ROOT/'out').resolve()
    if not nested_out.is_relative_to(ROOT.resolve()) or not base.resolve().is_relative_to(nested_out):
        raise Refused('PC_OUTPUT_PATH')
    base.mkdir(parents=True, exist_ok=True)
    work = base / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    return work


def collect(path):
    requested = Path(path)
    if requested.is_symlink():
        raise Refused('INPUT')
    resolved = requested.resolve(strict=True)
    nested_out = (ROOT/'out').resolve()
    if not nested_out.is_relative_to(ROOT.resolve()) or not resolved.is_relative_to(nested_out) or not resolved.is_file() or resolved.stat().st_size > 8192:
        raise Refused('INPUT')
    with resolved.open('rb') as stream:
        raw = stream.read(8193)
    if len(raw) > 8192:
        raise Refused('INPUT')
    try:
        config = admission(json.loads(raw))
    except (UnicodeError, json.JSONDecodeError):
        raise Refused('INPUT') from None
    pins = {PROFILE: PROFILE_SHA, ADB: ADB_SHA, FORMAT_PROOF: FORMAT_SHA, HELP_PROOF: HELP_SHA}
    pins.update({PROTO_SOURCE/name: expected for name, expected in SOURCE_PINS.items()})
    for p, expected in pins.items():
        if digest(p) != expected:
            raise Refused('PC_PIN')
    # This import executes authored function definitions only. The helper is
    # called ONLY in explicit --collect, selecting exactly the root-given serial.
    helper = runpy.run_path(str(PROFILE))
    result = {'status': 'UNRESOLVED_READ', 'records': [], 'discardCounts': {}, 'runtimeOrSecurityAccepted': False}
    try:
        data = helper['adb'](['-s', config['serial'], *logcat_args(config)], LIMIT)
        result = parse_snapshot(data, config)
    except Refused:
        result = {'status': 'INCONCLUSIVE_INVALID_OR_INCOMPLETE_PROTO', 'records': [],
                  'discardCounts': {}, 'runtimeOrSecurityAccepted': False}
    except Exception:
        # No exception string, stderr, raw stdout, message prefix or line is kept.
        pass
    for p, expected in pins.items():
        if digest(p) != expected:
            raise Refused('PC_PIN')
    with resolved.open('rb') as stream:
        after = stream.read(8193)
    if after != raw:
        raise Refused('INPUT_MOVED')
    result.update(schema='retained-capture-code-snapshot/v1', admissionSha256=hashlib.sha256(raw).hexdigest(),
                  phoneOperation='ONE_READ_ONLY_PROTO_LOGCAT_SNAPSHOT', timeoutSeconds=20, outputByteLimit=LIMIT,
                  rawOutputStored=False, rawErrorsStored=False, phoneModified=False,
                  processStartIdentity='Root-supplied external precondition; collector makes no identity query',
                  sourcePins={'helper': PROFILE_SHA, 'adb': ADB_SHA, 'formatProof': FORMAT_SHA,
                              'formatHelp': HELP_SHA, 'framingSource': SOURCE_PINS['source.json']})
    encoded = json.dumps(result, indent=2)+'\n'
    if len(encoded.encode('utf-8')) > LIMIT:
        raise Refused('OUTPUT_LIMIT')
    work = new_work('retained-capture-code-snapshots')
    (work/'snapshot.json').write_text(encoded)
    print(json.dumps({'status': result['status'], 'accepted': len(result['records']),
                      'snapshot': str((work/'snapshot.json').relative_to(ROOT))}))


def fixtures():
    config = admission({'schema': 'retained-capture-code-admission/v1', 'serverPort': 5038, 'serial': 'fixture-device',
                        'newSystemServerPid': 30001, 'previousSystemServerPid': 27202,
                        'systemServerStartTimeTicks': '123456', 'startUtc': '2026-11-06T05:00:00.000Z',
                        'endUtc': '2026-11-06T05:02:00.000Z'})
    def varint(value):
        result = bytearray()
        while value >= 128:
            result.append((value & 127) | 128); value >>= 7
        result.append(value)
        return bytes(result)
    def frame(body):
        return struct.pack('<Q', len(body))+body
    def body(message, *, pid=30001, tag=PROTO_TAG, second=None, nsec=123000000,
             priority=6, uid=1000, tid=30001, process_name=None):
        if second is None:
            second = epoch_ns(utc('2026-11-06T05:01:00.000Z'))//1000000000
        fields = {1:second, 3:priority, 4:uid, 5:pid, 6:tid, 7:tag, 8:message}
        if nsec is not None:
            fields[2] = nsec
        if process_name is not None:
            fields[9] = process_name
        result = bytearray()
        for key, value in sorted(fields.items()):
            wire = 0 if key <= 6 else 2
            result.extend(varint((key << 3) | wire))
            if wire == 0:
                result.extend(varint(value))
            else:
                result.extend(varint(len(value))); result.extend(value)
        return bytes(result)
    def entry(message, **values):
        return frame(body(message, **values))
    checks = []
    def check(name, condition):
        if not condition:
            raise Refused('FIXTURE_FAILURE')
        checks.append(name)
    valid = b''.join(entry(c.encode())+entry(PACKAGE+b': '+c.encode()) for c in CODES)
    got = parse_snapshot(valid, config)
    check('all_seven_exact_codes_and_exact_package_prefix', len(got['records']) == 14)
    check('only_four_record_fields', all(set(x) == {'timestamp','pid','tid','code'} for x in got['records']))
    zero = parse_snapshot(entry(b'FAMILY_BOUND', nsec=None), config)
    check('proto3_omitted_nsec_means_real_zero', zero['records'][0]['timestamp'].endswith('.000000000Z'))
    check('nanoseconds_preserved', got['records'][0]['timestamp'].endswith('.123000000Z'))
    check('decimal_epoch_not_tail_count', re.fullmatch(r'[1-9][0-9]*\.[0-9]{3}', logcat_args(config)[8]) is not None)
    check('bounded_pid_proto_command_only', logcat_args(config)[6] == '--pid=30001' and '-B' not in logcat_args(config)
          and '-t' not in logcat_args(config) and logcat_args(config)[9:11] == ('-m','128'))
    secret = b'ARTIFICIAL_PRIVATE_PAYLOAD_NEVER_PERSIST'
    prefix = b'2026-11-06 05:01:00.123  30001  30001 E OneOSRetainedCaptureV2: '
    repeated_prefix_text = prefix+b'unknown\n'+prefix+b'FAMILY_BOUND\n'
    if digest(HISTORICAL_TOOL) != HISTORICAL_SHA:
        raise Refused('PC_PIN')
    old = runpy.run_path(str(HISTORICAL_TOOL))
    old_result = old['parse_snapshot'](repeated_prefix_text, config)
    check('CC01_real_repeat_prefix_old_parser_admits', len(old_result['records']) == 1
          and old_result['records'][0]['code'] == 'FAMILY_BOUND')
    check('CC01_whole_proto_message_rejects_embedded_code', not parse_snapshot(entry(b'unknown\nFAMILY_BOUND'), config)['records'])
    check('optional_process_name_not_retained', secret.decode() not in json.dumps(parse_snapshot(
        entry(b'FAMILY_BOUND', process_name=secret), config)))
    second = epoch_ns(utc('2026-11-06T05:02:00.000Z'))//1000000000
    negatives = {
        'previous_pid': entry(b'FAMILY_BOUND', pid=27202),
        'other_pid': entry(b'FAMILY_BOUND', pid=30002),
        'tag_prefix_lookalike': entry(b'FAMILY_BOUND', tag=b'Evil'+PROTO_TAG),
        'tag_suffix_lookalike': entry(b'FAMILY_BOUND', tag=PROTO_TAG+b'Evil'),
        'missing_source_terminal_tag_nul': entry(b'FAMILY_BOUND', tag=TAG),
        'double_tag_nul_not_stripped': entry(b'FAMILY_BOUND', tag=PROTO_TAG+b'\0'),
        'message_terminal_nul_not_stripped': entry(b'FAMILY_BOUND\0'),
        'embedded_code': entry(secret+b' FAMILY_BOUND'),
        'trailing_private_payload': entry(b'FAMILY_BOUND '+secret),
        'wrong_module_prefix': entry(b'other.package: FAMILY_BOUND'),
        'wrong_priority': entry(b'FAMILY_BOUND', priority=4),
        'wrong_uid': entry(b'FAMILY_BOUND', uid=0),
        'after_interval_by_one_nsec': entry(b'FAMILY_BOUND', second=second, nsec=1),
        'before_interval': entry(b'FAMILY_BOUND', second=second-121, nsec=999999999),
        'zero_tid': entry(b'FAMILY_BOUND', tid=0),
        'oversized_tid': entry(b'FAMILY_BOUND', tid=2**64-1),
        'multiline_throwable_and_secret': entry(b'java.lang.Exception: '+secret+b'\nFAMILY_BOUND'),
        'non_utf8_unknown': entry(b'\xff '+secret),
        'embedded_carriage_return': entry(b'FAMILY_BOUND\r'+secret),
        'embedded_vertical_tab': entry(b'FAMILY_BOUND\v'+secret),
        'embedded_complete_fake_text_header': entry(b'unknown\n'+prefix+b'FAMILY_BOUND'),
    }
    for name, data in negatives.items():
        value = parse_snapshot(data, config)
        check(name, not value['records'] and secret.decode() not in json.dumps(value))
    malformed = {
        'byte_bound': b'x'*(LIMIT+1),
        'record_bound': entry(b'FAMILY_BOUND')*129,
        'text_format_not_reinterpreted': repeated_prefix_text,
        'truncated_size_header': b'\x01'*7,
        'truncated_frame_body': entry(b'FAMILY_BOUND')[:-1],
        'zero_frame_size': b'\0'*8,
        'oversized_frame_size': struct.pack('<Q', LIMIT),
        'truncated_varint': frame(b'\x08\x80'),
        'overflow_varint': frame(b'\x08'+b'\x80'*10+b'\x01'),
        'noncanonical_varint': frame(b'\x08\x80\x00'),
        'unknown_schema_field': frame(body(b'FAMILY_BOUND')+b'\x50\x01'),
        'wrong_wire_type': frame(b'\x3d\x00\x00\x00\x00'),
        'duplicate_pid_field': frame(body(b'FAMILY_BOUND')+varint(5 << 3)+varint(30001)),
        'invalid_nsec': entry(b'FAMILY_BOUND', nsec=1000000000),
        'valid_then_truncated_no_prefix_publication': entry(b'FAMILY_BOUND')+b'\x01',
        'valid_then_unknown_schema_no_prefix_publication': entry(b'FAMILY_BOUND')+frame(b'\x50\x01'),
        'invalid_optional_string_utf8': entry(b'FAMILY_BOUND', process_name=b'\xff'),
    }
    for name, data in malformed.items():
        try:
            parse_snapshot(data, config)
        except Refused:
            check(name, True)
        else:
            check(name, False)
    for name, changes in [('same_old_and_new_pid', {'previousSystemServerPid':30001}),
                          ('non_utc_interval', {'startUtc':'2026-11-06T05:00:00.000+00:00'}),
                          ('overlong_interval', {'endUtc':'2026-11-06T05:02:00.001Z'}),
                          ('foreign_server', {'serverPort':5037}), ('shell_serial', {'serial':'device;anything'}),
                          ('zero_epoch_tail_ambiguity', {'startUtc':'1970-01-01T00:00:00.000Z', 'endUtc':'1970-01-01T00:01:00.000Z'})]:
        base = {k:v for k,v in config.items() if not k.startswith('_')}; base.update(changes)
        try:
            admission(base)
        except Refused:
            check(name, True)
        else:
            check(name, False)
    check('silence_inconclusive', parse_snapshot(b'', config)['status'] == 'INCONCLUSIVE_NO_ADMITTED_CODES')
    receipt = {'schema':'retained-capture-code-privacy-fixtures/v1', 'status':'PASS_AUTHORED_PC_FIXTURES_ONLY',
               'checks':checks, 'checkCount':len(checks), 'phoneCalls':0, 'androidOrOemExecuted':False,
               'fixtureRawLinesStored':False, 'toolSha256':digest(Path(__file__)),
               'CC01OldTextParserAdmitsSyntheticRepeatedPrefix':True, 'newWholeEntryParserRejectsIt':True,
               'historicalToolSha256':HISTORICAL_SHA}
    work = new_work('retained-capture-code-fixtures')
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'], 'checks':len(checks), 'receipt':str((work/'receipt.json').relative_to(ROOT))}))


class QuietParser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('PC_ARGUMENTS')


def main():
    parser = QuietParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--collect', action='store_true', help='Later root-coordinated ONE read-only snapshot')
    modes.add_argument('--fixtures', action='store_true', help='Run authored PC privacy/stale-PID fixtures; no phone')
    parser.add_argument('--admission', type=Path, help='Root-provided bounded admission JSON under nested out/')
    args = parser.parse_args()
    if args.collect:
        if args.admission is None:
            raise Refused('INPUT')
        collect(args.admission)
    elif args.admission is not None:
        raise Refused('PC_ARGUMENTS')
    elif args.fixtures:
        fixtures()
    else:
        print(json.dumps({'status':'PC_ONLY_NO_PHONE_CALLS', 'collectEnabled':False}))


if __name__ == '__main__':
    try:
        main()
    except Refused as error:
        print(json.dumps({'status':'REFUSED', 'reason':str(error)}))
        raise SystemExit(2)
    except Exception:
        print(json.dumps({'status':'REFUSED', 'reason':'UNRESOLVED_PC_OR_READ_ERROR'}))
        raise SystemExit(2)
