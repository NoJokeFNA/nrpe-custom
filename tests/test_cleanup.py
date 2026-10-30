"""Destructive cleanup must preserve active work, current packages and evidence."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from nrpe_cli import cleanup, cli, state


class CleanupFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def age(self, path):
        if path.is_dir():
            for child in path.rglob('*'):
                os.utime(child, (1, 1))
        os.utime(path, (1, 1))

    def report(self, number, status='passed', artifact=None):
        run_id = f'202001{number:02}T000000-abcdef01'
        directory = self.root / '.nrpe/runs' / run_id
        directory.mkdir(parents=True)
        report = {'schema': 1, 'id': run_id, 'action': 'test', 'started': f'2020-01-{number:02}T00:00:00+00:00',
                  'finished': f'2020-01-{number:02}T01:00:00+00:00', 'status': status,
                  'targets': {'debian12': {'test': 'passed', 'artifact': artifact}}}
        (directory / 'report.json').write_text(json.dumps(report))
        (directory / 'run.log').write_text('original log')
        self.age(directory)
        return directory



class CleanupTests(CleanupFixture, unittest.TestCase):
    def test_empty_preview_creates_no_state_and_needs_no_docker(self):
        with patch('nrpe_cli.cleanup.check_docker') as docker:
            self.assertEqual(cli.main(['clean'], self.root), 0)
        self.assertEqual(list(self.root.iterdir()), [])
        docker.assert_not_called()

    def test_preview_then_apply_preserves_latest_and_current_package_evidence(self):
        current = {'file': 'current.deb', 'sha256': 'a' * 64}
        matching = self.report(1, artifact=current)
        expired = self.report(2)
        latest = self.report(3, status='failed')
        output = self.root / 'output/debian12'
        output.mkdir(parents=True)
        package = output / 'current.deb'
        package.write_bytes(b'untouched package')
        with patch('nrpe_cli.cleanup.artifact', return_value=current):
            cleanup.clean(self.root, older_than=1, keep_runs=0)
            self.assertTrue(expired.exists())
            cleanup.clean(self.root, older_than=1, keep_runs=0, apply=True)
        self.assertTrue(matching.exists())
        self.assertTrue(latest.exists())
        self.assertFalse(expired.exists())
        self.assertEqual(package.read_bytes(), b'untouched package')

    def test_recent_files_running_interrupted_metadata_and_unknown_files_are_preserved(self):
        running = self.report(1, status='running')
        unknown = self.report(2)
        (unknown / 'operator-notes.txt').write_text('keep me')
        self.age(unknown)
        changed = self.report(3)
        (changed / 'run.log').write_text('recently updated')
        invalid = self.report(4)
        metadata = json.loads((invalid / 'report.json').read_text())
        metadata['finished'] = 'invalid timestamp'
        (invalid / 'report.json').write_text(json.dumps(metadata))
        self.age(invalid)
        self.report(5)
        cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue(all(path.exists() for path in (running, unknown, changed, invalid)))

    def test_retention_count_protects_recent_history(self):
        directories = [self.report(n) for n in range(1, 8)]
        cleanup.clean(self.root, keep_runs=5, apply=True)
        self.assertFalse(directories[0].exists())
        self.assertFalse(directories[1].exists())
        self.assertTrue(all(p.exists() for p in directories[2:]))

    def test_runtime_only_test_does_not_discard_full_verify_evidence(self):
        current = {'file': 'current.deb', 'sha256': 'a' * 64}
        verified = self.report(1, artifact=current)
        data = json.loads((verified / 'report.json').read_text())
        data['action'] = 'verify'
        data['targets']['debian12'].update(build='passed', package='passed')
        (verified / 'report.json').write_text(json.dumps(data))
        self.age(verified)
        expired = self.report(2)
        runtime = self.report(3, artifact=current)
        with patch('nrpe_cli.cleanup.artifact', return_value=current):
            cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue(verified.exists())
        self.assertTrue(runtime.exists())
        self.assertFalse(expired.exists())

    def test_cleanup_keeps_all_package_outputs_including_unknown_directories(self):
        for target in ('sles12sp3', 'debian12', 'unknown-platform'):
            directory = self.root / 'output' / target
            directory.mkdir(parents=True)
            (directory / 'package.bin').write_bytes(b'keep package')
            self.age(directory)
        expired = self.report(1)
        self.report(2)
        cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertFalse(expired.exists())
        for target in ('sles12sp3', 'debian12', 'unknown-platform'):
            self.assertEqual((self.root / 'output' / target / 'package.bin').read_bytes(), b'keep package')

    def test_active_or_interrupted_target_lock_blocks_all_deletion(self):
        expired = self.report(1)
        self.report(2)
        lock = self.root / '.nrpe/locks/sles12sp3'
        lock.mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, 'target locks'):
            cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue(expired.exists())
        self.assertTrue(lock.exists())

    def test_maintenance_prevents_new_target_run_and_retained_lock_is_not_removed(self):
        with state.maintenance_guard(self.root):
            with self.assertRaisesRegex(RuntimeError, 'maintenance'):
                with state.target_lock(self.root, 'debian12', 'other'):
                    self.fail('Target started during cleanup')
            self.assertTrue((self.root / '.nrpe/locks/maintenance').exists())
        self.assertFalse((self.root / '.nrpe/locks/debian12').exists())

    def test_symlinked_evidence_is_rejected_without_touching_destination(self):
        expired = self.report(1)
        self.report(2)
        outside = self.root / 'operator-data'
        outside.write_text('keep')
        (expired / 'run.log').unlink()
        try:
            (expired / 'run.log').symlink_to(outside)
        except OSError:
            self.skipTest('Host does not permit symlink creation')
        with self.assertRaisesRegex(RuntimeError, 'links'):
            cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertEqual(outside.read_text(), 'keep')

    def test_linked_state_root_is_rejected(self):
        destination = self.root / 'operator-state'
        destination.mkdir()
        try:
            (self.root / '.nrpe').symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest('Host does not permit symlink creation')
        with self.assertRaisesRegex(RuntimeError, 'links'):
            cleanup.clean(self.root, apply=True)
        self.assertTrue(destination.exists())

    def test_mounted_run_is_not_traversed_or_deleted(self):
        expired = self.report(1)
        self.report(2)
        with patch('nrpe_cli.cleanup.os.path.ismount', side_effect=lambda path: Path(path) == expired):
            with self.assertRaisesRegex(RuntimeError, 'mounted'):
                cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue((expired / 'run.log').exists())

    def test_changed_plan_is_rejected_before_deletion(self):
        expired = self.report(1)
        self.report(2)
        real_plan = cleanup.plan
        with patch('nrpe_cli.cleanup.plan', side_effect=[real_plan(self.root, 30, 0), []]):
            with self.assertRaisesRegex(RuntimeError, 'candidates changed'):
                cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue(expired.exists())

    def test_invalid_retention_is_a_cli_error_without_deletion(self):
        expired = self.report(1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['clean', '--older-than', '-1', '--apply'], self.root), 1)
        self.assertTrue(expired.exists())

    def test_corrupt_metadata_is_kept_instead_of_guessed_as_an_old_run(self):
        cases = ({'action': 'operator-backup'}, {'started': 123}, {'targets': None},
                 {'targets': {'unknown-system': {}}}, {'started': 'invalid'})
        directories = []
        for number, change in enumerate(cases, 1):
            directory = self.report(number)
            data = json.loads((directory / 'report.json').read_text())
            data.update(change)
            (directory / 'report.json').write_text(json.dumps(data))
            self.age(directory)
            directories.append(directory)
        self.report(8)
        cleanup.clean(self.root, keep_runs=0, apply=True)
        self.assertTrue(all(directory.exists() for directory in directories))


class ImageCleanupTests(CleanupFixture, unittest.TestCase):
    def test_non_project_images_and_wildcards_are_rejected_before_docker(self):
        with patch('nrpe_cli.cleanup.check_docker') as docker:
            for name in ('python:3.13-slim', 'nrpe-custom-builder', '*', 'sha256:abc'):
                with self.assertRaisesRegex(RuntimeError, 'explicit nrpe-custom'):
                    cleanup.clean(self.root, images=[name], apply=True)
        docker.assert_not_called()

    @patch('nrpe_cli.cleanup.check_docker', return_value='docker')
    @patch('nrpe_cli.cleanup.subprocess.check_output', return_value='')
    @patch('nrpe_cli.cleanup.subprocess.run')
    def test_selected_image_preview_does_not_remove_and_apply_never_forces(self, run, containers, docker):
        image = 'nrpe-custom-builder:sles12sp3'
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps([{'Id': 'sha256:' + 'a' * 64}]), '')
        cleanup.clean(self.root, images=[image])
        self.assertFalse(any('rm' in call.args[0] for call in run.call_args_list))
        cleanup.clean(self.root, images=[image], apply=True)
        self.assertEqual(run.call_args.args[0], ['docker', 'image', 'rm', image])

    @patch('nrpe_cli.cleanup.check_docker', return_value='docker')
    @patch('nrpe_cli.cleanup.subprocess.check_output', return_value='container-id\n')
    @patch('nrpe_cli.cleanup.subprocess.run')
    def test_in_use_image_blocks_file_cleanup_too(self, run, containers, docker):
        expired = self.report(1)
        self.report(2)
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps([{'Id': 'sha256:' + 'a' * 64}]), '')
        with self.assertRaisesRegex(RuntimeError, 'used by'):
            cleanup.clean(self.root, keep_runs=0, images=['nrpe-custom-builder:sles12sp3'], apply=True)
        self.assertTrue(expired.exists())
