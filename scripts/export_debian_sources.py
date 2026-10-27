#!/usr/bin/env python3
"""Validate and export the exact source files referenced by a custom Debian DSC."""

import argparse
from email.parser import Parser
import hashlib
from pathlib import Path
import re
import shutil


def source_files(description, version):
    """Return checked source assets, rejecting incomplete or unsafe descriptions."""
    fields = Parser().parsestr(description.read_text(encoding='utf-8'))
    if fields.get('Source') != 'nagios-nrpe' or fields.get('Version') != version:
        raise ValueError('Source package identity does not match the custom binary version')
    if fields.get('Format') != '3.0 (quilt)':
        raise ValueError('Unexpected Debian source format; review source export')
    entries = fields.get('Checksums-Sha256', '').splitlines()
    files = []
    seen = {description.name}
    for line in entries:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError('Invalid source checksum entry')
        digest, size, name = parts
        if (not re.fullmatch(r'[0-9a-f]{64}', digest) or not size.isdigit()
                or Path(name).name != name or '\\' in name or name in ('.', '..')
                or name in seen):
            raise ValueError('Invalid or unsafe source checksum entry')
        path = description.parent / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Source asset is missing or is a symlink: ' + name)
        checksum = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(block)
        if path.stat().st_size != int(size) or checksum.hexdigest() != digest:
            raise ValueError('Source checksum mismatch: ' + name)
        seen.add(name)
        files.append((path, digest))
    if (not any('.orig.tar.' in path.name for path, _ in files)
            or not any('.debian.tar.' in path.name for path, _ in files)):
        raise ValueError('Expected upstream archive and custom Debian packaging archive')
    return [(description, hashlib.sha256(description.read_bytes()).hexdigest())] + files


def export_sources(description, destination, version):
    files = source_files(description, version)
    # Finish validation before creating or replacing any exported source files.
    destination.mkdir(parents=True, exist_ok=False)
    for path, _ in files:
        shutil.copyfile(path, destination / path.name)
    (destination / 'SHA256SUMS').write_text(
        ''.join('{}  {}\n'.format(digest, path.name) for path, digest in files),
        encoding='ascii',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('version')
    args = parser.parse_args()
    export_sources(args.description, args.destination, args.version)
    print('PASS: Matching Debian DSC, upstream source and custom packaging exported')


if __name__ == '__main__':
    main()
