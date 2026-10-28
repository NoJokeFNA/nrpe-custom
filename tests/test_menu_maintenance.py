"""Menu maintenance must reuse CLI checks and require previewed consent."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from nrpe_cli import menu


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.candidate = [(self.root / '.nrpe/runs/old', 42)]

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.choose', side_effect=['preview', False, None])
    @patch('nrpe_cli.cleanup.plan')
    def test_cancel_after_preview_never_applies(self, plan, choose, pause):
        plan.return_value = self.candidate
        dispatch = Mock(return_value=0)
        menu.cleanup_menu(self.root, dispatch)
        dispatch.assert_called_once_with(['clean', '--older-than', '30', '--keep-runs', '5'])
        self.assertIs(choose.call_args_list[1].args[1][0][0], False)

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.choose', side_effect=['preview', True, None])
    @patch('nrpe_cli.cleanup.plan')
    def test_only_explicit_approval_applies_the_same_options(self, plan, choose, pause):
        plan.return_value = self.candidate
        dispatch = Mock(return_value=0)
        menu.cleanup_menu(self.root, dispatch)
        before, after = [call.args[0] for call in dispatch.call_args_list]
        self.assertNotIn('--apply', before)
        self.assertEqual(after, before + ['--apply'])
        self.assertEqual(plan.call_count, 2)

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.choose', side_effect=['preview', True, None, None])
    @patch('nrpe_cli.cleanup.plan')
    def test_changed_candidates_require_another_preview(self, plan, choose, pause):
        plan.side_effect = [self.candidate, []]
        dispatch = Mock(return_value=0)
        menu.cleanup_menu(self.root, dispatch)
        self.assertEqual(dispatch.call_count, 1)
        self.assertIn('changed', choose.call_args_list[2].args[0])

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.choose', side_effect=['preview', None])
    @patch('nrpe_cli.cleanup.plan')
    def test_failed_preview_never_offers_deletion(self, plan, choose, pause):
        plan.return_value = self.candidate
        dispatch = Mock(return_value=1)
        menu.cleanup_menu(self.root, dispatch)
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(choose.call_count, 2)

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.enter_path')
    @patch('nrpe_cli.menu.choose', side_effect=['file', 'path', 'nrpe', None])
    def test_nrpe_diagnosis_uses_local_file_and_explicit_context(self, choose, enter, pause):
        path = self.root / 'log with spaces.txt'
        enter.return_value = path
        dispatch = Mock(return_value=0)
        menu.diagnostics_menu(self.root, dispatch)
        dispatch.assert_called_once_with(['diagnose', str(path), '--context', 'nrpe'])

    @patch('nrpe_cli.menu.pause')
    @patch('nrpe_cli.menu.reports')
    @patch('nrpe_cli.menu.choose', side_effect=['target:debian12', None])
    @patch('nrpe_cli.menu.view_text')
    def test_results_show_recorded_target_identity_without_rerunning(self, viewer, choose, reports, pause):
        reports.return_value = [{'id':'run1', 'status':'failed', 'targets':{
            'debian12':{'build':'passed','package':'passed','test':'failed','artifact':{'sha256':'example'}}}}]
        dispatch = Mock()
        menu.result_menu(self.root, dispatch, 'run1', 42)
        self.assertIn('example', viewer.call_args.args[1])
        dispatch.assert_not_called()
