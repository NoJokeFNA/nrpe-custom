"""TLS hints based on real tool messages and failed workflow behavior."""

import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from nrpe_cli import controller, state
from nrpe_cli.diagnostics import TLSFailure


class TLSMessageTests(unittest.TestCase):
    def test_recognizes_certificate_verification_errors(self):
        messages = (
            'curl: (60) SSL certificate problem: unable to get local issuer certificate',
            'Curl error 60: SSL peer certificate or SSH remote key was not OK',
            '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed',
            'Certificate verification failed: The certificate is NOT trusted. The certificate issuer is unknown.',
            'x509: certificate signed by unknown authority',
            'self-signed certificate in certificate chain',
        )
        for message in messages:
            with self.subTest(message=message):
                failure = TLSFailure()
                failure.observe(message)
                hint = failure.hint(ca_configured=False)
                self.assertIn('No company CA certificate was supplied', hint)
                self.assertIn('--ca-cert', hint)
                self.assertIn('NRPE_CA_CERT', hint)
                self.assertIn('Workflow options', hint)
                self.assertIn('Docker Desktop/Engine and BuildKit', hint)

    def test_existing_ca_does_not_get_missing_ca_hint(self):
        failure = TLSFailure()
        failure.observe('SSL certificate problem: unable to get local issuer certificate')
        hint = failure.hint(ca_configured=True)
        self.assertIn('A CA certificate was supplied', hint)
        self.assertIn('correct issuing company CA', hint)
        self.assertNotIn('No company CA', hint)

    def test_expiry_hostname_and_handshake_errors_do_not_claim_missing_ca(self):
        for message in (
                'curl: (60) SSL certificate problem: certificate has expired',
                'certificate verify failed: certificate is not yet valid',
                'x509: certificate is valid for example.org, not registry.example.org',
                'SSL: no alternative certificate subject name matches target hostname',
                'curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL',
                'net/http: TLS handshake timeout'):
            for configured in (False, True):
                with self.subTest(message=message, ca_configured=configured):
                    failure = TLSFailure()
                    failure.observe(message)
                    hint = failure.hint(ca_configured=configured)
                    self.assertIn('A TLS/SSL connection failed', hint)
                    self.assertNotIn('No company CA certificate was supplied', hint)

    def test_unrelated_errors_and_ssl_feature_messages_have_no_hint(self):
        failure = TLSFailure()
        for line in ('SSL support enabled', 'ca-certificates is already installed',
                     'curl: (6) Could not resolve host', 'connection refused',
                     'failed to read dockerfile: no such file or directory'):
            failure.observe(line)
        self.assertIsNone(failure.hint(ca_configured=False))


class TLSWorkflowTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    @staticmethod
    def process(output, code):
        child = MagicMock()
        child.stdout = io.StringIO(output)
        child.wait.return_value = code
        child.poll.return_value = code
        return child

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_failed_build_prints_and_persists_hint_without_changing_exit_code(self, popen, run, docker):
        original = 'curl: (60) SSL certificate problem: unable to get local issuer certificate\n'
        popen.return_value = self.process(original, 60)
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with patch('nrpe_cli.controller.workflow_identity', return_value=None):
            self.assertEqual(controller.execute('verify', ['debian12'], self.root), 60)
        report = state.reports(self.root)[0]
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['exit_code'], 60)
        self.assertEqual(report['targets']['debian12']['test'], 'not run')
        log = (self.root / '.nrpe/runs' / report['id'] / 'run.log').read_text()
        for output in (log, self.output.getvalue()):
            self.assertIn(original, output)
            self.assertEqual(output.count('HINT:'), 1)
            self.assertIn('No company CA certificate was supplied', output)
        self.assertEqual(run.call_args.args[0], ['docker', 'rm', '-f',
                         'nrpe-' + report['id'] + '-debian12-build'])
        self.assertFalse((self.root / '.nrpe/locks/debian12').exists())

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_successful_command_tls_output_does_not_trigger_hint_for_later_failure(self, popen, run):
        popen.side_effect = [
            self.process('retry: certificate verify failed\nretry succeeded\n', 0),
            self.process('unrelated package error\n', 42),
        ]
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        log = io.StringIO()
        with state.target_lock(self.root, 'debian12', 'pull') as lock:
            code = controller.run_phase('docker', self.root, 'pull', 'debian12',
                                        'build', log, lock, pull=True)
        self.assertEqual(code, 42)
        self.assertNotIn('HINT:', log.getvalue())
        self.assertNotIn('HINT:', self.output.getvalue())

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_test_image_pull_with_supplied_ca_explains_separate_registry_trust(self, popen, run):
        popen.return_value = self.process('failed to resolve source metadata: x509: certificate signed by unknown authority\n', 1)
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        log = io.StringIO()
        with state.target_lock(self.root, 'debian12', 'pull') as lock:
            code = controller.run_phase('docker', self.root, 'pull', 'debian12',
                                        'test', log, lock, pull=True,
                                        ca_cert={'pem': 'validated PEM', 'sha256': 'digest'})
        self.assertEqual(code, 1)
        self.assertEqual(popen.call_count, 1)
        self.assertIn('A CA certificate was supplied', log.getvalue())
        self.assertIn('--ca-cert configures container trust only', log.getvalue())
