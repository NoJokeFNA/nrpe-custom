"""Certificate parsing, ephemeral snapshots, and the Docker trust boundary."""

import contextlib
import hashlib
import io
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from nrpe_cli.certificates import prepared_certificate
from nrpe_cli import cli, controller, state

FIXTURE = Path(__file__).parent / 'fixtures/test-ca.pem'


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_optional_certificate_produces_no_snapshot(self):
        with prepared_certificate(None) as certificate:
            self.assertIsNone(certificate)

    def test_pem_and_der_have_same_snapshot_and_cache_identity(self):
        der = self.root / 'company.cer'
        der.write_bytes(ssl.PEM_cert_to_DER_cert(FIXTURE.read_text()))
        with prepared_certificate(FIXTURE) as pem, prepared_certificate(der) as binary:
            self.assertEqual(pem['sha256'], binary['sha256'])
            self.assertEqual(pem['path'].read_bytes(), binary['path'].read_bytes())
            self.assertEqual(hashlib.sha256(pem['path'].read_bytes()).hexdigest(), pem['sha256'])
            path = pem['path']
        self.assertFalse(path.exists())

    def test_rejects_missing_empty_invalid_oversized_and_private_key_files(self):
        for data in (b'', b'not a certificate', b'x' * (1024 * 1024 + 1),
                     b'-----BEGIN PRIVATE KEY-----\nprivate\n-----END PRIVATE KEY-----'):
            with self.subTest(size=len(data)):
                path = self.root / 'bad.cer'
                path.write_bytes(data)
                with self.assertRaises(RuntimeError):
                    with prepared_certificate(path):
                        self.fail('Accepted invalid CA')
        with self.assertRaisesRegex(RuntimeError, 'existing file'):
            with prepared_certificate(self.root / 'missing.cer'):
                self.fail('Accepted missing CA')

    def test_multiple_certificates_are_rejected_with_clear_error(self):
        path = self.root / 'bundle.pem'
        path.write_bytes(FIXTURE.read_bytes() * 2)
        with self.assertRaisesRegex(RuntimeError, 'one PEM or DER'):
            with prepared_certificate(path):
                self.fail('Accepted a bundle')

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_cli_passes_live_snapshot_and_cleans_it_after_execution(self, execute):
        def inspect(*args, **kwargs):
            certificate = kwargs['ca_cert']
            self.assertTrue(certificate['path'].is_file())
            return 0
        execute.side_effect = inspect
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['build', 'sles15sp4', '--ca-cert', str(FIXTURE)], self.root), 0)
        self.assertFalse(execute.call_args.kwargs['ca_cert']['path'].exists())

    @patch('nrpe_cli.cli.execute')
    def test_invalid_certificate_fails_before_docker(self, execute):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['test', 'debian12', '--ca-cert', 'missing.cer'], self.root), 1)
        execute.assert_not_called()

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_environment_certificate_can_be_overridden_by_explicit_path(self, execute):
        with patch.dict(os.environ, {'NRPE_CA_CERT': 'missing.cer'}):
            self.assertEqual(cli.main(['test', 'debian12', '--ca-cert', str(FIXTURE)], self.root), 0)
        self.assertIn('ca_cert', execute.call_args.kwargs)

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_secret_and_cache_identity_reach_pull_build_and_runtime_image(self, popen, run):
        def process(*args, **kwargs):
            child = MagicMock()
            child.stdout = io.StringIO('')
            child.wait.return_value = 0
            child.poll.return_value = 0
            return child
        popen.side_effect = process
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with prepared_certificate(FIXTURE) as certificate:
            with state.target_lock(self.root, 'sles15sp4', 'ca') as lock:
                self.assertEqual(controller.run_phase('docker', self.root, 'ca', 'sles15sp4',
                                 'test', io.StringIO(), lock, pull=True, ca_cert=certificate), 0)
            for call in popen.call_args_list:
                environment = call.kwargs['env']
                self.assertEqual(environment['NRPE_CA_CERT'], certificate['path'].as_posix())
                self.assertEqual(environment['NRPE_CA_SHA256'], certificate['sha256'])
                self.assertNotIn(str(certificate['path']), call.args[0])
