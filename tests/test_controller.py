import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from nrpe_cli import cli, controller, state
from nrpe_cli.targets import TARGET_CONFIG


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def package(self, target='debian12', data=b'package content'):
        directory = self.root / 'output' / target
        directory.mkdir(parents=True, exist_ok=True)
        config = TARGET_CONFIG[target]
        name = config['prefix'] + '4.1.3-1+withargs1' + config['suffix']
        (directory / name).write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        (directory / 'SHA256SUMS').write_text(f'{digest}  {name}\n')
        if target == 'sles15sp3':
            helper_name = 'system-user-nagios-1.0.0-0.noarch.rpm'
            helper_data = b'user package'
            (directory / helper_name).write_bytes(helper_data)
            with (directory / 'SHA256SUMS').open('a') as checksums:
                checksums.write(hashlib.sha256(helper_data).hexdigest() + '  ' + helper_name + '\n')
        return directory / name

    def report(self):
        return state.reports(self.root)[0]

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase')
    def test_verify_runs_build_and_test_in_order_and_binds_hash(self, phase, docker):
        for target in state.TARGETS:
            self.package(target)
        phase.return_value = 0
        self.assertEqual(controller.execute('verify', list(state.TARGETS), self.root, rebuild=True), 0)
        self.assertEqual([(c.args[3], c.args[4]) for c in phase.call_args_list],
                         [(t, p) for t in state.TARGETS for p in ('build', 'test')])
        for target, result in self.report()['targets'].items():
            self.assertEqual(result['test'], 'passed')
            self.assertEqual(result['artifact'], state.artifact(self.root, target))

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', return_value=42)
    def test_failed_build_never_tests_stale_package(self, phase, docker):
        self.package()
        self.assertEqual(controller.execute('verify', ['debian12', 'debian13'], self.root, rebuild=True), 42)
        self.assertEqual(phase.call_count, 1)
        report = self.report()
        self.assertEqual(report['targets']['debian12']['test'], 'not run')
        self.assertEqual(report['targets']['debian13']['build'], 'not run')
        self.assertFalse((self.root / '.nrpe/locks/debian12').exists())

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', return_value=7)
    def test_integration_failure_preserves_exit_code_and_stops(self, phase, docker):
        self.package()
        self.assertEqual(controller.execute('test', ['debian12', 'debian13'], self.root), 7)
        self.assertEqual(phase.call_count, 1)
        self.assertEqual(self.report()['targets']['debian12']['test'], 'failed')

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase')
    def test_missing_artifact_fails_before_test_image_build(self, phase, docker):
        self.assertEqual(controller.execute('test', ['debian12'], self.root), 1)
        phase.assert_not_called()
        self.assertEqual(self.report()['targets']['debian12']['package'], 'failed')

    def test_lock_excludes_other_runs_and_preserves_owner(self):
        with state.target_lock(self.root, 'debian12', 'first') as lock:
            with self.assertRaisesRegex(RuntimeError, 'locked'):
                with state.target_lock(self.root, 'debian12', 'second'):
                    self.fail('Acquired existing lock')
            self.assertEqual(json.loads((lock / 'owner.json').read_text())['run'], 'first')
        self.assertFalse(lock.exists())

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', side_effect=KeyboardInterrupt)
    def test_interrupt_records_outcome_and_releases_lock(self, phase, docker):
        self.assertEqual(controller.execute('build', ['debian12'], self.root), 130)
        self.assertEqual(self.report()['status'], 'interrupted')
        self.assertEqual(self.report()['targets']['debian12']['build'], 'interrupted')
        self.assertFalse((self.root / '.nrpe/locks/debian12').exists())

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', return_value=0)
    def test_replaced_package_does_not_inherit_passed_test(self, phase, docker):
        self.package()
        controller.execute('test', ['debian12'], self.root)
        self.output.truncate(0)
        self.output.seek(0)
        self.package(data=b'new package')
        cli.show_status(self.root)
        self.assertIn('not tested', self.output.getvalue())
        self.assertNotIn('passed (run', self.output.getvalue())

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase')
    def test_package_changed_during_test_invalidates_result(self, phase, docker):
        self.package()
        def replace(*args, **kwargs):
            self.package(data=b'replaced during test')
            return 0
        phase.side_effect = replace
        self.assertEqual(controller.execute('test', ['debian12'], self.root), 1)
        self.assertEqual(self.report()['targets']['debian12']['test'], 'failed')

    def test_bad_checksum_is_rejected(self):
        package = self.package()
        package.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RuntimeError, 'checksum'):
            state.artifact(self.root, 'debian12')

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase', return_value=0)
    def test_changed_companion_package_invalidates_sles_test_status(self, phase, docker):
        self.package('sles15sp3')
        self.assertEqual(controller.execute('test', ['sles15sp3'], self.root), 0)
        original = state.artifact(self.root, 'sles15sp3')
        directory = self.root / 'output/sles15sp3'
        helper = directory / 'system-user-nagios-1.0.0-0.noarch.rpm'
        helper.write_bytes(b'changed user package')
        checksums = directory / 'SHA256SUMS'
        server_line = checksums.read_text().splitlines()[0]
        checksums.write_text(server_line + '\n' + hashlib.sha256(helper.read_bytes()).hexdigest()
                             + '  ' + helper.name + '\n')
        current = state.artifact(self.root, 'sles15sp3')
        self.assertEqual(original['sha256'], current['sha256'])
        self.assertNotEqual(original['companions'], current['companions'])
        self.output.truncate(0)
        self.output.seek(0)
        cli.show_status(self.root)
        line = next(line for line in self.output.getvalue().splitlines() if line.startswith('sles15sp3'))
        self.assertIn('not tested', line)

    @patch('nrpe_cli.controller.check_docker', return_value='docker')
    @patch('nrpe_cli.controller.run_phase')
    def test_existing_package_requires_explicit_rebuild(self, phase, docker):
        package = self.package()
        self.assertEqual(controller.execute('build', ['debian12'], self.root), 1)
        phase.assert_not_called()
        self.assertEqual(package.read_bytes(), b'package content')

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_pull_updates_base_before_running_without_rebuilding_twice(self, popen, run):
        def process(*args, **kwargs):
            child = MagicMock()
            child.stdout = io.StringIO('cached layer\n')
            child.wait.return_value = 0
            child.poll.return_value = 0
            return child
        popen.side_effect = process
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with state.target_lock(self.root, 'debian12', 'pull') as lock:
            result = controller.run_phase('docker', self.root, 'pull', 'debian12',
                                          'build', io.StringIO(), lock, pull=True)
        self.assertEqual(result, 0)
        commands = [call.args[0] for call in popen.call_args_list]
        self.assertEqual(commands[0][-3:], ['build', '--pull', 'debian12'])
        self.assertNotIn('--build', commands[1])

    @patch('nrpe_cli.cli.check_docker', side_effect=AssertionError('Must be offline'))
    def test_status_and_logs_work_without_docker(self, docker):
        self.assertEqual(cli.main(['status'], self.root), 0)
        directory = self.root / '.nrpe/runs/example'
        directory.mkdir(parents=True)
        state.save_report(directory, {'schema': 1, 'id': 'example', 'action': 'test',
                                     'status': 'failed', 'error': 'Test failure'})
        (directory / 'run.log').write_text('Container diagnostics\n')
        self.assertEqual(cli.main(['logs', '--last'], self.root), 0)
        self.assertIn('Container diagnostics', self.output.getvalue())
        self.assertIn('Test failure', self.output.getvalue())

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_runner_streams_logs_returns_code_and_cleans_only_its_container(self, popen, run):
        process = MagicMock()
        process.stdout = io.StringIO('diagnostic output\n')
        process.wait.return_value = 42
        process.poll.return_value = 42
        popen.return_value = process
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with state.target_lock(self.root, 'debian12', 'run') as lock:
            log = io.StringIO()
            code = controller.run_phase('docker', self.root, 'run', 'debian12', 'build', log, lock)
        self.assertEqual(code, 42)
        self.assertIn('diagnostic output', log.getvalue())
        self.assertEqual(run.call_args.args[0], ['docker', 'rm', '-f', 'nrpe-run-debian12-build'])
        self.assertEqual(popen.call_args.kwargs['cwd'], self.root)

    @patch('nrpe_cli.controller.subprocess.run')
    @patch('nrpe_cli.controller.subprocess.Popen')
    def test_failed_cleanup_retains_target_lock(self, popen, run):
        process = MagicMock()
        process.stdout = io.StringIO('')
        process.poll.return_value = 0
        process.wait.return_value = 0
        popen.return_value = process
        run.return_value = subprocess.CompletedProcess([], 1, '', 'Docker disconnected')
        with self.assertRaisesRegex(RuntimeError, 'lock retained'):
            with state.target_lock(self.root, 'debian12', 'run') as lock:
                controller.run_phase('docker', self.root, 'run', 'debian12', 'test', io.StringIO(), lock)
        self.assertTrue((lock / 'cleanup-required').exists())


if __name__ == '__main__':
    unittest.main()
