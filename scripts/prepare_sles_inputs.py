#!/usr/bin/env python3
"""Download pinned SLE-12 inputs; RPM signatures are checked in the target stage."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import ssl
import urllib.request
import urllib.parse

from fetch_sles_packages import download_packages
from sles_source import fetch_sources


def prepare(packaging, destination, role, ca=None, ca_sha256='none'):
    context = ssl.create_default_context()
    if ca and ca.is_file() and ca.stat().st_size:
        data = ca.read_bytes()
        if hashlib.sha256(data).hexdigest() != ca_sha256:
            raise ValueError('Build CA checksum mismatch')
        context.load_verify_locations(cadata=data.decode('ascii'))
    elif ca_sha256 != 'none':
        raise ValueError('Selected build CA is missing')
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)))
    destination.mkdir(parents=True, exist_ok=True)
    packages = json.loads((packaging / 'sles12sp3-bootstrap.json').read_text())
    source_manifest = json.loads((packaging / 'sles12sp3-source.json').read_text())
    key = packaging / 'sles12sp3-suse.asc'
    if hashlib.sha256(key.read_bytes()).hexdigest() != source_manifest['suse_key']['sha256']:
        raise ValueError('Reviewed SUSE signing-key bytes changed')
    for entry in packages['packages']:
        path = urllib.parse.urlsplit(entry['url']).path
        if not re.match(r'^/public/build/SUSE:SLE-12(?:-SP3)?:(?:GA|Update)/', path):
            raise ValueError('SLES 12 bootstrap may only use matching original SLE-12 pools')
    directory = destination / 'packages'
    identities, checksums = [], []
    for entry, path in download_packages(packages, directory, role):
        fields = [entry[k] for k in ('file', 'name', 'version_release', 'arch', 'vendor', 'signature_key')]
        if any('\t' in value or '\n' in value or '\r' in value for value in fields):
            raise ValueError('Invalid RPM identity field')
        identities.append('\t'.join(fields) + '\n')
        checksums.append(entry['sha256'] + '  ' + path.name + '\n')
    if not identities:
        raise ValueError('No pinned packages for the selected role')
    (directory / 'IDENTITIES.tsv').write_text(''.join(identities))
    (directory / 'SHA256SUMS').write_text(''.join(checksums))
    metadata = destination / 'metadata'
    metadata.mkdir()
    shutil.copyfile(packaging / 'sles12sp3-bootstrap.json', metadata / 'bootstrap.json')
    shutil.copyfile(packaging / 'sles12sp3-suse.asc', destination / 'suse.asc')
    if role == 'build':
        for label, filename in [('nrpe', 'source'), ('system-user-nagios', 'user-source'),
                                ('nagios-rpm-macros', 'macros-source')]:
            original = packaging / ('sles12sp3-' + filename + '.json')
            manifest = json.loads(original.read_text())
            fetch_sources(manifest, destination / 'sources' / label,
                          originals=destination / 'originals' / label)
            shutil.copyfile(original, metadata / (filename + '.json'))
            if label == 'nrpe':
                (metadata / 'expected-version').write_text(manifest['version'] + '-' + manifest['custom_release'] + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packaging', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('role', choices=('build', 'runtime'))
    parser.add_argument('--ca', type=Path)
    parser.add_argument('--ca-sha256', default='none')
    args = parser.parse_args()
    prepare(args.packaging, args.destination, args.role, args.ca, args.ca_sha256)
    print('PASS: Pinned input hashes checked; native SUSE RPM signature verification still required')


if __name__ == '__main__':
    main()
