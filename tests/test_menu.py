"""Exercise menu navigation and its boundary with the existing controller."""

import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nrpe_cli import menu

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
except ImportError:
    Application = None


class MenuWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        # The browser resolves paths; Windows TEMP may use a short-name alias.
        self.root = Path(self.directory.name).resolve()
        # Windows Python needs these to initialize OS services in child processes.
        system_environment = {name: os.environ[name] for name in ('SystemRoot', 'WINDIR')
                              if name in os.environ}
        self.env = patch.dict(os.environ, system_environment, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'run', False])
    def test_review_cancellation_does_not_build(self, choose):
        self.assertIsNone(menu.workflow(self.root, 'verify'))

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'pull', 'run', True])
    def test_existing_output_requires_explicit_review_and_passes_rebuild(self, choose):
        output = self.root / 'output/debian12'
        output.mkdir(parents=True)
        (output / 'nagios-nrpe-server_test_amd64.deb').touch()
        self.assertEqual(menu.workflow(self.root, 'verify'),
                         ['verify', 'debian12', '--pull', '--rebuild'])
        self.assertIn('Rebuild existing packages: debian12', choose.call_args.args[0])

    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'run', True])
    def test_test_action_never_requests_rebuild(self, choose):
        self.assertEqual(menu.workflow(self.root, 'test'), ['test', 'debian12'])

    @patch('nrpe_cli.menu.choose', side_effect=[['sles15sp3'], 'run', True])
    def test_inherited_media_is_visible_and_forwarded(self, choose):
        with patch.dict(os.environ, {'SLES_MEDIA_DIR': str(self.root)}):
            self.assertEqual(menu.workflow(self.root, 'test'),
                             ['test', 'sles15sp3', '--sles-media', str(self.root)])
        self.assertIn(str(self.root), choose.call_args.args[0])

    @patch('nrpe_cli.media.validate_media', side_effect=RuntimeError('Wrong product'))
    @patch('nrpe_cli.menu.browse_directory')
    @patch('nrpe_cli.menu.choose', side_effect=[
        ['sles15sp3'], 'media', 'browse', None, 'run', True])
    def test_invalid_browsed_media_is_not_forwarded(self, choose, browse, validate):
        browse.return_value = self.root
        self.assertEqual(menu.workflow(self.root, 'test'), ['test', 'sles15sp3'])
        self.assertIn('Wrong product', choose.call_args_list[3].args[0])

    @patch('nrpe_cli.menu.choose', side_effect=['0'])
    def test_certificate_browser_selects_a_file(self, choose):
        certificate = self.root / 'company.cer'
        certificate.touch()
        (self.root / 'not-a-certificate.txt').touch()
        self.assertEqual(menu.browse_certificate(self.root), certificate)
        labels = [label for _, label in choose.call_args.args[1]]
        self.assertIn('company.cer', labels)
        self.assertNotIn('not-a-certificate.txt', labels)

    @patch('nrpe_cli.menu.browse_certificate')
    @patch('nrpe_cli.menu.choose', side_effect=[
        ['debian12'], 'certificate', 'browse', 'run', True])
    def test_selected_certificate_is_reviewed_and_forwarded(self, choose, browse):
        fixture = Path(__file__).parent / 'fixtures/test-ca.pem'
        browse.return_value = fixture
        self.assertEqual(menu.workflow(self.root, 'test'),
                         ['test', 'debian12', '--ca-cert', str(fixture)])
        self.assertIn(str(fixture), choose.call_args.args[0])

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.choose', side_effect=['doctor', 'status', 'quit'])
    def test_failure_returns_to_menu_and_next_action_runs(self, choose, pause):
        dispatch = Mock(side_effect=[1, 0])
        self.assertEqual(menu.run_menu(self.root, dispatch), 0)
        self.assertEqual([call.args[0] for call in dispatch.call_args_list],
                         [['doctor'], ['status']])
        self.assertEqual([call.args[0] for call in pause.call_args_list], [1, 0])

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.reports', return_value=[
        {'id': 'run1', 'action': 'test', 'status': 'passed'}])
    @patch('nrpe_cli.menu.choose', side_effect=['logs', 'run1', 'quit'])
    def test_log_selection_dispatches_exact_run(self, choose, reports, pause):
        dispatch = Mock(return_value=0)
        menu.run_menu(self.root, dispatch)
        dispatch.assert_called_once_with(['logs', '--run', 'run1'])

    @patch('nrpe_cli.menu.choose', side_effect=KeyboardInterrupt)
    def test_interrupt_exits_without_dispatch(self, choose):
        dispatch = Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(menu.run_menu(self.root, dispatch), 130)
        dispatch.assert_not_called()

    @patch('nrpe_cli.menu.choose', side_effect=['0', 'use'])
    def test_directory_browser_selects_a_child_without_text_input(self, choose):
        child = self.root / 'media'
        child.mkdir()
        self.assertEqual(menu.browse_directory(self.root), child)

    def test_optional_dependencies_are_not_imported_by_cli(self):
        # A separate interpreter ensures earlier UI tests cannot hide an eager
        # import. Direct commands must continue to work without the menu extra.
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c',
            "import sys; from nrpe_cli.cli import main; main(['status']); "
            "assert 'prompt_toolkit' not in sys.modules"],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipIf(Application is None, 'Install requirements-menu.txt for terminal input tests')
class TerminalNavigationTests(unittest.TestCase):
    def choose_with_keys(self, keys, **options):
        with create_pipe_input() as pipe:
            pipe.send_text(keys)
            def create(**kwargs):
                return Application(input=pipe, output=DummyOutput(), **kwargs)
            with patch('prompt_toolkit.application.Application', side_effect=create):
                return menu.choose('Test', [('one', 'First'), ('two', 'Second')], **options)

    def test_down_and_enter_select_second_item(self):
        self.assertEqual(self.choose_with_keys('\x1b[B\r'), 'two')

    def test_empty_multiselect_stays_open_until_space_selects(self):
        self.assertEqual(self.choose_with_keys('\r \x1b[B \r', multiple=True), ['one', 'two'])

    def test_select_all_shortcut(self):
        self.assertEqual(self.choose_with_keys('A\r', multiple=True), ['one', 'two'])

    def test_space_toggles_off_selected_item(self):
        self.assertEqual(self.choose_with_keys('  \x1b[B \r', multiple=True), ['two'])

    def test_escape_returns_without_selection(self):
        self.assertIsNone(self.choose_with_keys('\x1b'))

    def test_ctrl_d_ends_input(self):
        with self.assertRaises(EOFError):
            self.choose_with_keys('\x04')

    def test_ctrl_c_interrupts(self):
        with self.assertRaises(KeyboardInterrupt):
            self.choose_with_keys('\x03')

    def test_monochrome_navigation(self):
        with patch.dict(os.environ, {'NO_COLOR': '1'}):
            self.assertEqual(self.choose_with_keys('\r'), 'one')


if __name__ == '__main__':
    unittest.main()
