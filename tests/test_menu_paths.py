"""Regression coverage for optional typed paths alongside keyboard browsing."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nrpe_cli import menu


try:
    from prompt_toolkit import prompt as terminal_prompt
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
except ImportError:
    terminal_prompt = None


class MenuPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.certificate = self.root / 'Company Root.cer'
        self.certificate.touch()

    def test_quoted_windows_path_keeps_literal_backslashes_and_spaces(self):
        path = r'C:\Certificates\Company Root.cer'
        self.assertEqual(menu._path_text('  "' + path + '"  '), path)
        self.assertEqual(menu._path_text("'" + path + "'"), path)
        self.assertEqual(menu._path_text(r'\\server\share\root.cer'), r'\\server\share\root.cer')

    @patch('nrpe_cli.menu._prompt_path')
    def test_copy_as_path_accepts_quoted_absolute_file(self, prompt):
        prompt.return_value = '"' + str(self.certificate) + '"'
        self.assertEqual(menu.enter_path('Certificate', kind='file'), self.certificate)

    @patch('nrpe_cli.menu._prompt_path', return_value='Company Root.cer')
    def test_browser_relative_path_uses_current_directory(self, prompt):
        self.assertEqual(menu.enter_path('Certificate', base=self.root), self.certificate)

    @patch('nrpe_cli.menu._prompt_path', return_value='$NRPE_TEST_PATH/Company Root.cer')
    def test_environment_variable_expansion(self, prompt):
        with patch.dict(os.environ, {'NRPE_TEST_PATH': str(self.root)}):
            self.assertEqual(menu.enter_path('Certificate', kind='file'), self.certificate)

    @patch('nrpe_cli.menu.choose', return_value='retry')
    @patch('nrpe_cli.menu._prompt_path')
    def test_missing_path_can_be_corrected(self, prompt, choose):
        prompt.side_effect = [str(self.root / 'missing.cer'), str(self.certificate)]
        self.assertEqual(menu.enter_path('Certificate', kind='file'), self.certificate)
        choose.assert_called_once()

    @patch('nrpe_cli.menu.choose', return_value=None)
    @patch('nrpe_cli.menu._prompt_path')
    def test_directory_cannot_be_used_as_certificate_file(self, prompt, choose):
        prompt.return_value = str(self.root)
        self.assertIsNone(menu.enter_path('Certificate', kind='file'))
        self.assertIn('not a directory', choose.call_args.args[0])

    @patch('nrpe_cli.menu._prompt_path', return_value=None)
    def test_escape_cancels_path_entry(self, prompt):
        self.assertIsNone(menu.enter_path('Certificate'))

    @patch('nrpe_cli.menu.enter_path', return_value=None)
    @patch('nrpe_cli.menu.choose', side_effect=['path', '0'])
    def test_cancelled_entry_keeps_browser_in_current_directory(self, choose, enter):
        self.assertEqual(menu.browse_certificate(self.root), self.certificate)
        self.assertEqual(choose.call_args_list[0].args[0], choose.call_args_list[1].args[0])

    @patch('nrpe_cli.menu.enter_path')
    @patch('nrpe_cli.menu.choose', side_effect=['path', '0'])
    def test_entered_directory_opens_in_certificate_browser(self, choose, enter):
        child = self.root / 'certs'
        child.mkdir()
        selected = child / 'root.cer'
        selected.touch()
        enter.return_value = child
        self.assertEqual(menu.browse_certificate(self.root), selected)
        self.assertIn(str(child), choose.call_args.args[0])

    @patch('nrpe_cli.menu.enter_path')
    @patch('nrpe_cli.menu.choose', side_effect=[['debian12'], 'certificate', 'path', 'run', True])
    def test_direct_certificate_path_is_validated_and_forwarded(self, choose, enter):
        fixture = Path(__file__).parent / 'fixtures/test-ca.pem'
        enter.return_value = fixture
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(menu.workflow(self.root, 'test'),
                             ['test', 'debian12', '--ca-cert', str(fixture)])
        self.assertIn(str(fixture), choose.call_args.args[0])


@unittest.skipIf(terminal_prompt is None, 'Install requirements-menu.txt for terminal input tests')
class PathEntryTerminalTests(unittest.TestCase):
    def input_with_keys(self, keys):
        with create_pipe_input() as pipe:
            pipe.send_text(keys)
            def prompt(*args, **kwargs):
                from prompt_toolkit import PromptSession
                return PromptSession(input=pipe, output=DummyOutput()).prompt(*args, **kwargs)
            with patch('prompt_toolkit.prompt', side_effect=prompt):
                return menu._prompt_path('Certificate path')

    def test_typing_windows_path_preserves_backslashes(self):
        value = r'"C:\Certificates\Company Root.cer"'
        self.assertEqual(self.input_with_keys(value + '\r'), value)

    def test_escape_cancels_without_exiting_menu(self):
        self.assertIsNone(self.input_with_keys('unfinished path\x1b'))


if __name__ == '__main__':
    unittest.main()
