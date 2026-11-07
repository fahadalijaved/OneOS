#!/usr/bin/env python3
"""Publish Fold8 experimental payload updates without rebuilding the APK.

Example: release-patch-channel.py --set n6-global-f8 --revision coloros-2
         --overrides out/my-coloros-patches --publish
Without --publish, creates a reviewable release folder. Only Fold8SystemUI.apk and GlobalVerifiedAddons.tar may be replaced.
Only existing payload names can change; scripts and new payload roles need an APK.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
# The only files a channel may replace (PatchManifest.REPLACEABLE in the app, which refuses every other
# difference): never guards.txt, a guarded jar or binary, a payload image or a script.
REPLACEABLE = {'Fold8SystemUI.apk', 'GlobalVerifiedAddons.tar'}
def source_config(source_id):
    catalog = json.loads((ROOT / 'app-android/packages/patch-sources.json').read_text())
    if catalog['schema'] != 1:
        raise ValueError('unsupported patch source registry schema')
    source = next((source for source in catalog['contributors'] if source['id'] == source_id), None)
    if source is None:
        raise ValueError(f'unknown contributor id: {source_id}')
    return source


def table(path):
    return dict(line.split(None, 1) for line in path.read_text().splitlines()
                if line and not line.startswith('#'))


def sums(path):
    return {line.split()[1]: line.split()[0] for line in path.read_text().splitlines()
            if line and not line.startswith("#")}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def gh(repo, *args):
    return subprocess.check_output(['gh', *args, '--repo', repo], text=True)


def prepare(sid, revision, overrides, output, source_id='that-josh-guy', profile=None):
    config = source_config(source_id)
    candidates = [t for t in config['targets'] if t['set'] == sid and (profile is None or t['profile'] == profile)]
    if len({t['profile'] for t in candidates}) != 1:
        raise ValueError('choose --profile for this contributor and system')
    profile = candidates[0]['profile']
    images = {t['imageSha256'] for t in candidates}
    if len(images) != 1:
        raise ValueError('source does not declare one image for this package set')
    repo, tag = config['repository'], config['tag']
    if not revision.strip() or len(revision) > 100:
        raise ValueError('revision must contain 1..100 characters')
    packages = ROOT / 'app-android/packages'
    base = sums(packages / f'{sid}.sha256')
    sizes = table(packages / 'sizes.txt')
    remote = table(packages / 'remote.txt')
    provided = {p.name: p for p in overrides.iterdir() if p.is_file()}
    if set(provided) - base.keys():
        raise ValueError(f'unknown payload names: {sorted(set(provided) - base.keys())}')
    if any(p.is_symlink() for p in overrides.iterdir()):
        raise ValueError('override symlinks are not accepted')
    if set(provided) - REPLACEABLE:
        raise ValueError(f'a channel may only replace {sorted(REPLACEABLE)}, not {sorted(set(provided) - REPLACEABLE)}')
    output.mkdir(parents=True, exist_ok=False)
    files = []
    for name, sha in base.items():
        if name in provided:
            path = provided[name]
            sha = digest(path)
            size = path.stat().st_size
            if not 0 < size <= 268435456:
                raise ValueError(f'{name} exceeds root receive limit')
            shutil.copyfile(path, output / sha)
            source = f'gh:{repo}:{tag}'
        else:
            size = int(sizes[sha])
            source = next(s for s in remote[sha].split(',') if s.startswith('gh:'))
            if source.count(':') == 1:
                source = source.replace('gh:', 'gh:fahadalijaved/OneOS-files:')
        files.append(dict(name=name, sha256=sha, bytes=size, source=source))
    expected = {f['name']: f['sha256'] for f in files}
    guards = sums(packages / f'{sid}.guards.txt')
    if any(expected[name] != sha for name, sha in guards.items()):
        raise ValueError('a guarded payload differs from the app\'s guards.txt')
    manifest = output / f'{profile}-{sid}.json'
    manifest.write_text(json.dumps(dict(schema=1, profile=profile, set=sid, imageSha256=next(iter(images)), revision=revision, files=files), indent=2) + '\n')
    return manifest


def publish(manifest, source_id='that-josh-guy'):
    config = source_config(source_id)
    repo, tag = config['repository'], config['tag']
    probe = subprocess.run(['gh', 'release', 'view', tag, '--json', 'assets', '--repo', repo], capture_output=True, text=True)
    if probe.returncode:
        if 'release not found' not in probe.stderr.lower():
            raise ValueError(probe.stderr.strip())
        gh(repo, 'release', 'create', tag, '--prerelease', '--latest=false', '--title', config['label'],
           '--notes', 'Device-scoped patch manifests and immutable SHA-256 payloads.')
        release = {'assets': []}
    else:
        release = json.loads(probe.stdout)
    assets = {a['name']: a['size'] for a in release['assets']}
    payloads = [p for p in manifest.parent.iterdir() if len(p.name) == 64 and p.name == digest(p)]
    for path in payloads:
        if path.name in assets and assets[path.name] != path.stat().st_size:
            raise ValueError(f'published hash asset has another size: {path.name}')
        if path.name not in assets:
            gh(repo, 'release', 'upload', tag, str(path))
        with urllib.request.urlopen(f'https://github.com/{repo}/releases/download/{tag}/{path.name}', timeout=120) as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != path.name:
                raise ValueError(f'public download failed verification: {path.name}')
    # The small channel pointer changes only after every immutable payload is verified.
    gh(repo, 'release', 'upload', tag, str(manifest), '--clobber')
    print(f'Published {manifest.name} to https://github.com/{repo}/releases/tag/{tag}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--set', required=True, dest='sid')
    parser.add_argument('--profile', help='target device profile, required when several devices share the set')
    parser.add_argument('--source', default='that-josh-guy', help='contributor id in packages/patch-sources.json')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--overrides', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'out/patch-channel-next')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    try:
        manifest = prepare(args.sid, args.revision, args.overrides, args.out, args.source, args.profile)
        print(f'Prepared {manifest}')
        if args.publish:
            publish(manifest, args.source)
    except (ValueError, KeyError, StopIteration) as error:
        parser.exit(1, f'{error}\n')
