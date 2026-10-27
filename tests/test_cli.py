import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from nrpe_cli import cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_multiple_targets_are_deduplicated_in_order(self, execute):
        self.assertEqual(cli.main(['verify', 'debian14', 'debian12', 'debian14']), 0)
        self.assertEqual(execute.call_args.args[:2], ('verify', ['debian14', 'debian12']))

    @patch('nrpe_cli.cli.execute')
    def test_all_cannot_be_mixed_with_specific_targets(self, execute):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli.main(['build', 'all', 'debian12'])
        self.assertEqual(error.exception.code, 2)
        execute.assert_not_called()

    @patch('sys.stdin.isatty', return_value=False)
    @patch('builtins.input', side_effect=AssertionError('Must not prompt'))
    @patch('nrpe_cli.cli.execute')
    def test_noninteractive_no_arguments_prints_help(self, execute, user_input, tty):
        self.assertEqual(cli.main([]), 0)
        self.assertIn('usage:', self.output.getvalue())
        execute.assert_not_called()

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    @patch('builtins.input', side_effect=['invalid', '1', '4 1', '1 3'])
    @patch('nrpe_cli.cli.execute', return_value=0)
    def test_interactive_menu_validates_action_and_targets(self, execute, user_input, out_tty, in_tty):
        self.assertEqual(cli.main([]), 0)
        self.assertEqual(execute.call_args.args[:2], ('verify', ['debian12', 'debian14']))

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    @patch('builtins.input', side_effect=EOFError)
    def test_end_of_input_exits_without_work(self, user_input, out_tty, in_tty):
        self.assertEqual(cli.main([]), 0)

    @patch('nrpe_cli.cli.check_docker', return_value='docker')
    @patch('nrpe_cli.cli.subprocess.run')
    def test_doctor_validates_both_compose_files(self, run, check):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        self.assertEqual(cli.doctor(cli.ROOT), 0)
        self.assertEqual([call.args[0][3] for call in run.call_args_list],
                         ['compose.yaml', 'compose.test.yaml'])


if __name__ == '__main__':
    unittest.main()
