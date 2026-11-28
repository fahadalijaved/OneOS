"""Verify/extract the already-approved fixed Gradle ZIP; never execute software.

Root runs this explicit preparation step. The APK invocation is a separate step
after actual source-overlay, package-set and SDK inputs have been admitted.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import stat
import uuid
import zipfile

ROOT = Path(__file__).absolute().parent.parent
BASE = ROOT / 'out/full-apk-toolchain/preparation'
ZIP = ROOT / 'out/full-apk-toolchain/downloads/gradle-9.8.0-bin.zip'
ZIP_SHA = 'bafd5ce9cfaea0fbccfdc8439a1ac42fbd4cd9c89dc9a988228d8a2639a58e6c'
ZIP_BYTES = 151611662
TOP = 'gradle-9.8.0'
EXPECTED_ENTRIES = 723
EXPECTED_FILES = 716
EXPECTED_EXPANDED_BYTES = 170451591
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *('COM' + str(i) for i in range(1, 10)),
            *('LPT' + str(i) for i in range(1, 10))}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def contained(path):
    path = Path(path)
    path.relative_to(ROOT)
    for part in [path, *path.parents]:
        need(not part.is_symlink() and not getattr(part, 'is_junction', lambda: False)(),
             'Reparse path refused: ' + str(part))
        if part == ROOT:
            break
    path.resolve().relative_to(ROOT.resolve())
    return path


def save(path, value):
    with contained(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def profile(archive):
    entries = archive.infolist()
    need(len(entries) == EXPECTED_ENTRIES, 'Exact trusted distribution entry count')
    names = {}
    total = 0
    for entry in entries:
        name = entry.filename
        parts = PurePosixPath(name).parts
        need(name and not name.startswith('/') and '\\' not in name and ':' not in name
             and parts and parts[0] == TOP and '..' not in parts and '.' not in parts,
             'Contained distribution path')
        need(all(p and p == p.rstrip(' .') and p.split('.')[0].upper() not in RESERVED
                 for p in parts), 'Windows-safe distribution path')
        key = name.rstrip('/').casefold()
        need(key not in names, 'Case-insensitive duplicate distribution entry')
        mode = entry.external_attr >> 16
        need(not stat.S_ISLNK(mode) and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR),
             'Only regular distribution files and directories')
        need(not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED,
                                                               zipfile.ZIP_DEFLATED),
             'Unencrypted supported ZIP entry')
        need(0 <= entry.file_size <= MAX_FILE_BYTES, 'Individual distribution size bound')
        total += entry.file_size
        need(total <= MAX_EXPANDED_BYTES, 'Distribution expanded size bound')
        names[key] = entry
    for key, entry in names.items():
        parent = PurePosixPath(key).parent
        while str(parent) != '.':
            if str(parent) in names:
                need(names[str(parent)].is_dir(), 'File cannot be an ancestor')
            parent = parent.parent
    need(total == EXPECTED_EXPANDED_BYTES
         and sum(not e.is_dir() for e in entries) == EXPECTED_FILES,
         'Exact trusted expanded distribution profile')
    need(TOP + '/bin/gradle.bat' in {e.filename for e in entries}, 'Windows launcher present')
    return entries


def extract():
    source = contained(Path(__file__)).read_bytes()
    zip_path = contained(ZIP)
    need(zip_path.is_file() and zip_path.stat().st_size == ZIP_BYTES, 'Exact approved ZIP size')
    # Retain the admitted bytes once; extraction never reopens a moving ZIP path.
    zip_bytes = zip_path.read_bytes()
    need(len(zip_bytes) == ZIP_BYTES and digest(zip_bytes) == ZIP_SHA,
         'Exact official/wrapper distribution SHA-256 before extraction')
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        entries = profile(archive)
        contained(BASE)
        BASE.mkdir(parents=True, exist_ok=True)
        run = contained(BASE / ('r-' + uuid.uuid4().hex[:8]))
        run.mkdir()
        result = {'schema': 'full-apk-fixed-gradle-preparation/v1', 'status': 'FAILED',
                  'run': run.relative_to(ROOT).as_posix(),
                  'producerSha256': digest(source),
                  'zip': {'path': ZIP.relative_to(ROOT).as_posix(), 'bytes': len(zip_bytes),
                          'sha256': ZIP_SHA},
                  'softwareDownloaded': False, 'softwareExecuted': False,
                  'gradleOrApkBuilt': False, 'sdkOrLicensesChanged': False}
        try:
            (run / 'executed-source.py').write_bytes(source)
            destination = contained(run / 'distribution')
            destination.mkdir()
            extracted = {}
            for entry in entries:
                target = contained(destination / Path(*PurePosixPath(entry.filename).parts))
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                need(not target.exists(), 'No output clobber')
                sha = hashlib.sha256()
                written = 0
                with archive.open(entry, 'r') as src, target.open('xb') as dst:
                    while True:
                        block = src.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        need(written <= entry.file_size and written <= MAX_FILE_BYTES,
                             'Expanded stream size bound')
                        dst.write(block)
                        sha.update(block)
                need(written == entry.file_size, 'Complete CRC-checked ZIP entry')
                extracted[target.relative_to(destination).as_posix()] = {
                    'bytes': written, 'sha256': sha.hexdigest()}
            actual = {p.relative_to(destination).as_posix(): p for p in destination.rglob('*')
                      if p.is_file()}
            need(set(actual) == set(extracted) and len(actual) == EXPECTED_FILES,
                 'Exact final extracted file closure')
            for name, path in actual.items():
                contained(path)
                data = path.read_bytes()
                need(len(data) == extracted[name]['bytes']
                     and digest(data) == extracted[name]['sha256'], 'Extracted bytes conserved')
            need(Path(__file__).read_bytes() == source and ZIP.read_bytes() == zip_bytes,
                 'Producer/approved ZIP identity unchanged')
            result.update(status='PASS_FIXED_GRADLE_DISTRIBUTION_EXTRACTED_NOT_EXECUTED',
                          distribution=(destination / TOP).relative_to(ROOT).as_posix(),
                          extractedFilePins=extracted, expandedBytes=EXPECTED_EXPANDED_BYTES)
        except BaseException as error:
            result.update(failureType=type(error).__name__, failureMessage=str(error)[:2048])
            raise
        finally:
            save(run / 'receipt.json', result)
            print(json.dumps({'status': result['status'],
                              'receipt': (run / 'receipt.json').relative_to(ROOT).as_posix()}),
                  flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-gradle', action='store_true')
    args = parser.parse_args()
    if args.extract_gradle:
        extract()
    else:
        print(json.dumps({'status': 'SOURCE_PLAN_ONLY_NO_DOWNLOAD_EXTRACTION_OR_EXECUTION',
                          'fixedZip': ZIP.relative_to(ROOT).as_posix(), 'sha256': ZIP_SHA,
                          'futureTask': ':app:assembleFullDebug',
                          'remainingBuildInputs': ['actual source overlay receipt',
                                                   'genuine package-set files/metadata',
                                                   'reviewed repo-local SDK layout']}))
