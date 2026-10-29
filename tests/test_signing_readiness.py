"""Readiness checks validate public enrollment without handling private keys."""
import base64
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('check_release_signing', Path(__file__).resolve().parents[1] / 'scripts/check_release_signing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SigningReadinessTests(unittest.TestCase):
    def test_empty_and_invalid_public_enrollment_are_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'signers'
            for content in ['# not enrolled\n', 'unexpected key data',
                            'nrpe-custom-release namespaces="nrpe-custom-release" ssh-ed25519 YWJj']:
                path.write_text(content)
                with self.assertRaises(ValueError): module.signer_fingerprints(path)

    def test_fingerprints_are_public_and_duplicates_are_rejected(self):
        key = base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes(range(32))).decode()
        line = 'nrpe-custom-release namespaces="nrpe-custom-release" ssh-ed25519 ' + key + '\n'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'signers'
            path.write_text(line)
            self.assertRegex(module.signer_fingerprints(path)[0], r'^SHA256:[A-Za-z0-9+/]{43}$')
            path.write_text(line * 2)
            with self.assertRaisesRegex(ValueError, 'Duplicate'): module.signer_fingerprints(path)

    @unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH is unavailable')
    def test_public_fingerprint_matches_openssh(self):
        key = base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes(range(32))).decode()
        with tempfile.TemporaryDirectory() as temporary:
            public = Path(temporary) / 'key.pub'
            public.write_text('ssh-ed25519 ' + key + '\n')
            signers = Path(temporary) / 'signers'
            signers.write_text('nrpe-custom-release namespaces="nrpe-custom-release" ssh-ed25519 ' + key + '\n')
            result = subprocess.run(['ssh-keygen', '-lf', str(public)], capture_output=True, text=True, check=True)
            self.assertEqual(module.signer_fingerprints(signers), [result.stdout.split()[1]])

    def test_remote_check_reads_only_specific_variable_and_secret_metadata(self):
        calls = []
        def call(argv, **kwargs):
            calls.append(argv)
            payload = {'value': 'ssh-ed25519'} if '/variables/' in argv[-1] else {'name': 'NRPE_RELEASE_SIGNING_KEY'}
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), '')
        module.github_metadata('owner/project', call)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(argv[:2] == ['gh', 'api'] for argv in calls))
        self.assertTrue(calls[-1][-1].endswith('/secrets/NRPE_RELEASE_SIGNING_KEY'))

    def test_inaccessible_metadata_or_disabled_mode_is_not_ready(self):
        def denied(argv, **kwargs): return subprocess.CompletedProcess(argv, 1, '', 'HTTP 403')
        with self.assertRaisesRegex(RuntimeError, 'unavailable'): module.github_metadata('owner/project', denied)
        def off(argv, **kwargs): return subprocess.CompletedProcess(argv, 0, '{"value":"off"}', '')
        with self.assertRaises(ValueError): module.github_metadata('owner/project', off)
