import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from nrpe_cli.signing import ARCH_PAYLOADS, PAYLOADS, check_assets, sign_release, verify_release


@unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH ssh-keygen is not installed')
class ReleaseSigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run(['ssh-keygen', '-Y', 'verify'], capture_output=True)
        if b'unknown option' in probe.stderr.lower() or b'illegal option' in probe.stderr.lower():
            raise unittest.SkipTest('OpenSSH lacks SSH signature support (8.2+ required)')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / 'release'
        self.assets.mkdir()
        for name in PAYLOADS:
            (self.assets / name).write_bytes(('fixture ' + name).encode())
        self.write_checksums()
        self.key = self.root / 'private-key'
        self.make_key(self.key)
        self.signers = self.root / 'allowed-signers'
        self.signers.write_text('nrpe-custom-release namespaces="nrpe-custom-release" ' +
                                self.key.with_suffix('.pub').read_text())

    def make_key(self, path):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)],
                       check=True, stdin=subprocess.DEVNULL, capture_output=True)

    def write_checksums(self, names=PAYLOADS):
        (self.assets / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256((self.assets / name).read_bytes()).hexdigest() + '  ' + name + '\n'
            for name in sorted(names)))

    def sign(self):
        sign_release(self.assets, self.key, self.signers)

    def test_regular_profile_requires_five_targets_and_excludes_optional_arch(self):
        archives = {name for name in PAYLOADS if name.startswith('nrpe-custom-')}
        self.assertEqual(archives, {'nrpe-custom-' + target + '.tar.gz' for target in
                                   ('debian11', 'debian12', 'debian13', 'debian14', 'sles12sp3')})
        self.assertNotIn('nrpe-custom-archlinux.tar.gz', PAYLOADS)

    def test_optional_arch_signature_requires_explicit_profile(self):
        for name in PAYLOADS - ARCH_PAYLOADS:
            (self.assets / name).unlink()
        for name in ARCH_PAYLOADS - PAYLOADS:
            (self.assets / name).write_bytes(b'optional native Arch fixture')
        self.write_checksums(ARCH_PAYLOADS)
        with self.assertRaises(RuntimeError):
            check_assets(self.assets)
        sign_release(self.assets, self.key, self.signers, profile='archlinux')
        verify_release(self.assets, self.signers, profile='archlinux')
        with self.assertRaisesRegex(RuntimeError, 'expected regular asset files'):
            verify_release(self.assets, self.signers)
        (self.assets / 'nrpe-custom-archlinux.tar.gz').write_bytes(b'tampered')
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            verify_release(self.assets, self.signers, profile='archlinux')

    def test_offline_round_trip_and_refusal_to_overwrite_signature(self):
        self.sign()
        verify_release(self.assets, self.signers)
        original = (self.assets / 'SHA256SUMS.sig').read_bytes()
        with self.assertRaises(RuntimeError):
            self.sign()
        self.assertEqual(original, (self.assets / 'SHA256SUMS.sig').read_bytes())

    def test_changed_payload_fails_even_with_valid_signature(self):
        self.sign()
        (self.assets / 'release.json').write_bytes(b'tampered')
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            verify_release(self.assets, self.signers)

    def test_changed_checksum_and_payload_fail_authentication(self):
        self.sign()
        (self.assets / 'release.json').write_bytes(b'tampered')
        self.write_checksums()
        with self.assertRaisesRegex(RuntimeError, 'SSH signature operation failed'):
            verify_release(self.assets, self.signers)

    def test_unknown_signer_and_wrong_namespace_fail(self):
        self.sign()
        other = self.root / 'other-key'
        self.make_key(other)
        for public, namespace in ((other.with_suffix('.pub').read_text(), 'nrpe-custom-release'),
                                  (self.key.with_suffix('.pub').read_text(), 'other-namespace')):
            self.signers.write_text('nrpe-custom-release namespaces="' + namespace + '" ' + public)
            with self.assertRaisesRegex(RuntimeError, 'SSH signature operation failed'):
                verify_release(self.assets, self.signers)

    def test_wrong_key_cannot_leave_publishable_signature(self):
        self.signers.write_text('# no enrolled key\n')
        with self.assertRaises(RuntimeError):
            self.sign()
        self.assertFalse((self.assets / 'SHA256SUMS.sig').exists())

    def test_extra_missing_and_directory_assets_are_rejected(self):
        extra = self.assets / 'unreviewed'
        extra.write_bytes(b'x')
        with self.assertRaises(RuntimeError):
            self.sign()
        extra.unlink()
        asset = self.assets / 'release.json'
        asset.unlink()
        with self.assertRaises(RuntimeError):
            self.sign()
        asset.mkdir()
        with self.assertRaises(RuntimeError):
            self.sign()

    def test_duplicate_traversal_and_incomplete_manifests_are_rejected(self):
        manifest = self.assets / 'SHA256SUMS'
        original = manifest.read_text()
        for invalid in (original + original.splitlines()[0] + '\n',
                        original.replace('  LICENSE\n', '  ../LICENSE\n'),
                        '\n'.join(original.splitlines()[1:]) + '\n'):
            manifest.write_text(invalid)
            with self.assertRaises(RuntimeError):
                check_assets(self.assets)

    @unittest.skipIf(os.name == 'nt', 'Symlink permissions depend on Windows host policy')
    def test_symlinked_payload_is_rejected(self):
        payload = self.assets / 'LICENSE'
        outside = self.root / 'original-license'
        payload.rename(outside)
        payload.symlink_to(outside)
        with self.assertRaises(RuntimeError):
            self.sign()

    def test_cli_missing_secret_fails_without_leaking_environment(self):
        env = dict(os.environ, NRPE_TEST_SIGNING_SECRET='')
        result = subprocess.run([
            os.sys.executable, 'scripts/release_signature.py', 'sign',
            '--directory', str(self.assets), '--allowed-signers', str(self.signers),
            '--key-env', 'NRPE_TEST_SIGNING_SECRET',
        ], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('nonempty private-key', result.stderr)
        self.assertFalse((self.assets / 'SHA256SUMS.sig').exists())

    def test_cli_sign_and_verify_with_ephemeral_key(self):
        env = dict(os.environ, NRPE_TEST_SIGNING_SECRET=self.key.read_text())
        command = [os.sys.executable, 'scripts/release_signature.py']
        arguments = ['--directory', str(self.assets), '--allowed-signers', str(self.signers)]
        signed = subprocess.run(command + ['sign'] + arguments + ['--key-env', 'NRPE_TEST_SIGNING_SECRET'],
                                env=env, capture_output=True, text=True)
        self.assertEqual(signed.returncode, 0, signed.stderr)
        self.assertNotIn(self.key.read_text().strip(), signed.stdout + signed.stderr)
        verified = subprocess.run(command + ['verify'] + arguments, capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_cli_invalid_secret_is_not_echoed(self):
        value = 'sensitive-invalid-key-\u00e4'
        result = subprocess.run([
            os.sys.executable, 'scripts/release_signature.py', 'sign',
            '--directory', str(self.assets), '--allowed-signers', str(self.signers),
            '--key-env', 'NRPE_TEST_SIGNING_SECRET',
        ], env=dict(os.environ, NRPE_TEST_SIGNING_SECRET=value), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(value, result.stdout + result.stderr)
        self.assertIn('OpenSSH private-key format', result.stderr)
