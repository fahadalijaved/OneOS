"""Review legacy integrated tester Stop records for offline diagnostics."""

import argparse
import json
from pathlib import Path
import re

from check_file_stage_device_preflight import FINGERPRINT, require
from file_stage_integrated_cohort import integrated_cohort
from file_stage_stop_carrier import verify_stop_carrier
from file_stage_stop_processes import verify_stop_processes
from read_staged_file_carrier_receipt import STAGED_JOB, read_completed_stage
from review_file_stage_observation import review as review_transcript
from run_guest_tree_install_transport import ROOT, load_io, pinned


CAPTURES = ROOT / 'out/file-stage-integrated-stop-evidence'
SCHEMA = 'oneos-integrated-file-stage-stop/v1'
CONFIG = 'firmware/read-only-resume-20261106/profile/kernel_config.stdout'
CONFIG_SHA = 'a0a80528b74a6dd72cd37077bd7ec60d1291ff0a8fc6485bb073687b46a48587'
REF_FIELDS = {'savedRelativePath', 'sha256', 'recordLocator'}
HELD = 'RECORDED_STOP_EVIDENCE_HELD'


def raw_reader(io, directory):
    files = {}

    def read(ref):
        require(type(ref) is dict and ref.keys() == REF_FIELDS and all(type(v) is str for v in ref.values()),
                'Invalid raw evidence reference')
        name, digest, locator = (ref[key] for key in ('savedRelativePath', 'sha256', 'recordLocator'))
        require(re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'Invalid raw evidence digest')
        path = ROOT / name
        if (name, digest, locator) == (CONFIG, CONFIG_SHA, 'record:kernel_config'):
            require(len(pinned(io, name, digest, 48809)) == 48809, 'Kernel config evidence changed')
            return digest
        require(path.is_relative_to(directory) and path.relative_to(ROOT).as_posix() == name
                and '..' not in path.parts, 'Raw evidence must be in this capture job')
        key = name, digest
        if key not in files:
            require(len(files) < 64, 'Too many raw evidence files')
            files[key] = pinned(io, name, digest, 256 * 1024)
        data = files[key]
        if re.fullmatch(r'line:[1-9][0-9]{0,9}', locator):
            lines = data.splitlines()
            line = int(locator[5:])
            require(line <= len(lines) and lines[line - 1], 'Raw line is missing')
            return lines[line - 1].decode('ascii')
        require(re.fullmatch(r'record:[A-Za-z0-9_.-]{1,80}', locator) is not None, 'Invalid raw record locator')
        records = json.loads(data, object_pairs_hook=io['unique_object'])['records']
        return records[locator[7:]]

    return read


def refs(value):
    if type(value) is dict:
        if value.keys() == REF_FIELDS:
            yield value
        else:
            for child in value.values():
                yield from refs(child)
    elif type(value) is list:
        for child in value:
            yield from refs(child)


def row_without_ref(row):
    return {key: value for key, value in row.items() if key != 'rawRef'}


def process_birth_line(mode, birth):
    ns = birth['pidNamespace']
    if ns is None:
        device, inode = 0, 0
    else:
        major, minor, inode = ns['deviceMajor'], ns['deviceMinor'], ns['inode']
        device = (minor & 0xff) | ((major & 0xfff) << 8) | ((minor & ~0xff) << 12) | ((major & ~0xfff) << 32)
    return f"ONEOS_STOP_PROC_V1 {mode} LIVE {birth['pid']} {birth['startTicks']} {device} {inode}"


def verify_record(doc, cohort, publication, read):
    require(type(doc) is dict and doc.keys() == {'schema', 'transcriptRef', 'terminal', 'processes', 'carrier'}
            and doc['schema'] == SCHEMA, 'Unexpected Stop record envelope')
    transcript = read(doc['transcriptRef'])
    ui = review_transcript(transcript, cohort)
    require(ui['status'] == 'ORDERED_UI_TRANSCRIPT_REQUIRES_DEVICE_READBACK', 'Stop transcript is incomplete')
    final = transcript['observations'][-1]
    attempt = final['attempt']
    terminal = doc['terminal']
    require(type(terminal) is dict and terminal.keys() == {'elapsedUpperMs', 'rawRef'}
            and type(terminal['elapsedUpperMs']) is int and terminal['elapsedUpperMs'] >= final['elapsedMs'],
            'Invalid terminal boottime bound')
    require(read(terminal['rawRef']) == {'elapsedUpperMs': terminal['elapsedUpperMs'], 'attempt': attempt,
                                       'lines': final['lines']}, 'Raw terminal sample differs')
    processes, carrier = doc['processes'], doc['carrier']
    context = verify_stop_processes(processes, attempt=attempt, terminal_elapsed_ms=terminal['elapsedUpperMs'])
    prior = processes['preStop']
    proc_view = prior['context']['procView']
    global_view = proc_view['pidNamespace'].get('mode') == 'global-no-config-pid-ns'
    require(prior['context']['buildFingerprint'] == FINGERPRINT, 'Process evidence build differs')
    require(carrier['publication'] == publication, 'Carrier differs from the verified staging witness')
    verify_stop_carrier(carrier, attempt=attempt, context=context | {'globalPidView': global_view})
    stop = next(event['elapsedMs'] for event in transcript['observations'] if event['event'] == 'stop_confirmed')
    require(prior['elapsedMs'] < stop and carrier['before']['endElapsedMs'] < stop
            and carrier['continuity']['ownerBirth'] == prior['context']['reader']['birth'],
            'Pre-Stop process or carrier holder differs from the admitted occurrence')
    if global_view:
        require(read(proc_view['pidNamespace']['configRawRef']) == CONFIG_SHA, 'Global PID view lacks the pinned config')
    mode = 'PINNED_GLOBAL' if global_view else 'PID_NAMESPACE'
    for role in ('controller', 'child'):
        entry = prior[role]
        require(read(entry['rawRef']) == process_birth_line(mode, entry['birth']), 'Raw process birth differs')
    for phase in ('postStart', 'postEnd'):
        for probe in processes[phase]['probes'].values():
            require(read(probe['rawRef']) == f"ONEOS_STOP_PROC_V1 {mode} DIRECT_ENOENT {probe['pid']}",
                    'Raw process lookup differs from the direct ENOENT record')
    for phase in ('before', 'after'):
        window = carrier[phase]
        measurement = window['measurement']
        require(read(measurement['rawRef']) == row_without_ref(measurement), 'Raw fs-verity measurement differs')
        require(read(window['rawRef']) == row_without_ref(window), 'Raw descriptor window differs')
    continuity = carrier['continuity']
    require(read(continuity['rawRef']) == row_without_ref(continuity), 'Raw descriptor lifecycle differs')
    for reference in refs(doc):
        read(reference)
    # V1 probe lines omit lookup time and reader context. The remaining v1
    # references have no defined raw format binding those normalized claims.
    return {'status': HELD, 'reason': 'V1_PROCESS_TIMING_AND_VISIBILITY_UNBOUND',
            'mayExecute': False, 'deviceAcceptance': False}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('capture', type=Path)
    path = cli.parse_args(argv).capture.absolute()
    try:
        require(path.parent.parent == CAPTURES and path.name == 'observation.json'
                and re.fullmatch(r'r-[0-9a-f]{8}', path.parent.name), 'Expected a fixed saved Stop capture path')
        io = load_io()
        with io['checked_input'](path, max_size=65536) as stream:
            doc = json.loads(stream.read(65536), object_pairs_hook=io['unique_object'])
        _, publication = read_completed_stage(ROOT / STAGED_JOB)
        result = verify_record(doc, integrated_cohort(), publication, raw_reader(io, path.parent))
    except (KeyError, OSError, RecursionError, TypeError, ValueError):
        result = {'status': HELD, 'mayExecute': False, 'deviceAcceptance': False}
    print(json.dumps(result, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
