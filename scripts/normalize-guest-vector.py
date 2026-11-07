#!/usr/bin/env python3
"""Normalize the pinned official Vector ZIP without executing its installer."""
import argparse
import hashlib
import zipfile
from pathlib import Path

EXPECTED = '9ee8323575d615f7b3f1076ff60b2a63a49390ef11881b52632311a37f6f79cc'

def normalize(source, destination):
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('Expected the official Vector v2.2 ZIP; SHA-256 mismatch')
    with zipfile.ZipFile(source) as archive:
        entries = {}
        for name in ('action.sh', 'cli', 'daemon', 'daemon.apk', 'framework/vector.dex',
                     'manager.apk', 'module.prop', 'service.sh', 'uninstall.sh'):
            executable = name.endswith('.sh') or name in ('daemon', 'cli')
            entries[name] = (archive.read(name), '755' if executable else '644')
        daemon = entries['daemon'][0].decode()
        begin = daemon.index('tmpDaemonApk=')
        end = daemon.index('# Apply debug options', begin)
        daemon = daemon[:begin] + 'debug=false\njava_options="-Djava.class.path=$dir/daemon.apk"\n\n' + daemon[end:]
        entries['daemon'] = (daemon.encode(), '755')
        for abi, bits in [('arm64-v8a', '64'), ('armeabi-v7a', '32')]:
            for original, target in [('dex2oat', 'dex2oat'+bits), ('liboat_hook.so', 'liboat_hook'+bits+'.so')]:
                entries['bin/'+target] = (archive.read('bin/'+abi+'/'+original), '755')
        entries['zygisk/arm64-v8a.so'] = (archive.read('lib/arm64-v8a/libzygisk.so'), '644')
        with destination.open('wb') as output:
            output.write(b'ONEOS1\n')
            # Metadata follows the sorted payloads, matching the shipped bundle.
            for name, (data, mode) in sorted(entries.items()):
                path = name.encode()
                output.write(f'{len(path)} {len(data)} {mode}\n'.encode()+path+data)
            data = b'vector';path = b'.oneos-framework'
            output.write(f'{len(path)} {len(data)} 600\n'.encode()+path+data+b'0 0 0\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    normalize(args.zip, args.output)
