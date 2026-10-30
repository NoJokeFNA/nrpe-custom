"""Offline release authentication through OpenSSH Ed25519 signatures."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess

from .targets import DEFAULT_TARGETS


IDENTITY = 'nrpe-custom-release'
NAMESPACE = 'nrpe-custom-release'
PAYLOADS = {'nrpe-custom-' + target + '.tar.gz' for target in DEFAULT_TARGETS} | {
    'workflow-source.tar.gz', 'LICENSE', 'THIRD_PARTY.md', 'release.json',
    'RELEASE_NOTES.md',
}
ARCH_PAYLOADS = (PAYLOADS - {'nrpe-custom-' + target + '.tar.gz' for target in DEFAULT_TARGETS}) | {'nrpe-custom-archlinux.tar.gz'}


def payloads(profile):
    if profile == 'regular':
        return PAYLOADS
    if profile == 'archlinux':
        return ARCH_PAYLOADS
    raise RuntimeError('Unknown release profile')


def ssh(*args, input=None):
    executable = shutil.which('ssh-keygen')
    if not executable:
        raise RuntimeError('OpenSSH 8.2+ ssh-keygen with SSH signature support is required')
    env = dict(os.environ, SSH_ASKPASS_REQUIRE='never')
    try:
        result = subprocess.run([executable, *map(str, args)], input=input,
                                stdin=subprocess.DEVNULL if input is None else None,
                                capture_output=True, timeout=30, env=env)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('SSH signature operation timed out') from exc
    if result.returncode:
        if b'bad permissions' in result.stderr.lower() or b'unprotected private key' in result.stderr.lower():
            raise RuntimeError('SSH signature operation failed: private-key file permissions are too open')
        raise RuntimeError('SSH signature operation failed; check the key, trusted signers and OpenSSH support')
    return result.stdout


def check_assets(directory, signed=False, profile='regular'):
    """Require the fixed flat release layout and hash every payload before use."""
    directory = Path(directory)
    selected = payloads(profile)
    expected = selected | {'SHA256SUMS'}
    if signed:
        expected |= {'SHA256SUMS.sig'}
    entries = list(directory.iterdir())
    if {p.name for p in entries} != expected or any(p.is_symlink() or not p.is_file() for p in entries):
        raise RuntimeError('Release must contain exactly the expected regular asset files')
    checksums = {}
    for line in (directory / 'SHA256SUMS').read_text(encoding='ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)', line)
        if not match or match[2] not in selected or match[2] in checksums:
            raise RuntimeError('Invalid, duplicate or unexpected checksum entry')
        checksums[match[2]] = match[1]
    if set(checksums) != selected:
        raise RuntimeError('Release checksum manifest is incomplete')
    for name, expected_hash in checksums.items():
        digest = hashlib.sha256()
        with (directory / name).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise RuntimeError('Release checksum mismatch: ' + name)


def verify_release(directory, allowed_signers, profile='regular'):
    directory = Path(directory).resolve()
    # Authenticate the manifest before trusting any filenames or checksum claims.
    manifest = directory / 'SHA256SUMS'
    signature = directory / 'SHA256SUMS.sig'
    if manifest.is_symlink() or signature.is_symlink() or not manifest.is_file() or not signature.is_file():
        raise RuntimeError('Regular SHA256SUMS and SHA256SUMS.sig files are required')
    ssh('-Y', 'verify', '-f', Path(allowed_signers).resolve(), '-I', IDENTITY,
        '-n', NAMESPACE, '-s', signature, input=manifest.read_bytes())
    check_assets(directory, signed=True, profile=profile)


def sign_release(directory, key, allowed_signers, profile='regular'):
    directory = Path(directory).resolve()
    check_assets(directory, profile=profile)
    public_key = ssh('-y', '-f', Path(key).resolve())
    if not public_key.startswith(b'ssh-ed25519 '):
        raise RuntimeError('Release signing requires an Ed25519 key')
    signature = directory / 'SHA256SUMS.sig'
    try:
        ssh('-Y', 'sign', '-q', '-f', Path(key).resolve(), '-n', NAMESPACE,
            directory / 'SHA256SUMS')
        verify_release(directory, allowed_signers, profile=profile)
    except Exception:
        signature.unlink(missing_ok=True)
        raise
