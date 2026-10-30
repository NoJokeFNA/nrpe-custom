#!/usr/bin/env python3
"""Check public signing prerequisites; never read, create or change private keys."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def signer_fingerprints(path):
    records = []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(
            r'nrpe-custom-release\s+namespaces="nrpe-custom-release"\s+ssh-ed25519\s+([A-Za-z0-9+/=]+)(?:\s+[^\r\n]+)?', line.strip())
        if not match:
            raise ValueError('Signer entries must use the release identity, namespace and Ed25519 format')
        try:
            key = base64.b64decode(match[1], validate=True)
        except ValueError as exc:
            raise ValueError('Invalid public-key encoding') from exc
        prefix = b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20'
        if not key.startswith(prefix) or len(key) != len(prefix) + 32:
            raise ValueError('Invalid Ed25519 public-key structure')
        fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(key).digest()).decode().rstrip('=')
        if fingerprint in records:
            raise ValueError('Duplicate release signer')
        records.append(fingerprint)
    if not records:
        raise ValueError('No maintainer public release key is enrolled')
    return records


def github_metadata(repository, call=subprocess.run):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Use an explicit owner/repository name')
    def get(endpoint):
        result = call(['gh', 'api', 'repos/' + repository + '/actions/' + endpoint],
                      capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            raise RuntimeError('GitHub metadata unavailable: ' + endpoint + ' (missing setting or insufficient access)')
        return json.loads(result.stdout)
    mode = get('variables/NRPE_RELEASE_SIGNING').get('value')
    secret = get('secrets/NRPE_RELEASE_SIGNING_KEY').get('name')
    if mode != 'ssh-ed25519':
        raise ValueError('NRPE_RELEASE_SIGNING must be ssh-ed25519 for production signing')
    if secret != 'NRPE_RELEASE_SIGNING_KEY':
        raise ValueError('Release signing secret metadata was not found')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allowed-signers', type=Path, default=ROOT / 'packaging/release-allowed-signers')
    parser.add_argument('--repository', help='Optional read-only GitHub variable/secret-name checks; requires gh access')
    args = parser.parse_args(argv)
    failed = False
    try:
        for fingerprint in signer_fingerprints(args.allowed_signers):
            print('PUBLIC SIGNER: ' + fingerprint)
    except (OSError, ValueError) as exc:
        print('BLOCKED: ' + str(exc)); failed = True
    if not shutil.which('ssh-keygen'):
        print('BLOCKED: OpenSSH ssh-keygen is unavailable'); failed = True
    else:
        print('INFO: ssh-keygen found; actual sign/verify tests must establish signature support')
    if args.repository:
        try:
            github_metadata(args.repository)
            print('PASS: GitHub signing mode and secret name are configured')
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            print('BLOCKED: ' + str(exc)); failed = True
    else:
        print('NOT CHECKED: GitHub signing mode and secret metadata')
    print('No private key was read or changed. Metadata cannot prove that the secret matches the public key.')
    print('A verified signed release and independently trusted fingerprint are still required.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
