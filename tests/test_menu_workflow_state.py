"""Back navigation and session CA choices must not dispatch unintended work."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nrpe_cli import cli, menu


class StatefulWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'pull', None, ['debian12'], 'run', 'back', 'run', True])
    def test_back_preserves_targets_and_options_and_review_defaults_to_cancel(self, choose):
        session = menu.new_session()
        session.update(certificate=None, certificate_source='none')
        self.assertEqual(menu.workflow(self.root, 'verify', session), ['verify', 'debian12', '--pull'])
        target_calls = [call for call in choose.call_args_list if call.args[0].startswith('1/3')]
        self.assertEqual(target_calls[1].kwargs['selected'], ['debian12'])
        reviews = [call for call in choose.call_args_list if call.args[0].startswith('3/3')]
        self.assertEqual(reviews[-1].args[1][0][0], False)
        self.assertEqual(session['targets'], ['debian12'])
        self.assertTrue(session['pull'])

    @patch.dict(os.environ, {'NRPE_CA_CERT': '/missing/company-ca.pem'})
    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'certificate', 'none', 'run', True])
    def test_explicit_no_ca_overrides_environment_for_this_session(self, choose):
        session = menu.new_session()
        self.assertEqual(menu.workflow(self.root, 'test', session), ['test', 'debian12', '--no-ca-cert'])
        self.assertEqual(session['certificate_source'], 'disabled')
        self.assertEqual(os.environ['NRPE_CA_CERT'], '/missing/company-ca.pem')
        with patch('nrpe_cli.menu.choose', side_effect=[['debian13'], 'run', True]):
            self.assertEqual(menu.workflow(self.root, 'test', session), ['test', 'debian13', '--no-ca-cert'])

    @patch.dict(os.environ, {'NRPE_CA_CERT': '/missing/company-ca.pem'})
    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_cli_no_ca_does_not_validate_or_forward_environment_certificate(self, execute):
        self.assertEqual(cli.main(['test', 'debian12', '--no-ca-cert'], self.root), 0)
        self.assertNotIn('ca_cert', execute.call_args.kwargs)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(['test', 'debian12', '--no-ca-cert', '--ca-cert', 'other.pem'], self.root)

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'run', True])
    def test_existing_package_tests_hide_build_refresh_even_if_previously_enabled(self, choose):
        session = menu.new_session()
        session.update(pull=True, certificate=None, certificate_source='none')
        self.assertEqual(menu.workflow(self.root, 'test', session), ['test', 'debian12'])
        options = choose.call_args_list[1].args[1]
        self.assertNotIn('pull', [option[0] for option in options])

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'run', None, None, None])
    def test_invalid_environment_ca_cannot_reach_run_confirmation(self, choose):
        session = menu.new_session()
        session.update(certificate='/missing/company.pem', certificate_source='environment')
        self.assertIsNone(menu.workflow(self.root, 'verify', session))
        self.assertTrue(any('Invalid CA certificate' in call.args[0] for call in choose.call_args_list))
        self.assertFalse(any(call.args[0].startswith('3/3') for call in choose.call_args_list))
