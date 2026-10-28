"""Presentation events preserve controller outcomes and full log evidence."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from nrpe_cli import controller, menu, progress, state


class ProgressTests(unittest.TestCase):
    def test_nested_observers_are_restored_and_frontend_errors_are_isolated(self):
        outer, inner = Mock(), Mock()
        with progress.listen(outer):
            progress.notify('first')
            with progress.listen(inner):
                progress.notify('inner')
            progress.notify('last')
        self.assertFalse(progress.notify('outside'))
        self.assertEqual(outer.call_count, 2)
        self.assertEqual(inner.call_count, 1)
        with progress.listen(Mock(side_effect=RuntimeError('UI unavailable'))):
            self.assertFalse(progress.notify('log', text='must remain printable'))
            self.assertFalse(progress.notify('after-error'))

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', side_effect=KeyboardInterrupt)
    def test_interruption_is_recorded_and_releases_lock_with_live_observer(self, phase, docker):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            ui = menu.LiveWorkflow('build')
            with progress.listen(ui.event):
                code = controller.execute('build', ['debian12'], root)
            self.assertEqual(code, 130)
            report = state.reports(root)[0]
            self.assertEqual(report['status'], 'interrupted')
            self.assertEqual(ui.run_id, report['id'])
            self.assertIn('build: interrupted', ui.render())
            self.assertFalse((root / '.nrpe/locks/debian12').exists())

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', return_value=42)
    def test_failed_target_and_unrun_targets_remain_distinct(self, phase, docker):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            ui = menu.LiveWorkflow('verify')
            with progress.listen(ui.event):
                self.assertEqual(controller.execute('verify', ['debian12', 'debian13'], root), 42)
            self.assertEqual(ui.states[('debian12', 'build')], 'failed')
            self.assertEqual(ui.states[('debian13', 'build')], 'not run')
            self.assertNotIn('%', ui.render())

    def test_recent_output_is_bounded_and_terminal_escapes_are_not_executed(self):
        ui = menu.LiveWorkflow('verify')
        for index in range(1000):
            ui.event('log', {'text': f'line {index}\x1b[2J\n'})
        self.assertEqual(len(ui.output.lines), 5)
        rendered = ui.render(50)
        self.assertNotIn('\x1b', rendered)
        self.assertIn('line 999', rendered)
        self.assertNotIn('line 100', rendered)
        self.assertTrue(all(len(line) <= 48 for line in rendered.splitlines()))

    def test_direct_command_fallback_preserves_dispatch_exit_code(self):
        dispatch = Mock(return_value=7)
        with patch('sys.stdout.isatty', return_value=False):
            self.assertEqual(menu.dispatch_workflow('test', ['test', 'debian12'], dispatch), (7, None))
        dispatch.assert_called_once_with(['test', 'debian12'])
