"""Filtering, retained focus and a compact browser with many drive roots."""
import ctypes
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


class BrowserTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    @patch('nrpe_cli.menu.is_windows', return_value=True)
    @patch('nrpe_cli.menu.windows_drives')
    def test_zero_one_and_twelve_drives_have_their_own_selector(self, drives, platform):
        for count in (0, 1, 12):
            roots = [f'{chr(65 + index)}:\\' for index in range(count)]
            drives.return_value = roots
            with patch('nrpe_cli.menu.choose', return_value=None) as choose:
                menu.drive_selector(self.root)
            options = choose.call_args.args[1]
            self.assertEqual([item[0] for item in options[:-1]], roots)
            self.assertEqual(len(options), count + 1)

    @patch('nrpe_cli.menu.is_windows', return_value=True)
    @patch('nrpe_cli.menu.windows_drives', side_effect=AssertionError('Do not enumerate inside folders'))
    @patch('nrpe_cli.menu.drive_selector', return_value=None)
    @patch('nrpe_cli.menu.choose', side_effect=['drives', None])
    def test_cancel_drive_selection_retains_directory_and_browser_state(self, choose, selector, drives, platform):
        (self.root / 'company.crt').touch()
        self.assertIsNone(menu.browse_certificate(self.root))
        first, second = choose.call_args_list
        self.assertIs(first.kwargs['state'], second.kwargs['state'])
        self.assertEqual(first.args[0], second.args[0])
        self.assertEqual([value for value, *_ in first.args[1]].count('drives'), 1)
        self.assertIn('company.crt', [label for _, label in first.args[1]])
        selector.assert_called_once()

    @patch('nrpe_cli.menu.is_windows', return_value=True)
    @patch('nrpe_cli.menu.drive_selector', return_value='unavailable-root')
    @patch('nrpe_cli.menu.choose', side_effect=['drives', None, None])
    def test_unavailable_drive_returns_to_original_directory(self, choose, selector, platform):
        self.assertIsNone(menu.browse_directory(self.root))
        first, error, last = choose.call_args_list
        self.assertIn('Cannot open', error.args[0])
        self.assertEqual(first.args[0], last.args[0])
        self.assertIs(first.kwargs['state'], last.kwargs['state'])

    @patch('nrpe_cli.menu.is_windows', return_value=True)
    def test_drive_enumeration_uses_os_mask_without_accessing_roots(self, platform):
        library = Mock()
        library.kernel32.GetLogicalDrives.return_value = (1 << 12) - 1
        with patch.object(ctypes, 'windll', library, create=True):
            self.assertEqual(len(menu.windows_drives()), 12)
        library.kernel32.GetLogicalDrives.assert_called_once_with()


@unittest.skipIf(Application is None, 'Install requirements-menu.txt')
class NavigationTests(unittest.TestCase):
    def choose(self, keys, **kwargs):
        with create_pipe_input() as pipe:
            pipe.send_text(keys)
            def create(**options):
                return Application(input=pipe, output=DummyOutput(), **options)
            with patch('prompt_toolkit.application.Application', side_effect=create):
                return menu.choose('Directory', [('one', 'First'), ('two', 'Second'), ('qdrive', 'Q drive')], **kwargs)

    def test_filter_selects_matching_entry_and_can_type_q(self):
        self.assertEqual(self.choose('/second\r'), 'two')
        self.assertEqual(self.choose('/q\r'), 'qdrive')

    def test_focus_is_retained_after_back(self):
        state = {}
        self.assertIsNone(self.choose('\x1b[Bq', state=state))
        self.assertEqual(self.choose('\r', state=state), 'two')

    def test_select_all_only_selects_visible_matches(self):
        self.assertEqual(self.choose('/second\tA\r', multiple=True), ['two'])
        self.assertEqual(self.choose(' /second\tA\r', multiple=True), ['one', 'two'])

    def test_empty_filter_and_escape_are_safe(self):
        self.assertIsNone(self.choose('/not-found\x1b\x1b'))
