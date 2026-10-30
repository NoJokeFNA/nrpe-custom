#!/usr/bin/env python3
"""Fetch only the reviewed latest stable NRPE source for the optional Arch build."""
import hashlib
import json
import io
import tarfile
import subprocess
from pathlib import Path
import shutil
import sys
import urllib.request

LATEST = 'https://api.github.com/repos/NagiosEnterprises/nrpe/releases/latest'

def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'nrpe-custom-source-review'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('Oversized upstream response')
    return data

def prepare(root, destination):
    manifest = json.loads((root / 'packaging/archlinux-source.json').read_text())
    latest = json.loads(fetch(LATEST, 2 * 1024 * 1024))
    if (latest.get('tag_name') != 'nrpe-' + manifest['version']
            or latest.get('draft') or latest.get('prerelease')):
        raise RuntimeError('New latest stable NRPE release requires source, license and native package review')
    archive = fetch(manifest['url'], 16 * 1024 * 1024)
    if hashlib.sha256(archive).hexdigest() != manifest['sha256']:
        raise RuntimeError('Upstream NRPE source checksum mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    for source in (root / 'packaging/archlinux').iterdir():
        if source.is_file():
            shutil.copyfile(source, destination / source.name)
    (destination / manifest['archive']).write_bytes(archive)
    shutil.copyfile(root / 'packaging/archlinux-source.json', destination / 'source-manifest.json')
    print('PASS: reviewed source matches the current stable upstream release')

def checked_members(path):
    result = {}
    total = 0
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            if member.isdir():
                continue
            total += member.size
            if (not member.isfile() or member.name in result or total > 32 * 1024 * 1024
                    or member.name.startswith('/') or '..' in Path(member.name).parts
                    or "\\" in member.name):
                raise RuntimeError('Unsafe Arch source archive')
            result[member.name] = archive.extractfile(member).read()
    return result

def validate_export(root, directory, evidence, notices):
    manifest = json.loads((root / 'packaging/archlinux-source.json').read_text())
    if json.loads((directory / 'source-manifest.json').read_text()) != manifest:
        raise RuntimeError('Arch source manifest differs from the reviewed recipe')
    version = manifest['version'] + '-' + manifest['pkgrel']
    if evidence['artifact']['version'] != version:
        raise RuntimeError('Arch binary/source version mismatch')
    binary = directory / evidence['artifact']['file']
    metadata = subprocess.check_output(['tar', '--zstd', '-xOf', str(binary), '.PKGINFO'], text=True)
    for field, value in [('pkgname', 'nrpe'), ('pkgver', version), ('arch', 'x86_64')]:
        if [line.split(' = ', 1)[1] for line in metadata.splitlines() if line.startswith(field + ' = ')] != [value]:
            raise RuntimeError('Arch binary package metadata mismatch')
    source_name = 'sources/nrpe-' + version + '.src.tar.gz'
    members = checked_members(directory / source_name)
    expected = {'nrpe/' + name: (root / 'packaging/archlinux' / name).read_bytes()
                for name in ('PKGBUILD', 'nrpe.service', 'nrpe.sysusers', 'ARGUMENT-POLICY.md', 'nrpe.install')}
    for name, content in expected.items():
        if members.get(name) != content:
            raise RuntimeError('Arch corresponding build recipe changed: ' + name)
        if (directory / 'build-recipe' / Path(name).name).read_bytes() != content:
            raise RuntimeError('Arch exported recipe changed')
    hook = subprocess.check_output(['tar', '--zstd', '-xOf', str(binary), '.INSTALL'])
    if hook != expected['nrpe/nrpe.install']:
        raise RuntimeError('Arch installation policy notice changed')
    archive_name = 'nrpe/' + manifest['archive']
    source = members.get(archive_name, b'')
    if hashlib.sha256(source).hexdigest() != manifest['sha256']:
        raise RuntimeError('Arch corresponding upstream source changed')
    if set(members) != set(expected) | {archive_name, 'nrpe/.SRCINFO'}:
        raise RuntimeError('Unexpected Arch source package contents')
    if (directory / 'ARGUMENT-POLICY.md').read_bytes() != expected['nrpe/ARGUMENT-POLICY.md']:
        raise RuntimeError('Arch policy notice changed')
    notice_dir = notices / 'archlinux'
    notice_dir.mkdir()
    with tarfile.open(fileobj=io.BytesIO(source), mode='r:gz') as archive:
        for name, digest in manifest['licenses'].items():
            content = archive.extractfile('nrpe-' + manifest['version'] + '/' + name).read()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError('Arch upstream license changed')
            (notice_dir / name).write_bytes(content)
    return ({evidence['artifact']['file'], source_name, 'source-manifest.json',
             'ARGUMENT-POLICY.md', 'SHA256SUMS'}
            | {'build-recipe/' + Path(name).name for name in expected})

if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
