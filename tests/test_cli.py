import contextlib
import io
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from nrpe_cli import cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def test_help_explains_multiple_targets_without_repeating_choices(self):
        with self.assertRaises(SystemExit) as exit_status:
            cli.main(['verify', '--help'], self.root)
        self.assertEqual(exit_status.exception.code, 0)
        text = self.output.getvalue()
        self.assertIn('TARGET [TARGET ...]', text)
        self.assertIn('one or more targets:', text)
        self.assertEqual(text.count('debian11'), 1)
        self.assertNotIn('{debian11', text)

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_multiple_targets_are_deduplicated_in_order(self, execute):
        self.assertEqual(cli.main(['verify', 'debian14', 'debian12', 'debian14'], self.root), 0)
        self.assertEqual(execute.call_args.args[:2], ('verify', ['debian14', 'debian12']))

    @patch('nrpe_cli.cli.execute')
    def test_all_cannot_be_mixed_with_specific_targets(self, execute):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli.main(['build', 'all', 'debian12'])
        self.assertEqual(error.exception.code, 2)
        execute.assert_not_called()

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_all_selects_corrected_sp3_target_in_order(self, execute):
        self.assertEqual(cli.main(['verify', 'all'], self.root), 0)
        self.assertEqual(execute.call_args.args[:2],
                         ('verify', ['debian11', 'debian12', 'debian13', 'debian14', 'sles12sp3']))

    @patch('nrpe_cli.cli.execute')
    def test_previous_service_pack_is_not_silently_reinterpreted(self, execute):
        for target in ('sles15sp3', 'sles15sp4', 'sles12sp5'):
            with self.subTest(target=target), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    cli.main(['verify', target], self.root)
                self.assertEqual(error.exception.code, 2)
                execute.assert_not_called()

    @patch('sys.stdin.isatty', return_value=False)
    @patch('builtins.input', side_effect=AssertionError('Must not prompt'))
    @patch('nrpe_cli.cli.execute')
    def test_noninteractive_no_arguments_prints_help(self, execute, user_input, tty):
        self.assertEqual(cli.main([], self.root), 0)
        self.assertIn('usage:', self.output.getvalue())
        execute.assert_not_called()

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    @patch('nrpe_cli.menu.run_menu', return_value=0)
    def test_interactive_session_uses_shared_command_dispatch(self, menu, out_tty, in_tty):
        self.assertEqual(cli.main([], self.root), 0)
        root, dispatch = menu.call_args.args
        self.assertEqual(root, self.root)
        with patch('nrpe_cli.cli.execute', return_value=7) as execute:
            self.assertEqual(dispatch(['test', 'debian12']), 7)
        self.assertEqual(execute.call_args.args[:2], ('test', ['debian12']))

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    @patch('nrpe_cli.menu.run_menu', side_effect=EOFError)
    def test_end_of_input_exits_without_work(self, menu, out_tty, in_tty):
        self.assertEqual(cli.main([], self.root), 0)

    @patch('nrpe_cli.cli.check_docker', return_value='docker')
    @patch('nrpe_cli.cli.subprocess.run')
    def test_doctor_validates_both_compose_files(self, run, check):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        self.assertEqual(cli.doctor(cli.ROOT), 0)
        self.assertEqual([call.args[0][3] for call in run.call_args_list],
                         ['compose.yaml', 'compose.test.yaml'])

    @patch('sys.stdin.isatty', return_value=False)
    @patch('nrpe_cli.cli.execute')
    def test_existing_output_is_not_silently_rebuilt_in_automation(self, execute, tty):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'output/debian12').mkdir(parents=True)
            (root / 'output/debian12/nagios-nrpe-server_test_amd64.deb').touch()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(['build', 'debian12'], root), 1)
            execute.assert_not_called()
            self.assertEqual(cli.main(['build', 'debian12', '--rebuild', '--pull'], root),
                             execute.return_value)
            self.assertEqual(execute.call_args.kwargs, {'rebuild': True, 'pull': True})

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    @patch('builtins.input', return_value='')
    @patch('nrpe_cli.cli.execute')
    def test_default_confirmation_keeps_existing_packages(self, execute, user_input, out_tty, in_tty):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'output/debian12').mkdir(parents=True)
            (root / 'output/debian12/nagios-nrpe-server_test_amd64.deb').touch()
            self.assertEqual(cli.main(['verify', 'debian12'], root), 0)
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
