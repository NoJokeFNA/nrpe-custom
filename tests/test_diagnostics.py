"""Explain observed failures without guessing a CA cause or running log text."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nrpe_cli import cli
from nrpe_cli import controller, state
from nrpe_cli.diagnostics import FailureDiagnostics


class DiagnosticTests(unittest.TestCase):
    def hint(self, message, context='build', ca=False):
        diagnostics = FailureDiagnostics()
        diagnostics.observe(message)
        return diagnostics.hint(ca, context)

    def test_build_trust_and_deployed_nrpe_trust_are_distinguished(self):
        message = 'certificate verify failed: unable to get local issuer certificate'
        self.assertIn('No company CA certificate was supplied', self.hint(message))
        self.assertIn('A CA certificate was supplied', self.hint(message, ca=True))
        runtime = self.hint(message, context='nrpe')
        self.assertIn('deployed daemon', runtime)
        self.assertNotIn('No company CA', runtime)

    def test_nrpe_215_handshake_does_not_claim_a_missing_ca(self):
        for message in ('Error: Could not complete SSL handshake. 1', 'no shared cipher',
                        'tlsv1 alert protocol version', 'peer did not return a certificate'):
            with self.subTest(message=message):
                hint = self.hint(message, 'nrpe')
                self.assertIn('NRPE TLS negotiation failed', hint)
                self.assertIn('NRPE 2.15', hint)
                self.assertNotIn('No company CA certificate was supplied', hint)

    def test_plaintext_success_and_unknown_command_are_not_tls_failures(self):
        for message in ('NRPE_PLAIN_OK', 'NRPE v2.15', 'CHECK_NRPE: Error - Command not defined',
                        'SSL support enabled', 'Reading config file /etc/nrpe.cfg'):
            self.assertIsNone(self.hint(message, 'nrpe'))

    def test_refused_and_header_underflow_have_distinct_explanations(self):
        refused = self.hint('connect to address 192.0.2.20 port 15666: Connection refused', 'nrpe')
        self.assertIn('before TLS negotiation', refused)
        self.assertIn('listener', refused)
        underflow = self.hint('CHECK_NRPE: Receive header underflow - only -1 bytes received', 'nrpe')
        self.assertIn('packet version (-2', underflow)
        self.assertNotIn('No company CA', underflow)

    def test_old_daemon_options_permissions_and_wrong_host_are_actionable(self):
        self.assertIn('NRPE 2.15 uses -d', self.hint("invalid option -- 'f'", 'nrpe'))
        self.assertIn('directory traversal permissions', self.hint(
            "Unable to open config file '/run/example/nrpe.cfg' for reading", 'nrpe'))
        self.assertIn('disable_syslog=0', self.hint(
            "Unknown option specified in config file '/etc/nrpe.cfg' - Line 272", 'nrpe'))
        self.assertIn('ip -4 addr show', self.hint('Cannot assign requested address', 'nrpe'))

    def test_proxy_and_dns_errors_do_not_get_certificate_advice(self):
        for message in ('407 Proxy Authentication Required', 'CONNECT tunnel failed, response 407',
                        'proxyconnect tcp: connection refused'):
            hint = self.hint(message)
            self.assertIn('Proxy connection or authentication failed', hint)
            self.assertNotIn('No company CA', hint)
        self.assertIn('Name resolution failed', self.hint('curl: (6) Could not resolve host: example.invalid'))

    def test_repository_and_integrity_errors_do_not_suggest_bypasses(self):
        self.assertIn('signature and validity checks enabled', self.hint(
            "The repository does not have a Release file"))
        for message in ('Original SUSE RPM checksum mismatch', 'NO_PUBKEY 12345678',
                        'package checksum is missing or incorrect', 'sha256sum: WARNING: 1 computed checksum did NOT match'):
            hint = self.hint(message)
            self.assertIn('integrity verification failed', hint)
            self.assertIn('Do not disable signatures', hint)

    def test_storage_hint_previews_cleanup_without_pruning(self):
        hint = self.hint('write: No space left on device')
        self.assertIn('python3 nrpe.py clean', hint)
        self.assertIn('does not prune Docker', hint)

    def test_only_categories_are_retained_when_observing_large_logs(self):
        diagnostics = FailureDiagnostics()
        for _ in range(10000):
            diagnostics.observe('ordinary build output ' * 10)
        self.assertIsNone(diagnostics.hint())
        self.assertEqual(diagnostics.categories, set())

    def test_diagnose_reads_log_without_docker_execution_or_echoing_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'example.log'
            path.write_text('private-token-example\nError: Could not complete SSL handshake. 1\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch('subprocess.Popen') as process:
                self.assertEqual(cli.main(['diagnose', str(path), '--context', 'nrpe']), 0)
            process.assert_not_called()
            self.assertIn('NRPE TLS negotiation failed', output.getvalue())
            self.assertNotIn('private-token-example', output.getvalue())

    def test_host_checksum_failure_persists_hint_and_never_runs_integration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'output/debian12'
            output.mkdir(parents=True)
            (output / 'nagios-nrpe-server_1+withargs1_amd64.deb').write_bytes(b'changed package')
            (output / 'SHA256SUMS').write_text('wrong checksum')
            with contextlib.redirect_stdout(io.StringIO()), patch(
                    'nrpe_cli.controller.check_docker', return_value='docker'), patch(
                    'nrpe_cli.controller.run_phase') as phase:
                self.assertEqual(controller.execute('test', ['debian12'], root), 1)
            phase.assert_not_called()
            report = state.reports(root)[0]
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['targets']['debian12']['test'], 'not run')
            self.assertIn('integrity verification failed', report['hint'])
