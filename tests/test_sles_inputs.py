"""The download/native-verification boundary must not weaken SLE package trust."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_sles_inputs import prepare
from sles_source import fetch_sources
import io


class SlesInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.packaging = self.root / 'packaging'
        self.packaging.mkdir()
        self.key = self.packaging / 'sles12sp3-suse.asc'
        self.key.write_bytes(b'reviewed key fixture')
        self.source = {'suse_key': {'sha256': hashlib.sha256(self.key.read_bytes()).hexdigest()}}
        (self.packaging / 'sles12sp3-source.json').write_text(json.dumps(self.source))
        self.package = {'file': 'libwrap0-7.6-1.x86_64.rpm', 'name': 'libwrap0',
                        'version_release': '7.6-1', 'arch': 'x86_64', 'vendor': 'SUSE LLC',
                        'signature_key': '39db7c82', 'sha256': 'a' * 64,
                        'url': 'https://api.opensuse.org/public/build/SUSE:SLE-12-SP3:GA/SLES/x86_64/_repository/libwrap0.rpm'}
        self.save()

    def save(self):
        (self.packaging / 'sles12sp3-bootstrap.json').write_text(json.dumps({'packages': [self.package]}))

    @patch('prepare_sles_inputs.download_packages')
    def test_sle15_inputs_are_rejected_before_download(self, download):
        self.package['url'] = self.package['url'].replace('SLE-12-SP3', 'SLE-15-SP3')
        self.save()
        with self.assertRaisesRegex(ValueError, 'matching original SLE-12'):
            prepare(self.packaging, self.root / 'stage', 'runtime')
        download.assert_not_called()

    @patch('prepare_sles_inputs.download_packages')
    def test_changed_reviewed_key_is_rejected(self, download):
        self.key.write_bytes(b'other key')
        with self.assertRaisesRegex(ValueError, 'signing-key bytes changed'):
            prepare(self.packaging, self.root / 'stage', 'runtime')
        download.assert_not_called()

    def test_missing_or_wrong_ca_stops_before_download(self):
        ca = self.root / 'ca.pem'
        with self.assertRaisesRegex(ValueError, 'missing'):
            prepare(self.packaging, self.root / 'stage', 'runtime', ca, 'a' * 64)
        ca.write_bytes(b'not the selected CA')
        with self.assertRaisesRegex(ValueError, 'CA checksum mismatch'):
            prepare(self.packaging, self.root / 'stage', 'runtime', ca, 'a' * 64)

    @patch('prepare_sles_inputs.download_packages')
    def test_hash_checked_download_emits_native_verification_inputs(self, download):
        def downloaded(manifest, directory, role):
            self.assertEqual(role, 'runtime')
            directory.mkdir()
            path = directory / self.package['file']
            path.write_bytes(b'downloaded fixture')
            yield self.package, path
        download.side_effect = downloaded
        target = self.root / 'stage'
        prepare(self.packaging, target, 'runtime')
        self.assertEqual((target / 'packages/SHA256SUMS').read_text(),
                         'a' * 64 + '  ' + self.package['file'] + '\n')
        self.assertIn('libwrap0\t7.6-1\tx86_64\tSUSE LLC\t39db7c82',
                      (target / 'packages/IDENTITIES.tsv').read_text())
        self.assertEqual((target / 'suse.asc').read_bytes(), self.key.read_bytes())
        self.assertFalse((target / 'sources').exists())

    @patch('prepare_sles_inputs.download_packages', return_value=iter(()))
    def test_empty_role_cannot_produce_installable_inputs(self, download):
        with self.assertRaisesRegex(ValueError, 'No pinned packages'):
            prepare(self.packaging, self.root / 'stage', 'runtime')

    def test_real_macro_recipe_version_is_checked_without_modification(self):
        spec = b'Name: nagios-rpm-macros\nVersion: 0.14\nRelease: 0\n'
        manifest = {'project': 'server:monitoring', 'package': 'nagios-rpm-macros',
                    'revision': 'pinned', 'version': '0.14', 'release': '0',
                    'files': {'nagios-rpm-macros.spec': {'size': len(spec),
                              'sha256': hashlib.sha256(spec).hexdigest()}}}
        target = self.root / 'macro'
        fetch_sources(manifest, target, lambda *a, **k: io.BytesIO(spec))
        self.assertEqual((target / 'nagios-rpm-macros.spec').read_bytes(), spec)
        manifest['version'] = '0.15'
        with self.assertRaisesRegex(ValueError, 'support-package version'):
            fetch_sources(manifest, target, lambda *a, **k: io.BytesIO(spec))


@unittest.skipIf(os.name == 'nt', 'Native SLES verification uses POSIX shell')
class NativeRpmVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'rpms'
        self.directory.mkdir()
        self.file = self.directory / 'example-1-0.x86_64.rpm'
        self.file.write_bytes(b'RPM fixture')
        sha = hashlib.sha256(self.file.read_bytes()).hexdigest()
        (self.directory / 'SHA256SUMS').write_text(sha + '  ' + self.file.name + '\n')
        (self.directory / 'IDENTITIES.tsv').write_text(self.file.name + '\texample\t1-0\tx86_64\tSUSE LLC\t39db7c82\n')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name, variable in [('rpmkeys', 'SIGNATURE'), ('rpm', 'IDENTITY')]:
            script = self.bin / name
            script.write_text('#!/bin/sh\nprintf "%s\\n" "$' + variable + '"\n')
            script.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        SIGNATURE='Header V3 RSA/SHA256 Signature, key ID 39db7c82: OK',
                        IDENTITY='example 1-0 x86_64|SUSE LLC')

    def run_verifier(self):
        return subprocess.run(['bash', 'scripts/verify-sles-packages.sh', str(self.directory)],
                              env=self.env, capture_output=True, text=True)

    def test_valid_signature_hash_and_identity_are_all_required(self):
        self.assertEqual(self.run_verifier().returncode, 0)
        self.env['SIGNATURE'] = 'Payload digest: OK'
        self.assertNotEqual(self.run_verifier().returncode, 0)
        self.env['SIGNATURE'] = 'Signature, key ID aaaaaaaa: OK'
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_vendor_mismatch_is_rejected_with_good_signature(self):
        self.env['IDENTITY'] = 'example 1-0 x86_64|Different vendor'
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_modified_rpm_fails_even_with_good_signature_output(self):
        self.file.write_bytes(b'replaced')
        self.assertNotEqual(self.run_verifier().returncode, 0)

    def test_extra_rpm_is_rejected_before_installation(self):
        (self.directory / 'unreviewed.rpm').write_bytes(b'unreviewed')
        self.assertNotEqual(self.run_verifier().returncode, 0)
