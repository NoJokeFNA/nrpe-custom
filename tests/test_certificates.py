"""Certificate parsing, in-memory snapshots, and the Docker trust boundary."""

import contextlib
import hashlib
import io
import os
from pathlib import Path, PureWindowsPath
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
            self.assertEqual(pem['pem'], binary['pem'])
            self.assertEqual(hashlib.sha256(pem['pem'].encode('ascii')).hexdigest(), pem['sha256'])
            self.assertNotIn('path', pem)

    @patch('tempfile.TemporaryDirectory', side_effect=AssertionError('No TEMP path may be used'))
    def test_certificate_preparation_does_not_use_system_temp(self, temporary):
        with prepared_certificate(FIXTURE) as certificate:
            self.assertEqual(certificate['pem'], FIXTURE.read_text())

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
    def test_cli_passes_normalized_pem_snapshot(self, execute):
        def inspect(*args, **kwargs):
            certificate = kwargs['ca_cert']
            self.assertEqual(certificate['pem'], FIXTURE.read_text())
            return 0
        execute.side_effect = inspect
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['build', 'sles15sp3', '--ca-cert', str(FIXTURE)], self.root), 0)
        self.assertNotIn('path', execute.call_args.kwargs['ca_cert'])

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
            with state.target_lock(self.root, 'sles15sp3', 'ca') as lock:
                self.assertEqual(controller.run_phase('docker', self.root, 'ca', 'sles15sp3',
                                 'test', io.StringIO(), lock, pull=True, ca_cert=certificate), 0)
            for call in popen.call_args_list:
                environment = call.kwargs['env']
                self.assertEqual(environment['NRPE_CA_PEM'], certificate['pem'])
                self.assertNotIn('NRPE_CA_CERT', environment)
                self.assertEqual(environment['NRPE_CA_SHA256'], certificate['sha256'])
                self.assertNotIn(certificate['pem'], call.args[0])

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_secret_handoff_ignores_windows_paths_and_inherited_pem(self, popen, run):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        root = PureWindowsPath('D:/Work/NRPE project')
        certificate = {'pem': FIXTURE.read_text(), 'sha256': 'validated-digest'}
        for phase in ('build', 'test'):
            for pull in (False, True):
                with self.subTest(phase=phase, pull=pull):
                    popen.reset_mock()
                    def process(*args, **kwargs):
                        child = MagicMock()
                        child.stdout = io.StringIO('')
                        child.wait.return_value = 0
                        child.poll.return_value = 0
                        return child
                    popen.side_effect = process
                    with patch.dict(os.environ, {'NRPE_CA_CERT': r'C:\Users\Old\Temp\ca.pem',
                                                 'NRPE_CA_PEM': 'unvalidated', 'NRPE_CA_SHA256': 'stale'}):
                        controller.run_phase('docker', root, 'ca', 'debian12', phase,
                                             io.StringIO(), self.root, pull=pull, ca_cert=certificate)
                    self.assertEqual(popen.call_count, 2 if pull else 1)
                    for call in popen.call_args_list:
                        self.assertNotIn('NRPE_CA_CERT', call.kwargs['env'])
                        self.assertEqual(call.kwargs['env']['NRPE_CA_PEM'], certificate['pem'])
                        self.assertEqual(call.kwargs['env']['NRPE_CA_SHA256'], 'validated-digest')
                    with patch.dict(os.environ, {'NRPE_CA_CERT': r'C:\Temp\ca.pem',
                                                 'NRPE_CA_PEM': 'unvalidated', 'NRPE_CA_SHA256': 'stale'}):
                        controller.run_phase('docker', root, 'ca', 'debian12', phase,
                                             io.StringIO(), self.root, pull=pull)
                        environment = popen.call_args.kwargs['env']
                        self.assertEqual(environment['NRPE_CA_PEM'], '')
                        self.assertNotIn('NRPE_CA_SHA256', environment)
                        self.assertNotIn('NRPE_CA_CERT', environment)
                        self.assertEqual(os.environ['NRPE_CA_PEM'], 'unvalidated')
